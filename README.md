# NCSS CoffeeRun by Maddy

## Running Locally
* Create a virtual environment:
  `virtualenv2 --python="$(which python2)" ~/.virtualenvs/coffeerun`
* Activate the virtual enviroment:
  `source ~/.virtualenvs/coffeerun/bin/activate`
* install requirements:
  `pip install -r requirements/dev.txt`
* Change application/\_\_init\_\_.py to use the dev config with a sqlite3 database
* Create the database and tables and a default user with create\_db.py
* Run on command line:
  * run.py (for the web ui)
  * coffeebot.py (for the slack bot)
* Open the browser at http://localhost:5000

## Running tests locally
 * Activate the virtual enviroment:
   `source ~/.virtualenvs/coffeerun/bin/activate`
 * Run the coffeespec tests:
   `python test_coffeespecs.py`

## Running On The Website
* Push changes to the site using git push heroku master
* The program is started by this
* There's no DB migration, manually do any changes before you push the dependent changes
