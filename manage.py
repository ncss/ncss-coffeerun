__author__ = 'maddy'

from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

from application import app, db

manager = Manager(app)

migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == "__main__":
    manager.run()