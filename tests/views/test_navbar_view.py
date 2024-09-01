import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from unittest import TestCase

from flask import render_template, url_for

from src.app import create_app

# ==================================================

app = create_app("freestreammovies_test", testing=True)
app.config.update(
    WTF_CSRF_ENABLED=False,
    SERVER_NAME="localhost:5000"
)
app.app_context().push()

# --------------------------------------------------


class NavbarViewTestCase(TestCase):
    """Tests the view for the navbar."""

    @classmethod
    def setUpClass(cls):
        cls.home_url = url_for('home', _external=True)
        cls.search_titles_url = url_for('search_titles', _external=True)
        cls.register_user_url = url_for('register_user', _external=True)
        cls.login_user_url = url_for('login_user', _external=True)
        cls.logout_user_url = url_for('logout_user', _external=True)

    def test_display_common_navbar_elements(self):
        """Tests displaying the home button and search bar."""

        # Act
        html = render_template('partials/navbar.html')

        # Assert
        self.assertIn(f'href="{self.home_url}">Home</a>', html)
        self.assertIn(f'action="{self.search_titles_url}"', html)
        self.assertIn('placeholder="Search Movie Titles"', html)

    def test_display_navbar_when_not_logged_in(self):
        """Tests displaying the registration and login links."""

        # Arrange
        current_user = {'is_authenticated': False}

        # Act
        html = render_template('partials/navbar.html', current_user=current_user)

        # Assert
        self.assertIn(f'href="{self.register_user_url}"', html)
        self.assertIn(f'href="{self.login_user_url}"', html)
        self.assertNotIn(f'action="{self.logout_user_url}"', html)

    def test_display_navbar_when_logged_in(self):
        """Tests displaying the profile and logout buttons."""

        # Arrange
        current_user = {'is_authenticated': True}

        # Act
        html = render_template('partials/navbar.html', current_user=current_user)

        # Assert
        self.assertIn(f'action="{self.logout_user_url}"', html)
        self.assertNotIn(f'href="{self.register_user_url}"', html)
        self.assertNotIn(f'href="{self.login_user_url}"', html)
