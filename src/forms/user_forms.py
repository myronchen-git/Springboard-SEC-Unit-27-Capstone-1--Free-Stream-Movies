from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField
from wtforms.validators import EqualTo, InputRequired

# ==================================================


class RegisterUserForm(FlaskForm):
    """Form to register a user."""

    username = StringField("Username", validators=[
        InputRequired(message="Username is required.")],
        render_kw={"placeholder": "username"})

    password = PasswordField("Password", validators=[
        InputRequired(message="Password is required.")],
        render_kw={"placeholder": "password"})

    repeated_password = PasswordField("Repeat Password", validators=[
        InputRequired("Repeated password is required."),
        EqualTo("password", message="Password must match.")],
        render_kw={"placeholder": "password"})

    email = EmailField("Email", validators=[
        InputRequired(message="Email is required.")],
        render_kw={"placeholder": "email"})


class LoginUserForm(FlaskForm):
    """Form to log in a user."""

    username = StringField("Username", validators=[
        InputRequired(message="Username is required.")],
        render_kw={"placeholder": "username"})

    password = PasswordField("Password", validators=[
        InputRequired(message="Password is required.")],
        render_kw={"placeholder": "password"})
