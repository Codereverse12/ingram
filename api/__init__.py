"""
Welcome to the documentation for the Ingram API!
"""
import sqlite3

from flask import Flask, redirect, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
from flask_cors import CORS
from apifairy import APIFairy
from config import config
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.engine import Engine


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """Enable SQLite foreign key enforcement on every connection."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()



metadata = sa.MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

db = SQLAlchemy(metadata=metadata)
migrate = Migrate()
cors = CORS()
ma = Marshmallow()
apifairy = APIFairy()

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    migrate.init_app(app, db)

    if app.config["USE_CORS"]:
        cors.init_app(app)

    apifairy.init_app(app)
    ma.init_app(app)

    # blueprints
    from api.errors import errors
    app.register_blueprint(errors)

    from api.tokens import tokens
    app.register_blueprint(tokens, url_prefix='/api')

    from api.roles import roles
    app.register_blueprint(roles, url_prefix='/api')

    from api.users import users
    app.register_blueprint(users, url_prefix='/api')

    from api.equipments import equipments
    app.register_blueprint(equipments, url_prefix='/api')

    from api.hospitals import hospitals
    app.register_blueprint(hospitals, url_prefix='/api')

    from api.installations import installations
    app.register_blueprint(installations, url_prefix='/api')

    from api.services import services
    app.register_blueprint(services, url_prefix='/api')

    from api.fake import fake
    app.register_blueprint(fake)

    @app.route("/")
    def index():  # pragma: no cover
        return redirect(url_for("apifairy.docs"))

    @app.after_request
    def after_request(response):
        # Werkzeug sometimes does not flush the request body, so we do it here.
        request.get_data()
        return response

    return app