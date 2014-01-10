"""
models.py

"""

from application import db, app
from datetime import datetime
import pytz

def sydney_timezone_now():
    localtz = pytz.timezone("Australia/Sydney")
    localdt = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(localtz)
    return localdt


class User(db.Model):
    __tablename__ = "Users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    device = db.Column(db.String)

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

class Run(db.Model):
    __tablename__ = "Runs"
    id = db.Column(db.Integer, primary_key=True)
    person = db.Column(db.Integer, db.ForeignKey("Users.id"))
    time = db.Column(db.DateTime)
    deadline = db.Column(db.DateTime)
    cafe = db.Column(db.String)
    pickup = db.Column(db.String)
    status = db.Column(db.Integer, db.ForeignKey("Statuses.id"))
    statusobj = db.relationship("Status")
    modified = db.Column(db.DateTime, default=sydney_timezone_now);

    fetcher = db.relationship("User", backref=db.backref("runs", order_by=id))

    def __init__(self, time):
        #self.personid = personid
        self.time = time

    def __repr__(self):
        return "<Run('%s','%s')>" % (self.fetcher.name, self.time)

    def readtime(self):
        return self.time.strftime("%I:%M %p %a %d %b")

    def readdeadline(self):
        return self.deadline.strftime("%I:%M %p %a %d %b")

    def readmodified(self):
        return self.modified.strftime("%I:%M %p %a %d %b")

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
    sugar = db.Column(db.String)
    run = db.Column(db.Integer, db.ForeignKey("Runs.id"))
    modified = db.Column(db.DateTime(timezone=True), default=sydney_timezone_now);
    
    runobj = db.relationship("Run", backref=db.backref("coffees", order_by="Coffee.id"))
    addict = db.relationship("User", backref=db.backref("coffees", order_by="Coffee.id"))

    def __init__(self, coffeetype):
        self.coffeetype = coffeetype

    def __repr__(self):
        return "<Coffee(%d,%d,'%s %s %ds')>" % (self.id, self.person, self.size, self.coffeetype, self.sugar)

    def readmodified(self):
        return self.modified.strftime("%I:%M %p %a %d %b")

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


