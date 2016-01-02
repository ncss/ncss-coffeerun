
from application import app, db
from application.models import Cafe

db.drop_all()
db.init_app(app)
db.create_all()

db.session.add(Cafe('Toby\'s Estate', 'City Rd'))
db.session.add(Cafe('Campos', 'Newtown'))
db.session.add(Cafe('Twenty 8 Acres', 'Ivy Ln, Darlington'))
db.session.add(Cafe('Taste Baguette', 'Sydney Uni Law Building'))

db.session.commit()
