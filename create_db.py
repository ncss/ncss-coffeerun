
from application import db
from application.models import Status

#print Status
db.create_all()

sopen = Status("Open")
sorder = Status("Ordering")
spickup = Status("Pickup")
sclosed = Status("Closed")

db.session.add(sopen)
db.session.add(sorder)
db.session.add(spickup)
db.session.add(sclosed)
db.session.commit()
