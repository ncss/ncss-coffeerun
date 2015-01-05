#!/bin/python
"""config.py
Configuration objects for the ncss-coffee Flask app
Maddy Reid 2014"""
import os

class Config(object):
    CSFR_ENABLED = True
    SECRET_KEY = "fake"
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = "465"
    MAIL_USERNAME = "ncsscoffeerun@gmail.com"
    MAIL_PASSWORD = "fake"
    MAIL_DEFAULT_SENDER = ("NCSS Coffeebot", "ncsscoffeerun@gmail.com")
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True

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
        SQLALCHEMY_DATABASE_URI = "INSERT KEY HERE"
    else:
        SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    API_KEY = "fake"
