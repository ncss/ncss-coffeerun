

from flask import render_template, flash, redirect, session, url_for, request, jsonify
from flask.ext.login import login_required, login_user, current_user, logout_user
from flask.ext.mail import Message
import pytz
import datetime
from application import app, db, lm
from tasks import send_email
from models import User, Run, Coffee, RunStatus, Cafe, Price, Event, RegistrationID, sydney_timezone_now
from forms import LoginForm, CoffeeForm, RunForm, UserForm, CafeForm, PriceForm

@lm.user_loader
def load_user(userid):
    return User.query.get(int(userid))

@app.route("/")
@login_required
def home():
    run = next_run()
    events = Event.query.order_by(Event.time.desc())[:4]
    return render_template("index.html", run=run, events=events, current_user=current_user)

@app.route("/login/", methods=["GET","POST"])
def login():
    loginform = LoginForm()
    registerform = UserForm()
    users = db.session.query(User).all()
    loginform.users.choices = [(u.id, u.name) for u in users]
    if loginform.validate_on_submit():
        if loginform.newuser.data:
            user = User(loginform.newuser.data)
            db.session.add(user)
            db.session.commit()
            write_to_events("created", "user", user.id, user)
        else:
            user = db.session.query(User).filter_by(id=loginform.users.data).first()
        if login_user(user):
            flash("You are now logged in.", "success")
            return redirect(request.args.get("next") or url_for("home"))
        else:
            flash("Login unsuccessful.", "danger")
            return render_template("login.html", loginform=loginform, registerform=registerform)
    return render_template("login.html", loginform=loginform, registerform=registerform)

@app.route("/register/", methods=["POST"])
def register():
    registerform = UserForm()
    if registerform.validate_on_submit():
        user = User()
        user.name = registerform.data["name"]
        user.email = registerform.data["email"]
        user.group = registerform.data["group"]
        user.tutor = registerform.data["tutor"]
        user.teacher = registerform.data["teacher"]
        db.session.add(user)
        db.session.commit()
        write_to_events("created", "user", user.id, user)
        login_user(user)
        flash("You are now logged in.", "success")
    else:
        flash("Register unsuccessful.", "danger")
        for field, errors in registerform.errors.items():
            flash("Error in %s: %s" % (field, "; ".join(errors)), "danger")
        loginform = LoginForm()
        users = db.session.query(User).all()
        loginform.users.choices = [(u.id, u.name) for u in users]
        return render_template("login.html", loginform=loginform, registerform=registerform)
    return redirect(url_for("home"))

@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/about/")
def about():
    return render_template("about/main.html")

@app.route("/about/history/")
def about_history():
    return render_template("about/history.html")

@app.route("/about/faqs/")
def about_faqs():
    return render_template("about/faqs.html")

@app.route("/run/")
def view_all_runs(): 
    runs = Run.query.order_by(Run.id.desc()).all()
    return render_template("viewallruns.html", runs=runs)

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
    run = Run.query.filter(Run.id==runid).first_or_404()
    nextstatusid = run.statusid + 1
    nextstatus = RunStatus.query.filter(RunStatus.id==nextstatusid).first()
    return render_template("viewrun.html", run=run, current_user=current_user, nextstatus=nextstatus)

@app.route("/run/<int:runid>/edit/", methods=["GET", "POST"])
@login_required
def edit_run(runid):
    run = Run.query.filter_by(id=runid).first_or_404()
    form = RunForm(request.form, obj=run)
    statuses = RunStatus.query.all()
    form.statusid.choices = [(s.id, s.description) for s in statuses]
    users = User.query.all()
    form.person.choices = [(user.id, user.name) for user in users]
    cafes = Cafe.query.all()
    form.cafeid.choices = [(cafe.id, cafe.name) for cafe in cafes]
    if request.method == "GET":
        print run.time.strftime('%Y-%m-%d %H:%M:%S %Z%z')
        return render_template("runform.html", form=form, formtype="Edit", current_user=current_user)
    if request.method == "POST" and form.validate_on_submit():
        print form.data
        oldstatus = run.status.description
        person = User.query.filter_by(id=form.data["person"]).first()
        run.person = person.id
        run.fetcher = person
        run.cafeid = form.data["cafeid"]
        run.pickup = form.data["pickup"]
        run.statusid = form.data["statusid"]
        
        #localtz = pytz.timezone("Australia/Sydney")
        newstatus = RunStatus.query.filter_by(id=form.data["statusid"]).first().description
        #run.modified = sydney_timezone_now()
        db.session.commit()
        write_to_events("updated", "run", run.id)
        db.session.commit()
        flash("Run edited", "success")
        if oldstatus != newstatus and newstatus == "Pickup":
            call_to_pickup(run)
        return redirect(url_for("view_run", runid=run.id))
    else:
        for field, errors in form.errors.items():
            flash("Error in %s: %s" % (field, "; ".join(errors)), "danger")
        return render_template("runform.html", form=form, formtype="Edit", current_user=current_user)

@app.route("/run/<int:runid>/nextstatus/")
@login_required
def next_status_for_run(runid):
    run = Run.query.filter_by(id=runid).first_or_404()
    if run.status.description != "closed":
        nextstatus = RunStatus.query.filter_by(id=run.statusid+1).first()
        run.status = nextstatus
        run.modified = sydney_timezone_now()
        db.session.commit()
        write_to_events("updated", "run", run.id)
        flash("Run edited", "success")
    else:
        flash("There is no next status for this run", "danger")
    return redirect(url_for("view_run", runid=run.id))
    
@app.route("/coffee/<int:coffeeid>/")
@login_required
def view_coffee(coffeeid):
    coffee = Coffee.query.filter(Coffee.id==coffeeid).first_or_404()
    print coffee, coffee.price
    return render_template("viewcoffee.html", coffee=coffee, current_user=current_user)

@app.route("/coffee/<int:coffeeid>/edit/", methods=["GET", "POST"])
@login_required
def edit_coffee(coffeeid):
    coffee = Coffee.query.filter(Coffee.id==coffeeid).first_or_404()
    form = CoffeeForm(request.form, obj=coffee)
    runs = Run.query.filter(Run.time >= sydney_timezone_now()).all()
    form.runid.choices = [(r.id, r.time) for r in runs]
    form.runid.data = coffee.runid
    users = User.query.all()
    form.person.choices = [(user.id, user.name) for user in users]
    if request.method == "GET":
        return render_template("coffeeform.html", form=form, formtype="Edit", price=coffee.price, current_user=current_user)
    if request.method == "POST" and form.validate_on_submit():
        form.populate_obj(coffee)
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
    coffee = Coffee.query.filter(Coffee.id==coffeeid).first_or_404()
    coffee.paid = True
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

@app.route("/user/<int:userid>/edit/", methods=["GET", "POST"])
@login_required
def edit_user(userid):
    if userid != current_user.id:
        flash("You cannot edit a different user!", "danger")
        return redirect(url_for("view_user", userid=userid))
    form = UserForm(request.form, obj=current_user)
    if request.method == "GET":
        return render_template("userform.html", form=form, current_user=current_user)
    if request.method == "POST" and form.validate_on_submit():
        form.populate_obj(current_user)
        db.session.commit()
        write_to_events("updated", "user", current_user.id)
        flash("User edited", "success")
        return redirect(url_for("view_user", userid=userid))
    else:
        for field, errors in form.errors.items():
            flash("Error in %s: %s" % (field, "; ".join(errors)), "danger")
        return redirect(url_for("view_user", userid=userid))

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
    statuses = RunStatus.query.all()
    form.statusid.choices = [(s.id, s.description) for s in statuses]
    cafes = Cafe.query.all()
    if not cafes:
        flash("There are no cafes currently configured. Please add one before creating a run", "warning")
        return redirect(url_for("home"))
    form.cafeid.choices = [(cafe.id, cafe.name) for cafe in cafes]
    if request.method == "GET":
        if cafeid:
            form.cafe.data = cafeid
        form.person.data = current_user.id
        form.time.data = sydney_timezone_now()
        form.deadline.data = sydney_timezone_now()
        return render_template("runform.html", form=form, formtype="Add", current_user=current_user)
    if form.validate_on_submit():
        # Add run
        run = Run(form.data["time"])
        person = User.query.filter_by(id=form.data["person"]).first()
        run.person = person.id
        run.fetcher = person
        run.deadline = form.data["deadline"]
        run.cafeid = form.data["cafeid"]
        run.pickup = form.data["pickup"]
        run.statusid = form.data["statusid"]
        run.modified = sydney_timezone_now()
        db.session.add(run)
        db.session.commit()
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
    runs = Run.query.filter(Run.deadline >= sydney_timezone_now()).filter(Run.statusid==1).all()
    # if not runs:
    #     flash("There are no upcoming coffee runs. Would you like to make one instead?", "warning")
    #     return redirect(url_for("home"))
    lastcoffee = Coffee.query.filter(Coffee.addict==current_user).order_by(Coffee.id.desc()).first()
    form = CoffeeForm(request.form)
    form.runid.choices = [(-1, '')] + [(r.id, r.time) for r in runs]
    if runid:
        run = Run.query.filter_by(id=runid).first()
        localmodified = run.deadline.replace(tzinfo=pytz.timezone("Australia/Sydney"))
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
        if lastcoffee:
            form.coffeetype.data = lastcoffee.coffeetype
            form.size.data = lastcoffee.size
            form.sugar.data = lastcoffee.sugar
        return render_template("coffeeform.html", form=form, formtype="Add", current_user=current_user)
    if form.validate_on_submit():
        print form.data
        coffee = Coffee(form.data["coffeetype"])
        coffee.size = form.data["size"]
        coffee.sugar = form.data["sugar"]
        person = User.query.filter_by(id=form.data["person"]).first()
        coffee.personid = person.id
        coffee.addict = person
        coffee.price = form.data["price"]
        if form.data["runid"] == -1:
            coffee.startTime = form.data["starttime"]
            coffee.endTime = form.data["endtime"]
        else:
            coffee.runid = form.data["runid"]
            run = Run.query.filter_by(id=form.data["runid"]).first()
        coffee.modified = sydney_timezone_now()
        db.session.add(coffee)
        db.session.commit()
        write_to_events("created", "coffee", coffee.id)
        if form.data["runid"] != -1:
            notify_run_owner_of_coffee(run.fetcher, person, coffee)
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
    runid = request.args.get("runid", 0, type=int)
    run = Run.query.filter_by(id=runid).first()
    prices = run.cafe.pricelist
    print prices
    jprices = {p.size: p.amount for p in prices}
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
        form.cafeid.choices = [(cafe.id, cafe.name) for cafe in cafes]
    if request.method == "GET":
        return render_template("priceform.html", cafe=cafe, form=form, formtype="Add", current_user=current_user)
    if request.method == "POST" and form.validate_on_submit():
        cafeid = form.data["cafeid"]
        if Price.query.filter_by(cafeid=cafeid).filter_by(size=form.data["size"]).first():
            flash("There is already a price for this size", "danger")
            return redirect(url_for("add_cafe_price", cafeid=cafeid))
        price = Price(cafe.id)
        if cafeid:
            price.cafeid = cafeid
        else:
            price.cafeid = form.data["cafeid"]
        price.size = form.data["size"]
        price.amount = form.data["amount"]
        db.session.add(price)
        db.session.commit()
        write_to_events("created", "price", price.id)
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
    coffees = Coffee.query.filter_by(priceid=priceid).all()
    for coffee in coffees:
        coffee.price = None
        write_to_events("updated", "coffee", coffee.id)
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
    run = Run.query.filter(Run.statusid < 4).order_by(Run.time).first()
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
        newcoffee = Coffee(coffee.coffeetype)
        newcoffee.addict = coffee.addict
        newcoffee.size = coffee.size
        newcoffee.sugar = coffee.sugar
        newcoffee.person = coffee.person
        newcoffee.addict = coffee.addict
        newcoffee.price = coffee.price
        starttime = coffee.startTime.replace(tzinfo=pytz.timezone("Australia/Sydney"))
        starttime += datetime.timedelta(days=i+1)
        newcoffee.startTime = starttime
        endtime = coffee.endTime
        endtime += datetime.timedelta(days=i+1)
        newcoffee.endTime = endtime
        db.session.add(newcoffee)
        db.session.commit()
        write_to_events("created", "coffee", newcoffee.id)

def get_coffees_for_time(time):
    coffees = Coffee.query.filter(Coffee.endTime >= time) \
        .filter(Coffee.startTime <= time).filter(Coffee.expired==False).all()
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

# Mail helpers

def notify_run_owner_of_coffee(owner, addict, coffee):
    if owner.alerts:
        recipients = [owner.email]
        run = coffee.run
        subject = "Alert: coffee added for run to %s at %s" % (run.cafe.name, run.readtime())
        body = "%s has requested a coffee for run %d. See the NCSS Coffeerun site for details." % (addict.name, run.id)
        msg = Message(subject, recipients)
        send_email(msg)

def call_to_pickup(run):
    recipients = [c.addict.email for c in run.coffees if c.addict.alerts]
    subject = "Alert: your coffee is ready to pickup!"
    body = "%s has taken your coffee to %s. Please go fetch and pay.\nRegards, your favourite Coffee Bot!" % (run.fetcher.name, run.pickup)
    msg = Message(subject=subject, body=body, recipients=recipients)
    send_email(msg)

## Error handlers
# Handle 404 errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Handle 500 errors
@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

