
from application import app, db
from application.models import *

from migrate.versioning import api
from config import Config
import os.path

db.drop_all()
db.init_app(app)
db.create_all()
if not os.path.exists(Config.SQLALCHEMY_MIGRATE_REPO):
    api.create(Config.SQLALCHEMY_MIGRATE_REPO, 'database repository')
    api.version_control(Config.SQLALCHEMY_DATABASE_URI, Config.SQLALCHEMY_MIGRATE_REPO)
else:
    api.version_control(Config.SQLALCHEMY_DATABASE_URI, Config.SQLALCHEMY_MIGRATE_REPO, api.version(Config.SQLALCHEMY_MIGRATE_REPO))


# db.drop_all()
# db.init_app(app)
# db.create_all()
#
# sopen = Status("Open")
# sorder = Status("Ordering")
# spickup = Status("Pickup")
# sclosed = Status("Closed")
#
# inituser = User("Maddy")
# inituser.email = "maddy.reid.21@gmail.com"
# inituser.tutor = True
# inituser.alerts = True
#
# other = User("Test")
# other.email = "silverdragon_star@hotmail.com"
# other.tutor = True
# other.alerts = True
#
# db.session.add(sopen)
# db.session.add(sorder)
# db.session.add(spickup)
# db.session.add(sclosed)
# db.session.add(inituser)
# db.session.add(other)
# db.session.commit()
