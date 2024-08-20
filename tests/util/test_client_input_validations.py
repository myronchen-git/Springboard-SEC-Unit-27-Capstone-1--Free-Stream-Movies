import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from unittest import TestCase

from src.util.client_input_validations import has_comma_in_query_parameters

# ==================================================


class ClientInputValidationsTestCaseHasCommaInQueryParameters(TestCase):
    """Tests for client input validation utility function has_comma_in_query_parameters."""

    def test_comma_in_query_params_returns_true(self):
        """Tests that a comma in one of the query parameter lists/values returns true."""

        # Arrange
        query_params = [
            ['0', '1'],
            ['verticalPoster'],
            ['w240, w360']
        ]

        # Act
        result = has_comma_in_query_parameters(query_params)

        # Assert
        self.assertTrue(result)

    def test_no_comma_in_query_params_returns_false(self):
        """Tests that no comma in any of the query parameters returns false."""

        # Arrange
        query_params = [
            ['123'],
            ['verticalPoster'],
            ['w240']
        ]

        # Act
        result = has_comma_in_query_parameters(query_params)

        # Assert
        self.assertFalse(result)
