#!/usr/bin/env python3
import collections
import pprint

from absl import app, flags, logging

from application import db, models

import coffeespecs


FLAGS = flags.FLAGS

flags.DEFINE_string('echo', None, 'Text to echo.')
flags.DEFINE_string('cafe', None, 'The cafe to process.')
flags.DEFINE_integer('run_id', None, 'The specific run to process.')
flags.DEFINE_boolean('dry_run', True, 'Should this execution modify any data?')
flags.DEFINE_boolean('all_coffee', False, 'Should all coffees be processed, or only coffees that have the default price?')


def main(argv):
    del argv    # Unused.

    # Map from cafe -> fuzzy key -> real key
    unknown_coffees = collections.defaultdict(lambda: collections.defaultdict(set))
    changed = 0
    unknown = 0
    delta = 0.0

    filters = [
    ]
    if not FLAGS.all_coffee:
        filters.append(models.Coffee.price == 4.0)
    if FLAGS.cafe:
        filters.append(models.Cafe.name == FLAGS.cafe)
    if FLAGS.run_id:
        filters.append(models.Run.id == FLAGS.run_id)

    query = models.Coffee.query.filter(*filters).join(models.Run).join(models.Cafe)
    logging.info('About to execute the query: %s', query)

    for coffee in query:
        logging.info('Processing %s, current price: $%s', coffee, coffee.price)
        new_price = coffee.lookup_price(default_price=None)
        if new_price is not None:
            if coffee.price == new_price:
                continue
            logging.info('Updating price for coffee %s from %s to %s', coffee.id, coffee.price, new_price)
            delta += new_price - coffee.price
            coffee.price = new_price
            changed += 1
        else:
            logging.warn('No price for: %s', coffee)
            spec = coffeespecs.Coffee.fromJSON(coffee.coffee)
            unknown_coffees[coffee.run.cafe.name][spec.get_price_key(fuzzy_fields={'type', 'size', 'strength'})].add(spec.get_price_key())
            unknown += 1
    if FLAGS.dry_run:
        db.session.rollback()
    else:
        db.session.commit()

    unknown_coffees = {
            cafe_name: {
                fuzzy_key: full_keys
                for fuzzy_key, full_keys in _.items()}
            for cafe_name, _ in unknown_coffees.items()}

    pprint.pprint(unknown_coffees)
    print('Changes: {} (${}), unknowns: {}'.format(changed, delta, unknown))


if __name__ == '__main__':
    app.run(main)
