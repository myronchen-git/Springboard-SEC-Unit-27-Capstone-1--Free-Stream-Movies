import re
from typing import Self

from flask_bcrypt import Bcrypt
from flask_login import UserMixin
from sqlalchemy import CheckConstraint
from sqlalchemy.exc import IntegrityError

from src.exceptions.UserRegistrationError import UserRegistrationError
from src.models.common import db

# ==================================================

bcrypt = Bcrypt()

# --------------------------------------------------


class User(db.Model, UserMixin):
    """Represents a user."""

    MIN_PASS_LENGTH = 6

    # password regex:
    # https://stackoverflow.com/a/21456918
    _ESCAPED_SYMBOLS = re.escape(r"""!@#$%^&*()-=[];',./_+{}:"<>?""")
    PASSWORD_REGEX_PATTERN = (rf'^(?=.*[a-z])'
                              rf'(?=.*[A-Z])'
                              rf'(?=.*\d)'
                              rf'(?=.*[{_ESCAPED_SYMBOLS}])'
                              rf'[A-Za-z\d{_ESCAPED_SYMBOLS}]{{{MIN_PASS_LENGTH},}}$')

    PASSWORD_REQUIREMENTS_TEXT = ('Password must contain at least one uppercase letter, '
                                  'one lowercase letter, one number, one special character, '
                                  f'and be at least {MIN_PASS_LENGTH} characters long.')

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

    @classmethod
    def register(cls, user_data: dict) -> Self:
        """
        Saves user info into database.

        :param user_data: A dict containing all of the User properties except id.
        :return: User object if successful.
        :raises UserRegistrationError: If user_data does not have all of the properties, excluding id;
            or if database throws an error, such as if the username or email is already taken.
        """

        required_properties = [
            column.key
            for column in cls.__table__.columns
            if column.key != 'id' and not column.nullable
        ]

        for prop in required_properties:
            if not user_data.get(prop):
                raise UserRegistrationError(
                    f"Missing {prop} for user registration.")

        # Put user data into new dictionary if data is a table column, other than ID, and if value is truthy.
        data = {k: v for k, v in user_data.items()
                if k in cls.__table__.columns and k != 'id' and v}

        if not re.match(cls.PASSWORD_REGEX_PATTERN, data["password"]):
            raise UserRegistrationError(cls.PASSWORD_REQUIREMENTS_TEXT)

        data["password"] = bcrypt.generate_password_hash(
            data["password"]).decode("utf8")
        user = cls(**data)

        db.session.add(user)
        try:
            db.session.commit()
            return user
        except IntegrityError:  # can catch other non-duplicate integrity errors; need to revisit
            db.session.rollback()
            raise UserRegistrationError("Duplicate username or email.")

    @classmethod
    def authenticate(cls, username: str, password: str) -> Self | False:
        """
        Verifies that username and password are correct by checking the database to see if a user with the provided
        username exists, and that the password matches with that user.

        :param username: A registered username.
        :param password: The password belonging to the username.
        :return: User object if valid, else returns False.
        """

        user = db.session.query(User).filter_by(
            username=username).one_or_none()

        if user and bcrypt.check_password_hash(user.password, password):
            return user
        else:
            return False
