#!/bin/python
"""config.py
Configuration objects for the ncss-coffee Flask app
Maddy Reid 2014"""

class Config(object):
    CSFR_ENABLED = True
    SECRET_KEY = "HyP0oHYnYeqv47uXohfvOkiv"

class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///coffeerun-dev.db"

class TestConfig(Config):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///coffeerun-test.db"
    
class ProdConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///coffeerun-prod.db"
