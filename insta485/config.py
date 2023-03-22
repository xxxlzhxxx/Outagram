"""Insta485 development configuration."""


import pathlib


# Root of this application, useful if it doesn't occupy an entire domain
APPLICATION_ROOT = "/"


# Secret key for encrypting cookies
SECRET_KEY = (
    b"\xed\xdc>;\x8c\x8a\x14\x8b\x96\xc9\x00\x8b" +
    b"\xa9\xb7ZS\xd2F\x90\xf6\x9d[\xa7\x85"
)
SESSION_COOKIE_NAME = "login"


# File Upload to var/uploads/
INSTA485_ROOT = pathlib.Path(__file__).resolve().parent.parent
UPLOAD_FOLDER = INSTA485_ROOT / "var" / "uploads"
ALLOWED_EXTENSIONS = set(["png", "jpg", "jpeg", "gif"])
MAX_CONTENT_LENGTH = 16 * 1024 * 1024


SECRET_KEY = 'my_precious'
SECURITY_PASSWORD_SALT = 'my_precious_two'
# Mail Settings

MAIL_SERVER = "smtp.sjtu.edu.cn"
MAIL_PORT = 465
MAIL_USE_TLS = False
MAIL_USE_SSL = True
MAIL_DEBUG = False
MAIL_USERNAME = xxx
MAIL_PASSWORD = xxx
MAIL_SSL_VERIFY = False # disable SSL verification
# Database file is var/insta485.sqlite3
DATABASE_FILENAME = INSTA485_ROOT / "var" / "insta485.sqlite3"
