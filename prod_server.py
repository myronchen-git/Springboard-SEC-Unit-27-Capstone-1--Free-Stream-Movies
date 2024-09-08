from src.app import create_app
from src.models.common import connect_db

# for gunicorn to use
app = create_app("freestreammovies")
connect_db(app)
