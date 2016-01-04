#NCSS CoffeeRun by Maddy

##Running Locally
* Create a virtual environment:
  `virtualenv2 --python=`which python2` ~/.virtualenvs/coffeerun`
* Activate the virutal enviroment:
  `source ~/.virtualenvs/coffeerun/bin/activate`
* install requirements:
  `pip install -r requirements/dev.txt`
* Change application/__init__.py to use the dev config with a sqlite3 database
* Create the database and tables and a default user with create_db.py
* Run on command line:
  * run.py (for the web ui)
  * coffeebot.py (for the slack bot)
* Open the browser at localhost:5000

##Running On The Website
* Push changes to the site using git push heroku master
* The program is started by this
* There's no DB migration, manually do any changes before you push the dependent changes
