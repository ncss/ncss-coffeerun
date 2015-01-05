"""models.py
DB models for the ncss-coffeerun app
Maddy Reid 2014
"""

from application import db, app
from datetime import datetime
import pytz

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
    email = db.Column(db.String)
    device = db.Column(db.String)
    tutor = db.Column(db.Boolean, default=False)
    teacher = db.Column(db.Boolean, default=False)
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
        return unicode(self.id)

    def moneyOwedTotal(self):
        amount = 0.0
        for coffee in self.coffees:
            if not coffee.paid and coffee.run.person != self.id:
                amount += coffee.price
        return amount

    def moneyIsOwedTotal(self):
        amount = 0.0
        for run in self.runs:
            for coffee in run.coffees:
                if not coffee.paid and coffee.person != self.id:
                    amount += coffee.price
        return amount

    def moneyOwedPerson(self, debtor):
        amount = 0.0
        for coffee in self.coffees:
            if not coffee.paid and coffee.run.fetcher == debtor:
                amount += coffee.price
        return amount

    def moneyIsOwedPower(self, debtor):
        amount = 0.0
        for coffee in debtor.coffees:
            if not coffee.paid and coffee.run.fetcher == self:
                amount += coffee.price
        return amount

class Run(db.Model):
    __tablename__ = "Runs"
    id = db.Column(db.Integer, primary_key=True)
    person = db.Column(db.Integer, db.ForeignKey("Users.id"))
    time = db.Column(db.DateTime(timezone=True))
    deadline = db.Column(db.DateTime(timezone=True))
    cafeid = db.Column(db.Integer, db.ForeignKey("Cafes.id"))
    cafe = db.relationship("Cafe", backref=db.backref("runs", order_by=id))

    pickup = db.Column(db.String)
    statusid = db.Column(db.Integer, db.ForeignKey("Statuses.id"))
    status = db.relationship("Status")
    modified = db.Column(db.DateTime(timezone=True), default=sydney_timezone_now);

    fetcher = db.relationship("User", backref=db.backref("runs", order_by=time.desc()))

    def __init__(self, time):
        #self.personid = personid
        self.time = time

    def __repr__(self):
        return "<Run('%s','%s')>" % (self.fetcher.name, self.time)

    def readtime(self):
        localtz = pytz.timezone("Australia/Sydney")
        #return self.time.astimezone(localtz).strftime("%I:%M %p %a %d %b")
        return self.time.strftime("%I:%M %p %a %d %b")

    def readdeadline(self):
        localtz = pytz.timezone("Australia/Sydney")
        #return self.deadline.astimezone(localtz).strftime("%I:%M %p %a %d %b")
        return self.deadline.strftime("%I:%M %p %a %d %b")

    def readmodified(self):
        localtz = pytz.timezone("Australia/Sydney")
        return self.modified.replace(tzinfo=pytz.utc).astimezone(localtz).strftime("%I:%M %p %a %d %b")

    def jsondatetime(self, arg):
        tformat = "%Y-%m-%d %H:%M:%S"
        if arg == "time":
            return self.time.strftime(tformat)
        if arg == "deadline":
            return self.deadline.strftime(tformat)
        if arg == "modified":    
            return self.modified.strftime(tformat)

    #def sydney_timezone_now(self, utcdt):
    #    localtz = pytz.timezone("Australia/Sydney")
    #    localdt = utcdt.replace(tzinfo=pytz.utc).astimezone(localtz)
    #    return localdt

    def calculateTotalRunCost(self):
        total = 0.0
        for coffee in self.coffees:
            if not coffee.paid:
                total += coffee.price
        return total

    def toJSON(self):
        return {"id": self.id, 
                "person": self.fetcher.name,
                "time": self.jsondatetime("time"),
                "deadline": self.jsondatetime("deadline"),
                "cafe": self.cafe,
                "pickup": self.pickup,
                "status": self.status,
                "modified": self.jsondatetime("modified") }

class Coffee(db.Model):
    __tablename__ = "Coffees"
    id = db.Column(db.Integer, primary_key=True)
    person = db.Column(db.Integer, db.ForeignKey("Users.id"))
    coffeetype = db.Column(db.String)
    size = db.Column(db.String)
    sugar = db.Column(db.Integer)
    runid = db.Column(db.Integer, db.ForeignKey("Runs.id"))
    modified = db.Column(db.DateTime(timezone=True), default=sydney_timezone_now);
    
    run = db.relationship("Run", backref=db.backref("coffees"))
    addict = db.relationship("User", backref=db.backref("coffees", order_by="Coffee.id"))

    priceid = db.Column(db.Integer, db.ForeignKey("Prices.id"))
    #price = db.relationship("Price")
    price = db.Column(db.Float)

    #pricemodid = db.Column(db.Integer, db.ForeignKey("PriceModifiers.id"))

    paid = db.Column(db.Boolean, default=False)

    def __init__(self, coffeetype):
        self.coffeetype = coffeetype

    def __repr__(self):
        return "<Coffee(%d,%d,'%s %s %ds')>" % (self.id, self.person, self.size, self.coffeetype, self.sugar)

    #def readmodified(self):
    #    return self.modified.strftime("%I:%M %p %a %d %b")

    def readmodified(self):
        localtz = pytz.timezone("Australia/Sydney")
        return self.modified.replace(tzinfo=pytz.utc).astimezone(localtz).strftime("%I:%M %p %a %d %b")

    def jsondatetime(self, arg):
        if arg == "modified":
            return self.modified.strftime("%Y-%m-%d %H:%M:%S")

    #def sydney_timezone_now(self, utcdt):
    #    localtz = pytz.timezone("Australia/Sydney")
    #    localdt = utcdt.replace(tzinfo=pytz.utc).astimezone(localtz)
    #    return localdt

    def toJSON(self):
        return {"id": self.id, 
                "person": self.addict.name,
                "coffeetype": self.coffeetype,
                "size": self.size,
                "sugar": self.sugar,
                "runid": self.run,
                "modified": self.jsondatetime("modified") }

class Status(db.Model):
    __tablename__ = "Statuses"
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String)
    
    def __init__(self, description=""):
        self.description = description

    def __repr__(self):
        return "<Status(%d,'%s')>" % (self.id, self.description)

class RegistrationID(db.Model):
    __tablename__ = "RegistrationIDs"
    userid = db.Column(db.Integer, db.ForeignKey("Users.id"), primary_key=True)
    regid = db.Column(db.String, primary_key=True)
    
    user = db.relationship("User", backref=db.backref("regids", order_by="RegistrationID.regid"))

    def __init__(self, userid, regid):
        self.userid = userid
        self.regid = regid

    def __repr__(self):
        return "<RegistrationID(%d,'%s')>" % (self.userid, self.regid)

class Cafe(db.Model):
    __tablename__ = "Cafes"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    location = db.Column(db.String)

    def __init__(self, name=""):
        self.name = name

    def __repr__(self):
        return "<Cafe(%d,'%s')>" % (self.id, self.name)

class Price(db.Model):
    __tablename__ = "Prices"
    id = db.Column(db.Integer, primary_key=True)
    cafeid = db.Column(db.Integer, db.ForeignKey("Cafes.id"))
    size = db.Column(db.String)
    amount = db.Column(db.Float)

    cafe = db.relationship("Cafe", backref=db.backref("pricelist", lazy="dynamic", single_parent=True, cascade="all, delete, delete-orphan"))

    def __init__(self, cafeid, size=""):
        self.cafeid = cafeid
        self.size = size
        self.amount = 0.0

    def __repr__(self):
        return "<Price(%d,'%s','%f')>" % (self.cafeid, self.size, self.amount)

class PriceModifier(db.Model):
    __tablename__ = "PriceModifiers"
    id = db.Column(db.Integer, primary_key=True)
    cafeid = db.Column(db.Integer, db.ForeignKey("Cafes.id"))
    modtype = db.Column(db.String)
    amount = db.Column(db.Float)

    cafe = db.relationship("Cafe", backref=db.backref("pricemods"))

    def __init__(self, cafeid, modtype=""):
        self.cafeid = cafeid
        self.modtype = size
        self.amount = 0.0

    def __repr__(self):
        return "<PriceModifier(%d,'%s','%f')>" % (self.cafeid, self.modtype, self.amount)

class Event(db.Model):
    __tablename__ = "Events"
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey("Users.id"))
    action = db.Column(db.String)
    objtype = db.Column(db.String)
    objid = db.Column(db.Integer)
    time = db.Column(db.DateTime(timezone=True), default=sydney_timezone_now)

    user = db.relationship("User", backref=db.backref("events", order_by=id.desc()))

    def __init__(self, userid=0, action="", objtype="", objid=""):
        self.userid = userid
        self.action = action
        self.objtype = objtype
        self.objid = objid

    def __repr__(self):
        return "<PriceModifier(%d, %d, '%s', '%s', %d, '%s')>" % (self.id, self.userid, self.cation, self.objtype, self.objid, self.time)
    
    def readtime(self):
        localtz = pytz.timezone("Australia/Sydney")
        return self.time.replace(tzinfo=pytz.utc).astimezone(localtz).strftime("%I:%M %p %a %d %b")

    def descrobj(self):
        if self.objtype == "run":
            run = Run.query.filter_by(id=self.objid).first()
            return "for time %s" % run.readtime()
        elif self.objtype == "coffee":
            coffee = Coffee.query.filter_by(id=self.objid).first()
            return "for <a href=\"/run/%s/\">run</a> at time %s" % (coffee.run.id, coffee.run.readtime())
        elif self.objtype == "cafe":
            cafe = Cafe.query.filter_by(id=self.objid).first()
            return "named '%s'" % cafe.name
        elif self.objtype == "price":
            price = Price.query.filter_by(id=self.objid).first()
            return "for <a href=\"/cafe/%s/\">cafe</a> '%s'" % (price.cafe.id, price.cafe.name)
        else:
            return ""
