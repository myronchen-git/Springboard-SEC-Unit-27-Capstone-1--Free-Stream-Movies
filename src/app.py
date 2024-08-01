import os

import flask_login
from flask import Flask, flash, redirect, render_template, url_for
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import LoginManager, login_user

from exceptions.UserRegistrationError import UserRegistrationError
from forms.user_forms import LoginUserForm, RegisterUserForm
from models.models import User, connect_db, db

# ==================================================

CURR_USER_KEY = "curr_user"


def create_app(db_name, testing=False):
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = (
        os.environ.get('DATABASE_URL', f'postgresql://postgres@localhost/{db_name}'))

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")

    login_manager = LoginManager()
    login_manager.init_app(app)

    if not testing:
        app.config['SQLALCHEMY_ECHO'] = False
        app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
        app.config['DEBUG_TB_HOSTS'] = ["dont-show-debug-toolbar"]

    else:
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_ECHO'] = True
        app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
        debug = DebugToolbarExtension(app)

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
                User.register(form.data)

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
