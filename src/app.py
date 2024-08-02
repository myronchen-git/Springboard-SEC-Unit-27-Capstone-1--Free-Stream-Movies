import os

from flask import Flask, flash, redirect, render_template, url_for

from exceptions.UserRegistrationError import UserRegistrationError
from forms.user_forms import RegisterUserForm
from models.models import User, connect_db, db

# ==================================================

CURR_USER_KEY = "curr_user"


def create_app(db_name, testing=False):
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = (
        os.environ.get('DATABASE_URL', f'postgresql://postgres@localhost/{db_name}'))

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")

    if not testing:
        app.config['SQLALCHEMY_ECHO'] = False
        app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
        app.config['DEBUG_TB_HOSTS'] = ["dont-show-debug-toolbar"]

    else:
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_ECHO'] = True
        app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
        # debug = DebugToolbarExtension(app)

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

    return app

# ==================================================


if __name__ == "__main__":
    app = create_app("freestreammovies")
    connect_db(app)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
