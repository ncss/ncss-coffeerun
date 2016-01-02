
from application import app, db
from application.models import RunStatus

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

sopen = RunStatus("Open")
sorder = RunStatus("Ordering")
spickup = RunStatus("Pickup")
sclosed = RunStatus("Closed")

db.session.add(sopen)
db.session.add(sorder)
db.session.add(spickup)
db.session.add(sclosed)

db.session.commit()
