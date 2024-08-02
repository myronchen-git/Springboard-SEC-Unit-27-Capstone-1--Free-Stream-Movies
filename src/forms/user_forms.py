from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField
from wtforms.validators import EqualTo, InputRequired

# ==================================================


class RegisterUserForm(FlaskForm):
    """Form to register a user."""

    username = StringField("Username", validators=[
        InputRequired(message="Username is required.")])

    password = PasswordField("Password", validators=[
        InputRequired(message="Password is required.")])

    repeated_password = PasswordField("Repeat Password", validators=[
        InputRequired("Repeated password is required."),
        EqualTo("password", message="Password must match.")])

    email = EmailField("Email", validators=[
        InputRequired(message="Email is required.")])
