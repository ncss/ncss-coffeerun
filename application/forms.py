"""
forms.py

Web forms based on Flask-WTForms

See: http://flask.pocoo.org/docs/patterns/wtforms/
     http://wtforms.simplecodes.com/

"""

from flask.ext.wtf import Form
from wtforms import validators, SelectField, TextField, IntegerField, DateTimeField, FloatField, BooleanField

class LoginForm(Form):
    users = SelectField("User", coerce=int)
    newuser = TextField("Register")

class CoffeeForm(Form):
    person = SelectField("Addict", coerce=int)
    coffeetype = TextField("Coffee", [validators.Required()])
    size = SelectField("Size", choices=[("S","S"),("M","M"),("L","L")])
    sugar = IntegerField("Sugar", default=0)
    price = FloatField("Price", default=0)
    runid = SelectField("Run", coerce=int)
    paid = BooleanField("Paid", default=False)
    recurring = BooleanField("Recurring", default=False)
    starttime = DateTimeField("Start Time", format="%Y/%m/%d %H:%M")
    endtime = DateTimeField("End Time", format="%Y/%m/%d %H:%M")
    days = IntegerField("Days Repeating", default = 1)

class RunForm(Form):
    person = SelectField("Person", coerce=int)
    time = DateTimeField("Time of Run", [validators.Required()], format="%Y/%m/%d %H:%M")
    deadline = DateTimeField("Deadline for Adding", format="%Y/%m/%d %H:%M")
    cafeid = SelectField("Cafe", coerce=int)
    pickup = TextField("Pickup Location")
    statusid = SelectField("Status", coerce=int)
    addpending = BooleanField("Add All Pending Coffees", default=True)

class UserForm(Form):
    name = TextField("Name")
    email = TextField("Email", [validators.Required()])
    group = TextField("Group")
    tutor = BooleanField("Tutor")
    teacher = BooleanField("Teacher")
    alerts = BooleanField("Email Alerts")

class CafeForm(Form):
    name = TextField("Name", [validators.Required()])
    location = TextField("Location")

class PriceForm(Form):
    cafeid = SelectField("Cafe", coerce=int)
    size = SelectField("Size", [validators.Required()], choices=[("S", "S"), ("M", "M"), ("L", "L")])
    amount = FloatField("Amount", [validators.Required()])
