# NCSS CoffeeRun by Maddy

## Running Locally
* Create a virtual environment:
  `virtualenv --python="$(which python3)" env`
* Activate the virtual enviroment:
  `source env/bin/activate`
* install requirements:
  `pip install -r requirements/dev.txt`
* Create the database and tables and a default user with create\_db.py
  `python3 create_db.py`
* Run on command line:
  * `python3 run.py` (for the web ui)
  * `python3 coffeebot.py` (for the slack bot)
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

## Making a new instance

### Prereqs
1. Heroku CLI - https://devcenter.heroku.com/articles/heroku-cli
1. `psql` - idono, search your package manager (should come with postgres)
1. `git clone git@github.com:ncss/ncss-coffeerun.git`
1. `python -m venv .venv`
1. `source .venv/bin/activate` (Every time you want to run/use this code)
1. `pip install -r requirements/prod.txt` (You need postgres, and you might have to mess with versions because of changes in Python - remove the version requirement and see what happens!)

### Heroku
1. Create a new app: https://dashboard.heroku.com/new-app
1. `heroku heroku git:remote -a <heroku-app-name>` (add `--remote=<blah>` if you want to have a different name)
1. `git push heroku master` (replace `heroku` with custom remote name if you did that)

### Slack
1. Create a new Slack app: https://api.slack.com/apps?new\_app=1
1. Add a bot user (and always show as online - but it probably doesn't matter)
1. Install app to workspace (under OAuth & Permissions menu)
1. Add redirect urls (under OAuth & Permissions)
   - `https://<heroku-app-name>.herokuapp.com/login/authorized`
   - `https://<heroku-app-name>.herokuapp.com/team-auth-done/`

### Auth things
1. On Slack app settings page under Basic Information get the Client ID and Client Secret
1. On Heroku, go to the Settings tab and Reveal Config Vars
   - Add `KEY=SLACK_OAUTH_CLIENT_ID`, `VALUE=<client_id>`
   - Add `KEY=SLACK_OAUTH_CLIENT_SECRET`, `VALUE=<client_secret>`

### Database things
1. `export SLACK_OAUTH_CLIENT_ID='<client_id>'`
1. `export SLACK_OAUTH_CLIENT_SECRET='<client_secret>'`
1. `export DATABASE_URL=$(heroku config:get DATABASE_URL -a <heroku-app-name>`
1. (In virtualenv) `python create_db.py`

### More auth and database things
1. Go to https://<heroku-app-name>.herokuapp.com/ and login with Slack
1. Go to https://<heroku-app-name>.herokuapp.com/team-auth/ and add it to the right workspace and channel
   - "Access token stored in db" is Good!
1. Get the bot user details
   - Slack user id (This is probably terrible and totally wrong): New direct message to the bot user, pick out the part after /team/ in the URL you get when you hover over the @name.
   - Bot OAuth access token: In Slack app settings, OAuth & Permissions, copy the Bot token
1. Hack the database
   1. `psql psql $(heroku config:get DATABASE_URL -a <heroku-app-name>`
   1. `update slack_team_access_token set coffee_bot_slack_user_id = '<user_id>', coffee_bot_slack_access_token = '<bot_token>', wants_slack_notifications=true;`

### Last steps
1. On Heroku, go to the Resources tab
1. Enable the worker `python coffeebot.py`
1. Add the bot user to the right channel somehow (I like to @ it)
