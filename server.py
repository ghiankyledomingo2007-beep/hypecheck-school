"""HypeCheck school app: feature parity with personal app, using MySQL 8.0.16+."""
import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
import re
import sys
import ssl
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen
import base64
import secrets
import time

import pymysql
import pymysql.cursors

import auth

ROOT = Path(__file__).resolve().parent
TABLES = ['users', 'categories', 'wishlist_items', 'decision_logs', 'expenses', 'monthly_budgets']

# MySQL error codes that mean "this data breaks a rule", answered with a 400 instead of a 500.
RULE_MESSAGES = {
    1048: 'A required value is missing.',
    1062: 'That already exists.',
    1264: 'That number is out of range.',
    1292: 'That date or time is not valid.',
    1366: 'That value has the wrong type.',
    1406: 'That text is too long.',
    1451: 'Something else still depends on this record.',
    1452: 'That refers to something that does not exist.',
    3819: 'That value breaks one of the database rules.',
}


def load_env(path=ROOT / '.env'):
    """Read KEY=value lines from .env into the environment (real env vars win)."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"\''))  # `vercel env pull` quotes its values


load_env()


def db_config():
    """MySQL settings: one HYPECHECK_DATABASE_URL (hosted MySQL) or the separate HYPECHECK_DB_* values (local)."""
    url = os.environ.get('HYPECHECK_DATABASE_URL', '')
    if url:
        parts = urlparse(url)
        if parts.scheme not in ('mysql', 'mysql+pymysql'):
            raise SystemExit('HYPECHECK_DATABASE_URL must start with mysql://')
        config = {
            'host': parts.hostname,
            'port': parts.port or 3306,
            'user': unquote(parts.username or ''),
            'password': unquote(parts.password or ''),
            'database': parts.path.lstrip('/') or 'hypecheck',
        }
        ssl_mode = (parse_qs(parts.query).get('ssl-mode') or parse_qs(parts.query).get('ssl_mode') or [''])[0].upper()
    else:
        config = {
            'host': os.environ.get('HYPECHECK_DB_HOST', 'localhost'),
            'port': int(os.environ.get('HYPECHECK_DB_PORT', '3306')),
            'user': os.environ.get('HYPECHECK_DB_USER', 'hypecheck'),
            'password': os.environ.get('HYPECHECK_DB_PASSWORD', ''),
            'database': os.environ.get('HYPECHECK_DB_NAME', 'hypecheck'),
        }
        ssl_mode = ''
        if os.environ.get('HYPECHECK_DB_SOCKET'):
            config['unix_socket'] = os.environ['HYPECHECK_DB_SOCKET']
    # Hosted MySQL is reached over TLS: fully verified when a CA certificate is given,
    # otherwise encrypted without certificate checks (the same as MySQL's ssl-mode=REQUIRED).
    ca_pem = os.environ.get('HYPECHECK_DB_SSL_CA_PEM', '').replace('\\n', '\n')
    ca_file = os.environ.get('HYPECHECK_DB_SSL_CA', '')
    if ca_pem or ca_file:
        config['ssl'] = ssl.create_default_context(cadata=ca_pem or None, cafile=ca_file or None)
    elif ssl_mode in ('REQUIRED', 'REQUIRE') or os.environ.get('HYPECHECK_DB_SSL', '').lower() in ('1', 'true', 'required'):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        config['ssl'] = context
    return config


DB = db_config()
# New accounts need this code when it is set. On Vercel with no code set, sign-ups are closed.
SIGNUP_CODE = os.environ.get('HYPECHECK_SIGNUP_CODE', '')
SESSION_COOKIE, SESSION_DAYS = 'hc_school_session', 30
MAX_FAILED_LOGINS, LOCK_MINUTES = 8, 15
MAX_FAILED_PER_EMAIL = 40  # backstop against many networks guessing one account; high, so a stranger cannot cheaply lock you out
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
OAUTH_COOKIE = 'hc_school_oauth'
# Anyone with a Google account can join: Google has already verified who they are. Set to 'invite' to ask them for the
# sign-up code as well. Email + password sign-ups always need the code, because nothing verifies those addresses.
GOOGLE_SIGNUP = os.environ.get('HYPECHECK_GOOGLE_SIGNUP', 'open')
MAX_NEW_GOOGLE_ACCOUNTS = 5  # per network per 15 minutes
GOOGLE_ONLY = 'google-only'  # password_hash of an account made with Google: not a scrypt hash, so no password can ever match it
UNCLAIMED = 'disabled-demo-login'  # password_hash of the seeded user: nobody can sign in as it until it is claimed


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def stamp(value):
    return value.strftime('%Y-%m-%d %H:%M:%S')


def connect():
    # All times are stored as UTC; the session time zone keeps CURRENT_TIMESTAMP defaults in UTC too.
    db = pymysql.connect(**DB, charset='utf8mb4', autocommit=False, connect_timeout=10,
                           cursorclass=pymysql.cursors.DictCursor,
                           init_command="SET time_zone = '+00:00'")
    q(db, "SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
    return db


def q(db, sql, params=()):
    cursor = db.cursor()
    cursor.execute(sql, params)
    return cursor


def statements(sql_text):
    """Split schema.sql into single statements, skipping -- comment lines."""
    lines = [line for line in sql_text.splitlines() if not line.strip().startswith('--')]
    return [part.strip() for part in '\n'.join(lines).split(';') if part.strip()]


def tables_exist(db):
    row = q(db, "SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'users'").fetchone()
    return row['n'] > 0


def seed(db):
    q(db, "INSERT INTO users (user_id, full_name, email, password_hash, created_at) VALUES (1, 'Your space', 'demo@hypecheck.local', 'disabled-demo-login', %s)", (now(),))
    for ident, name in enumerate(['Tech', 'Style', 'Lifestyle', 'Food & drinks', 'Transport', 'Other'], 1):
        q(db, 'INSERT INTO categories (category_id, category_name) VALUES (%s, %s)', (ident, name))
    current = now()
    wishes = [
        (1, 1, 'Everyday headphones', 4990, -72, -24, 'For playlists, study sessions, and a little quiet.', 'waiting'),
        (2, 2, 'The weekend sneakers', 3295, -18, 30, 'Do I have a pair that already does the job?', 'waiting'),
        (3, 3, 'A little digital camera', 6490, -20, 52, 'For the moments I want to keep.', 'waiting'),
        (4, 2, 'Another canvas tote', 890, -96, -48, 'The one I own still has a lot of life in it.', 'skipped'),
    ]
    for ident, category, name, price, start, end, notes, status in wishes:
        q(db, 'INSERT INTO wishlist_items (wishlist_item_id, user_id, category_id, item_name, estimated_price, created_at, wait_until, notes, status) VALUES (%s, 1, %s, %s, %s, %s, %s, %s, %s)',
          (ident, category, name, price, current + timedelta(hours=start), current + timedelta(hours=end), notes, status))
    q(db, "INSERT INTO decision_logs (wishlist_item_id, decision, reflection, decided_at) VALUES (4, 'skip', 'I already have one I love.', %s)", (current - timedelta(hours=24),))
    today = current.date()
    rows = [('Coffee & a slow morning', 165, 4, 0), ('Lunch with friends', 285, 4, 1), ('Ride home', 120, 5, 1),
            ('Groceries for the week', 1480, 3, 2), ('Monthly phone plan', 599, 1, 3), ('A good book', 450, 3, 4),
            ('Weekend dinner', 650, 4, 5), ('Train rides', 180, 5, 6), ('Study café', 220, 4, 7)]
    for description, amount, category, days in rows:
        spent_on = max(today.replace(day=1), today - timedelta(days=days))
        q(db, 'INSERT INTO expenses (user_id, category_id, description, amount, expense_date) VALUES (1, %s, %s, %s, %s)',
          (category, description, amount, spent_on))
    q(db, 'INSERT INTO monthly_budgets (user_id, budget_year, budget_month, budget_amount) VALUES (1, %s, %s, 10000)', (today.year, today.month))


def initialize(with_demo_data=True):
    """Create or upgrade the school schema without replacing existing rows."""
    db = connect()
    try:
        # MySQL DDL commits implicitly; serialize the idempotent upgrade across server starts.
        acquire_lock(db, 'schema')
        fresh = not tables_exist(db)
        for statement in statements((ROOT / 'schema.sql').read_text()):
            if fresh or 'IF NOT EXISTS' in statement:
                q(db, statement)
        if not q(db, "SELECT 1 FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'users' AND column_name = 'google_sub'").fetchone():
            q(db, 'ALTER TABLE users ADD COLUMN google_sub VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin UNIQUE')
        if fresh and with_demo_data:
            seed(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()  # also releases the named lock, including after a failed upgrade


def acquire_lock(db, name):
    """Named locks last until this request closes its connection, including across commits."""
    key = auth.token_hash(f"hypecheck:{DB['database']}:{name}")
    if q(db, 'SELECT GET_LOCK(%s, 10) AS acquired', (key,)).fetchone()['acquired'] != 1:
        raise pymysql.OperationalError(1205, 'Please retry; another request is still finishing.')


def text_field(data, key, limit, required=True):
    value = data.get(key, '')
    if not isinstance(value, str) or len(value.strip()) > limit or (required and not value.strip()):
        raise ValueError(f'Please enter a valid {key.replace("_", " ")} (up to {limit} characters).')
    return value.strip()


def money(value, zero=False):
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or (not zero and number == 0) or number > Decimal('9999999999.99') or number != number.quantize(Decimal('.01')):
            raise ValueError()
        return str(number.quantize(Decimal('.01')))
    except (InvalidOperation, ValueError):
        raise ValueError('Enter a valid amount with at most two decimal places.')


def integer(value, low, high, label):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f'Please enter a valid {label}.')
    return value


def category(db, data):
    ident = integer(data.get('category_id'), 1, 100000, 'category')
    if not q(db, 'SELECT 1 FROM categories WHERE category_id = %s', (ident,)).fetchone():
        raise ValueError('Choose an existing category.')
    return ident


def wish_fields(db, data):
    """Validated editable details of a wish, shared by create and update: category, name, price, notes, link."""
    name = text_field(data, 'item_name', 150)
    notes = text_field(data, 'notes', 2000, False)
    price = money(data.get('estimated_price'), zero=True)
    link = text_field(data, 'product_url', 2048, False)
    if link and (urlparse(link).scheme not in ('http', 'https') or not urlparse(link).netloc):
        raise ValueError('Use a complete http or https product link.')
    return category(db, data), name, price, notes, link


def expense_fields(db, data):
    """Validated editable details of an expense, shared by create and update."""
    description = text_field(data, 'description', 255)
    amount = money(data.get('amount'))
    try:
        expense_date = date.fromisoformat(data.get('expense_date', ''))
    except (ValueError, TypeError):
        raise ValueError('Choose a valid expense date.')
    return category(db, data), description, amount, expense_date, text_field(data, 'notes', 2000, False)


def mutate(db, path, data, user_id):
    """Apply one change for this user inside the caller's transaction (the caller commits or rolls back)."""
    current = now()
    if path == '/api/wishlist':
        fields = wish_fields(db, data)
        hours = integer(data.get('wait_hours'), 1, 720, 'waiting period')
        q(db, 'INSERT INTO wishlist_items (user_id, category_id, item_name, estimated_price, notes, product_url, created_at, wait_until) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
          (user_id, *fields, current, current + timedelta(hours=hours)))
    elif path in ('/api/wishlist/update', '/api/wishlist/delete'):
        ident = integer(data.get('wishlist_item_id'), 1, 2147483647, 'wishlist item')
        item = q(db, 'SELECT status FROM wishlist_items WHERE wishlist_item_id = %s AND user_id = %s FOR UPDATE', (ident, user_id)).fetchone()
        if not item:
            raise ValueError('This wish no longer exists.')
        if item['status'] != 'waiting':
            raise ValueError('This wish is already decided, so it stays in your history as it was.')
        if path.endswith('/update'):
            # details only: created_at and wait_until are never touched, so editing cannot shorten the wait
            q(db, 'UPDATE wishlist_items SET category_id = %s, item_name = %s, estimated_price = %s, notes = %s, product_url = %s WHERE wishlist_item_id = %s',
              (*wish_fields(db, data), ident))
        else:
            # a waiting wish can only have "wait longer" logs; they go with it
            q(db, 'DELETE FROM decision_logs WHERE wishlist_item_id = %s', (ident,))
            q(db, 'DELETE FROM wishlist_items WHERE wishlist_item_id = %s', (ident,))
    elif path == '/api/decisions':
        ident = integer(data.get('wishlist_item_id'), 1, 2147483647, 'wishlist item')
        # lock the row so two decisions on the same item can't both go through
        item = q(db, 'SELECT * FROM wishlist_items WHERE wishlist_item_id = %s AND user_id = %s FOR UPDATE', (ident, user_id)).fetchone()
        if not item or item['status'] != 'waiting':
            raise ValueError('This item is no longer waiting for a decision.')
        if item['wait_until'] > current:
            raise ValueError('Give it a little time. Your waiting period has not ended yet.')
        decision = data.get('decision')
        if decision not in ('buy', 'skip', 'wait_longer'):
            raise ValueError('Choose buy, skip, or wait longer.')
        reflection = text_field(data, 'reflection', 2000, False)
        deadline = None
        if decision == 'wait_longer':
            hours = integer(data.get('wait_hours'), 1, 720, 'waiting period')
            deadline = current + timedelta(hours=hours)
            q(db, 'UPDATE wishlist_items SET wait_until = %s WHERE wishlist_item_id = %s', (deadline, ident))
        else:
            q(db, 'UPDATE wishlist_items SET status = %s WHERE wishlist_item_id = %s', ('bought' if decision == 'buy' else 'skipped', ident))
        q(db, 'INSERT INTO decision_logs (wishlist_item_id, decision, reflection, decided_at, new_wait_until) VALUES (%s, %s, %s, %s, %s)',
          (ident, decision, reflection, current, deadline))
        if decision == 'buy' and data.get('record_expense') is True:
            amount = money(data.get('amount'))
            try:
                bought_on = date.fromisoformat(data.get('expense_date', current.date().isoformat()))
            except (ValueError, TypeError):
                raise ValueError('Choose a valid purchase date.')
            q(db, 'INSERT INTO expenses (user_id, category_id, wishlist_item_id, description, amount, expense_date) VALUES (%s, %s, %s, %s, %s, %s)',
              (user_id, item['category_id'], ident, item['item_name'], amount, bought_on))
    elif path == '/api/expenses':
        q(db, 'INSERT INTO expenses (user_id, category_id, description, amount, expense_date, notes) VALUES (%s, %s, %s, %s, %s, %s)',
          (user_id, *expense_fields(db, data)))
    elif path == '/api/expenses/update':
        ident = integer(data.get('expense_id'), 1, 2147483647, 'expense')
        # wishlist_item_id is left alone: a purchase stays linked to the wish it came from
        changed = q(db, 'UPDATE expenses SET category_id = %s, description = %s, amount = %s, expense_date = %s, notes = %s WHERE expense_id = %s AND user_id = %s',
                    (*expense_fields(db, data), ident, user_id))
        if changed.rowcount != 1 and not q(db, 'SELECT 1 FROM expenses WHERE expense_id = %s AND user_id = %s', (ident, user_id)).fetchone():
            raise ValueError('This expense no longer exists.')
    elif path == '/api/budget':
        year = integer(data.get('budget_year'), 1, 9999, 'year')
        month = integer(data.get('budget_month'), 1, 12, 'month')
        amount = money(data.get('budget_amount'), zero=True)
        q(db, 'INSERT INTO monthly_budgets (user_id, budget_year, budget_month, budget_amount) VALUES (%s, %s, %s, %s) '
              'ON DUPLICATE KEY UPDATE budget_amount = VALUES(budget_amount)', (user_id, year, month, amount))
    elif path == '/api/expenses/delete':
        ident = integer(data.get('expense_id'), 1, 2147483647, 'expense')
        if q(db, 'DELETE FROM expenses WHERE expense_id = %s AND user_id = %s', (ident, user_id)).rowcount != 1:
            raise ValueError('This expense was already removed.')
    else:
        raise ValueError('Unknown action.')


def serialize(row):
    """MySQL gives Decimal/datetime/date objects; the browser app expects numbers and strings."""
    out = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            value = float(value)
        elif isinstance(value, datetime):
            value = stamp(value)
        elif isinstance(value, date):
            value = value.isoformat()
        out[key] = value
    return out


def read_state(user_id):
    """Everything the app shows for one user. Categories are shared; the rest is theirs alone."""
    db = connect()
    try:
        mine = {
            'categories': ('', ()),
            'wishlist_items': (' WHERE user_id = %s', (user_id,)),
            'decision_logs': (' WHERE wishlist_item_id IN (SELECT wishlist_item_id FROM wishlist_items WHERE user_id = %s)', (user_id,)),
            'expenses': (' WHERE user_id = %s', (user_id,)),
            'monthly_budgets': (' WHERE user_id = %s', (user_id,)),
        }
        result = {table: [serialize(row) for row in q(db, f'SELECT * FROM {table}{where}', params).fetchall()] for table, (where, params) in mine.items()}
        result['user'] = q(db, 'SELECT full_name, email FROM users WHERE user_id = %s', (user_id,)).fetchone()
        db.commit()
        return result
    finally:
        db.close()


def account_fields(data):
    name = text_field(data, 'full_name', 100)
    email = text_field(data, 'email', 255).lower()
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
        raise ValueError('Enter a valid email address.')
    password = data.get('password')
    if not isinstance(password, str) or not 10 <= len(password) <= 200:
        raise ValueError('Use a password of at least 10 characters.')
    return name, email, password


def throttle(db, limits):
    """Refuse when any identifier already has too many recent failures. `limits` maps identifier -> cap.

    The advisory lock makes concurrent requests for the same identifier queue up, so they cannot all read
    a count below the cap before any of them records its failure. It is released when the request closes its connection.
    """
    since = now() - timedelta(minutes=LOCK_MINUTES)
    for identifier in sorted(limits):  # fixed order: two requests can never wait on each other
        acquire_lock(db, identifier)
    q(db, 'DELETE FROM login_attempts WHERE attempted_at < %s', (since,))
    for identifier, cap in limits.items():
        if q(db, 'SELECT COUNT(*) AS n FROM login_attempts WHERE identifier = %s AND attempted_at >= %s', (identifier, since)).fetchone()['n'] >= cap:
            raise ValueError(f'Too many attempts. Try again in {LOCK_MINUTES} minutes.')


def record_failures(db, identifiers):
    for identifier in identifiers:
        q(db, 'INSERT INTO login_attempts (identifier, attempted_at) VALUES (%s, %s)', (identifier[:320], now()))


def check_signup_code(db, code, ip):
    """New accounts are invite-only. A wrong code records an attempt: the CALLER must commit even when this raises."""
    if SIGNUP_CODE:
        throttle(db, {f'signup:{ip}': MAX_FAILED_LOGINS})  # the invite code must not be guessable at full speed
        if not hmac.compare_digest(str(code or '').encode(), SIGNUP_CODE.encode()):
            record_failures(db, [f'signup:{ip}'])
            raise ValueError('That sign-up code is not right.')
    elif os.environ.get('VERCEL'):
        raise ValueError('Sign-ups are closed.')


def create_or_claim_user(db, name, email, password_hash, google_sub=None):
    """Insert the account, or take over the seeded unclaimed user (and its data) when one is still waiting."""
    acquire_lock(db, 'account-create')
    unclaimed = q(db, 'SELECT user_id FROM users WHERE password_hash = %s ORDER BY user_id LIMIT 1 FOR UPDATE', (UNCLAIMED,)).fetchone()
    if unclaimed:
        q(db, 'UPDATE users SET full_name = %s, email = %s, password_hash = %s, google_sub = %s WHERE user_id = %s',
          (name, email, password_hash, google_sub, unclaimed['user_id']))
        return unclaimed['user_id']
    return q(db, 'INSERT INTO users (full_name, email, password_hash, google_sub, created_at) VALUES (%s, %s, %s, %s, %s)',
             (name, email, password_hash, google_sub, now())).lastrowid


def register(db, data, ip='unknown'):
    """Create a password account and return its user_id. A wrong sign-up code must still be committed by the CALLER."""
    check_signup_code(db, data.get('signup_code'), ip)
    name, email, password = account_fields(data)
    if q(db, 'SELECT 1 FROM users WHERE email = %s', (email,)).fetchone():
        raise ValueError('An account with this email already exists.')
    return create_or_claim_user(db, name, email, auth.hash_password(password))


def google_identity(claims):
    """Check the claims of an ID token that came straight from Google's token endpoint over TLS
    (OpenID Connect allows skipping the signature check in that case) and return (sub, email, name)."""
    if claims.get('iss') not in ('https://accounts.google.com', 'accounts.google.com'):
        raise ValueError('That sign-in did not come from Google.')
    if not GOOGLE_CLIENT_ID or claims.get('aud') != GOOGLE_CLIENT_ID:
        raise ValueError('That sign-in was meant for a different app.')
    if not isinstance(claims.get('exp'), (int, float)) or claims['exp'] < time.time():
        raise ValueError('That sign-in has expired. Please try again.')
    sub, email = claims.get('sub'), claims.get('email')
    if not isinstance(sub, str) or not sub or not isinstance(email, str) or claims.get('email_verified') is not True:
        raise ValueError('Google has not verified that email address.')
    name = claims.get('name') if isinstance(claims.get('name'), str) and claims.get('name').strip() else email.split('@')[0]
    return sub[:255], email.strip().lower()[:255], name.strip()[:100]


def google_sign_in(db, claims, signup_code, ip):
    """Return the user_id for a Google sign-in: the linked account, else the account with that verified email
    (linking it), else a new account. A wrong sign-up code (invite mode) must still be committed by the CALLER."""
    sub, email, name = google_identity(claims)
    user = q(db, 'SELECT user_id FROM users WHERE google_sub = %s', (sub,)).fetchone()
    if user:
        return user['user_id']
    user = q(db, 'SELECT user_id FROM users WHERE email = %s FOR UPDATE', (email,)).fetchone()
    if user:
        # Google has proved this person owns the address; whoever set the password never did. So the password stops
        # working and every older session ends, or a stranger could pre-register someone's email and wait for them.
        q(db, 'UPDATE users SET google_sub = %s, password_hash = %s WHERE user_id = %s', (sub, GOOGLE_ONLY, user['user_id']))
        q(db, 'DELETE FROM sessions WHERE user_id = %s', (user['user_id'],))
        return user['user_id']
    if GOOGLE_SIGNUP == 'invite':
        check_signup_code(db, signup_code, ip)
    else:
        throttle(db, {f'gsignup:{ip}': MAX_NEW_GOOGLE_ACCOUNTS})
        record_failures(db, [f'gsignup:{ip}'])  # counts new accounts, not failures: same table, same 15-minute window
    return create_or_claim_user(db, name, email, GOOGLE_ONLY, sub)


def fetch_google_claims(code, redirect_uri):
    """Swap the one-time code for Google's ID token and return its claims. The only outbound call in the app."""
    body = urlencode({'code': code, 'client_id': GOOGLE_CLIENT_ID, 'client_secret': GOOGLE_CLIENT_SECRET,
                      'redirect_uri': redirect_uri, 'grant_type': 'authorization_code'}).encode()
    request = Request('https://oauth2.googleapis.com/token', data=body, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urlopen(request, timeout=10) as response:
        payload = json.load(response)['id_token'].split('.')[1]
    return json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))


def start_session(db, user_id):
    token = auth.new_token()
    q(db, 'INSERT INTO sessions (session_id, user_id, created_at, expires_at) VALUES (%s, %s, %s, %s)',
      (auth.token_hash(token), user_id, now(), now() + timedelta(days=SESSION_DAYS)))
    return token


def login(db, data, ip):
    """Check the password and return a new session token. A failure records an attempt: the CALLER must commit it."""
    email = str(data.get('email') or '').strip().lower()[:255]
    password = data.get('password') if isinstance(data.get('password'), str) else ''
    # One network guessing (ip), one network on one account (pair), and a high backstop per account (email).
    limits = {f'ip:{ip}': MAX_FAILED_LOGINS * 3, f'pair:{email}|{ip}': MAX_FAILED_LOGINS, f'email:{email}': MAX_FAILED_PER_EMAIL}
    q(db, 'DELETE FROM sessions WHERE expires_at < %s', (now(),))
    throttle(db, limits)
    user = q(db, 'SELECT user_id, password_hash FROM users WHERE email = %s', (email,)).fetchone()
    # an unknown email still pays for one hash check, so timing does not reveal which emails exist
    if not auth.verify_password(password[:200], user['password_hash'] if user else auth.DUMMY_HASH) or not user:
        record_failures(db, limits)
        raise ValueError('Email or password is incorrect.')
    q(db, 'DELETE FROM login_attempts WHERE identifier = %s', (f'pair:{email}|{ip}',))
    return start_session(db, user['user_id'])


def session_user(db, token):
    if not token or not isinstance(token, str) or len(token) > 200:
        return None
    return q(db, 'SELECT u.user_id, u.full_name, u.email FROM sessions s JOIN users u ON u.user_id = s.user_id '
                 'WHERE s.session_id = %s AND s.expires_at > %s', (auth.token_hash(token), now())).fetchone()


def logout(db, token):
    if token:
        q(db, 'DELETE FROM sessions WHERE session_id = %s', (auth.token_hash(token),))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'static'), **kwargs)

    def send_json(self, payload, status=200, cookie=None):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        if cookie is not None:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('X-Frame-Options', 'DENY')
        # everything is first-party; inline style attributes size the progress bars, there are no inline scripts
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                                                    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        if os.environ.get('VERCEL'):
            self.send_header('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        super().end_headers()

    def session_cookie(self, token):
        """HttpOnly keeps scripts away from it; SameSite=Lax plus the Origin check below covers cross-site posts."""
        secure = '; Secure' if os.environ.get('VERCEL') or self.headers.get('X-Forwarded-Proto') == 'https' else ''
        age = SESSION_DAYS * 86400 if token else 0
        return f'{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={age}{secure}'

    def token(self):
        for part in self.headers.get('Cookie', '').split(';'):
            name, _, value = part.strip().partition('=')
            if name == SESSION_COOKIE:
                return value
        return ''

    def client_ip(self):
        """Vercel sets x-vercel-forwarded-for itself and clients cannot override it. Anywhere else, headers are
        whatever the client typed, so only the socket address counts."""
        if os.environ.get('VERCEL'):
            return (self.headers.get('x-vercel-forwarded-for', '').split(',')[0].strip() or self.client_address[0])[:64]
        return self.client_address[0][:64]

    def redirect(self, location, cookies=()):
        self.send_response(302)
        self.send_header('Location', location)
        self.send_header('Cache-Control', 'no-store')
        for cookie in cookies:
            self.send_header('Set-Cookie', cookie)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def log_message(self, fmt, *args):
        # the OAuth callback URL carries the authorization code and state: keep them out of the log
        first = args[0] if args else ''
        if isinstance(first, str) and '/api/auth/google/callback' in first:
            args = ('%s /api/auth/google/callback?<redacted> %s' % (first.split(' ')[0], first.split(' ')[-1]), *args[1:])
        super().log_message(fmt, *args)

    def google_redirect_uri(self):
        # must match a redirect URI registered in Google Cloud exactly, so a forged Host header only breaks the attempt
        proto = 'https' if os.environ.get('VERCEL') or self.headers.get('X-Forwarded-Proto') == 'https' else 'http'
        return f"{proto}://{self.headers.get('Host', '')}/api/auth/google/callback"

    def oauth_cookie(self, value):
        secure = '; Secure' if os.environ.get('VERCEL') or self.headers.get('X-Forwarded-Proto') == 'https' else ''
        return f"{OAUTH_COOKIE}={value}; Path=/api/auth/google; HttpOnly; SameSite=Lax; Max-Age={600 if value else 0}{secure}"

    def google_start(self):
        if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
            return self.send_json({'error': 'Google sign-in is not set up.'}, 404)
        state = secrets.token_urlsafe(24)
        nonce = secrets.token_urlsafe(24)
        signup_code = (parse_qs(urlparse(self.path).query).get('code') or [''])[0][:100]
        # the state ties the callback to this browser, the nonce ties the ID token to this request;
        # the invite code rides along and is checked server-side later
        cookie = self.oauth_cookie(f'{state}.{nonce}.{quote(signup_code, safe="")}')
        query = urlencode({'client_id': GOOGLE_CLIENT_ID, 'redirect_uri': self.google_redirect_uri(), 'response_type': 'code',
                           'scope': 'openid email profile', 'state': state, 'nonce': nonce, 'prompt': 'select_account'})
        self.redirect('https://accounts.google.com/o/oauth2/v2/auth?' + query, [cookie])

    def google_callback(self):
        clear = self.oauth_cookie('')
        params = parse_qs(urlparse(self.path).query)
        saved = ''
        for part in self.headers.get('Cookie', '').split(';'):
            name, _, value = part.strip().partition('=')
            if name == OAUTH_COOKIE:
                saved = value
        state, _, rest = saved.partition('.')
        nonce, _, signup_code = rest.partition('.')
        given = (params.get('state') or [''])[0]
        if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET) or not state or not hmac.compare_digest(state.encode(), given.encode()) or 'code' not in params:
            return self.redirect('/app?auth_error=google', [clear])
        try:
            claims = fetch_google_claims(params['code'][0], self.google_redirect_uri())
            if not nonce or not hmac.compare_digest(nonce.encode(), str(claims.get('nonce', '')).encode()):
                raise ValueError('That sign-in did not match this request.')
        except Exception:  # network trouble, a reused code, a malformed token: all the same to the person signing in
            return self.redirect('/app?auth_error=google', [clear])
        try:
            db = connect()
        except pymysql.MySQLError:
            return self.redirect('/app?auth_error=server', [clear])
        try:
            try:
                token = start_session(db, google_sign_in(db, claims, unquote(signup_code), self.client_ip()))
            except ValueError as error:
                db.commit()  # keep a wrong sign-up code on record for the rate limit; nothing else was written
                kind = 'throttled' if 'Too many' in str(error) else 'invite' if 'sign-up' in str(error).lower() or 'Sign-ups' in str(error) else 'google'
                return self.redirect(f'/app?auth_error={kind}', [clear])
            db.commit()
            self.redirect('/', [clear, self.session_cookie(token)])
        except pymysql.MySQLError:
            db.rollback()
            self.redirect('/app?auth_error=server', [clear])
        finally:
            db.close()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/state':
            try:
                db = connect()
                try:
                    user = session_user(db, self.token())
                    db.commit()
                finally:
                    db.close()
                if not user:
                    return self.send_json({'error': 'Please sign in.'}, 401)
                self.send_json(read_state(user['user_id']))
            except pymysql.MySQLError:
                self.send_json({'error': 'Could not load your data right now. Please try again.'}, 500)
        elif path == '/api/auth/options':
            self.send_json({'signup': bool(SIGNUP_CODE) or not os.environ.get('VERCEL'), 'needs_code': bool(SIGNUP_CODE),
                            'google': bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET), 'google_open': GOOGLE_SIGNUP != 'invite'})
        elif path == '/api/auth/google/start':
            self.google_start()
        elif path == '/api/auth/google/callback':
            self.google_callback()
        elif path.startswith('/api/'):
            self.send_json({'error': 'Not found.'}, 404)
        else:
            # Visitors see the landing page at the front door; anyone holding a session cookie gets the app there
            # (so the home-screen icon keeps opening the app). /app is always the app, which signs people in itself.
            page = path.rstrip('/') or '/'
            if page in ('/', '/index.html'):
                self.path = '/index.html' if self.token() else '/landing.html'
            elif page in ('/app', '/login', '/signin', '/signup'):  # the app signs people in itself; /signup opens on "create account"
                self.path = '/index.html'
            elif page == '/welcome':  # the landing page, even for someone who is signed in
                self.path = '/landing.html'
            super().do_GET()

    def do_POST(self):
        origin = self.headers.get('Origin', '')
        # same-site only, and fail closed: browsers always send Origin on a POST, so a request without one is not our page.
        # Compares the host so it works over http locally and https when hosted.
        if urlparse(origin).netloc != self.headers.get('Host', '') or not origin:
            return self.send_json({'error': 'Request origin not allowed.'}, 403)
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.send_json({'error': 'Expected JSON.'}, 415)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16384:
                raise ValueError('Request is too large or empty.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object.')
        except ValueError as error:  # includes malformed JSON
            return self.send_json({'error': str(error)}, 400)
        try:
            db = connect()
        except pymysql.MySQLError:
            return self.send_json({'error': 'Could not reach the database. Please try again.'}, 500)
        path = urlparse(self.path).path
        try:
            if path == '/api/auth/register':
                try:
                    token = start_session(db, register(db, data, self.client_ip()))
                except ValueError:
                    db.commit()  # keep a wrong sign-up code on record for the rate limit; nothing else was written
                    raise
                db.commit()
                return self.send_json({'ok': True}, cookie=self.session_cookie(token))
            if path == '/api/auth/login':
                try:
                    token = login(db, data, self.client_ip())
                except ValueError:
                    db.commit()  # keep the failed attempt on record for the rate limit
                    raise
                db.commit()
                return self.send_json({'ok': True}, cookie=self.session_cookie(token))
            if path == '/api/auth/logout':
                logout(db, self.token())
                db.commit()
                return self.send_json({'ok': True}, cookie=self.session_cookie(''))
            user = session_user(db, self.token())
            if not user:
                db.rollback()
                return self.send_json({'error': 'Please sign in.'}, 401)
            mutate(db, path, data, user['user_id'])
            db.commit()
            self.send_json({'ok': True})
        except ValueError as error:
            db.rollback()
            self.send_json({'error': str(error)}, 400)
        except pymysql.MySQLError as error:
            db.rollback()
            code = error.args[0] if error.args else None
            if code in RULE_MESSAGES:
                self.send_json({'error': RULE_MESSAGES[code]}, 400)
            else:
                self.send_json({'error': 'Could not save right now. Please try again.'}, 500)
        finally:
            db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4175)
    parser.add_argument('--database', help='MySQL database name (default: HYPECHECK_DB_NAME from .env)')
    args = parser.parse_args()
    if args.database:
        DB['database'] = args.database
    try:
        initialize()
    except pymysql.MySQLError as error:
        sys.exit(f'Could not connect to MySQL database "{DB["database"]}" as "{DB["user"]}": {error}\n'
                 'Check that MySQL is running and that .env has the right settings (see README).')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'HypeCheck is ready at http://127.0.0.1:{server.server_port} (MySQL database: {DB["database"]})', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
