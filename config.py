"""config.py
Configuration objects for the ncss-coffee Flask app
Maddy Reid 2014"""
import base64
import os
import os.path


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class Config(object):
    CSFR_ENABLED = True
    SECRET_KEY = base64.b64decode(
            os.environ.get("SECRET_KEY", "SHlQMG9IWW5ZZXF2NDd1WG9oZnZPa2l2"))
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = "465"
    MAIL_USERNAME = "ncsscoffeerun@gmail.com"
    MAIL_PASSWORD = "kpTMnBNZn06z"
    MAIL_DEFAULT_SENDER = ("NCSS Coffeebot", "ncsscoffeerun@gmail.com")
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    SLACK_TEAM_ID = os.environ.get('SLACK_TEAM_ID')
    SLACK_OAUTH_CLIENT_ID = os.environ.get('SLACK_OAUTH_CLIENT_ID')
    SLACK_OAUTH_CLIENT_SECRET = os.environ.get('SLACK_OAUTH_CLIENT_SECRET')
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:////' + os.path.join(CURRENT_DIR, 'application', 'coffeerun-dev.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', SQLALCHEMY_DATABASE_URI)
    SESSION_TYPE = 'sqlalchemy'


class TestConfig(Config):
    CSRF_ENABLED = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:////' + os.path.join(CURRENT_DIR, 'application', 'coffeerun-test.db')


class ProdConfig(Config):
    API_KEY = "AIzaSyDdtXLXJWPJS9bEay-nq0QsAvFxHMvGw3U"
    DEBUG = True
    SESSION_TYPE = 'sqlalchemy'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
