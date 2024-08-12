import sys
from os.path import abspath, dirname, join

# Adds src folder as a working directory.
# This is needed so that imports can be found.
src_dir = abspath(join(dirname(__file__), '../../src'))  # nopep8
sys.path.append(src_dir)  # nopep8

# --------------------------------------------------

from types import MappingProxyType
from unittest import TestCase

from sqlalchemy.exc import IntegrityError

from app import create_app
from exceptions.UserRegistrationError import UserRegistrationError
from models.common import connect_db, db
from models.user import User

# ==================================================

app = create_app("freestreammovies_test", testing=True)
connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------

_USER_DATA_1 = MappingProxyType({
    "username": "testuser1",
    "password": "HASHED_PASSWORD",
    "email": "test1@test.com",
})

_USER_DATA_2 = MappingProxyType({
    "username": "testuser2",
    "password": "HASHED_PASSWORD",
    "email": "test2@test.com",
})


class UserModelTestCase(TestCase):
    """Tests for User model."""

    def setUp(self):
        db.session.query(User).delete()
        db.session.commit()

    def tearDown(self):
        db.session.rollback()

    def test_user_creation_in_database(self):
        """Tests that a user can be created in the database."""

        # Arrange
        user = User(**_USER_DATA_1)

        # Act
        db.session.add(user)
        db.session.commit()

        # Assert
        users = db.session.query(User).all()

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, _USER_DATA_1['username'])
        self.assertTrue(users[0].password)
        self.assertEqual(users[0].email, _USER_DATA_1['email'])

    def test_null_info_in_user_creation(self):
        """Tests that giving null properties during user creation results in an integrity error."""

        # Arrange
        null_properties = ["username", "password", "email"]

        for property in null_properties:
            with self.subTest(null_property=property):
                data = dict(_USER_DATA_1)
                data[property] = None

                user = User(**data)

        # Act/Assert
                db.session.add(user)
                db.session.commit
                self.assertRaises(IntegrityError, db.session.commit)

        # clean up
                # needed since subtest is not a true parametrized test
                db.session.rollback()

    def test_empty_string_info_in_user_creation(self):
        """Tests that giving empty string properties during user creation results in an integrity error."""

        # Arrange
        empty_properties = ["username", "password", "email"]

        for property in empty_properties:
            with self.subTest(empty_property=property):
                data = dict(_USER_DATA_1)
                data[property] = ""

                user = User(**data)

        # Act/Assert
                db.session.add(user)
                db.session.commit
                self.assertRaises(IntegrityError, db.session.commit)

        # clean up
                # needed since subtest is not a true parametrized test
                db.session.rollback()

    def test_nonunique_info_in_user_creation(self):
        """Tests that giving nonunique properties during user creation results in an integrity error."""

        # Arrange
        user1 = User(**_USER_DATA_1)
        db.session.add(user1)
        db.session.commit()

        nonunique_properties = {
            "username": _USER_DATA_1['username'],
            "email": _USER_DATA_1['email']
        }

        for property, value in nonunique_properties.items():
            with self.subTest(nonunique_property=property):
                data = dict(_USER_DATA_2)
                data[property] = value

                user = User(**data)

        # Act/Assert
                db.session.add(user)
                self.assertRaises(IntegrityError, db.session.commit)

        # clean up
                # needed since subtest is not a true parametrized test
                db.session.rollback()


class UserRegistrationTestCase(TestCase):
    """Tests for user registration."""

    def setUp(self):
        db.session.query(User).delete()
        db.session.commit()

    def tearDown(self):
        db.session.rollback()

    def test_user_registration(self):
        """Tests successfully registering a user."""

        # Act
        user = User.register(_USER_DATA_1)

        # Assert
        self.assertEqual(user.username, _USER_DATA_1['username'])
        self.assertTrue(user.password)
        self.assertNotEqual(user.password, _USER_DATA_1['password'])
        self.assertEqual(user.email, _USER_DATA_1['email'])

        users = db.session.query(User).all()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, _USER_DATA_1['username'])
        self.assertTrue(users[0].password)
        self.assertNotEqual(users[0].password, _USER_DATA_1['password'])
        self.assertEqual(users[0].email, _USER_DATA_1['email'])

    def test_user_registration_without_required_data(self):
        """Tests that registration fast-fails if required info is not given."""

        # Arrange
        required_properties = ["username", "password", "email"]

        for property in required_properties:
            with self.subTest(required_property=property):
                data = dict(_USER_DATA_1)
                data[property] = None

        # Act/Assert
                self.assertRaises(UserRegistrationError, User.register, data)

        # clean up
                # needed since subtest is not a true parametrized test
                db.session.rollback()

    def test_user_registration_with_empty_string_required_data(self):
        """Tests that registration fast-fails if required info is given as empty strings."""

        # Arrange
        required_properties = ["username", "password", "email"]

        for property in required_properties:
            with self.subTest(required_property=property):
                data = dict(_USER_DATA_1)
                data[property] = ""

        # Act/Assert
                self.assertRaises(UserRegistrationError, User.register, data)

        # clean up
                # needed since subtest is not a true parametrized test
                db.session.rollback()


class UserAuthenticateTestCase(TestCase):
    """Tests for user authentication."""

    def setUp(self):
        db.session.query(User).delete()
        db.session.commit()

    def tearDown(self):
        db.session.rollback()

    def test_user_authentication(self):
        """Tests successfully authenticating a user."""

        # Arrange
        User.register(_USER_DATA_1)

        # Act
        user = User.authenticate(
            _USER_DATA_1['username'], _USER_DATA_1['password'])

        # Assert
        self.assertTrue(user)
        self.assertEqual(user.username, _USER_DATA_1['username'])

    def test_user_authentication_with_nonexistent_username(self):
        """Authenticating with a nonexistent username should return False."""

        # Act
        user = User.authenticate(
            _USER_DATA_1['username'], _USER_DATA_1['password'])

        # Assert
        self.assertFalse(user)

    def test_user_authentication_with_incorrect_password(self):
        """Authenticating with an incorrect password should return False."""

        # Arrange
        User.register(_USER_DATA_1)
        diff_pass = "incorrect password"

        # Act
        user = User.authenticate(_USER_DATA_1['username'], diff_pass)

        # Assert
        self.assertFalse(user)
