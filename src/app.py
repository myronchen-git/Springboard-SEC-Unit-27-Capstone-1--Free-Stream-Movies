import os

import flask_login
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, url_for
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import LoginManager, login_user

from exceptions.UserRegistrationError import UserRegistrationError
from forms.user_forms import LoginUserForm, RegisterUserForm
from models.common import connect_db, db
from models.country_service import CountryService
from models.movie import Movie
from models.service import Service
from models.streaming_option import StreamingOption
from models.user import User

# ==================================================

load_dotenv()


def create_app(db_name, testing=False):
    app = Flask(__name__)

    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'DATABASE_URL', f'postgresql://postgres@localhost/{db_name}'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.environ.get('SECRET_KEY', "it's a secret"),
        REMEMBER_COOKIE_DURATION=60  # temp for development
    )

    login_manager = LoginManager()
    login_manager.init_app(app)

    if not testing:
        app.config.update(
            SQLALCHEMY_ECHO=False,
            DEBUG_TB_INTERCEPT_REDIRECTS=False
        )
        debug = DebugToolbarExtension(app)

    else:
        app.config.update(
            TESTING=True,
            SQLALCHEMY_ECHO=True
        )

    # --------------------------------------------------

    @app.route('/')
    def home():
        """Render homepage."""

        return render_template('base.html')

    @app.route("/users/registration", methods=["GET", "POST"])
    def register_user():
        """Displays the form to register a user, and registers a user."""

        form = RegisterUserForm()

        if form.validate_on_submit():
            try:
                user = User.register(form.data)
                flask_login.login_user(user, remember=True)

                flash("Successfully registered.", "info")
                return redirect(url_for("home"))

            except UserRegistrationError as e:
                flash(f"Invalid input(s) on registration form: "
                      f"{str(e)}", "error")

        return render_template("users/registration.html", form=form)

    @app.route('/users/login', methods=['GET', 'POST'])
    def login_user():
        """Displays the form to log in a user, and logs in a user."""

        form = LoginUserForm()

        if form.validate_on_submit():
            user = User.authenticate(form.username.data, form.password.data)

            if user:
                flask_login.login_user(user, remember=True)

                flash("Successfully logged in.", "info")
                return redirect(url_for("home"))

            flash("Invalid credentials.", 'danger')

        return render_template("users/login.html", form=form)

    @app.route('/users/logout', methods=['POST'])
    def logout_user():
        """Logs out the current user."""

        flask_login.logout_user()

        flash("Logout successful.", "info")
        return redirect(url_for("home"))

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, user_id)

    @login_manager.unauthorized_handler
    def unauthorized_handler():
        return 'Unauthorized', 401

    return app

# ==================================================


if __name__ == "__main__":
    app = create_app("freestreammovies")
    connect_db(app)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
