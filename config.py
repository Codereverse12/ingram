import os
from dotenv import load_dotenv

load_dotenv()
basedir = os.path.abspath(os.path.dirname(__file__))


def as_bool(value):
    if value:
        return value.lower() in ['true', 'yes', 'on', '1']
    return False

class Config:
    # database options
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # security options
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    DISABLE_AUTH = as_bool(os.environ.get('DISABLE_AUTH'))
    ACCESS_TOKEN_MINUTES = int(os.environ.get('ACCESS_TOKEN_MINUTES') or '15')
    REFRESH_TOKEN_DAYS = int(os.environ.get('REFRESH_TOKEN_DAYS') or '7')

    USE_CORS = as_bool(os.environ.get('USE_CORS') or 'yes')
    CORS_SUPPORTS_CREDENTIALS = True

    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')

    # API documentation
    APIFAIRY_TITLE = 'Ingram API'
    APIFAIRY_VERSION = '1.0'
    APIFAIRY_UI = os.environ.get('DOCS_UI', 'elements')
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite://'

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data.sqlite')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}