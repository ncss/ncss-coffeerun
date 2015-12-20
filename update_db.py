
from application import app, db
from application.models import *

db.init_app(app)
db.create_all()

s = RunStatus.query.all()
if len(s) == 0:
    sopen = RunStatus("Open")
    sorder = RunStatus("Ordering")
    spickup = RunStatus("Pickup")
    sclosed = RunStatus("Closed")

    inituser = User("Maddy")

    db.session.add(sopen)
    db.session.add(sorder)
    db.session.add(spickup)
    db.session.add(sclosed)
    db.session.add(inituser)
    db.session.commit()
