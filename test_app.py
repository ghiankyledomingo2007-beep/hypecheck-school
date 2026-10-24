"""MySQL parity suite. Rebuilds only the separate hypecheck_test database."""
from datetime import date
import ssl
from decimal import Decimal
import json
import os
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

import pymysql
import tempfile
from unittest.mock import patch

import auth
import server

TEST_DB = os.environ.get('HYPECHECK_TEST_DB_NAME', 'hypecheck_test')
if not TEST_DB.startswith('hypecheck_test') or TEST_DB == server.DB['database']:
    raise RuntimeError('Tests require a separate hypecheck_test database.')


class DatabaseConfigTest(unittest.TestCase):
    def test_development_profile_blocks_dotenv_hosted_url(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = server.Path(directory) / '.env'
            env_file.write_text('HYPECHECK_DATABASE_URL=mysql://app:password@db.example.com/hc\n')
            with patch.dict(os.environ, {'HYPECHECK_DATABASE_URL': '', 'HYPECHECK_DB_SOCKET': '/private/mysql.sock'}):
                server.load_env(env_file)
                self.assertEqual(server.db_config()['unix_socket'], '/private/mysql.sock')

    def test_private_socket_only_applies_to_local_configuration(self):
        with patch.dict(os.environ, {'HYPECHECK_DATABASE_URL': '', 'HYPECHECK_DB_SOCKET': '/private/mysql.sock'}):
            self.assertEqual(server.db_config()['unix_socket'], '/private/mysql.sock')
            os.environ['HYPECHECK_DATABASE_URL'] = 'mysql://app:password@db.example.com/hc'
            self.assertNotIn('unix_socket', server.db_config())


class HypeCheckTest(unittest.TestCase):
    def setUp(self):
        self.original = dict(server.DB)
        server.DB['database'] = TEST_DB
        db = server.connect()
        try:
            server.q(db, 'SET FOREIGN_KEY_CHECKS = 0')
            for table in ['sessions', 'login_attempts', *server.TABLES]:
                server.q(db, f'DROP TABLE IF EXISTS {table}')
            server.q(db, 'SET FOREIGN_KEY_CHECKS = 1')
            db.commit()
        finally:
            db.close()
        server.initialize()

    def tearDown(self):
        server.DB.clear()
        server.DB.update(self.original)

    def test_upgrade_preserves_existing_school_data(self):
        before = server.read_state(1)
        db = server.connect()
        try:
            server.q(db, 'DROP TABLE sessions')
            server.q(db, 'DROP TABLE login_attempts')
            server.q(db, 'ALTER TABLE users DROP COLUMN google_sub')
            db.commit()
        finally:
            db.close()
        server.initialize()
        server.initialize()  # repeat startup must not reseed or duplicate data
        self.assertEqual(before, server.read_state(1))
        self.assertEqual(8, self.one('SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema = DATABASE()')['n'])

    def test_concurrent_failed_logins_obey_limit(self):
        from concurrent.futures import ThreadPoolExecutor
        def attempt(_):
            db = server.connect()
            try:
                try:
                    server.login(db, {'email': 'parallel@example.test', 'password': 'wrong'}, 'parallel-test')
                except ValueError as error:
                    db.commit()
                    return str(error)
            finally:
                db.close()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(attempt, range(server.MAX_FAILED_LOGINS + 3)))
        self.assertEqual(server.MAX_FAILED_LOGINS, results.count('Email or password is incorrect.'))
        self.assertEqual(3, sum('Too many' in result for result in results))

    def test_legacy_import_clears_old_sessions(self):
        import sqlite3
        from scripts import migrate_sqlite_to_mysql
        db = server.connect()
        try:
            before = {table: server.q(db, f'SELECT * FROM {table}').fetchall() for table in server.TABLES}
            token = server.start_session(db, 1)
            db.commit()
        finally:
            db.close()
        with tempfile.TemporaryDirectory() as directory:
            source = server.Path(directory) / 'legacy.sqlite3'
            with sqlite3.connect(source) as sqlite:
                for table, rows in before.items():
                    columns = [column for column in rows[0] if column != 'google_sub']
                    sqlite.execute(f'CREATE TABLE {table} ({", ".join(columns)})')
                    for row in rows:
                        values = server.serialize(row)
                        sqlite.execute(f'INSERT INTO {table} VALUES ({", ".join(["?"] * len(columns))})', [values[column] for column in columns])
            with patch('sys.argv', ['migrate', '--sqlite', str(source), '--replace']):
                migrate_sqlite_to_mysql.main()
        db = server.connect()
        try:
            self.assertIsNone(server.session_user(db, token))
            for table, rows in before.items():
                self.assertEqual(rows, server.q(db, f'SELECT * FROM {table}').fetchall())
        finally:
            db.close()

    def action(self, path, data, user_id=1):
        db = server.connect()
        try:
            server.mutate(db, path, data, user_id)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def one(self, sql, params=()):
        db = server.connect()
        try:
            return server.q(db, sql, params).fetchone()
        finally:
            db.close()

    def test_eight_tables_and_foreign_keys(self):
        tables = self.one('SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema = DATABASE()')
        self.assertEqual(8, tables['n'])  # the six app tables + sessions + login_attempts
        keys = self.one('SELECT COUNT(*) AS n FROM information_schema.referential_constraints WHERE constraint_schema = DATABASE()')
        self.assertEqual(8, keys['n'])  # + sessions.user_id

    def test_buy_and_expense_are_linked_once(self):
        payload = {'wishlist_item_id': 1, 'decision': 'buy', 'record_expense': True, 'amount': '4499.95', 'reflection': 'It fits my plan.'}
        self.action('/api/decisions', payload)
        self.assertEqual('bought', self.one('SELECT status FROM wishlist_items WHERE wishlist_item_id = 1')['status'])
        self.assertEqual(Decimal('4499.95'), self.one('SELECT amount FROM expenses WHERE wishlist_item_id = 1')['amount'])
        self.assertEqual('It fits my plan.', self.one('SELECT reflection FROM decision_logs WHERE wishlist_item_id = 1')['reflection'])
        with self.assertRaises(ValueError):
            self.action('/api/decisions', payload)

    def test_early_decision_rejected(self):
        with self.assertRaises(ValueError):
            self.action('/api/decisions', {'wishlist_item_id': 2, 'decision': 'buy'})

    def test_invalid_expense_rolls_back_decision(self):
        with self.assertRaises(ValueError):
            self.action('/api/decisions', {'wishlist_item_id': 1, 'decision': 'buy', 'record_expense': True, 'amount': '-2'})
        self.assertEqual('waiting', self.one('SELECT status FROM wishlist_items WHERE wishlist_item_id = 1')['status'])
        self.assertEqual(0, self.one('SELECT COUNT(*) AS n FROM decision_logs WHERE wishlist_item_id = 1')['n'])

    def test_wait_extension_then_skip(self):
        self.action('/api/decisions', {'wishlist_item_id': 1, 'decision': 'wait_longer', 'wait_hours': 48})
        self.assertGreater(self.one('SELECT wait_until FROM wishlist_items WHERE wishlist_item_id = 1')['wait_until'], server.now())
        db = server.connect()
        try:
            server.q(db, "UPDATE wishlist_items SET created_at = '2020-01-01 00:00:00', wait_until = '2020-01-02 00:00:00' WHERE wishlist_item_id = 1")
            db.commit()
        finally:
            db.close()
        self.action('/api/decisions', {'wishlist_item_id': 1, 'decision': 'skip', 'reflection': 'Already have one.'})
        self.assertEqual(2, self.one('SELECT COUNT(*) AS n FROM decision_logs WHERE wishlist_item_id = 1')['n'])
        self.assertEqual(0, self.one('SELECT COUNT(*) AS n FROM expenses WHERE wishlist_item_id = 1')['n'])

    def test_budget_upsert_and_manual_expense(self):
        for amount in ['5000', '6000']:
            self.action('/api/budget', {'budget_year': 2028, 'budget_month': 1, 'budget_amount': amount})
        self.action('/api/expenses', {'category_id': 4, 'description': 'Lunch', 'amount': '129.50', 'expense_date': '2028-01-12'})
        self.assertEqual(Decimal('6000.00'), self.one('SELECT budget_amount FROM monthly_budgets WHERE budget_year = 2028')['budget_amount'])
        self.assertEqual(1, self.one('SELECT COUNT(*) AS n FROM monthly_budgets WHERE budget_year = 2028')['n'])
        row = self.one("SELECT * FROM expenses WHERE expense_date = '2028-01-12'")
        self.assertIsNone(row['wishlist_item_id'])
        self.assertEqual(Decimal('129.50'), row['amount'])
        self.assertEqual(date(2028, 1, 12), row['expense_date'])

    def test_edit_wish_keeps_the_timer(self):
        before = self.one('SELECT created_at, wait_until FROM wishlist_items WHERE wishlist_item_id = 2')
        self.action('/api/wishlist/update', {'wishlist_item_id': 2, 'item_name': 'Trail sneakers', 'estimated_price': '3100.50',
                                             'category_id': 3, 'notes': 'For hikes.', 'product_url': 'https://example.test/shoe'})
        row = self.one('SELECT * FROM wishlist_items WHERE wishlist_item_id = 2')
        self.assertEqual(('Trail sneakers', Decimal('3100.50'), 3, 'For hikes.', 'https://example.test/shoe'),
                         (row['item_name'], row['estimated_price'], row['category_id'], row['notes'], row['product_url']))
        # editing details must never shorten or restart the wait
        self.assertEqual((before['created_at'], before['wait_until']), (row['created_at'], row['wait_until']))
        for bad in [{'wishlist_item_id': 999, 'item_name': 'Ghost', 'estimated_price': '1', 'category_id': 1},      # no such wish
                    {'wishlist_item_id': 4, 'item_name': 'Tote again', 'estimated_price': '1', 'category_id': 1},  # already decided
                    {'wishlist_item_id': 2, 'item_name': '', 'estimated_price': '1', 'category_id': 1},            # empty name
                    {'wishlist_item_id': 2, 'item_name': 'Bag', 'estimated_price': '1', 'category_id': 1, 'product_url': 'javascript:alert(1)'}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.action('/api/wishlist/update', bad)

    def test_remove_wish_only_while_waiting(self):
        self.action('/api/decisions', {'wishlist_item_id': 1, 'decision': 'wait_longer', 'wait_hours': 24})
        self.action('/api/wishlist/delete', {'wishlist_item_id': 1})
        self.assertIsNone(self.one('SELECT 1 FROM wishlist_items WHERE wishlist_item_id = 1'))
        self.assertEqual(0, self.one('SELECT COUNT(*) AS n FROM decision_logs WHERE wishlist_item_id = 1')['n'])
        # a decided wish is history: it stays, with its log
        with self.assertRaises(ValueError):
            self.action('/api/wishlist/delete', {'wishlist_item_id': 4})
        self.assertEqual(1, self.one('SELECT COUNT(*) AS n FROM decision_logs WHERE wishlist_item_id = 4')['n'])
        with self.assertRaises(ValueError):
            self.action('/api/wishlist/delete', {'wishlist_item_id': 1})  # already gone

    def test_edit_expense(self):
        ident = self.one('SELECT expense_id FROM expenses ORDER BY expense_id LIMIT 1')['expense_id']
        self.action('/api/expenses/update', {'expense_id': ident, 'description': 'Flat white', 'amount': '180', 'category_id': 4,
                                             'expense_date': '2028-02-03', 'notes': 'Treat.'})
        row = self.one('SELECT * FROM expenses WHERE expense_id = %s', (ident,))
        self.assertEqual(('Flat white', Decimal('180.00'), date(2028, 2, 3), 'Treat.'), (row['description'], row['amount'], row['expense_date'], row['notes']))
        # a purchase expense keeps its link to the wish it came from
        self.action('/api/decisions', {'wishlist_item_id': 1, 'decision': 'buy', 'record_expense': True, 'amount': '4500', 'expense_date': '2028-02-01'})
        linked = self.one('SELECT expense_id FROM expenses WHERE wishlist_item_id = 1')['expense_id']
        self.action('/api/expenses/update', {'expense_id': linked, 'description': 'Headphones (sale)', 'amount': '4200', 'category_id': 1, 'expense_date': '2028-02-02'})
        self.assertEqual(1, self.one('SELECT wishlist_item_id FROM expenses WHERE expense_id = %s', (linked,))['wishlist_item_id'])
        for bad in [{'expense_id': 99999, 'description': 'x', 'amount': '1', 'category_id': 1, 'expense_date': '2028-01-01'},
                    {'expense_id': ident, 'description': 'x', 'amount': '0', 'category_id': 1, 'expense_date': '2028-01-01'},
                    {'expense_id': ident, 'description': 'x', 'amount': '1', 'category_id': 1, 'expense_date': 'not-a-date'}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.action('/api/expenses/update', bad)

    def test_validation_and_ownership(self):
        for value in ['NaN', 'Infinity', '-1', '1.999', '10000000000']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                server.money(value)
        with self.assertRaises(ValueError):
            self.action('/api/wishlist', {'item_name': 'Bag', 'estimated_price': '100', 'wait_hours': 48, 'category_id': 1, 'product_url': 'javascript:alert(1)'})
        db = server.connect()
        try:
            server.q(db, "INSERT INTO users (user_id, full_name, email, password_hash) VALUES (2, 'Test', 'test@example.test', 'disabled')")
            # user 2 may not record an expense against user 1's wishlist item
            with self.assertRaises(pymysql.IntegrityError):
                server.q(db, "INSERT INTO expenses (user_id, category_id, wishlist_item_id, description, amount, expense_date) VALUES (2, 1, 1, 'Invalid ownership', 100, '2026-09-18')")
        finally:
            db.rollback()
            db.close()

    def test_database_enforces_check_rules(self):
        db = server.connect()
        try:
            for sql in [
                "UPDATE wishlist_items SET estimated_price = -1 WHERE wishlist_item_id = 1",
                "UPDATE wishlist_items SET status = 'lost' WHERE wishlist_item_id = 1",
                "INSERT INTO monthly_budgets (user_id, budget_year, budget_month, budget_amount) VALUES (1, 2030, 13, 100)",
                "INSERT INTO decision_logs (wishlist_item_id, decision) VALUES (1, 'wait_longer')",
            ]:
                with self.subTest(sql=sql), self.assertRaises(pymysql.MySQLError) as caught:
                    server.q(db, sql)
                self.assertEqual(3819, caught.exception.args[0])  # MySQL CHECK violation
        finally:
            db.rollback()
            db.close()

    def test_http_boundary(self):
        http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{http.server_port}'
        try:
            with self.assertRaises(HTTPError) as error:
                urlopen(base + '/api/state')
            self.assertEqual(401, error.exception.code)  # signed out: no data
            cookie = self.sign_in(base)
            state = json.load(urlopen(Request(base + '/api/state', headers={'Cookie': cookie})))
            self.assertEqual('owner@example.test', state['user']['email'])
            self.assertNotIn('password_hash', json.dumps(state))
            self.assertEqual(6, len(state['categories']))
            self.assertNotIn('users', state)
            self.assertIsInstance(state['expenses'][0]['amount'], float)
            req = Request(base + '/api/budget', data=b'{}', headers={'Content-Type': 'application/json', 'Origin': 'https://untrusted.example', 'Cookie': cookie})
            with self.assertRaises(HTTPError) as error:
                urlopen(req)
            self.assertEqual(403, error.exception.code)
            with self.assertRaises(HTTPError) as error:  # no Origin at all is refused too: fail closed
                urlopen(Request(base + '/api/budget', data=b'{}', headers={'Content-Type': 'application/json', 'Cookie': cookie}))
            self.assertEqual(403, error.exception.code)
            req = Request(base + '/api/expenses', data=b'{broken', headers={'Content-Type': 'application/json', 'Origin': base, 'Cookie': cookie})

            with self.assertRaises(HTTPError) as error:
                urlopen(req)
            self.assertEqual(400, error.exception.code)
        finally:
            http.shutdown()
            http.server_close()
            thread.join()


    def _serve(self):
        http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        return http, thread, f'http://127.0.0.1:{http.server_port}'

    def test_https_page_can_save(self):
        # hosted over https the browser sends Origin: https://host; that must count as same-site
        http, thread, base = self._serve()
        try:
            host = base.split('//')[1]
            cookie = self.sign_in(base)
            body = json.dumps({'category_id': 4, 'description': 'From https', 'amount': '10.00', 'expense_date': '2028-02-01'}).encode()
            req = Request(base + '/api/expenses', data=body, headers={'Content-Type': 'application/json', 'Origin': f'https://{host}', 'Cookie': cookie})
            self.assertEqual(200, urlopen(req).status)
            self.assertEqual(1, self.one("SELECT COUNT(*) AS n FROM expenses WHERE description = 'From https'")['n'])
        finally:
            http.shutdown(); http.server_close(); thread.join()

    def post(self, base, path, data, cookie=None):
        headers = {'Content-Type': 'application/json', 'Origin': base, **({'Cookie': cookie} if cookie else {})}
        return urlopen(Request(base + path, data=json.dumps(data).encode(), headers=headers))

    def sign_in(self, base, email='owner@example.test', password='correct horse battery'):
        """Register over HTTP (the first account claims the demo data) and return the session cookie."""
        response = self.post(base, '/api/auth/register', {'full_name': 'Owner', 'email': email, 'password': password})
        return response.headers['Set-Cookie'].split(';')[0]

    def test_database_survives_a_commit(self):
        # regression: after COMMIT the connection used to fall back to the default schema (the real data)
        db = server.connect()
        try:
            for end in (db.commit, db.rollback):
                end()
                self.assertEqual(TEST_DB, server.q(db, 'SELECT DATABASE() AS name').fetchone()['name'])
        finally:
            db.close()

    def test_password_hashing(self):
        stored = auth.hash_password('correct horse battery')
        self.assertTrue(stored.startswith('scrypt$'))
        self.assertNotIn('correct horse', stored)
        self.assertNotEqual(stored, auth.hash_password('correct horse battery'))  # fresh salt every time
        self.assertTrue(auth.verify_password('correct horse battery', stored))
        self.assertFalse(auth.verify_password('correct horse batterz', stored))
        for junk in ['', 'disabled-demo-login', 'scrypt$x$y', 'scrypt$16384$8$1$!!$!!']:
            self.assertFalse(auth.verify_password('anything', junk))

    def test_first_account_claims_the_data_and_others_are_separate(self):
        db = server.connect()
        try:
            owner = server.register(db, {'full_name': 'Ghian', 'email': ' Owner@Example.TEST ', 'password': 'correct horse battery'})
            friend = server.register(db, {'full_name': 'Friend', 'email': 'friend@example.test', 'password': 'another long secret'})
            db.commit()
        finally:
            db.close()
        self.assertEqual(1, owner)  # took over the unclaimed demo user, so the existing wishes are theirs
        self.assertNotEqual(1, friend)
        self.assertEqual('owner@example.test', self.one('SELECT email FROM users WHERE user_id = 1')['email'])
        self.assertEqual(4, len(server.read_state(owner)['wishlist_items']))
        mine = server.read_state(friend)
        self.assertEqual(([], [], [], []), (mine['wishlist_items'], mine['expenses'], mine['decision_logs'], mine['monthly_budgets']))
        self.assertEqual(6, len(mine['categories']))
        # the friend cannot touch the owner's records by guessing ids
        expense = self.one('SELECT expense_id FROM expenses WHERE user_id = 1 LIMIT 1')['expense_id']
        for path, data in [('/api/wishlist/update', {'wishlist_item_id': 2, 'item_name': 'Mine now', 'estimated_price': '1', 'category_id': 1}),
                           ('/api/wishlist/delete', {'wishlist_item_id': 2}),
                           ('/api/decisions', {'wishlist_item_id': 1, 'decision': 'skip'}),
                           ('/api/expenses/update', {'expense_id': expense, 'description': 'x', 'amount': '1', 'category_id': 1, 'expense_date': '2028-01-01'}),
                           ('/api/expenses/delete', {'expense_id': expense})]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.action(path, data, friend)
        self.action('/api/wishlist', {'item_name': 'Friend wish', 'estimated_price': '50', 'wait_hours': 24, 'category_id': 2}, friend)
        self.action('/api/budget', {'budget_year': 2028, 'budget_month': 1, 'budget_amount': '900'}, friend)
        self.assertEqual(['Friend wish'], [w['item_name'] for w in server.read_state(friend)['wishlist_items']])
        self.assertNotIn('Friend wish', [w['item_name'] for w in server.read_state(owner)['wishlist_items']])
        with self.assertRaises(ValueError):  # same email, different case
            self.action_register({'full_name': 'Copy', 'email': 'OWNER@example.test', 'password': 'correct horse battery'})
        for bad in [{'full_name': 'A', 'email': 'not-an-email', 'password': 'correct horse battery'},
                    {'full_name': 'A', 'email': 'a@example.test', 'password': 'short'},
                    {'full_name': '', 'email': 'b@example.test', 'password': 'correct horse battery'}]:
            with self.subTest(bad=bad['email']), self.assertRaises(ValueError):
                self.action_register(bad)

    def action_register(self, data):
        db = server.connect()
        try:
            ident = server.register(db, data)
            db.commit()
            return ident
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def test_signup_code_gates_new_accounts(self):
        original = server.SIGNUP_CODE
        server.SIGNUP_CODE = 'otter-club'
        try:
            for code in [None, '', 'wrong']:
                with self.subTest(code=code), self.assertRaises(ValueError):
                    self.action_register({'full_name': 'A', 'email': 'a@example.test', 'password': 'correct horse battery', 'signup_code': code})
            self.assertEqual(1, self.action_register({'full_name': 'A', 'email': 'a@example.test', 'password': 'correct horse battery', 'signup_code': 'otter-club'}))
        finally:
            server.SIGNUP_CODE = original

    def test_sessions(self):
        self.action_register({'full_name': 'Owner', 'email': 'owner@example.test', 'password': 'correct horse battery'})
        db = server.connect()
        try:
            for email, password in [('owner@example.test', 'wrong password!'), ('nobody@example.test', 'correct horse battery')]:
                with self.subTest(email=email), self.assertRaises(ValueError) as caught:
                    server.login(db, {'email': email, 'password': password}, '203.0.113.9')
                self.assertEqual('Email or password is incorrect.', str(caught.exception))  # never says which one
            db.commit()  # keep the failed attempts on record
            token = server.login(db, {'email': 'OWNER@example.test', 'password': 'correct horse battery'}, '203.0.113.9')
            db.commit()
            self.assertGreaterEqual(len(token), 40)
            self.assertIsNone(self.one('SELECT 1 FROM sessions WHERE session_id = %s', (token,)))  # only a hash of the token is stored
            self.assertEqual(1, server.session_user(db, token)['user_id'])
            self.assertIsNone(server.session_user(db, token + 'x'))
            self.assertIsNone(server.session_user(db, ''))
            server.q(db, "UPDATE sessions SET expires_at = '2020-01-01 00:00:00'")
            self.assertIsNone(server.session_user(db, token))  # expired
            db.rollback()
            server.logout(db, token)
            db.commit()
            self.assertIsNone(server.session_user(db, token))
        finally:
            db.close()

    def test_login_rate_limit(self):
        self.action_register({'full_name': 'Owner', 'email': 'owner@example.test', 'password': 'correct horse battery'})
        db = server.connect()
        try:
            for _ in range(server.MAX_FAILED_LOGINS):
                with self.assertRaises(ValueError):
                    server.login(db, {'email': 'owner@example.test', 'password': 'guess guess guess'}, '203.0.113.9')
                db.commit()
            with self.assertRaises(ValueError) as caught:  # even the right password waits now, from that network
                server.login(db, {'email': 'owner@example.test', 'password': 'correct horse battery'}, '203.0.113.9')
            self.assertIn('Too many', str(caught.exception))
            db.rollback()
            # ...but the owner, on their own network, is not locked out by a stranger's guesses
            self.assertTrue(server.login(db, {'email': 'owner@example.test', 'password': 'correct horse battery'}, '198.51.100.7'))
            db.commit()
        finally:
            db.close()

    def test_signup_code_cannot_be_guessed_at_speed(self):
        original = server.SIGNUP_CODE
        server.SIGNUP_CODE = 'otter-club'
        db = server.connect()
        try:
            person = {'full_name': 'A', 'email': 'a@example.test', 'password': 'correct horse battery'}
            for _ in range(server.MAX_FAILED_LOGINS):
                with self.assertRaises(ValueError):
                    server.register(db, {**person, 'signup_code': 'nope'}, '203.0.113.9')
                db.commit()
            with self.assertRaises(ValueError) as caught:  # the right code no longer works from that network
                server.register(db, {**person, 'signup_code': 'otter-club'}, '203.0.113.9')
            self.assertIn('Too many', str(caught.exception))
        finally:
            server.SIGNUP_CODE = original
            db.rollback()
            db.close()

    def test_forwarded_header_is_not_trusted_off_vercel(self):
        class Fake(server.Handler):
            def __init__(self):  # no socket: only the two attributes client_ip() reads
                self.headers = {'X-Forwarded-For': '1.2.3.4', 'x-vercel-forwarded-for': '5.6.7.8'}
                self.client_address = ('192.0.2.10', 5555)
        saved = os.environ.pop('VERCEL', None)
        try:
            self.assertEqual('192.0.2.10', Fake().client_ip())  # a typed-in header cannot dodge the rate limit
            os.environ['VERCEL'] = '1'
            self.assertEqual('5.6.7.8', Fake().client_ip())
        finally:
            os.environ.pop('VERCEL', None)
            if saved is not None:
                os.environ['VERCEL'] = saved

    def google_claims(self, **changes):
        return {'iss': 'https://accounts.google.com', 'aud': 'test-client-id', 'exp': time.time() + 600, 'sub': 'g-1001',
                'email': 'Owner@Example.test', 'email_verified': True, 'name': 'Owner G', **changes}

    def with_google(self):
        saved = (server.GOOGLE_CLIENT_ID, server.GOOGLE_CLIENT_SECRET, server.fetch_google_claims)
        server.GOOGLE_CLIENT_ID, server.GOOGLE_CLIENT_SECRET = 'test-client-id', 'test-secret'
        self.addCleanup(lambda: setattr(server, 'GOOGLE_CLIENT_ID', saved[0]) or setattr(server, 'GOOGLE_CLIENT_SECRET', saved[1]) or setattr(server, 'fetch_google_claims', saved[2]))

    def test_google_claims_are_checked(self):
        self.with_google()
        self.assertEqual(('g-1001', 'owner@example.test', 'Owner G'), server.google_identity(self.google_claims()))
        for bad in [{'iss': 'https://evil.example'}, {'aud': 'someone-elses-app'}, {'exp': time.time() - 5}, {'email_verified': False},
                    {'email_verified': 'true'}, {'sub': ''}, {'email': None}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                server.google_identity(self.google_claims(**bad))

    def test_google_sign_in_accounts(self):
        self.with_google()
        original = (server.SIGNUP_CODE, server.GOOGLE_SIGNUP)
        server.SIGNUP_CODE = 'otter-club'
        self.addCleanup(lambda: setattr(server, 'SIGNUP_CODE', original[0]) or setattr(server, 'GOOGLE_SIGNUP', original[1]))
        db = server.connect()
        try:
            server.GOOGLE_SIGNUP = 'invite'
            with self.assertRaises(ValueError):  # invite mode: a brand-new Google person needs the code
                server.google_sign_in(db, self.google_claims(), '', '203.0.113.9')
            db.commit()
            server.GOOGLE_SIGNUP = 'open'
            owner = server.google_sign_in(db, self.google_claims(), '', '203.0.113.9')  # open: Google alone is enough
            db.commit()
            self.assertEqual(1, owner)  # first account, so it claims the existing data
            self.assertEqual(owner, server.google_sign_in(db, self.google_claims(email='changed@example.test'), '', '203.0.113.9'))  # known Google id, even if the email changed
            with self.assertRaises(ValueError):  # made with Google, so no password works, not even the placeholder text
                server.login(db, {'email': 'owner@example.test', 'password': server.GOOGLE_ONLY}, '203.0.113.9')
            db.commit()
            stranger = server.google_sign_in(db, self.google_claims(sub='g-3003', email='new@example.test', name='New Person'), '', '198.51.100.20')
            db.commit()
            self.assertNotIn(stranger, (owner,))
            self.assertEqual([], server.read_state(stranger)['wishlist_items'])  # a new person starts empty and sees nobody else's data
        finally:
            db.close()

    def test_google_link_voids_an_unverified_password(self):
        # someone with an invite pre-registers a victim's address, hoping the victim later signs in with Google
        self.with_google()
        db = server.connect()
        try:
            squatter = server.register(db, {'full_name': 'Not Really', 'email': 'victim@example.test', 'password': 'attacker knows this one'}, '203.0.113.9')
            token = server.start_session(db, squatter)
            db.commit()
            victim = server.google_sign_in(db, self.google_claims(sub='g-4004', email='victim@example.test'), '', '198.51.100.7')
            db.commit()
            self.assertEqual(squatter, victim)  # same row...
            self.assertIsNone(server.session_user(db, token))  # ...but the squatter is signed out
            with self.assertRaises(ValueError):  # ...and their password no longer opens it
                server.login(db, {'email': 'victim@example.test', 'password': 'attacker knows this one'}, '203.0.113.9')
            db.commit()
        finally:
            db.close()

    def test_new_google_accounts_are_rate_limited_per_network(self):
        self.with_google()
        db = server.connect()
        try:
            for n in range(server.MAX_NEW_GOOGLE_ACCOUNTS):
                server.google_sign_in(db, self.google_claims(sub=f'g-{n}', email=f'p{n}@example.test'), '', '203.0.113.50')
                db.commit()
            with self.assertRaises(ValueError) as caught:
                server.google_sign_in(db, self.google_claims(sub='g-extra', email='extra@example.test'), '', '203.0.113.50')
            self.assertIn('Too many', str(caught.exception))
            db.rollback()
            self.assertTrue(server.google_sign_in(db, self.google_claims(sub='g-0', email='p0@example.test'), '', '203.0.113.50'))  # existing people still get in
        finally:
            db.rollback()
            db.close()

    def test_google_http_flow(self):
        self.with_google()  # restores the real settings afterwards
        server.GOOGLE_CLIENT_ID = server.GOOGLE_CLIENT_SECRET = ''  # start from "not set up", whatever this laptop's .env says
        http, thread, base = self._serve()
        try:
            with self.assertRaises(HTTPError) as error:  # not configured: the route does not exist
                urlopen(base + '/api/auth/google/start')
            self.assertEqual(404, error.exception.code)
            self.assertFalse(json.load(urlopen(base + '/api/auth/options'))['google'])
            server.GOOGLE_CLIENT_ID, server.GOOGLE_CLIENT_SECRET = 'test-client-id', 'test-secret'
            self.assertTrue(json.load(urlopen(base + '/api/auth/options'))['google'])

            class NoRedirect(HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None
            opener = build_opener(NoRedirect)

            def hop(path, cookie=''):
                try:
                    opener.open(Request(base + path, headers={'Cookie': cookie} if cookie else {}))
                except HTTPError as response:
                    return response
                self.fail('expected a redirect')

            start = hop('/api/auth/google/start')
            self.assertEqual(302, start.code)
            location = urlparse(start.headers['Location'])
            query = parse_qs(location.query)
            self.assertEqual(('accounts.google.com', ['test-client-id'], ['code']), (location.netloc, query['client_id'], query['response_type']))
            self.assertEqual([base + '/api/auth/google/callback'], query['redirect_uri'])
            oauth_cookie = start.headers['Set-Cookie'].split(';')[0]
            self.assertIn('HttpOnly', start.headers['Set-Cookie'])
            self.assertEqual(1, len(query['nonce']))  # the request carries an OIDC nonce
            server.fetch_google_claims = lambda code, redirect_uri: self.google_claims(nonce=query['nonce'][0])
            # a callback whose state does not match this browser's cookie is refused (login CSRF)
            forged = hop('/api/auth/google/callback?code=abc&state=not-the-state', oauth_cookie)
            self.assertEqual('/app?auth_error=google', forged.headers['Location'])
            self.assertNotIn('hc_school_session=', str(forged.headers))
            # an ID token minted for someone else's sign-in carries the wrong nonce and is refused
            server.fetch_google_claims = lambda code, redirect_uri: self.google_claims(nonce='another-request')
            replayed = hop(f"/api/auth/google/callback?code=abc&state={query['state'][0]}", oauth_cookie)
            self.assertEqual('/app?auth_error=google', replayed.headers['Location'])
            self.assertNotIn('hc_school_session=', str(replayed.headers))
            server.fetch_google_claims = lambda code, redirect_uri: self.google_claims(nonce=query['nonce'][0])
            done = hop(f"/api/auth/google/callback?code=abc&state={query['state'][0]}", oauth_cookie)
            self.assertEqual('/', done.headers['Location'])
            session = [c for c in done.headers.get_all('Set-Cookie') if c.startswith('hc_school_session=')][0].split(';')[0]
            state = json.load(urlopen(Request(base + '/api/state', headers={'Cookie': session})))
            self.assertEqual('owner@example.test', state['user']['email'])
        finally:
            http.shutdown(); http.server_close(); thread.join()

    def test_http_login_cookie(self):
        http, thread, base = self._serve()
        try:
            cookie_header = self.post(base, '/api/auth/register', {'full_name': 'Owner', 'email': 'owner@example.test', 'password': 'correct horse battery'}).headers['Set-Cookie']
            for flag in ['HttpOnly', 'SameSite=Lax', 'Path=/', 'Max-Age=']:
                self.assertIn(flag, cookie_header)
            page = urlopen(base + '/')
            self.assertIn("frame-ancestors 'none'", page.headers['Content-Security-Policy'])
            self.assertEqual('DENY', page.headers['X-Frame-Options'])
            cookie = cookie_header.split(';')[0]
            self.assertEqual(200, urlopen(Request(base + '/api/state', headers={'Cookie': cookie})).status)
            self.assertEqual(200, self.post(base, '/api/auth/logout', {}, cookie).status)
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(base + '/api/state', headers={'Cookie': cookie}))
            self.assertEqual(401, error.exception.code)
            with self.assertRaises(HTTPError) as error:
                self.post(base, '/api/expenses', {'category_id': 4, 'description': 'No session', 'amount': '10', 'expense_date': '2028-02-01'})
            self.assertEqual(401, error.exception.code)
            again = self.post(base, '/api/auth/login', {'email': 'owner@example.test', 'password': 'correct horse battery'})
            self.assertIn('hc_school_session=', again.headers['Set-Cookie'])
            front = urlopen(base + '/').read().decode()
            self.assertIn('l-hero', front)  # signed out: the front door is the landing page
            for path in ['/app', '/login', '/signup', '/login/']:
                with self.subTest(path=path):
                    self.assertIn('id="sheet"', urlopen(base + path).read().decode())  # always the app, which shows its own sign-in
            self.assertIn('l-hero', urlopen(Request(base + '/welcome', headers={'Cookie': again.headers['Set-Cookie'].split(';')[0]})).read().decode())  # the landing page even when signed in
            self.assertIn('id="sheet"', urlopen(Request(base + '/', headers={'Cookie': again.headers['Set-Cookie'].split(';')[0]})).read().decode())  # signed in: the front door is the app
        finally:
            http.shutdown(); http.server_close(); thread.join()

    def test_database_url_parsing(self):
        saved = {k: os.environ.get(k) for k in ('HYPECHECK_DATABASE_URL', 'HYPECHECK_DB_SSL_CA_PEM', 'HYPECHECK_DB_SSL_CA')}
        try:
            os.environ.pop('HYPECHECK_DB_SSL_CA_PEM', None)
            os.environ.pop('HYPECHECK_DB_SSL_CA', None)
            os.environ['HYPECHECK_DATABASE_URL'] = 'mysql://app%40x:p%23ss@db.example.com:12345/hc?ssl-mode=REQUIRED'
            config = server.db_config()
            self.assertEqual(('db.example.com', 12345, 'app@x', 'p#ss', 'hc'),
                             (config['host'], config['port'], config['user'], config['password'], config['database']))
            self.assertIsInstance(config['ssl'], ssl.SSLContext)
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == '__main__':
    unittest.main()
