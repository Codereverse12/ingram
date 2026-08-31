from flask import Blueprint, current_app
from api import apifairy
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

errors = Blueprint('errors', __name__)

@errors.app_errorhandler(HTTPException)
def http_error(error):
    return {
        'code': error.code,
        'name': error.name,
        'description': error.description
    }, error.code

@errors.app_errorhandler(IntegrityError)
def sqlalchemy_integrity_error(error):
    return {
        'code': 400,
        'name': 'Bad Request',
        'description': 'Database integrity error'
    }, 400

@errors.app_errorhandler(SQLAlchemyError)
def sqlalchemy_error(error):
    if current_app.config['DEBUG']:
        return {
            'code': 500,
            'name': 'Internal Server Error',
            'description': str(error)
        }, 500
    else:
        return {
            'code': 500,
            'name': 'Internal Server Error',
            'description': 'An unexpected error occurred'
        }, 500


@apifairy.error_handler
def validation_error(code, messages):
    return {
        'code': code,
        'message': 'Validation Error',
        'description': ('The server found one or more errors in the '
                        'information that you sent.'),
        'errors': messages,
    }, code