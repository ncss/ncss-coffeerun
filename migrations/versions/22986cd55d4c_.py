"""Convert iced coffee/chocolate to their native types.

Revision ID: 22986cd55d4c
Revises: 9be479dcb66e
Create Date: 2017-01-10 13:25:26.477215

"""
import json

from alembic import op
from application import models, db
import sqlalchemy as sa

from sqlalchemy.orm import sessionmaker
Session = sessionmaker()


# revision identifiers, used by Alembic.
revision = '22986cd55d4c'
down_revision = '9be479dcb66e'
branch_labels = None
depends_on = None


def upgrade():
    for coffee in models.Coffee.query.all():
        coffee_spec = json.loads(coffee.coffee)
        if not coffee_spec.get('iced') == 'Iced':
            # Nothing to do for this coffee
            continue
        old_coffee_spec = dict(coffee_spec)
        # We are removing the iced designation.
        del coffee_spec['iced']
        if coffee_spec['type'] in {'Hot Chocolate'}:
            coffee_spec['type'] = 'Iced Chocolate'
        elif coffee_spec['type'] in {'Latte', 'Cappuccino'}:
            coffee_spec['type'] = 'Iced Coffee'
        else:
            raise Exception('Unknown iced coffee type: %s' % coffee)
        coffee.coffee = json.dumps(coffee_spec, sort_keys=True)
        db.session.add(coffee)
    db.session.commit()


def downgrade():
    connection = op.get_bind()
    for coffee in models.Coffee.query.all():
        coffee_spec = json.loads(coffee.coffee)
        if not coffee_spec['type'].startswith('Iced'):
            # Nothing to do for this coffee
            continue
        # We are removing the iced designation.
        coffee_spec['iced'] = 'Iced'
        if coffee_spec['type'] in {'Iced Chocolate'}:
            coffee_spec['type'] = 'Hot Chocolate'
        elif coffee_spec['type'] in {'Iced Coffee'}:
            coffee_spec['type'] = 'Latte'  # This is lossy
        else:
            raise Exception('Unknown iced coffee type: %s' % coffee)
        coffee.coffee = json.dumps(coffee_spec, sort_keys=True)
        db.session.add(coffee)
    db.session.commit()
