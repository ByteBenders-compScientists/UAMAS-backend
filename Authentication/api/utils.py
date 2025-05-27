from werkzeug.security import generate_password_hash, check_password_hash
import random
import string

def hashing_password(password: str) -> str:
    """
    Uses Werkzeug’s PBKDF2+SHA256 to hash the given password.
    """
    # You can add salt length or method args here if you like:
    return generate_password_hash(password)

def compare_password(hashed_pwd: str, password: str) -> bool:
    """
    Verifies a plaintext password against the stored hash.
    """
    return check_password_hash(hashed_pwd, password)

def gen_password(length: int = 8) -> str:
    """
    Generates an alphanumeric temporary password.
    """
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

revoked_tokens = set()

def add_revoked_token(jti: str):
    """
    Adds a token to the revoked tokens set.
    """
    revoked_tokens.add(jti)


def is_token_revoked(jti: str) -> bool:
    """
    Checks if a token is revoked by its jti (JWT ID).
    """
    return jti in revoked_tokens