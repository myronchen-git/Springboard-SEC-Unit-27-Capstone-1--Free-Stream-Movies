import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from unittest import TestCase

from flask import render_template

from src.app import create_app

# ==================================================

app = create_app("freestreammovies_test", testing=True)
app.app_context().push()

# --------------------------------------------------


class NavbarViewTestCase(TestCase):
    """Tests the view for the navbar."""

    def test_display_common_navbar_elements(self):
        """Tests displaying the home button and search bar."""

        # Act
        html = render_template('partials/navbar.html')

        # Assert
        self.assertIn('<a href="/">Home</a>', html)
        self.assertIn('form action="/movies"', html)
        self.assertIn('placeholder="Search Movie Titles"', html)

    def test_display_navbar_when_not_logged_in(self):
        """Tests displaying the registration and login links."""

        # Arrange
        current_user = {'is_authenticated': False}

        # Act
        html = render_template('partials/navbar.html', current_user=current_user)

        # Assert
        self.assertIn('href="/users/registration"', html)
        self.assertIn('href="/users/login"', html)
        self.assertNotIn('action="/users/logout"', html)

    def test_display_navbar_when_logged_in(self):
        """Tests displaying the profile and logout buttons."""

        # Arrange
        current_user = {'is_authenticated': True}

        # Act
        html = render_template('partials/navbar.html', current_user=current_user)

        # Assert
        self.assertIn('action="/users/logout"', html)
        self.assertNotIn('href="/users/registration"', html)
        self.assertNotIn('href="/users/login"', html)
