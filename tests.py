"""tests.py
Unittesting module for the NCSS Coffeerun web app
Maddy Reid 2014"""

from application import app, db
from application.models import User, Run, Coffee, RunStatus, Cafe, Price
import config
import unittest
from flask.ext.testing import TestCase

from datetime import datetime

class UserModelTest(TestCase):
    
    def create_app(self):
        app.config["TESTING"] = True
        app.config['CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coffeerun-test.db'
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_add_user(self):
        user = User()
        db.session.add(user)
        db.session.commit()
        assert user in db.session
        assert user.is_authenticated() == True
        assert user.is_active() == True
        assert user.is_anonymous() == False
        assert unicode(user.id) == user.get_id()
        db.session.delete(user)
        db.session.commit()
        assert user not in db.session

    def test_user_attributes(self):
        user = User("Maddy")
        user.device = "testid"
        user.tutor = True
        user.tutor = False
        db.session.add(user)
        db.session.commit()
        assert user in db.session
    
    def test_user_has_runs(self):
        user = User()
        db.session.add(user)
        db.session.commit()
        run = Run(datetime.utcnow())
        run.fetcher = user
        assert len(user.runs) == 1
        db.session.add(run)
        db.session.commit()
        assert run in db.session

    def test_user_has_coffees(self):
        user = User()
        db.session.add(user)
        db.session.commit()
        coffee1 = Coffee("Latte")
        coffee2 = Coffee("Cappuccino")
        coffee1.addict = user
        coffee2.addict = user
        db.session.add(coffee1)
        db.session.add(coffee2)
        db.session.commit()
        assert len(user.coffees) == 2
        assert user.coffees[0] == coffee1
        assert user.coffees[1] == coffee2

    def test_user_owes_money_total(self):
        # Set up cafe with menu
        cafe = Cafe()
        db.session.add(cafe)
        db.session.commit()
        price1 = Price(cafe.id, "S")
        price1.amount = 1.4
        price1.cafe = cafe
        price2 = Price(cafe.id, "M")
        price2.amount = 2.5
        price2.cafe = cafe
        db.session.add(price1)
        db.session.add(price2)
        db.session.commit()
        # Create run and add some coffees
        run = Run(datetime.utcnow())
        user = User()
        db.session.add(run)
        db.session.commit()
        coffee1 = Coffee("Latte")
        coffee1.price = price1
        coffee1.run = run
        coffee1.addict = user
        coffee2 = Coffee("Cappuccino")
        coffee2.price = price2
        coffee2.run = run
        coffee3 = Coffee("Mocha")
        coffee3.price = price1
        coffee3.run = run
        coffee3.paid = True
        coffee3.addict = user
        db.session.add(coffee1)
        db.session.add(coffee2)
        db.session.add(coffee3)
        db.session.add(user)
        db.session.commit()
        amount = user.moneyOwedTotal()
        assert amount == 1.4

    def test_user_is_owed_total(self):
        pass

    def test_user_owes_money_to_person(self):
        # Set up cafe with menu
        cafe = Cafe()
        db.session.add(cafe)
        db.session.commit()
        price1 = Price(cafe.id, "S")
        price1.amount = 1.4
        price1.cafe = cafe
        price2 = Price(cafe.id, "M")
        price2.amount = 2.5
        price2.cafe = cafe
        db.session.add(price1)
        db.session.add(price2)
        db.session.commit()
        # Create run and add some coffees
        run = Run(datetime.utcnow())
        user1 = User()
        user2 = User()
        run.fetcher = user2
        db.session.add(user1)
        db.session.add(user2)
        db.session.add(run)
        db.session.commit()
        coffee1 = Coffee("Latte")
        coffee1.price = price1
        coffee1.run = run
        coffee2 = Coffee("Cappuccino")
        coffee2.price = price2
        coffee2.run = run
        coffee2.addict = user1
        coffee3 = Coffee("Mocha")
        coffee3.price = price1
        coffee3.run = run
        coffee3.paid = True
        coffee3.addict = user1
        db.session.add(coffee1)
        db.session.add(coffee2)
        db.session.add(coffee3)
        db.session.commit()
        amount = user1.moneyOwedPerson(user2)
        assert amount == 2.5

    def test_user_is_owed_person(self):
        pass

class RunModelTest(TestCase):
    
    def create_app(self):
        app.config["TESTING"] = True
        app.config['CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coffeerun-test.db'
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_add_run(self):
        run = Run(datetime.utcnow())
        db.session.add(run)
        db.session.commit()
        assert run in db.session
        db.session.delete(run)
        db.session.commit()
        assert run not in db.session

    def test_run_has_coffee(self):
        run = Run(datetime.utcnow())
        db.session.add(run)
        db.session.commit()
        coffee1 = Coffee("Latte")
        coffee2 = Coffee("Cappuccino")
        coffee1.run = run
        coffee2.run = run
        db.session.add(coffee1)
        db.session.add(coffee2)
        db.session.commit()
        assert len(run.coffees) == 2
        assert run.coffees[0] == coffee1
        assert run.coffees[1] == coffee2

    def test_run_has_status(self):
        status = RunStatus("Open")
        db.session.add(status)
        db.session.commit()
        run = Run(datetime.utcnow())
        run.status = status
        assert run.status.description == "Open"

    def test_run_has_cafe(self):
        cafe = Cafe()
        db.session.add(cafe)
        db.session.commit()
        run = Run(datetime.utcnow())
        run.cafe = cafe
        db.session.add(run)
        db.session.commit()
        assert run in cafe.runs

    def test_run_calculate_cost_total(self):
        # Set up cafe with menu
        cafe = Cafe()
        db.session.add(cafe)
        db.session.commit()
        price1 = Price(cafe.id, "S")
        price1.amount = 1.4
        price1.cafe = cafe
        price2 = Price(cafe.id, "M")
        price2.amount = 2.5
        price2.cafe = cafe
        db.session.add(price1)
        db.session.add(price2)
        db.session.commit()
        # Create run and add some coffees
        run = Run(datetime.utcnow())
        db.session.add(run)
        db.session.commit()
        coffee1 = Coffee("Latte")
        coffee1.price = price1
        coffee1.run = run
        coffee2 = Coffee("Cappuccino")
        coffee2.price = price2
        coffee2.run = run
        coffee3 = Coffee("Mocha")
        coffee3.price = price1
        coffee3.run = run
        coffee3.paid = True
        db.session.add(coffee1)
        db.session.add(coffee2)
        db.session.add(coffee3)
        db.session.commit()
        # Calculate total price of run
        total = run.calculateTotalRunCost()
        assert total == 3.9

    # Test timezone and datetime fun

class CoffeeModelTest(TestCase):
    
    def create_app(self):
        app.config["TESTING"] = True
        app.config['CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coffeerun-test.db'
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_add_coffee(self):
        coffee = Coffee("Latte")
        db.session.add(coffee)
        db.session.commit()
        assert coffee in db.session
        db.session.delete(coffee)
        db.session.commit()
        assert coffee not in db.session

    def test_add_to_run(self):
        coffee = Coffee("Latte")
        run = Run(datetime.utcnow())
        coffee.run = run
        db.session.add(coffee)
        db.session.add(run)
        db.session.commit()
        assert coffee in run.coffees

def CafeTestModel(TestCase):

    def create_app(self):
        app.config["TESTING"] = True
        app.config['CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coffeerun-test.db'
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_add_cafe(self):
        cafe = Cafe()
        db.session.add(cafe)
        db.session.commit()
        assert cafe in db.session
        db.session.remove(cafe)
        db.session.commit()
        assert cafe not in db.session


if __name__ == "__main__":
    unittest.main()
