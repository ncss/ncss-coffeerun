"""
forms.py

Web forms based on Flask-WTForms

See: http://flask.pocoo.org/docs/patterns/wtforms/
     http://wtforms.simplecodes.com/

"""

from flask.ext.wtf import Form
from wtforms import validators, SelectField, TextField, IntegerField, DateTimeField

class LoginForm(Form):
    users = SelectField("User", coerce=int)
    newuser = TextField("Register")

class CoffeeForm(Form):
    person = SelectField("Addict", coerce=int)
    coffeetype = TextField("Coffee", [validators.Required()])
    size = SelectField("Size", choices=[("S","S"),("M","M"),("L","L")])
    sugar = IntegerField("Sugar", default=0)
    run = SelectField("Run", coerce=int)

class RunForm(Form):
    person = SelectField("Person", coerce=int)
    time = DateTimeField("Time of Run", [validators.Required()], format="%Y/%m/%d %H:%M")
    deadline = DateTimeField("Deadline for Adding", format="%Y/%m/%d %H:%M")
    cafe = TextField("Cafe")
    pickup = TextField("Pickup Location")
    status = SelectField("Status", coerce=int)

class UserForm(Form):
    name = TextField("Name")
