from flask import Flask
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint

# ==================================================

bcrypt = Bcrypt()
db = SQLAlchemy()

# --------------------------------------------------


def connect_db(app: Flask):
    """Connect this database to provided Flask app."""

    with app.app_context():
        db.app = app
        db.init_app(app)


class User(db.Model):
    """Represents a user."""

    __tablename__ = 'users'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    username = db.Column(
        db.Text,
        CheckConstraint("TRIM(username) != ''"),
        nullable=False,
        unique=True,
    )

    password = db.Column(
        db.Text,
        CheckConstraint("TRIM(password) != ''"),
        nullable=False,
    )

    email = db.Column(
        db.Text,
        CheckConstraint("TRIM(email) != ''"),
        nullable=False,
        unique=True,
    )

    def __repr__(self) -> str:
        """Show info about user."""

        return (
            f"<User("
            f"username='{self.username}', "
            f"password='{self.password}', "
            f"email='{self.email}')>"
        )
