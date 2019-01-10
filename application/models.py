"""models.py
DB models for the ncss-coffeerun app
Maddy Reid 2014
"""
from datetime import datetime

from application import db

import coffeespecs

import pytz

import sqlalchemy


class UTCOnlyDateTime(sqlalchemy.types.TypeDecorator):
    """A wrapper around the sqlachemy DateTime class that stores stuff in UTC.

    Internally, this type uses timezone nieve datetime objects (which
    we know are actually in UTC). We use this notation, because:
      a) Not all database backends support datetimes with timezones
         (aka sqlite),
      b) You really should not do math with timezone aware datetimes
         if possible.
    """

    impl = sqlalchemy.types.DateTime

    def process_bind_param(self, value, dialect):
        """Convert from a tz aware object to a nieve object [in UTC]."""
        assert value.tzinfo is not None, (
                "Time should be tz aware, but is nieve")
        return value.astimezone(pytz.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        """Convert from a tz nieve object [in UTC] to a tz aware object."""
        assert value.tzinfo is None, (
                'Time should be nieve, but had timezone: %s' % value.tzinfo)
        tz_ = pytz.timezone("Australia/Sydney")
        return value.replace(tzinfo=pytz.utc).astimezone(tz_)


def sydney_timezone_now():
    localtz = pytz.timezone("Australia/Sydney")
    localdt = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(localtz)
    return localdt


def sydney_timezone(time):
    localtz = pytz.timezone("Australia/Sydney")
    localdt = time.astimezone(localtz)
    return localdt


class User(db.Model):
    __tablename__ = "Users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    slack_team_id = db.Column(db.String)
    slack_user_id = db.Column(db.String)
    email = db.Column(db.String)
    device = db.Column(db.String)
    tutor = db.Column(db.Boolean, default=False)
    teacher = db.Column(db.Boolean, default=False)
    group = db.Column(db.String)
    alerts = db.Column(db.Boolean, default=False)

    def __init__(self, name=""):
        self.name = name

    def __repr__(self):
        return "<User(%d,%s)>" % (self.id, self.name)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def get_slack_mention(self):
        return '<@{}>'.format(self.slack_user_id)

    def money_owed(self):
        coffee_money_owed = sqlalchemy.sql.select(
                [sqlalchemy.sql.functions.sum(Coffee.price).label('total')],
                Run.person == self.id,
                from_obj=sqlalchemy.sql.join(Run, Coffee))

        # NOTE: We may end up performing a sum of 0 rows... Which is
        # Null/None. This is why we need to do 'or 0'.
        amount = 0
        amount += (
                db.engine.execute(coffee_money_owed).first().total or 0)
        return amount

    def money_owing(self):
        coffee_money_owing = sqlalchemy.sql.select(
                [sqlalchemy.sql.functions.sum(Coffee.price).label('total')],
                Coffee.person == self.id,
                from_obj=Coffee)

        # NOTE: We may end up performing a sum of 0 rows... Which is
        # Null/None. This is why we need to do 'or 0'.
        amount = 0
        amount += (
                db.engine.execute(coffee_money_owing).first().total or 0)
        return amount


class SlackTeamAccessToken(db.Model):
    team_id = db.Column(db.String, primary_key=True)
    # OAuth token granted to us. This token is used to:
    #  - Log people into the coffeerun site (identity), and
    #  - Post notifications to the #coffee channel.
    access_token = db.Column(db.String)

    # The name of the workspace we were added to.
    workspace_name = db.Column(db.String)

    # The channel id to post read messages from, and to reply to.
    coffee_slack_channel = db.Column(db.String, nullable=True)
    # OAuth token for the chat bot (actually a different slack app to the one
    # above).
    coffee_bot_slack_access_token = db.Column(db.String, nullable=True)
    coffee_bot_slack_user_id = db.Column(db.String, nullable=True)

    # Should we send announcements to this slack workspace (broadcasts/etc).
    wants_slack_notifications = db.Column(db.Boolean, nullable=False, default=False)

    # Config to ensure that we do not allow people to accidently sign in from a
    # slack workspace that is not associated with NCSS.
    allow_login = db.Column(db.Boolean, default=False, nullable=False)


class Run(db.Model):
    __tablename__ = "Runs"
    id = db.Column(db.Integer, primary_key=True)
    person = db.Column(db.Integer, db.ForeignKey("Users.id"))
    time = db.Column(UTCOnlyDateTime(timezone=False))
    cafeid = db.Column(db.Integer, db.ForeignKey("Cafes.id"))
    cafe = db.relationship("Cafe", backref=db.backref("runs", order_by=id))

    pickup = db.Column(db.String)
    is_open = db.Column(db.Boolean, default=True)
    modified = db.Column(UTCOnlyDateTime(timezone=False), default=sydney_timezone_now)

    fetcher = db.relationship("User", backref=db.backref("runs", order_by=time.desc()))

    def __init__(self, time):
        self.time = time

    def __repr__(self):
        return "<Run('%s','%s')>" % (self.fetcher.name, self.time)

    def prettyprint(self):
        time_str = sydney_timezone(self.time).strftime("%I:%M %p (%a)")
        cafe = self.cafe.name
        return time_str + " to " + cafe

    def jsondatetime(self, arg):
        tformat = "%Y-%m-%d %H:%M:%S"
        if arg == "time":
            return self.time.strftime(tformat)
        if arg == "modified":
            return self.modified.strftime(tformat)

    def calculateTotalRunCost(self):
        total = 0
        for coffee in self.coffees:
            total += coffee.price
        return total

    def close_run(self, total_cost):
        self.is_open = False
        # TODO: Enter all the money exchanges

    def toJSON(self):
        return {
            "id": self.id,
            "person": self.fetcher.name,
            "time": self.jsondatetime("time"),
            "cafe": self.cafe,
            "pickup": self.pickup,
            "is_open": self.is_open,
            "modified": self.jsondatetime("modified")
        }


class Coffee(db.Model):
    __tablename__ = "Coffees"
    id = db.Column(db.Integer, primary_key=True)
    person = db.Column(db.Integer, db.ForeignKey("Users.id"))
    coffee = db.Column(db.String)  # json field
    runid = db.Column(db.Integer, db.ForeignKey("Runs.id"))
    modified = db.Column(UTCOnlyDateTime(timezone=False), default=sydney_timezone_now)

    run = db.relationship("Run", backref=db.backref("coffees"))
    addict = db.relationship("User", backref=db.backref("coffees", order_by="Coffee.id"))

    price = db.Column(db.Float)  # In Dollars

    starttime = db.Column(UTCOnlyDateTime(timezone=False), default=sydney_timezone_now)
    endtime = db.Column(UTCOnlyDateTime(timezone=False), default=sydney_timezone_now)
    expired = db.Column(db.Boolean, default=False)

    def __init__(self, coffee_request, entered_price, runid):
        if isinstance(coffee_request, coffeespecs.Coffee):
            c = coffee_request
        else:
            c = coffeespecs.Coffee(coffee_request)
        self.coffee = c.toJSON()
        if runid != -1:
            self.runid = runid
        if entered_price != 0:
            self.price = entered_price
        else:
            self.price = self.lookup_price()

    def __repr__(self):
        c = coffeespecs.Coffee.fromJSON(self.coffee)
        return "<Coffee(%s, %s,'%s')>" % (self.id, self.person, str(c))

    def jsondatetime(self, arg):
        if arg == "modified":
            return self.modified.strftime("%Y-%m-%d %H:%M:%S")

    def lookup_price(self, default_price=4.0):
        run = Run.query.filter_by(id=self.runid).first()
        if not run:
            return 0

        # Lookup all prices at the same time, then determine which one to use.
        price_keys = coffeespecs.Coffee.fromJSON(self.coffee).get_ordered_price_keys()
        prices = Price.query.filter(
                sqlalchemy.sql.and_(
                    Price.price_key.in_(price_keys),
                    Price.cafeid == run.cafeid)).all()

        if not prices:
            return default_price
        result_map = {price.price_key: price for price in prices}
        for price_key in price_keys:
            if price_key not in result_map:
                continue
            return result_map[price_key].amount
        else:
            assert False

    def pretty_print(self):
        return str(coffeespecs.Coffee.fromJSON(self.coffee))

    def toJSON(self):
        return {
            "id": self.id,
            "person": self.addict.name,
            "coffeetype": self.coffeetype,
            "size": self.size,
            "sugar": self.sugar,
            "runid": self.run,
            "modified": self.jsondatetime("modified")
        }


class Cafe(db.Model):
    __tablename__ = "Cafes"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    location = db.Column(db.String)

    def __init__(self, name="", location=""):
        self.name = name
        self.location = location

    def __repr__(self):
        return "<Cafe(%d,'%s')>" % (self.id, self.name)


class Price(db.Model):
    __tablename__ = "Prices"
    id = db.Column(db.Integer, primary_key=True)
    cafeid = db.Column(db.Integer, db.ForeignKey("Cafes.id"))
    price_key = db.Column(db.String)
    amount = db.Column(db.Float)  # Dollars

    cafe = db.relationship("Cafe", backref=db.backref("pricelist", lazy="dynamic", single_parent=True, cascade="all, delete, delete-orphan"))

    def __init__(self, cafeid, coffee):
        self.cafeid = cafeid
        self.price_key = coffee.get_price_key()
        self.amount = 0.0

    def __repr__(self):
        return "<Price(%d,'%s','%f')>" % (self.cafeid, self.price_key, self.amount)


class Event(db.Model):
    __tablename__ = "Events"
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey("Users.id"))
    action = db.Column(db.String)
    objtype = db.Column(db.String)
    objid = db.Column(db.Integer)
    time = db.Column(UTCOnlyDateTime(timezone=False), default=sydney_timezone_now)

    user = db.relationship("User", backref=db.backref("events", order_by=id.desc()))

    def __init__(self, userid=0, action="", objtype="", objid=""):
        self.userid = userid
        self.action = action
        self.objtype = objtype
        self.objid = objid

    def descrobj(self):
        if self.action != "deleted":
            if self.objtype == "run":
                run = Run.query.filter_by(id=self.objid).first()
                if run:
                    return "for time %s" % run.time
            elif self.objtype == "coffee":
                coffee = Coffee.query.filter_by(id=self.objid).first()
                if coffee and coffee.run:
                    return "for <a href=\"/run/%s/\">run</a> at time %s" % (
                            coffee.run.id, coffee.run.time)
            elif self.objtype == "cafe":
                cafe = Cafe.query.filter_by(id=self.objid).first()
                if cafe:
                    return "named '%s'" % cafe.name
            elif self.objtype == "price":
                price = Price.query.filter_by(id=self.objid).first()
                if price:
                    return "for <a href=\"/cafe/%s/\">cafe</a> '%s'" % (price.cafe.id, price.cafe.name)
            else:
                return ""
        return ""
