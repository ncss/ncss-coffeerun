
from application import app, db
from application.models import *

#print Status
db.drop_all()
db.init_app(app)
db.create_all()

sopen = Status("Open")
sorder = Status("Ordering")
spickup = Status("Pickup")
sclosed = Status("Closed")

inituser = User("Maddy")

db.session.add(sopen)
db.session.add(sorder)
db.session.add(spickup)
db.session.add(sclosed)
db.session.add(inituser)
db.session.commit()
