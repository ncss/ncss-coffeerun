from application import app, db
from application.models import Cafe


def main():
    db.drop_all()
    db.init_app(app)
    db.create_all()

    db.session.add(Cafe('ABS', 'Sydney Uni: Business School'))
    db.session.add(Cafe('Cafe Ella', '274 Abercrombie St, Darlington'))
    db.session.add(Cafe('Campos', 'Newtown'))
    db.session.add(Cafe('Taste Baguette (CPC)', 'Sydney Uni: Charles Perkins Centre'))
    db.session.add(Cafe('Taste Baguette (Law)', 'Sydney Uni: Law Building'))
    db.session.add(Cafe('The Shortlist', '258 Abercrombie St, Darlington'))
    db.session.add(Cafe('Toby\'s Estate', 'City Rd'))

    db.session.commit()


if __name__ == '__main__':
    main()
