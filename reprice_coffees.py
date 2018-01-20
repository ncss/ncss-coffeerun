from __future__ import print_function

import collections

import coffeespecs
from application import db
from application.models import Coffee

# Map from cafe -> fuzzy key -> real key
unknown_coffees = collections.defaultdict(lambda: collections.defaultdict(set))
changed = 0
unknown = 0
delta = 0.0

for coffee in Coffee.query.filter(Coffee.price == 4.0):
    if coffee.price == 4:
        print(coffee, coffee.price)

        new_price = coffee.lookup_price(default_price=None)
        if new_price is not None:
            if coffee.price == new_price:
                continue
            print('Updating price for coffee {} from {} to {}'.format(coffee.id, coffee.price, new_price))
            delta += new_price - coffee.price
            coffee.price = new_price
            changed += 1
        else:
            print('No price for:', coffee)
            spec = coffeespecs.Coffee.fromJSON(coffee.coffee)
            unknown_coffees[coffee.run.cafe.name][spec.get_price_key(fuzzy=True)].add(spec.get_price_key())
            unknown += 1
db.session.commit()

unknown_coffees = {
        cafe_name: {
            fuzzy_key: full_keys
            for fuzzy_key, full_keys in _.iteritems()}
        for cafe_name, _ in unknown_coffees.iteritems()}
import pprint
pprint.pprint(unknown_coffees)
print('Changes: {} (${}), unknowns: {}'.format(changed, delta, unknown))
