import logging
from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from db import db_read, db_write

# Logger für dieses Modul
logger = logging.getLogger(__name__)

login_manager = LoginManager()


class User(UserMixin):
    def __init__(self, id, username, password, role):
        self.id = id
        self.username = username
        self.password = password
        self.role = role

    @staticmethod
    def get_by_id(user_id):
        try:
            row = db_read(
                "SELECT * FROM users WHERE id = %s",
                (user_id,),
                single=True
            )
        except Exception:
            logger.exception("Error fetching user by id=%s", user_id)
            return None

        if row:
            return User(row["id"], row["username"], row["password"], row["role"])
        return None

    @staticmethod
    def get_by_username(username):
        try:
            row = db_read(
                "SELECT * FROM users WHERE username = %s",
                (username,),
                single=True
            )
        except Exception:
            logger.exception("Error fetching user by username=%s", username)
            return None

        if row:
            return User(row["id"], row["username"], row["password"], row["role"])
        return None


# Flask-Login
@login_manager.user_loader
def load_user(user_id):
    try:
        return User.get_by_id(int(user_id))
    except ValueError:
        logger.error("Invalid user_id format: %r", user_id)
        return None


# Helpers
def register_user(username, password, role):
    existing = User.get_by_username(username)
    if existing:
        return False

    hashed = generate_password_hash(password)
    try:
        user_id = db_write(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            (username, hashed, role),
            return_id=True
        )
        logger.info("User registered: %s", username)
    except Exception:
        logger.exception("Error registering user: %s", username)
        return False

    return user_id


def authenticate(username, password):
    user = User.get_by_username(username)

    if not user:
        return None

    if check_password_hash(user.password, password):
        logger.info("User logged in: %s", username)
        return user

    return None