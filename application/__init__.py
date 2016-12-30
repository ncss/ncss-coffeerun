

import os

from flask import Flask
from flask.ext.babel import Babel
from flask.ext.bootstrap import Bootstrap
from flask.ext.login import LoginManager
from flask.ext.mail import Mail
from flask.ext.session import Session
from flask.ext.sqlalchemy import SQLAlchemy
from celery import Celery

# Setup app
app = Flask(__name__)
app.config.from_object(
        os.environ.get("FLASK_CONFIG", "config.DevConfig"))
Bootstrap(app)

babel = Babel(app)
Session(app)

@babel.timezoneselector
def _timezone():
    return 'Australia/Sydney'  # There exist other places in the world?

@babel.localeselector
def _local():
    return 'en_AU'

db = SQLAlchemy(app)

lm = LoginManager()
lm.init_app(app)
lm.login_view = "login"

mail = Mail()
mail.init_app(app)

def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

celery = make_celery(app)


from application import views, models
