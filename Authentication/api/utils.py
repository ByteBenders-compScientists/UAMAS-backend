from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from flask import current_app
from dotenv import load_dotenv
import random
import string
import os

load_dotenv()

valid_domains = ['uonbi.ac.ke', 'mu.ac.ke', 'ku.ac.ke', 'jkuat.ac.ke', 'egerton.ac.ke', 'maseno.ac.ke', 'mmust.ac.ke',
                 'tukenya.ac.ke', 'tum.ac.ke', 'dkut.ac.ke', 'chuka.ac.ke', 'karatinauniversity.ac.ke', 'kisiiuniversity.ac.ke',
                 'mmarau.ac.ke', 'pu.ac.ke', 'seku.ac.ke', 'jooust.ac.ke', 'kibu.ac.ke', 'laikipia.ac.ke', 'mksu.ac.ke', 'must.ac.ke',
                 'mmu.ac.ke', 'mut.ac.ke', 'embuni.ac.ke', 'uoeld.ac.ke', 'kabianga.ac.ke', 'cuk.ac.ke', 'gau.ac.ke', 'rongovarsity.ac.ke',
                 'ttu.ac.ke', 'kyu.ac.ke', 'au.ac.ke', 'kafu.ac.ke', 'tmu.ac.ke', 'tharaka.ac.ke', 'ouk.ac.ke', 'ndu.ac.ke', 'buc.ac.ke',
                 'ksu.ac.ke', 'mnu.ac.ke', 'tuc.ac.ke', 'unika.ac.ke', 'strathmore.edu', 'usiu.ac.ke', 'daystar.ac.ke', 'mku.ac.ke', 'cuea.edu',
                 'anu.ac.ke', 'spu.ac.ke', 'kabarak.ac.ke', 'kca.ac.ke', 'kemu.ac.ke', 'zetech.ac.ke', 'pacuniversity.ac.ke', 'aiu.ac.ke', 'iuk.ac.ke',
                 'tangaza.ac.ke', 'ueab.ac.ke', 'umma.ac.ke', 'aku.edu', 'aua.ac.ke', 'east.ac.ke', 'scott.ac.ke', 'kwust.ac.ke', 'kheu.ac.ke',
                 'lukenyauniversity.ac.ke', 'gluk.ac.ke', 'puea.ac.ke', 'teau.ac.ke', 'amref.ac.ke', 'riarauniversity.ac.ke', 'mua.ac.ke',
                 'gretsauniversity.ac.ke', 'piu.ac.ke', 'uzimauniversity.ac.ke', 'kenya.ilu.edu', 'riu.ac.ke', 'miuc.ac.ke', 'kgs.ac.ke',
                 'nairobipoly.ac.ke', 'kisumupoly.ac.ke', 'tenp.ac.ke', 'kabetepolytechnic.ac.ke', 'nyerinationalpoly.ac.ke', 'sigalagalapoly.ac.ke',
                 'mnp.ac.ke', 'kitalenationalpolytechnic.ac.ke', 'kenyacoastpoly.ac.ke', 'kisiipoly.ac.ke', 'baringonationalpolytechnic.ac.ke',
                 'nyandaruanationalpoly.ac.ke', 'mawegopoly.ac.ke', 'bumbepoly.ac.ke', 'kerichopoly.ac.ke', 'wotetti.ac.ke', 'kerokatechnical.ac.ke',
                 'michukitech.ac.ke', 'sikriblinddeaf.ac.ke', 'okametvc.ac.ke', 'gatundusouthtvc.ac.ke', 'sist.ac.ke', 'tonp.ac.ke', 'kgs.ac.ke',
                 'ndu.ac.ke', 'ndu.ac.ke/niruc', 'ndu.ac.ke/ndc', 'ndu.ac.ke/dchs', 'ipstc.org'
                ]

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


def is_valid_institution_email(email: str) -> bool:
    """
    Validates if the email belongs to a recognized educational institution domain.
    """
    try:
        domain = email.split('@')[1].lower()
        # check if also for subdomains added to the domain e.g student.uonbi.ac.ke. check for pattern ending with valid domain
        for valid_domain in valid_domains:
            if domain == valid_domain or domain.endswith('.' + valid_domain):
                return True
        return False
    except IndexError:
        return False

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

# send notification email to the user after creating an account successfully
def send_account_creation_email(to_email: str, reciever_fname: str, reciever_lname: str) -> bool:
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
    You can now log in using your institutional email.

        link: https://intelli-mark-swart.vercel.app

    We look forward to supporting your learning journey.

    Thank you,
    UAMAS Team
    """
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def generate_numeric_code(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def generate_join_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=length))


def send_verification_email(to_email: str, verification_code: str) -> bool:
    try:
        mail = Mail(current_app)
        if not current_app.config.get('MAIL_DEBUG', False):
            import smtplib
            smtplib.SMTP.debuglevel = 0
        msg = Message(
            "IntelliLearn Email Verification",
            sender=os.getenv('MAIL_USERNAME'),
            recipients=[to_email]
        )
        msg.body = (
            f"Your IntelliLearn verification code is: {verification_code}\n\n"
            "This code will expire in 15 minutes. If you did not request this, "
            "you can ignore this email."
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send verification email: {e}")
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
