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
# from flask_debugtoolbar import DebugToolbarExtension
from flask_login import LoginManager

from src.adapters.streaming_availability_adapter import (
    convert_show_json_into_movie_object, transform_show)
from src.exceptions.base_exceptions import FreeStreamMoviesClientError
from src.exceptions.UserRegistrationError import UserRegistrationError
from src.forms.user_forms import LoginUserForm, RegisterUserForm
from src.models.common import connect_db, db
from src.models.country_service import CountryService
from src.models.movie import Movie
from src.models.movie_poster import MoviePoster
from src.models.service import Service
from src.models.streaming_option import StreamingOption
from src.models.user import User
from src.util.client_input_validations import has_comma_in_query_parameters

# ==================================================

load_dotenv()
RAPID_API_KEY = os.environ.get('RAPID_API_KEY')
STREAMING_AVAILABILITY_BASE_URL = "https://streaming-availability.p.rapidapi.com"

COOKIE_COUNTRY_CODE_NAME = 'countryCode'
DEFAULT_COUNTRY_CODE = 'us'

# --------------------------------------------------


def create_app(db_name, testing=False):
    app = Flask(__name__)

    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'DATABASE_URL', f'postgresql://postgres@localhost/{db_name}'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.environ.get('SECRET_KEY', "it's a secret"),
    )

    login_manager = LoginManager()
    login_manager.init_app(app)

    if not testing:
        app.config.update(
            SQLALCHEMY_ECHO=False,
            DEBUG_TB_INTERCEPT_REDIRECTS=False
        )
        # debug = DebugToolbarExtension(app)

    else:
        app.config.update(
            TESTING=True,
            SQLALCHEMY_ECHO=True
        )

    # --------------------------------------------------
    #
    # --------------------------------------------------

    @app.route('/')
    def home():
        """Render homepage."""

        country_code = request.cookies.get(COOKIE_COUNTRY_CODE_NAME, DEFAULT_COUNTRY_CODE)

        services = db.session\
            .query(Service)\
            .join(CountryService, Service.id == CountryService.service_id)\
            .filter(CountryService.country_code == country_code)\
            .all()

        return render_template('home.html', services=services)

    # --------------------------------------------------
    # users
    # --------------------------------------------------

    @app.route("/users/registration", methods=["GET", "POST"])
    def register_user():
        """Displays the form to register a user, and registers a user."""

        form = RegisterUserForm()

        if form.validate_on_submit():
            try:
                user = User.register(form.data)
                flask_login.login_user(user, remember=True)

                flash("Successfully registered.", "success")
                return redirect(url_for("home"))

            except UserRegistrationError as e:
                flash(f"Invalid input(s) on registration form: "
                      f"{str(e)}", "danger")

        return render_template("users/registration.html", form=form)

    @app.route('/users/login', methods=['GET', 'POST'])
    def login_user():
        """Displays the form to log in a user, and logs in a user."""

        form = LoginUserForm()

        if form.validate_on_submit():
            user = User.authenticate(form.username.data, form.password.data)

            if user:
                flask_login.login_user(user, remember=True)

                flash("Successfully logged in.", "success")
                return redirect(url_for("home"))

            flash("Invalid credentials.", 'danger')

        return render_template("users/login.html", form=form)

    @app.route('/users/logout', methods=['POST'])
    def logout_user():
        """Logs out the current user."""

        flask_login.logout_user()

        flash("Logout successful.", "success")
        return redirect(url_for("home"))

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, user_id)

    @login_manager.unauthorized_handler
    def unauthorized_handler():
        return render_template(
            'error.html',
            status_code=401,
            message='Unauthorized'
        ), 401

    # --------------------------------------------------
    # api
    # --------------------------------------------------

    @app.route('/api/v1/<country_code>/<service_id>/movies')
    def get_streaming_options(country_code, service_id):
        """Retrieves a list of movie streaming options for a specified country and streaming service."""

        page = request.args.get('page')
        page = int(page) if page else None

        movies_pagination = StreamingOption.get_streaming_options(
            country_code, service_id, page)

        items = [item.toJson() for item in movies_pagination.items]

        return {
            'items': items,
            'page': movies_pagination.page,
            'has_prev': movies_pagination.has_prev,
            'has_next': movies_pagination.has_next,
        }

    @app.route('/api/v1/movie-posters')
    def get_movie_posters():
        """
        Retrieves a dictionary of movie poster links for specified movies, types, and sizes.
        Requires query parameters movieId, type, and size.  Query parameters have to be repeated when passing different
        values (movieId=1234, movieId=5678).

        Returns JSON {movie_id: {type: {size: link}}}.
        """

        movie_ids = request.args.getlist('movieId')
        types = request.args.getlist('type')
        sizes = request.args.getlist('size')

        if not movie_ids or not types or not sizes:
            return {'message': 'Missing movieId, type, or size query parameters.'}, 400

        if has_comma_in_query_parameters([movie_ids, types, sizes]):
            return {'message':
                    'App API does not support comma-separated lists for query parameters '
                    '(movieId=1234,5678).  Use repeated query parameter assignment '
                    '(movieId=1234, movieId=5678).'}, 400

        try:
            movie_posters = MoviePoster.get_movie_posters(movie_ids, types, sizes)
            return MoviePoster.convert_list_to_dict(movie_posters)
        except FreeStreamMoviesClientError as e:
            return {"message": str(e)}, 400

    # --------------------------------------------------
    # movies
    # --------------------------------------------------

    @app.route('/movies')
    def search_titles():
        """Calls Streaming Availability API to search for a specific movie."""

        country_code = request.cookies.get(COOKIE_COUNTRY_CODE_NAME, DEFAULT_COUNTRY_CODE)
        title = request.args.get('title')

        if not title:
            return redirect(url_for("home"))

        url = f"{STREAMING_AVAILABILITY_BASE_URL}/shows/search/title"
        headers = {'X-RapidAPI-Key': RAPID_API_KEY}
        querystring = {"country": country_code,
                       "title": title,
                       "show_type": "movie"}

        resp = requests.get(url, headers=headers, params=querystring)

        if resp.status_code == 200:
            movies = resp.json()

            return render_template("movies/search_results.html", movies=movies)

        else:
            return render_template(
                'error.html',
                status_code=resp.status_code,
                message=resp.reason
            ), resp.status_code

    @app.route('/movie/<movie_id>')
    def movie_details_page(movie_id):
        """Displays a specified movie's details page."""

        movie = db.session.get(Movie, movie_id)

        if not movie:
            url = f"{STREAMING_AVAILABILITY_BASE_URL}/shows/{movie_id}"
            headers = {'X-RapidAPI-Key': RAPID_API_KEY}

            resp = requests.get(url, headers=headers)
            show = resp.json()

            if resp.status_code == 200:
                data = transform_show(show)
                Movie.upsert_database(data['movies'])
                MoviePoster.upsert_database(data['movie_posters'])
                StreamingOption.insert_database(data['streaming_options'])
                db.session.commit()

                # Temporary Movie object used to store data.
                # This is different than the same Movie retrieved from the database.
                # Do not add to database session.
                movie = convert_show_json_into_movie_object(show)

            else:
                return render_template(
                    'error.html',
                    status_code=resp.status_code,
                    message=resp.reason
                ), resp.status_code

        country_code = request.cookies.get(COOKIE_COUNTRY_CODE_NAME, DEFAULT_COUNTRY_CODE)
        streaming_options = db.session.query(StreamingOption).filter_by(
            country_code=country_code, movie_id=movie.id).all()

        movie_poster = MoviePoster.get_movie_posters([movie.id], ["verticalPoster"], ["w360"])[0]

        return render_template(
            "movies/details.html",
            movie=movie,
            streaming_options=streaming_options,
            movie_poster=movie_poster
        )

    # --------------------------------------------------
    # helper methods
    # --------------------------------------------------

    return app

# ==================================================


# for starting a server for development
if __name__ == "__main__":
    app = create_app("freestreammovies")
    connect_db(app)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
