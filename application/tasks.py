"""
tasks.py

Worker methods based on Celery

"""

from application import app, db, celery, mail
from application.models import Coffee, sydney_timezone_now
from flask.ext.mail import Message

@celery.task
def send_email(msg):
    """Background task to send an email with Flask-Mail."""
    with app.app_context():
        mail.send(msg)

@celery.task
def expire_coffees():
    coffees = Coffee.query.filter(Coffee.endTime <= sydney_timezone_now()).filter(Coffee.expired==False).all()
    print "coffees", len(coffees), sydney_timezone_now()
    for coffee in coffees:
        coffee.expired = True
        db.session.add(coffee)
        alert_expired(coffee)
    db.session.commit()

def alert_expired(coffee):
    owner = coffee.addict
    if owner.alerts:
        recipients = [owner.email]
        subject = "Alert: your coffee order has been expired"
        body = "No one has picked up your coffee order, so it has been expired.\nPlease consider going for a run yourself.\nRegards, your favourite Coffee Bot!"
        msg = Message(subject, recipients)
        msg.body = body
        send_email(msg)