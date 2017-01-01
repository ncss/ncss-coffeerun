#!/bin/python
"""config.py
Configuration objects for the ncss-coffee Flask app
Maddy Reid 2014"""
import os
from datetime import timedelta

from os.path import abspath, dirname, join
current_dir = dirname(abspath(__file__))

class Config(object):
    CSFR_ENABLED = True
    SECRET_KEY = os.environ.get("SECRET_KEY", "HyP0oHYnYeqv47uXohfvOkiv")
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = "465"
    MAIL_USERNAME = "ncsscoffeerun@gmail.com"
    MAIL_PASSWORD = "kpTMnBNZn06z"
    MAIL_DEFAULT_SENDER = ("NCSS Coffeebot", "ncsscoffeerun@gmail.com")
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    SLACK_API_TOKEN = os.environ.get('SLACK_API_TOKEN')
    SLACK_BOT_USER_ID = os.environ.get('SLACK_BOT_USER_ID')
    SLACK_TEAM_ID = os.environ.get('SLACK_TEAM_ID')
    SLACK_OAUTH_CLIENT_ID = os.environ.get('SLACK_OAUTH_CLIENT_ID')
    SLACK_OAUTH_CLIENT_SECRET = os.environ.get('SLACK_OAUTH_CLIENT_SECRET')
    SQLALCHEMY_DATABASE_URI = 'sqlite:////' + os.path.join(current_dir, 'application', 'coffeerun-dev.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:////' + os.path.join(current_dir, 'application', 'coffeerun-dev.db')
    SESSION_TYPE = 'sqlalchemy'


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///coffeerun-test.db"
    SQLALCHEMY_DATABASE_URI = 'sqlite:////' + os.path.join(current_dir, 'application', 'coffeerun-test.db')


class ProdConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:////' + os.path.join(current_dir, 'application', 'coffeerun-prod.db')
    SESSION_TYPE = 'sqlalchemy'
    DEBUG = True
    if os.environ.get('DATABASE_URL') is None:
        SQLALCHEMY_DATABASE_URL = "postgres://pzjpocurmvfdee:_J2pg9gvP0K5SJeMPHjUkERt2J@ec2-54-197-250-52.compute-1.amazonaws.com:5432/d4bnpmfglihmg0"
    else:
        SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    API_KEY = "AIzaSyDdtXLXJWPJS9bEay-nq0QsAvFxHMvGw3U"
