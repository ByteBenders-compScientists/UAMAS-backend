from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from flask import current_app
from dotenv import load_dotenv
import random
import string
import os

load_dotenv()
    

def hashing_password(password: str) -> str:
    """
    Uses Werkzeug’s PBKDF2+SHA256 to hash the given password.
    """
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


# JWT token revocation store
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

# # email notification for lecturers creation and temporary password
def send_email(to_email: str, reciever_fname: str, reciever_lname: str, temp_password: str) -> bool:
    try:
        mail = Mail(current_app)
        # Control SMTP debugging based on configuration
        if not current_app.config.get('MAIL_DEBUG', False):
            # Disable SMTP debugging to prevent verbose output
            import smtplib
            smtplib.SMTP.debuglevel = 0
        msg = Message("Welcome to the IntelliLearn!",
                    sender=os.getenv('MAIL_USERNAME'),
                    recipients=[to_email])
        msg.body = f"""
    Dear {reciever_lname} {reciever_fname},

    Welcome to the IntelliLearn! Your account has been created successfully.
    Please find your temporary password below:

        Temporary Password: {temp_password}
        link: https://intelli-mark-swart.vercel.app

    Please log in and change your password as soon as possible.

    Thank you,
    UAMAS Team
    """
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
    
# # email notification for lecturers password reset by their own request
def send_password_reset_email(to_email: str, reciever_fname: str, reciever_lname: str) -> bool:
    try:
        mail = Mail(current_app)
        # Control SMTP debugging based on configuration
        if not current_app.config.get('MAIL_DEBUG', False):
            # Disable SMTP debugging to prevent verbose output
            import smtplib
            smtplib.SMTP.debuglevel = 0
        msg = Message("IntelliLearn Password Reset",
                    sender=os.getenv('MAIL_USERNAME'),
                    recipients=[to_email])
        msg.body = f"""
    Dear {reciever_lname} {reciever_fname},

    Your password has been reset successfully.
    If you did not request this change, please contact support immediately.

    Thank you,
    UAMAS Team
    """
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
