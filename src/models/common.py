
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# ==================================================

db = SQLAlchemy()

# --------------------------------------------------


def connect_db(app: Flask):
    """Connect this database to provided Flask app."""

    with app.app_context():
        db.app = app
        db.init_app(app)
