
import imp
from migrate.versioning import api
from application import db
from config import ProdConfig
v = api.db_version(ProdConfig.SQLALCHEMY_DATABASE_URI, ProdConfig.SQLALCHEMY_MIGRATE_REPO)
migration = ProdConfig.SQLALCHEMY_MIGRATE_REPO + ('/versions/%03d_migration.py' % (v+1))
tmp_module = imp.new_module('old_model')
old_model = api.create_model(ProdConfig.SQLALCHEMY_DATABASE_URI, ProdConfig.SQLALCHEMY_MIGRATE_REPO)
exec(old_model, tmp_module.__dict__)
script = api.make_update_script_for_model(ProdConfig.SQLALCHEMY_DATABASE_URI, ProdConfig.SQLALCHEMY_MIGRATE_REPO, tmp_module.meta, db.metadata)
open(migration, "wt").write(script)
api.upgrade(ProdConfig.SQLALCHEMY_DATABASE_URI, ProdConfig.SQLALCHEMY_MIGRATE_REPO)
v = api.db_version(ProdConfig.SQLALCHEMY_DATABASE_URI, ProdConfig.SQLALCHEMY_MIGRATE_REPO)
print('New migration saved as ' + migration)
print('Current database version: ' + str(v))