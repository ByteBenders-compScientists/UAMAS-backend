from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import random
import string
import os

load_dotenv()

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

# email notification for lecturers creation and temporary password
def send_email(to_email, reciever_fname, reciever_lname, temp_password):
    smtp_server = os.getenv('SMTP_SERVER')
    port = os.getenv('SMTP_PORT')
    sender_email = os.getenv('SENDER_EMAIL')
    password = os.getenv('SENDER_PASSWORD')

    subject = 'Welcome to the UAMAS System'
    body = f"""
            Dear {reciever_lname} {reciever_fname},
            Welcome to the UAMAS System!
            Your account has been created successfully. Please find your temporary password below:
            Temporary Password: {temp_password}
            Please log in and change your password as soon as possible.
            Thank you,
            UAMAS Team
        """

    # Set up the email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Connect & send
    with smtplib.SMTP_SSL(smtp_server, port) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, to_email, msg.as_string())
    
    return True

# email notification for lecturers password reset by their own request (set new own password)
def send_password_reset_email(to_email, reciever_fname, reciever_lname):
    smtp_server = os.getenv('SMTP_SERVER')
    port = os.getenv('SMTP_PORT')
    sender_email = os.getenv('SENDER_EMAIL')
    password = os.getenv('SENDER_PASSWORD')

    subject = 'UAMAS System Password Reset'
    body = f"""
            Dear {reciever_lname} {reciever_fname},
            Your password has been reset successfully.
            If you did not request this change, please contact support immediately.
            Thank you,
            UAMAS Team
        """
    # Set up the email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Connect & send
    with smtplib.SMTP_SSL(smtp_server, port) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, to_email, msg.as_string())
    
    return True
