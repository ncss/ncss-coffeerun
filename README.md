#NCSS CoffeeRun by Maddy

##Running Locally
* Change application/__init__.py to use the dev config with a sqlite3 database
* Create the database and tables and a default user with create_db.py
* Run on command line with run.py
* Open the browser at localhost:5000

##Running On The Website
* Push changes to the site using git push heroku master
* The program is started by this
* There's no DB migration, manually do any changes before you push the dependent changes
