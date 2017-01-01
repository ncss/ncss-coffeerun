import os

from flask import Flask
from flask_babel import Babel
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from flask_mail import Mail
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

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
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

lm = LoginManager()
lm.init_app(app)
lm.login_view = "login"

mail = Mail()
mail.init_app(app)


from application import views, models
