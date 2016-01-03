
from application import app, db
from application.models import *

db.init_app(app)
db.create_all()
