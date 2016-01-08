
from application import db
from application.models import *


db.drop_all()
db.init_app(app)
db.create_all()

db.session.add(Cafe('Toby\'s Estate', 'City Rd'))
db.session.add(Cafe('Campos', 'Newtown'))
db.session.add(Cafe('Twenty 8 Acres', 'Ivy Ln, Darlington'))
db.session.add(Cafe('Taste Baguette', 'Sydney Uni Law Building'))
db.session.add(Cafe('The House', '9 Knox St, Chippendale'))
db.session.add(Cafe('In The Annex', 'Ross St, Forest Lodge'))
db.session.add(Cafe('Ralphs', 'Ralph\'s Cafe next to Physics'))

db.session.commit()
