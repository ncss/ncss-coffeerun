
from application import db
from application.models import Coffee

coffees = Coffee.query.all()

for coffee in coffees:
    if coffee.price == 4:
        print coffee, coffee.price

        new_price = coffee.lookup_price()
        if new_price != 4:
            print 'Updating price for coffee {} from {}  to {}'.format(coffee.id, coffee.price, new_price)
            coffee.price = new_price

        else:
            print 'No price for:', coffee

db.session.commit()
