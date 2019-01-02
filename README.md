# NCSS CoffeeRun by Maddy

## Running Locally
* Create a virtual environment:
  `virtualenv --python="$(which python2)" env`
* Activate the virtual enviroment:
  `source env/bin/activate`
* install requirements:
  `pip install -r requirements/dev.txt`
* Create the database and tables and a default user with create\_db.py
  `python2 create_db.py`
* Run on command line:
  * `python2 run.py` (for the web ui)
  * `python2 coffeebot.py` (for the slack bot)
* Open the browser at http://localhost:5000 (note: Use localhost, not 127.0.0.1)

## Running tests locally
 * Activate the virtual enviroment:
   `source env/bin/activate`
 * Run the coffeespec tests:
   `python test_coffeespecs.py`

## Running On The Website
* Push changes to the site using git push heroku master
* The program is started by this
* There's no DB migration, manually do any changes before you push the dependent changes
