
from application import app, db
from application.models import *

from migrate.versioning import api
from config import ProdConfig
import os.path

db.drop_all()
db.init_app(app)
db.create_all()
if not os.path.exists(ProdConfig.SQLALCHEMY_MIGRATE_REPO):
    api.create(ProdConfig.SQLALCHEMY_MIGRATE_REPO, 'database repository')
    api.version_control(ProdConfig.SQLALCHEMY_DATABASE_URI, ProdConfig.SQLALCHEMY_MIGRATE_REPO)
else:
    api.version_control(ProdConfig.SQLALCHEMY_DATABASE_URI, ProdConfig.SQLALCHEMY_MIGRATE_REPO, api.version(ProdConfig.SQLALCHEMY_MIGRATE_REPO))

db.session.add(Cafe('Toby\'s Estate', 'City Rd'))
db.session.add(Cafe('Campos', 'Newtown'))
db.session.add(Cafe('Twenty 8 Acres', 'Ivy Ln, Darlington'))
db.session.add(Cafe('Taste Baguette', 'Sydney Uni Law Building'))

db.session.commit()
