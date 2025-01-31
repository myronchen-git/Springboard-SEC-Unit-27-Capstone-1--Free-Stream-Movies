import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from types import MappingProxyType
from unittest import TestCase
from unittest.mock import patch

from flask import url_for
from flask_login import current_user, logout_user
from sqlalchemy.exc import DatabaseError, DBAPIError

from src.app import create_app
from src.models.common import connect_db, db
from src.models.user import User

# ==================================================

app = create_app("freestreammovies_test", testing=True)
app.config.update(
    WTF_CSRF_ENABLED=False,
    SERVER_NAME="localhost:5000"
)

connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------

_USER_REGISTRATION_DATA_1 = MappingProxyType({
    "username": "testuser1",
    "password": "Aa1!123",
    "repeated_password": "Aa1!123",
    "email": "test1@test.com",
})


class UserRegistrationViewTestCase(TestCase):
    """Tests for user registration views."""

    def setUp(self):
        db.session.query(User).delete()
        db.session.commit()

        self.url = url_for("register_user")

    def tearDown(self):
        db.session.rollback()

    def test_display_user_registration_form(self):
        """Tests displaying the user registration form."""

        # Act
        with app.test_client() as client:
            resp = client.get(self.url)
            html = resp.get_data(as_text=True)

        # Assert
        self.assertEqual(resp.status_code, 200)
        self.assertIn("User Registration</h1>", html)
        self.assertIn("Username", html)
        self.assertIn("Password", html)
        self.assertIn("Repeat Password", html)
        self.assertIn("Email", html)

    def test_register_user(self):
        """Tests for successfully registering a user."""

        # Act
        with app.test_client() as client:
            resp = client.post(
                self.url,
                data=dict(_USER_REGISTRATION_DATA_1),
                follow_redirects=True)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Successfully registered.", html)

            user = db.session.query(User).one()
            self.assertEqual(
                user.username, _USER_REGISTRATION_DATA_1['username'])
            self.assertTrue(user.password)
            self.assertNotEqual(
                user.password, _USER_REGISTRATION_DATA_1['password'])
            self.assertEqual(user.email, _USER_REGISTRATION_DATA_1['email'])

            self.assertIsInstance(current_user, User)

        # cleanup
            logout_user()

    def test_registering_user_with_missing_required_info(self):
        """Tests that registering without required info should fail."""

        # Arrange
        missing_data_list = ["username", "password",
                             "repeated_password", "email"]

        for missing_data in missing_data_list:
            with self.subTest(missing_data=missing_data):
                data = dict(_USER_REGISTRATION_DATA_1)
                del data[missing_data]

        # Act
                with app.test_client() as c:
                    resp = c.post(self.url, data=data, follow_redirects=True)
                    html = resp.get_data(as_text=True)

        # Assert
                self.assertIn("User Registration</h1>", html)
                self.assertIn("is required.", html)

                num_users = db.session.query(User).count()
                self.assertEqual(num_users, 0)

    def test_registering_user_with_empty_string_required_info(self):
        """Tests that registering with empty strings for required info should fail."""

        # Arrange
        empty_string_data_list = ["username", "password",
                                  "repeated_password", "email"]

        for empty_string_data in empty_string_data_list:
            with self.subTest(empty_string_data=empty_string_data):
                data = dict(_USER_REGISTRATION_DATA_1)
                data[empty_string_data] = ""

        # Act
                with app.test_client() as c:
                    resp = c.post(self.url, data=data, follow_redirects=True)
                    html = resp.get_data(as_text=True)

        # Assert
                self.assertIn("User Registration</h1>", html)
                self.assertIn("is required.", html)

                num_users = db.session.query(User).count()
                self.assertEqual(num_users, 0)

    def test_registering_user_with_invalid_password(self):
        """Tests that attempting to register with an invalid password should fail."""

        # Arrange
        password_data_list = ['1' * (User.MIN_PASS_LENGTH - 1),  # too short
                              '123456q1!',  # missing uppercase
                              '123456Q1!',  # missing lowercase
                              'abcdQq!',  # missing number
                              '123456Qq1',]  # missing special character

        for password in password_data_list:
            with self.subTest(password=password):
                data = dict(_USER_REGISTRATION_DATA_1)
                data['password'] = password
                data['repeated_password'] = password

                # Act
                with app.test_client() as client:
                    resp = client.post(self.url, data=data, follow_redirects=True)
                    html = resp.get_data(as_text=True)

                # Assert
                self.assertIn("User Registration</h1>", html)
                self.assertIn(f'Password must contain at least one', html)

                num_users = db.session.query(User).count()
                self.assertEqual(num_users, 0)

    def test_registering_user_with_mismatched_password_confirmation(self):
        """Tests that registering with mismatching password and repeated password should fail."""

        # Arrange
        data = dict(_USER_REGISTRATION_DATA_1)
        data['repeated_password'] = "other password"

        # Act
        with app.test_client() as client:
            resp = client.post(self.url, data=data, follow_redirects=True)
            html = resp.get_data(as_text=True)

        # Assert
        self.assertIn("User Registration</h1>", html)
        self.assertIn("Password must match.", html)

        num_users = db.session.query(User).count()
        self.assertEqual(num_users, 0)

    def test_registering_user_with_nonunique_info(self):
        """Tests that registering with already used info, such as username, should fail."""

        # Arrange
        nonunique_data_list = [
            {"username": _USER_REGISTRATION_DATA_1['username']},
            {"email": _USER_REGISTRATION_DATA_1['email']}
        ]
        user_data_2 = MappingProxyType({
            "username": "testuser2",
            "password": "Aa1!123",
            "repeated_password": "Aa1!123",
            "email": "test2@test.com",
        })

        with app.test_client() as client:
            client.post(
                self.url,
                data=dict(_USER_REGISTRATION_DATA_1),
                follow_redirects=True)

        for nonunique_data in nonunique_data_list:
            with self.subTest(nonunique_data=list(nonunique_data)[0]):
                data = user_data_2 | nonunique_data

        # Act
                with app.test_client() as c:
                    resp = c.post(self.url, data=data, follow_redirects=True)
                    html = resp.get_data(as_text=True)

        # Assert
                self.assertIn("Duplicate username or email.", html)

                user = db.session.query(User).one()
                self.assertEqual(
                    user.username, _USER_REGISTRATION_DATA_1['username'])
                self.assertEqual(
                    user.email, _USER_REGISTRATION_DATA_1['email'])

    @patch('src.models.user.db', autospec=True)
    def test_reload_registration_page_when_session_throws_exception(self, mock_db):
        """If the SQLAlchemy session throws an exception, the registration page should be rendered."""

        # Arrange mocks
        mock_db.session.commit.side_effect = DBAPIError(statement=None, params=None, orig=DatabaseError)

        # Act
        with app.test_client() as client:
            resp = client.post(
                self.url,
                data=dict(_USER_REGISTRATION_DATA_1),
                follow_redirects=True)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertEqual(resp.status_code, 200)
            self.assertIn("User Registration</h1>", html)
            self.assertIn("Username", html)
            self.assertIn("Password", html)
            self.assertIn("Repeat Password", html)
            self.assertIn("Email", html)
            self.assertIn('Server exception encountered when registering a user.', html)


class UserLoginViewTestCase(TestCase):
    """Tests for user login views."""

    def setUp(self):
        db.session.query(User).delete()
        db.session.commit()

        with app.test_client() as client:
            client.post(
                url_for("register_user"),
                data=dict(_USER_REGISTRATION_DATA_1),
                follow_redirects=True)

            logout_user()

        self.url = url_for("login_user")

    def tearDown(self):
        db.session.rollback()

    def test_display_user_login_form(self):
        """Tests displaying the user login form."""

        # Act
        with app.test_client() as client:
            resp = client.get(self.url)
            html = resp.get_data(as_text=True)

        # Assert
        self.assertEqual(resp.status_code, 200)
        self.assertIn("User Login</h1>", html)
        self.assertIn("Username", html)
        self.assertIn("Password", html)

    def test_login_user(self):
        """Tests that a user can successfully log in."""

        # Arrange
        data = {"username": _USER_REGISTRATION_DATA_1['username'],
                "password": _USER_REGISTRATION_DATA_1['password']}

        # Act
        with app.test_client() as client:
            resp = client.post(self.url, data=data, follow_redirects=True)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Successfully logged in.", html)

            self.assertIsInstance(current_user, User)

        # cleanup
            logout_user()

    def test_login_user_with_missing_info(self):
        """Tests that logging in with missing info should fail."""

        # Arrange
        data_list = [
            {"username": _USER_REGISTRATION_DATA_1['username']},
            {"username": _USER_REGISTRATION_DATA_1['username'],
                "password": ""},
            {"password": _USER_REGISTRATION_DATA_1['password']},
            {"username": "", "password": _USER_REGISTRATION_DATA_1['password']}]

        # Act
        for data in data_list:
            with self.subTest(data=data):
                with app.test_client() as client:
                    resp = client.post(self.url, data=data, follow_redirects=True)
                    html = resp.get_data(as_text=True)

        # Assert
                    self.assertIn("is required.", html)

                    self.assertNotIsInstance(current_user, User)

    def test_login_user_with_incorrect_info(self):
        """Tests that logging in with wrong username or password should fail."""

        # Arrange
        data_list = [
            {"username": "user99",
                "password": _USER_REGISTRATION_DATA_1['password']},
            {"username": _USER_REGISTRATION_DATA_1['username'],
                "password": "0000000000"}
        ]

        # Act
        for data in data_list:
            with self.subTest(data=data):
                with app.test_client() as client:
                    resp = client.post(self.url, data=data, follow_redirects=True)
                    html = resp.get_data(as_text=True)

        # Assert
                    self.assertIn("Invalid credentials.", html)

                    self.assertNotIsInstance(current_user, User)

    def test_login_user_with_password_too_short(self):
        """Logging in with a password that is too short should fail."""

        # Arrange
        data = {"username": _USER_REGISTRATION_DATA_1['username'],
                "password": "1" * (User.MIN_PASS_LENGTH - 1)}

        # Act
        with app.test_client() as client:
            resp = client.post(self.url, data=data, follow_redirects=True)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertIn(f'Field must be at least {User.MIN_PASS_LENGTH} characters long.', html)

            self.assertNotIsInstance(current_user, User)

    @patch('src.models.user.db', autospec=True)
    def test_reload_login_page_when_session_throws_exception(self, mock_db):
        """If the SQLAlchemy session throws an exception, the login page should be rendered."""

        # Arrange
        data = {"username": _USER_REGISTRATION_DATA_1['username'],
                "password": _USER_REGISTRATION_DATA_1['password']}

        # Arrange mocks
        mock_db.session.query.return_value.filter_by.return_value.one_or_none.side_effect = \
            DBAPIError(statement=None, params=None, orig=DatabaseError)

        # Act
        with app.test_client() as client:
            resp = client.post(self.url, data=data, follow_redirects=True)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertEqual(resp.status_code, 200)
            self.assertIn("User Login</h1>", html)
            self.assertIn("Username", html)
            self.assertIn("Password", html)
            self.assertIn('Server exception encountered when authenticating a user.', html)


class UserLogoutTestCase(TestCase):
    """Tests for user logout."""

    def setUp(self):
        db.session.query(User).delete()
        db.session.commit()

        with app.test_client() as client:
            client.post(
                url_for("register_user"),
                data=dict(_USER_REGISTRATION_DATA_1))

        self.url = url_for("logout_user")

    def tearDown(self):
        db.session.rollback()

    def test_logout_user(self):
        """Tests logging out successfully."""

        # Arrange
        login_data = {"username": _USER_REGISTRATION_DATA_1['username'],
                      "password": _USER_REGISTRATION_DATA_1['password']}

        with app.test_client() as client:
            client.post(
                url_for("login_user"),
                data=login_data)

            self.assertIsInstance(current_user, User)

        # Act
            resp = client.post(self.url)

        # Assert
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, url_for("home"))

            self.assertNotIsInstance(current_user, User)
