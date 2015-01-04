

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.bootstrap import Bootstrap
from flask.ext.mail import Mail

# Setup app
app = Flask(__name__)
app.config.from_object("config.ProdConfig")
Bootstrap(app)

db = SQLAlchemy(app)

lm = LoginManager()
lm.init_app(app)
lm.login_view = "login"

mail = Mail()
mail.init_app(app)

from application import views, models
