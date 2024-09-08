from src.app import create_app

# for gunicorn to use
app = create_app("freestreammovies")
