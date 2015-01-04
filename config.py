#!/bin/python
"""config.py
Configuration objects for the ncss-coffee Flask app
Maddy Reid 2014"""
import os

class Config(object):
    CSFR_ENABLED = True
    SECRET_KEY = "HyP0oHYnYeqv47uXohfvOkiv"

class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///coffeerun-dev.db"

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///coffeerun-test.db"
    
class ProdConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///coffeerun-prod.db"
    DEBUG = True
    if os.environ.get('DATABASE_URL') is None:
        SQLALCHEMY_DATABASE_URL = "postgres://pzjpocurmvfdee:_J2pg9gvP0K5SJeMPHjUkERt2J@ec2-54-197-250-52.compute-1.amazonaws.com:5432/d4bnpmfglihmg0"
    else:
        SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    API_KEY = "AIzaSyDdtXLXJWPJS9bEay-nq0QsAvFxHMvGw3U"
