
import datetime
import json
import logging
import pytz
import requests
import itertools

from flask import render_template, flash, redirect, session, url_for, request, jsonify
from flask_login import login_required, login_user, current_user, logout_user
from flask_mail import Message
from flask_oauthlib.client import OAuth

from application import app, db, events, lm
from forms import CoffeeForm, RunForm, CafeForm, PriceForm, TeacherForm
from models import User, Run, Coffee, Cafe, Price, Event, SlackTeamAccessToken, sydney_timezone_now, sydney_timezone

import coffeespecs
import utils

oauth = OAuth(app)

slack_user_auth = oauth.remote_app(
    'slack-user',
    consumer_key=app.config['SLACK_OAUTH_CLIENT_ID'],
    consumer_secret=app.config['SLACK_OAUTH_CLIENT_SECRET'],
    request_token_params={'scope': 'identity.basic', 'team': app.config['SLACK_TEAM_ID']},
    base_url='https://slack.com/api/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://slack.com/api/oauth.access',
    authorize_url='https://slack.com/oauth/authorize'
)

slack_team_auth = oauth.remote_app(
    'slack-team',
    consumer_key=app.config['SLACK_OAUTH_CLIENT_ID'],
    consumer_secret=app.config['SLACK_OAUTH_CLIENT_SECRET'],
    request_token_params={'scope': 'chat:write:bot incoming-webhook', 'team': app.config['SLACK_TEAM_ID']},
    base_url='https://slack.com/api/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://slack.com/api/oauth.access',
    authorize_url='https://slack.com/oauth/authorize'
)


@lm.user_loader
def load_user(user_id):
    return User.query.get(user_id)


def get_user_from_slack_token():
    logger = logging.getLogger('views.get_user_from_slack_token')
    token = session.get('slack_token')[0]
    resp = requests.get('http://slack.com/api/users.identity', params={'token': token})
    if resp.status_code != 200:
        logger.info('Failed to get user from slack: %s', resp)
        flash('Error retrieving user info')
        return None

    content = json.loads(resp.content)
    if not content['ok']:
        logger.info('Failed to get user from slack: %s', content)
        flash('Error retrieving user info: ' + content['error'])
        return None

    name = content['user']['name']
    slack_id = content['user']['id']
    slack_team = content['team']['id']
    user = utils.get_or_create_user(slack_id, slack_team, name)
    return user


@app.template_filter('sydney_time')
def _to_sydney_time(t):
    return sydney_timezone(t)


@app.template_filter('format_time')
def _format_time(t):
    # Sample: "11:40 AM Thu 07 Jan"
    return t.strftime("%I:%M %p %a %d %b")


@app.template_filter('sort_and_group_coffees')
def _sort_coffees(coffees):
    # This is a giant hack to group the coffees together, sorted by the
    # arbitary ordering below.
    coffees = list(coffees)
    logger = logging.getLogger('sort_coffees')
    def _key_for_coffee(coffee_model):
        coffee_spec = json.loads(coffee_model.coffee)
        # XXX: Giant hack to deal with the fact that some caffes only have 2 sizes.
        if coffee_spec.get('size') == 'Small':
            coffee_spec['size'] = 'Regular'
        SPEC_ORDERING = ['iced', 'type', 'size', 'decaf', 'strength', 'milk', 'sugar']
        spec_result = tuple(coffee_spec.get(spec, '') for spec in SPEC_ORDERING)
        return spec_result
    coffees.sort(key=_key_for_coffee)

    return ((group_key, list(group_iter))
            for group_key, group_iter in itertools.groupby(
                coffees, lambda x: json.loads(x.coffee)))


@app.route("/")
@login_required
def home():
    run = next_run()
    events = Event.query.order_by(Event.time.desc())[:4]
    return render_template("index.html", run=run, events=events, current_user=current_user)


@app.route('/team-auth/')
def team_auth_start():
  return slack_team_auth.authorize(callback=url_for('team_auth_done', _external=True))


@app.route('/team-auth-done/')
def team_auth_done():
  resp = slack_team_auth.authorized_response()
  if resp is None:
    return 'Access denied: reason=%s error=%s' % (
        request.args['error'],
        request.args['error_description']
    )
  if not resp.get('ok', False):
    return 'There was an error: ' + resp['error']

  access_token = resp['access_token']
  # Store access token in the DB
  access_token_entry = SlackTeamAccessToken.query.get(app.config['SLACK_TEAM_ID'])
  if access_token_entry is None:
      access_token_entry = SlackTeamAccessToken()
      access_token_entry.team_id = app.config['SLACK_TEAM_ID']
  access_token_entry.access_token = access_token
  db.session.add(access_token_entry)
  db.session.commit()
  return 'Access token stored in db'

@app.route("/slacklogin/")
def slacklogin():
  if 'slack_token' in session:
    user = get_user_from_slack_token()
    if user:
      login_user(user)
      return redirect(request.args.get("next") or url_for("home"))
  return slack_user_auth.authorize(callback=url_for('authorized', _external=True))


@app.route('/login/authorized')
def authorized():
    resp = slack_user_auth.authorized_response()
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error'],
            request.args['error_description']
        )
    if not resp.get('ok', False):
        return 'There was an error: ' + resp['error']

    session['slack_token'] = (resp['access_token'], '')
    user = get_user_from_slack_token()
    if user:
        login_user(user)
        return redirect(request.args.get("next") or url_for("home"))
    return redirect(url_for("home"))


@slack_user_auth.tokengetter
def get_slack_token():
    token = session.get('slack_token')
    return token


@app.route("/teacher/register/", methods=["GET","POST"])
def register_teachers():
    form = TeacherForm()
    if request.method == "GET":
        return render_template('teacherlogin.html', form=form, register=True)
    if request.method == "POST" and form.validate_on_submit():
        user = User()
        user.name = form.data["name"]
        user.email = form.data["email"]
        user.teacher = True
        db.session.add(user)
        db.session.commit()
        write_to_events("created", "user", user.id, user)
        login_user(user)
        return redirect(url_for("home"))
    else:
        for field, errors in form.errors.items():
            flash("Error in %s: %s" % (field, "; ".join(errors)), "danger")
        return render_template("teacherlogin.html", form=form, register=True)

@app.route("/teacher/login/", methods=["GET", "POST"])
def login_teachers():
    form = TeacherForm()
    if request.method == "GET":
        return render_template('teacherlogin.html', form=form, register=False)
    if request.method == "POST" and form.validate_on_submit():
        user = db.session.query(User).filter_by(name=form.data["name"]).first()
        if user and login_user(user):
            flash("You are now logged in.", "success")
            return redirect(request.args.get("next") or url_for("home"))
        else:
            flash("Login unsuccessful.", "danger")
            return render_template('teacherlogin.html', form=form, register=False)
    else:
        return render_template('teacherlogin.html', form=form, register=False)


@app.route("/login/", methods=["GET","POST"])
def login():
    return render_template("login.html")


@app.route("/logout/")
@login_required
def logout():
    session.pop('slack_token', None)
    logout_user()
    return redirect(url_for("login"))


@app.route("/about/")
def about():
    return render_template("about/main.html", current_user=current_user)


@app.route("/about/history/")
def about_history():
    return render_template("about/history.html", current_user=current_user)


@app.route("/about/faqs/")
def about_faqs():
    return render_template("about/faqs.html", current_user=current_user)


@app.route("/run/")
def view_all_runs():
    runs = Run.query.order_by(Run.time.desc()).all()
    return render_template("viewallruns.html", runs=runs, current_user=current_user)


@app.route("/coffee/")
def view_all_coffees():
    coffees = Coffee.query.order_by(Coffee.id.desc()).all()
    return render_template("viewallcoffees.html", coffees=coffees, current_user=current_user)


@app.route("/cafe/")
def view_all_cafes():
    cafes = Cafe.query.order_by(Cafe.name).all()
    return render_template("viewallcafes.html", cafes=cafes, current_user=current_user)


@app.route("/price/")
def view_all_prices():
    prices = Price.query.order_by(Price.cafeid, Price.amount).all()
    return render_template("viewallprices.html", prices=prices, current_user=current_user)


@app.route("/activity/", methods=["GET"])
def view_activity():
    events = Event.query.order_by(Event.time.desc()).all()
    return render_template("viewallactivity.html", events=events, current_user=current_user)


@app.route("/run/<int:runid>/")
@login_required
def view_run(runid):
    run = Run.query.filter_by(id=runid).first_or_404()
    return render_template("viewrun.html", run=run, current_user=current_user)

@app.route("/order/<int:runid>/")
@login_required
def view_order(runid):
    run = Run.query.filter_by(id=runid).first_or_404()
    return render_template("orderrun.html", run=run, current_user=current_user)


@app.route("/run/<int:runid>/edit/", methods=["GET", "POST"])
@login_required
def edit_run(runid):
    logger = logging.getLogger('views.edit_run')
    run = Run.query.filter_by(id=runid).first_or_404()
    form = RunForm(request.form, obj=run)
    users = User.query.all()
    form.person.choices = [(user.id, user.name) for user in users]
    cafes = Cafe.query.all()
    form.cafeid.choices = [(cafe.id, cafe.name) for cafe in cafes]

    if request.method == "GET":
        return render_template("runform.html", form=form, formtype="Edit", current_user=current_user)

    if request.method == "POST" and form.validate_on_submit():
        person = User.query.filter_by(id=form.data["person"]).first()

        run.person = person.id
        run.fetcher = person
        run.cafeid = form.data["cafeid"]
        run.pickup = form.data["pickup"]
        run.time = form.data["time"]
        run.is_open = form.data["is_open"]

        db.session.commit()
        write_to_events("updated", "run", run.id)
        db.session.commit()
        flash("Run edited", "success")
        return redirect(url_for("view_run", runid=run.id))
    else:
        for field, errors in form.errors.items():
            flash("Error in %s: %s" % (field, "; ".join(errors)), "danger")
        return render_template("runform.html", form=form, formtype="Edit", current_user=current_user)


@app.route("/run/<int:runid>/close/")
@login_required
def next_status_for_run(runid):
    run = Run.query.filter_by(id=runid).first_or_404()
    run.is_open = False
    # Create Money exchanges to pay for the purchased coffees.
    db.session.add(run)
    db.session.commit()
    events.run_closed(runid)
    write_to_events("updated", "run", run.id)
    flash("Run closed", "success")
    return redirect(url_for("view_run", runid=run.id))


@app.route("/run/<int:runid>/ping/")
@login_required
def ping_addicts_for_run(runid):
    run = Run.query.filter_by(id=runid).first_or_404()
    # Create Money exchanges to pay for the purchased coffees.
    events.run_delivered(runid)
    flash("The coffee addicts in this run have been notified.", "success")
    return redirect(url_for("view_run", runid=run.id))


@app.route("/coffee/<int:coffeeid>/")
@login_required
def view_coffee(coffeeid):
    logger = logging.getLogger('views.view_coffee')
    coffee = Coffee.query.filter(Coffee.id==coffeeid).first_or_404()
    logging.info('Coffee: %s, %s',  coffee, coffee.price)
    return render_template("viewcoffee.html", coffee=coffee, current_user=current_user)


@app.route("/coffee/<int:coffeeid>/edit/", methods=["GET", "POST"])
@login_required
def edit_coffee(coffeeid):
    coffee = Coffee.query.filter(Coffee.id==coffeeid).first_or_404()
    form = CoffeeForm(request.form, obj=coffee)
    runs = Run.query.filter_by(is_open=True).all()
    form.runid.choices = [(r.id, r.prettyprint()) for r in runs]

    # Make sure it is possible to edit coffees in a run that has already been
    # closed. We do this by adding the existing coffee run to the dropdown.
    if coffee.run and coffee.run.id not in [r.id for r in runs]:
        form.runid.choices.append((coffee.run.id, coffee.run.prettyprint()))

    c = coffeespecs.Coffee.fromJSON(coffee.coffee)
    users = User.query.all()
    form.person.choices = [(user.id, user.name) for user in users]

    if request.method == "GET":
        form.coffee.data = str(c)
        form.runid.data = coffee.runid
        return render_template("coffeeform.html", form=form, formtype="Edit", price=coffee.price, current_user=current_user)

    if request.method == "POST" and form.validate_on_submit():
        coffee.coffee = coffeespecs.Coffee(form.data["coffee"]).toJSON()
        coffee.price = form.data["price"]
        coffee.modified = sydney_timezone_now()
        db.session.commit()
        write_to_events("updated", "coffee", coffee.id)
        flash("Coffee edited", "success")
        return redirect(url_for("view_coffee", coffeeid=coffee.id))
    else:
        for field, errors in form.errors.items():
            flash("Error in %s: %s" % (field, "; ".join(errors)), "danger")
        return render_template("coffeeform.html", form=form, formtype="Edit", current_user=current_user)


@app.route("/coffee/<int:coffeeid>/pay/", methods=["GET"])
@login_required
def pay_for_coffee(coffeeid):
    coffee = Coffee.query.filter(Coffee.id == coffeeid).first_or_404()
    coffee.paid = True
    db.session.commit()
    write_to_events("updated", "coffee", coffee.id)
    flash("Coffee edited", "success")
    return redirect(url_for("view_coffee", coffeeid=coffee.id))


@app.route("/coffee/<int:coffeeid>/unpay/", methods=["GET"])
@login_required
def unpay_for_coffee(coffeeid):
    coffee = Coffee.query.filter(Coffee.id == coffeeid).first_or_404()
    coffee.paid = False
    db.session.commit()
    write_to_events("updated", "coffee", coffee.id)
    flash("Coffee edited", "success")
    return redirect(url_for("view_coffee", coffeeid=coffee.id))


@app.route("/user/", methods=["GET"])
def get_all_users():
    people = User.query.all()
    return render_template("viewallusers.html", people=people, current_user=current_user)


@app.route("/user/<int:userid>/", methods=["GET"])
@login_required
def view_user(userid):
    user = User.query.filter(User.id==userid).first_or_404()
    return render_template("viewuser.html", user=user, current_user=current_user)


@app.route("/user/<int:userid>/debts/", methods=["GET", "POST"])
@login_required
def view_debts(userid):
    if userid != current_user.id:
        flash("You can only view your own debts!", "danger")
        return redirect(url_for("view_user", userid=userid))
    owes = []
    owedtotal = 0.0
    isowed = []
    isowedtotal = 0.0
    owes = Coffee.query.filter(Coffee.person==userid).filter_by(paid=False).outerjoin(Run, Coffee.runid==Run.id).filter(Run.person!=userid).all()
    isowed = Coffee.query.outerjoin(Run, Coffee.runid==Run.id).filter(Run.person==userid).filter(Coffee.person!=userid).filter(Coffee.paid==False).all()
    return render_template("viewdebts.html", user=current_user, owes=owes, isowed=isowed, current_user=current_user)


@app.route("/cafe/<int:cafeid>/", methods=["GET"])
def view_cafe(cafeid):
    cafe = Cafe.query.filter(Cafe.id==cafeid).first_or_404()
    return render_template("viewcafe.html", cafe=cafe, current_user=current_user)


@app.route("/cafe/<int:cafeid>/edit/", methods=["GET", "POST"])
def edit_cafe(cafeid):
    cafe = Cafe.query.filter(Cafe.id==cafeid).first_or_404()
    form = CafeForm(request.form, obj=cafe)

    if request.method == "GET":
        return render_template("cafeform.html", form=form, formtype="Edit", current_user=current_user)

    if request.method == "POST" and form.validate_on_submit():
        form.populate_obj(cafe)
        db.session.commit()
        write_to_events("updated", "cafe", cafe.id)
        flash("Cafe edited", "success")
        return redirect(url_for("view_cafe", cafeid=cafeid))
    else:
        for field, errors in form.errors.items():
            flash("Error in %s: %s" % (field, "; ".join(errors)), "danger")
    return render_template("cafeform.html", form=form, formtype="Edit", current_user=current_user)


@app.route("/run/add/", methods=["GET", "POST"])
@app.route("/cafe/<int:cafeid>/run/add/", methods=["GET", "POST"])
@login_required
def add_run(cafeid=None):
    form = RunForm(request.form)
    users = User.query.all()
    form.person.choices = [(user.id, user.name) for user in users]
    cafes = Cafe.query.all()
    if not cafes:
        flash("There are no cafes currently configured. Please add one before creating a run", "warning")
        return redirect(url_for("home"))
    form.cafeid.choices = [(cafe.id, cafe.name) for cafe in cafes]

    if request.method == "GET":
        if cafeid:
            form.cafeid.data = cafeid
        form.person.data = current_user.id

        # Generate a time for the run. The algorithm here is we want the
        # default run time to be at least 15 minutes in the future, and also a
        # multiple of 15 minutes (since it look nicer).
        # This means that by default, the run will be between 15 and 30 minutes
        # from the current time.
        t = sydney_timezone_now().replace(second=0, microsecond=0)
        t += datetime.timedelta(minutes=15)
        t += datetime.timedelta(minutes=15 - (t.minute % 15))  # truncate up to the nearest 15 minutes
        form.time.data = t

        return render_template("runform.html", form=form, formtype="Add", current_user=current_user)

    if form.validate_on_submit():
        # Add run
        run = Run(form.data["time"])
        person = User.query.filter_by(id=form.data["person"]).first()
        run.person = person.id
        run.fetcher = person
        run.cafeid = form.data["cafeid"]
        run.pickup = form.data["pickup"]
        run.modified = sydney_timezone_now()

        db.session.add(run)
        db.session.commit()
        events.run_created(run.id)
        write_to_events("created", "run", run.id)
        if form.data["addpending"]:
            coffees = get_coffees_for_time(sydney_timezone_now())
            for coffee in coffees:
                coffee.runid = run.id
                db.session.add(coffee)
            db.session.commit()
        flash("Run added", "success")
        return redirect(url_for("view_run", runid=run.id))
    else:
        for field, errors in form.errors.items():
            flash("Error in %s: %s" % (field, "; ".join(errors)), "danger")
        return render_template("runform.html", form=form, formtype="Add", current_user=current_user)


@app.route("/run/<int:runid>/delete/", methods=["GET"])
@login_required
def delete_run(runid):
    run = Run.query.filter_by(id=runid).first_or_404()
    db.session.delete(run)
    db.session.commit()
    write_to_events("deleted", "run", run.id)
    flash("Run %d deleted" % runid, "success")
    return redirect(url_for("view_all_runs"))


@app.route("/run/<int:runid>/addcoffee/", methods=["GET", "POST"])
@app.route("/coffee/add/", methods=["GET", "POST"])
@login_required
def add_coffee(runid=None):
    logger = logging.getLogger('views.add_coffee')
    runs = Run.query.filter(Run.time >= sydney_timezone_now()).filter_by(is_open=True).all()
    form = CoffeeForm(request.form)
    form.runid.choices = [(-1, '')] + [(r.id, r.prettyprint()) for r in runs]
    if runid:
        run = Run.query.filter_by(id=runid).first()
        localmodified = run.time.replace(tzinfo=pytz.timezone("Australia/Sydney"))
        if sydney_timezone_now() > localmodified:
            flash("You can't add coffees to this run", "danger")
            return redirect(url_for("view_run", runid=runid))
        form.runid.data = runid
    users = User.query.all()
    form.person.choices = [(user.id, user.name) for user in users]

    if request.method == "GET":
        form.person.data = current_user.id
        form.starttime.data = sydney_timezone_now()
        form.endtime.data = sydney_timezone_now()
        return render_template("coffeeform.html", form=form, formtype="Add", current_user=current_user)

    if form.validate_on_submit():
        logger.info('Form: %s', form.data)
        coffee = Coffee(form.data["coffee"], form.data['price'], form.data['runid'])
        person = User.query.filter_by(id=form.data["person"]).first()
        coffee.personid = person.id
        coffee.addict = person
        if form.data["runid"] == -1:
            coffee.starttime = form.data["starttime"]
            coffee.endtime = form.data["endtime"]
        else:
            coffee.runid = form.data["runid"]
            run = Run.query.filter_by(id=form.data["runid"]).first()
        coffee.modified = sydney_timezone_now()
        db.session.add(coffee)
        db.session.commit()
        write_to_events("created", "coffee", coffee.id)
        if form.data["runid"] != -1:
            events.coffee_added(coffee.runid, coffee.id)
        flash("Coffee order added", "success")
        if form.data["recurring"]:
            recur_coffee(coffee, form.data["days"])
        return redirect(url_for("view_coffee", coffeeid=coffee.id))
    else:
        for field, errors in form.errors.items():
            flash("Error in %s: %s" % (field, "; ".join(errors)), "danger")
        return render_template("coffeeform.html", form=form, current_user=current_user)


@app.route("/_prices_for_run/")
def prices_for_run():
    logger = logging.getLogger('views.prices_for_run')
    runid = request.args.get("runid", 0, type=int)
    run = Run.query.filter_by(id=runid).first()
    prices = run.cafe.pricelist
    logger.info('Prices for cafe: %s', prices)
    jprices = {p.price_key: p.amount for p in prices}
    return jsonify(**jprices)


@app.route("/cafe/add/", methods=["GET", "POST"])
def add_cafe():
    form = CafeForm(request.form)
    if request.method == "GET":
        return render_template("cafeform.html", form=form, formtype="Add", current_user=current_user)
    if request.method == "POST" and form.validate_on_submit():
        # Add cafe
        cafe = Cafe()
        cafe.name = form.data["name"]
        cafe.location = form.data["location"]
        db.session.add(cafe)
        db.session.commit()
        write_to_events("created", "cafe", cafe.id)
        flash("Cafe added", "success")
        return redirect(url_for("view_cafe", cafeid=cafe.id))
    else:
        for field, errors in form.errors.items():
            flash("Error in %s: %s" % (field, "; ".join(errors)), "danger")
        return render_template("cafeform.html", form=form, formtype="Add", current_user=current_user)
    return redirect(url_for("home"))


@app.route("/price/add/", methods=["GET", "POST"])
@app.route("/cafe/<int:cafeid>/price/add/", methods=["GET", "POST"])
def add_cafe_price(cafeid=None):
    form = PriceForm()
    if cafeid:
        cafe = Cafe.query.filter_by(id=cafeid).first_or_404()
        form.cafeid.choices = [(cafe.id, cafe.name)]
        form.cafeid.data = cafe.id
    else:
        cafes = Cafe.query.all()
        if not cafes:
            flash("There are no existing cafes. Would you like to make one instead?", "warning")
            return redirect(url_for("home"))
        form.cafeid.choices = [(c.id, c.name) for c in cafes]
        cafe = cafes[0]

    if request.method == "GET":
        return render_template("priceform.html", cafe=cafe, form=form, formtype="Add", current_user=current_user)

    if request.method == "POST" and form.validate_on_submit():
        cafeid = form.data["cafeid"]
        cafe = Cafe.query.filter_by(id=cafeid).first_or_404()
        coffee = coffeespecs.Coffee(form.data["price_key"])
        price = Price(cafe.id, coffee)
        if cafeid:
            price.cafeid = cafeid
        else:
            price.cafeid = form.data["cafeid"]
        price.amount = form.data["amount"]
        db.session.add(price)
        db.session.commit()
        flash("Price added to cafe '%s'" % cafe.name, "success")
        return redirect(url_for("view_cafe", cafeid=cafeid))
    else:
        for field, errors in form.errors.items():
            flash("Error in %s: %s" % (field, "; ".join(errors)), "danger")
    return render_template("priceform.html", cafe=cafe, form=form, formtype="Add", current_user=current_user)


@app.route("/price/<int:priceid>/", methods=["GET"])
def view_price(priceid):
    price = Price.query.filter_by(id=priceid).first_or_404()
    return render_template("viewprice.html", price=price, current_user=current_user)


@app.route("/price/<int:priceid>/edit/", methods=["GET", "POST"])
def edit_price(priceid):
    price = Price.query.filter_by(id=priceid).first_or_404()
    form = PriceForm(obj=price)
    form.cafeid.choices = [(price.cafe.id, price.cafe.name)]
    form.cafeid.data = price.cafe.id

    if request.method == "GET":
        return render_template("priceform.html", cafe=price.cafe, form=form, formtype="Edit", current_user=current_user)

    if request.method == "POST" and form.validate_on_submit():
        form.populate_obj(price)
        coffee = coffeespecs.Coffee(form.data["price_key"])
        price.price_key = coffee.get_price_key()
        db.session.commit()
        write_to_events("updated", "price", price.id)
        flash("Price updated for cafe '%s'" % price.cafe.name, "success")
        return redirect(url_for("view_cafe", cafeid=price.cafe.id))
    else:
        for field, errors in form.errors.items():
            flash("Error in %s: %s" % (field, "; ".join(errors)), "danger")
    return render_template("priceform.html", cafe=price.cafe, form=form, formtype="Add", current_user=current_user)


@app.route("/price/<int:priceid>/delete/", methods=["GET"])
def delete_price(priceid):
    price = Price.query.filter_by(id=priceid).first_or_404()
    db.session.delete(price)
    db.session.commit()
    write_to_events("deleted", "price", price.id)
    flash("Price %d deleted" % priceid, "success")
    return redirect(url_for("view_all_cafes"))


@app.route("/coffee/<int:coffeeid>/delete/", methods=["GET"])
def delete_coffee(coffeeid):
    coffee = Coffee.query.filter_by(id=coffeeid).first_or_404()
    db.session.delete(coffee)
    db.session.commit()
    write_to_events("deleted", "coffee", coffee.id)
    flash("Coffee %d deleted" % coffeeid, "success")
    return redirect(url_for("view_all_coffees"))


@app.route("/cafe/<int:cafeid>/delete/", methods=["GET"])
def delete_cafe(cafeid):
    cafe = Cafe.query.filter_by(id=cafeid).first_or_404()
    db.session.delete(cafe)
    db.session.commit()
    write_to_events("deleted", "cafe", cafe.id)
    flash("Cafe %d deleted" % cafeid, "success")
    return redirect(url_for("view_all_cafes"))


def next_run():
    run = Run.query.filter_by(is_open=True).order_by(Run.time).first()
    return run


def get_person(name):
    person = User.query.filter(User.name.like(name)).first()
    if not person:
        person = User(name)
        db.session.add(person)
        db.session.commit()
        write_to_events("created", "user", person.id, person)
    return person


def recur_coffee(coffee, days):
    for i in range(days):
        newcoffee = Coffee(coffee.pretty_print())
        newcoffee.addict = coffee.addict
        newcoffee.person = coffee.person
        newcoffee.price = coffee.price
        starttime = coffee.starttime
        starttime += datetime.timedelta(days=i+1)
        newcoffee.starttime = starttime
        endtime = coffee.endtime
        endtime += datetime.timedelta(days=i+1)
        newcoffee.endtime = endtime
        db.session.add(newcoffee)
        db.session.commit()
        write_to_events("created", "coffee", newcoffee.id)


def get_coffees_for_time(time):
    coffees = Coffee.query.filter(Coffee.endtime >= time) \
        .filter(Coffee.starttime <= time).filter(Coffee.expired==False).all()
    return coffees


def write_to_events(action, objtype, objid, user=None):
    if user:
        event = Event(user.id, action, objtype, objid)
    else:
        event = Event(current_user.id, action, objtype, objid)
    event.time = sydney_timezone_now()
    db.session.add(event)
    db.session.commit()
    return event.id


## Error handlers
# Handle 404 errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# Handle 500 errors
@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500
