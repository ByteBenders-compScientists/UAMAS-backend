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


# # utility functions
# from flask_bcrypt import generate_password_hash, check_password_hash
# import uuid, random, string


# def hashing_password(password):
#     hashed_pswd = generate_password_hash(password, 14)

#     return hashed_pswd

# def compare_password(hashed_pwd, password):
#     matched = check_password_hash(hashed_pwd, password)

#     return matched

# Utility: generate random password
def gen_password(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))
