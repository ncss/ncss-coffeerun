"""
forms.py

Web forms based on Flask-WTForms

See: http://flask.pocoo.org/docs/patterns/wtforms/
     http://wtforms.simplecodes.com/

"""

from flask.ext.wtf import Form
from wtforms import validators, SelectField, TextField, IntegerField, DateTimeField, FloatField, BooleanField


class CoffeeForm(Form):
    person = SelectField("Addict", coerce=int)
    coffee = TextField("Coffee", [validators.Required()])
    price = FloatField("Price", default=0)
    runid = SelectField("Run", coerce=int)
    starttime = DateTimeField("Start Time", format="%Y/%m/%d %H:%M")
    endtime = DateTimeField("End Time", format="%Y/%m/%d %H:%M")
    recurring = BooleanField("Recurring", default=False)
    days = IntegerField("Days To Recur", default=0)

class RunForm(Form):
    person = SelectField("Person", coerce=int)
    time = DateTimeField("Time of Run", [validators.Required()], format="%Y/%m/%d %H:%M")
    cafeid = SelectField("Cafe", coerce=int)
    pickup = TextField("Pickup Location")
    addpending = BooleanField("Add All Pending Coffees", default=True)

class CafeForm(Form):
    name = TextField("Name", [validators.Required()])
    location = TextField("Location")

class PriceForm(Form):
    cafeid = SelectField("Cafe", coerce=int)
    price_key = TextField("Price ID (format is picky)")
    amount = FloatField("Amount", [validators.Required()])

class TeacherForm(Form):
    name = TextField("Username", [validators.Required()])
    email = TextField("Email")