
from application import app, db
from application.models import *

from migrate.versioning import api
import os.path

db.drop_all()
db.init_app(app)
db.create_all()
if not os.path.exists(app.config["SQLALCHEMY_MIGRATE_REPO"]):
    api.create(app.config["SQLALCHEMY_MIGRATE_REPO"], 'database repository')
    api.version_control(app.config["SQLALCHEMY_DATABASE_URI"], app.config["SQLALCHEMY_MIGRATE_REPO"])
else:
    api.version_control(app.config["SQLALCHEMY_DATABASE_URI"], app.config["SQLALCHEMY_MIGRATE_REPO"], api.version(app.config["SQLALCHEMY_MIGRATE_REPO"]))

db.session.add(Cafe('Toby\'s Estate', 'City Rd'))
db.session.add(Cafe('Campos', 'Newtown'))
db.session.add(Cafe('Twenty 8 Acres', 'Ivy Ln, Darlington'))
db.session.add(Cafe('Taste Baguette', 'Sydney Uni Law Building'))

db.session.commit()
