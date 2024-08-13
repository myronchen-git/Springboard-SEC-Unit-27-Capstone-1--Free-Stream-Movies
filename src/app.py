import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

import os

import flask_login
import requests
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import LoginManager, login_user

from src.adapters.streaming_availability_adapter import (
    convert_show_json_into_movie_object, store_movie_and_streaming_options)
from src.exceptions.UserRegistrationError import UserRegistrationError
from src.forms.user_forms import LoginUserForm, RegisterUserForm
from src.models.common import connect_db, db
from src.models.country_service import CountryService
from src.models.movie import Movie
from src.models.service import Service
from src.models.streaming_option import StreamingOption
from src.models.user import User

# ==================================================

load_dotenv()
RAPID_API_KEY = os.environ.get('RAPID_API_KEY')
DEFAULT_COUNTRY_CODE = 'us'

# --------------------------------------------------


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
    # users
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

    # --------------------------------------------------
    # api
    # --------------------------------------------------

    @app.route('/api/v1/<country_code>/<service>/movies')
    def get_streaming_options(country_code, service):
        """Retrieves a list of movie streaming options for a specified country and streaming service."""

        page = request.args.get('page')
        page = int(page) if page else None

        movies_pagination = StreamingOption.get_streaming_options(
            country_code, service, page)

        items = [item.toJson() for item in movies_pagination.items]

        return {
            'items': items,
            'page': movies_pagination.page,
            'has_prev': movies_pagination.has_prev,
            'has_next': movies_pagination.has_next,
        }

    # --------------------------------------------------
    # movies
    # --------------------------------------------------

    @app.route('/movies')
    def search_titles():
        """Calls Streaming Availability API to search for a specific movie."""

        country = request.args.get('country')
        title = request.args.get('title')

        if not country or not title:
            return redirect(url_for("home"))

        url = "https://streaming-availability.p.rapidapi.com/shows/search/title"
        headers = {'X-RapidAPI-Key': RAPID_API_KEY}
        querystring = {"country": country,
                       "title": title,
                       "show_type": "movie"}

        resp = requests.get(url, headers=headers, params=querystring)

        if resp.status_code == 200:
            movies = resp.json()

            return render_template("movies/search_results.html", movies=movies)

        else:
            # temp, replace with custom error
            return "Error", resp.status_code

    @app.route('/movie/<movie_id>')
    def movie_details_page(movie_id):
        """Displays a specified movie's details page."""

        movie = db.session.get(Movie, movie_id)

        if not movie:
            url = f"https://streaming-availability.p.rapidapi.com/shows/{movie_id}"
            headers = {'X-RapidAPI-Key': RAPID_API_KEY}

            resp = requests.get(url, headers=headers)
            show = resp.json()

            if resp.status_code == 200:
                store_movie_and_streaming_options(show)

                # Temporary Movie object used to store data.
                # This is different than the same Movie retrieved from the database.
                # Do not add to database session.
                movie = convert_show_json_into_movie_object(show)

            else:
                # temp, replace with custom error
                return "Error", resp.status_code

        country_code = request.cookies.get('country_code', DEFAULT_COUNTRY_CODE)
        streaming_options = db.session.query(StreamingOption).filter_by(
            country_code=country_code, movie_id=movie.id).all()

        return render_template("movies/details.html", movie=movie, streaming_options=streaming_options)

    # --------------------------------------------------
    # helper methods
    # --------------------------------------------------

    return app

# ==================================================


if __name__ == "__main__":
    app = create_app("freestreammovies")
    connect_db(app)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
