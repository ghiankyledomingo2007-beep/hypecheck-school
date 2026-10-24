"""Password and session-token helpers. Standard library only; no database access here."""
import base64
import hashlib
import hmac
import secrets

# scrypt cost: N=2^14, r=8, p=1 uses about 16 MB and tens of milliseconds per check.
SCRYPT_N, SCRYPT_R, SCRYPT_P, KEY_BYTES = 2 ** 14, 8, 1, 32


def _scrypt(password, salt, n, r, p):
    return hashlib.scrypt(password.encode('utf-8'), salt=salt, n=n, r=r, p=p, dklen=KEY_BYTES, maxmem=64 * 1024 * 1024)


def hash_password(password):
    """Return `scrypt$N$r$p$salt$key` (base64 parts) with a fresh random salt."""
    salt = secrets.token_bytes(16)
    key = _scrypt(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return '$'.join(['scrypt', str(SCRYPT_N), str(SCRYPT_R), str(SCRYPT_P),
                     base64.b64encode(salt).decode(), base64.b64encode(key).decode()])


def verify_password(password, stored):
    """True only for a matching scrypt hash. Anything malformed (or the demo placeholder) is simply False."""
    try:
        scheme, n, r, p, salt, key = stored.split('$')
        if scheme != 'scrypt':
            return False
        n, r, p = int(n), int(r), int(p)
        if not (2 ** 10 <= n <= 2 ** 20 and 1 <= r <= 32 and 1 <= p <= 16):  # refuse absurd costs from a tampered row
            return False
        expected = base64.b64decode(key, validate=True)
        actual = _scrypt(password, base64.b64decode(salt, validate=True), n, r, p)
    except (ValueError, TypeError, AttributeError):
        return False
    return hmac.compare_digest(actual, expected)


# Checked when the email is unknown, so a wrong email costs the same time as a wrong password.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def new_token():
    return secrets.token_urlsafe(32)


def token_hash(token):
    """Sessions are stored by hash, so a leaked database cannot be replayed as cookies."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()
