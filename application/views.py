

from flask import render_template, flash, redirect, session, url_for, request, g, json, jsonify
from flask.ext.login import login_required, login_user, current_user, logout_user
import requests
import json
from datetime import datetime
import pytz
from application import app, db, lm
from models import User, Run, Coffee, Status, Cafe, Price, PriceModifier, RegistrationID, sydney_timezone_now
from forms import LoginForm, CoffeeForm, RunForm, UserForm, CafeForm, PriceForm

@lm.user_loader
def load_user(userid):
    return User.query.get(int(userid))

@app.route("/")
@login_required
def home():
    run = next_run()
    return render_template("index.html", run=run, current_user=current_user)

@app.route("/login/", methods=["GET","POST"])
def login():
    form = LoginForm()
    users = db.session.query(User).all()
    form.users.choices = [(u.id, u.name) for u in users]
    if form.validate_on_submit():
        if form.newuser.data:
            user = User(form.newuser.data)
            db.session.add(user)
            db.session.commit()
        else:
            user = db.session.query(User).filter_by(id=form.users.data).first()
        if login_user(user):
            flash("You are now logged in.", "success")
            return redirect(request.args.get("next") or url_for("home"))
        else:
            flash("Login unsuccessful.", "danger")
            return render_template("login.html", form=form)
    return render_template("login.html", form=form)

@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/about/")
def about():
    return render_template("about.html")

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

@app.route("/run/<int:runid>/")
@login_required
def view_run(runid):
    run = Run.query.filter(Run.id==runid).first_or_404()
    return render_template("viewrun.html", run=run, current_user=current_user)

@app.route("/run/<int:runid>/edit/", methods=["GET", "POST"])
@login_required
def edit_run(runid):
    run = Run.query.filter_by(id=runid).first_or_404()
    form = RunForm(request.form, obj=run)
    statuses = Status.query.all()
    form.status.choices = [(s.id, s.description) for s in statuses]
    users = User.query.all()
    form.person.choices = [(user.id, user.name) for user in users]
    if request.method == "GET":
        return render_template("runform.html", form=form, formtype="Edit", current_user=current_user)
    if request.method == "POST" and form.validate_on_submit():
        #print form.data
        form.populate_obj(run)
        run.modified = sydney_timezone_now()
        #print run.modified, datetime.utcnow()
        #run.modified = datetime.utcnow()
        db.session.commit()
        flash("Run edited", "success")
        return redirect(url_for("view_run", runid=run.id))
    else:
        flash(form.errors, "danger")
        return render_template("runform.html", form=form, formtype="Edit", current_user=current_user)


@app.route("/coffee/<int:coffeeid>/")
@login_required
def view_coffee(coffeeid):
    coffee = Coffee.query.filter(Coffee.id==coffeeid).first_or_404()
    return render_template("viewcoffee.html", coffee=coffee, current_user=current_user)

@app.route("/coffee/<int:coffeeid>/edit/", methods=["GET", "POST"])
@login_required
def edit_coffee(coffeeid):
    coffee = Coffee.query.filter(Coffee.id==coffeeid).first_or_404()
    form = CoffeeForm(request.form, obj=coffee)
    runs = Run.query.filter(Run.time >= sydney_timezone_now()).all()
    form.run.choices = [(r.id, r.time) for r in runs]
    form.run.data = coffee.run
    users = User.query.all()
    form.person.choices = [(user.id, user.name) for user in users]
    if request.method == "GET":
        return render_template("coffeeform.html", form=form, formtype="Edit", current_user=current_user)
    if request.method == "POST" and form.validate_on_submit():
        form.populate_obj(coffee)
        #coffee.modified=sydney_timezone_now()
        coffee.modified = datetime.utcnow()
        db.session.commit()
        flash("Coffee edited", "success")
        return redirect(url_for("view_coffee", coffeeid=coffee.id))
    else:
        flash(form.errors, "danger")
        return render_template("coffeeform.html", form=form, formtype="Edit", current_user=current_user)

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
        flash("User edited", "success")
        return redirect(url_for("view_user", userid=userid))
    else:
        flash("User edit failed", "danger")
        return redirect(url_for("view_user", userid=userid))

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
    return redirect(url_for("home"))

@app.route("/run/add/", methods=["GET", "POST"])
@login_required
def add_run():
    form = RunForm(request.form)
    users = User.query.all()
    form.person.choices = [(user.id, user.name) for user in users]
    #form.person.data = current_user.name
    form.person.data = current_user.id
    statuses = Status.query.all()
    form.status.choices = [(s.id, s.description) for s in statuses]
    cafes = Cafe.query.all()
    form.cafe.choices = [(cafe.id, cafe.name) for cafe in cafes]
    if request.method == "GET":
        form.time.data = sydney_timezone_now()#.strftime("%Y/%m/%d %H:%M:%S")
        form.deadline.data = sydney_timezone_now()
        return render_template("runform.html", form=form, formtype="Add", current_user=current_user)
    if form.validate_on_submit():
        # Add run
        print form.data
        run = Run(form.data["time"])
        run.person = current_user.id
        run.fetcher = current_user
        #print run
        run.deadline = form.data["deadline"]
        run.cafe = form.data["cafe"]
        run.pickup = form.data["pickup"]
        run.status = form.data["status"]
        run.statusobj = Status.query.filter_by(id=form.data["status"]).first()
        #run.modified = sydney_timezone_now(datetime.utcnow())
        run.modified = datetime.utcnow()
        db.session.add(run)
        db.session.commit()
        flash("Run added", "success")
        notify_newrun(run)
        return redirect(url_for("view_run", runid=run.id))
    else:
        flash("It broke...", "danger")
        print form.errors
        print form.data
        return render_template("runform.html", form=form, formtype="Add", current_user=current_user)

@app.route("/run/<int:runid>/delete/", methods=["GET"])
@login_required
def delete_run(runid):
    run = Run.query.filter_by(id=runid).first_or_404()
    db.session.delete(run)
    db.session.commit()
    flash("Run %d deleted" % runid, "success")
    return redirect(url_for("view_all_runs"))

@app.route("/run/<int:runid>/addcoffee/", methods=["GET", "POST"])
@app.route("/coffee/add/", methods=["GET", "POST"])
@login_required
def add_coffee(runid=None):
    runs = Run.query.filter(Run.deadline >= sydney_timezone_now()).filter(Run.statusid==1).all()
    if not runs:
        flash("There are no upcoming coffee runs. Would you like to make one instead?", "warning")
        return redirect(url_for("home"))
    lastcoffee = Coffee.query.filter(Coffee.addict==current_user).order_by(Coffee.id.desc()).first()
    form = CoffeeForm(request.form)
    form.run.choices = [(r.id, r.time) for r in runs]
    if runid:
        run = Run.query.filter_by(id=runid).first()
        #print datetime.now(), run.deadline
        localmodified = run.deadline.replace(tzinfo=pytz.timezone("Australia/Sydney"))
        if sydney_timezone_now() > localmodified:
            flash("You can't add coffees to this run", "danger")
            return redirect(url_for("view_run", runid=runid))
        form.run.data = runid
    users = User.query.all()
    form.person.choices = [(user.id, user.name) for user in users]
    form.person.data = current_user.id
    if lastcoffee:
        form.coffeetype.data = lastcoffee.coffeetype
        form.size.data = lastcoffee.size
        form.sugar.data = lastcoffee.sugar
    if request.method == "GET":
        return render_template("coffeeform.html", form=form, formtype="Add", current_user=current_user)
    if form.validate_on_submit():
        coffee = Coffee(form.data["coffeetype"])
        coffee.size = form.data["size"]
        coffee.sugar = form.data["sugar"]
        coffee.personid = current_user.id
        coffee.addict = current_user
        coffee.run = form.data["run"]
        coffee.runobj = Run.query.filter(Run.id == form.data["run"]).first()
        #coffee.modified = sydney_timezone_now(datetime.utcnow())
        db.session.add(coffee)
        db.session.commit()
        flash("Coffee order added", "success")
        return redirect(url_for("view_coffee", coffeeid=coffee.id))
    else:
        flash(form.errors, "danger")
        print form.data
        return render_template("coffeeform.html", form=form, current_user=current_user)

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
        return redirect(url_for("view_cafe", cafeid=cafe.id))
    else:
        # Broken!
        flash("Add cafe caused an error", "danger")
        return render_template("cafeform.html", form=form, formtype="Add", current_user=current_user)
    return redirect(url_for("home"))

@app.route("/coffee/<int:coffeeid>/delete/", methods=["GET"])
def delete_coffee(coffeeid):
    coffee = Coffee.query.filter_by(id=coffeeid).first_or_404()
    db.session.delete(coffee)
    db.session.commit()
    flash("Coffee %d deleted" % coffeeid, "success")
    return redirect(url_for("view_all_coffees"))

def next_run():
    run = Run.query.filter(Run.statusid < 4).order_by(Run.time).first()
    return run

def get_person(name):
    person = User.query.filter(User.name.like(name)).first()
    if not person:
        person = User(name)
        db.session.add(person)
        db.session.commit()
    return person

# Mobile app parts

@app.route("/m/sync/", methods=["POST"])
def mobile_sync():
    if request.headers["Content-Type"] == "application/json":
        dinput = request.get_json()
    else:
        return redirect(url_for("home"))
    #print dinput
    doutput = {}
    qruns = Run.query.all()
    qcoffees = Coffee.query.all()
    #print len(qruns), len(qcoffees)
    runs = []
    coffees = []
    if len(dinput["runs"]) > 0:
        #print dinput["runs"]
        rdict = { int(d["id"]): d["modified"]  for d in dinput["runs"]}
    else:
        rdict = {}
    for r in qruns:
        #print r, rdict
        if r.id in rdict:
            #dt = datetime.
            #print r.id, r.modified, "|", r.readmodified(), "|", r.jsondatetime("modified"), "|", rdict[r.id]
            if r.jsondatetime("modified") != rdict[r.id]:
                runs.append(r.toJSON())
        else:
            runs.append(r.toJSON())
    if len(dinput["coffees"]) > 0:
        #print dinput["coffees"]
        cdict = { int(d["id"]): d["modified"]  for d in dinput["coffees"]}
    else:
        cdict = {}
    for c in qcoffees:
        if c.id in cdict:
            #print c, c.jsondatetime("modified"), cdict[c.id], c.jsondatetime("modified") == cdict[c.id]
            if c.jsondatetime("modified") != cdict[c.id]:
                coffees.append(c.toJSON())
        else:
            coffees.append(c.toJSON())
    #print jsonify(runs=runs, coffees=coffees)
    print "runs", runs
    print "coffees", coffees
    return jsonify(runs=runs, coffees=coffees)

@app.route("/m/run/", methods=["POST"])
def mobile_syncrun():
    if request.headers["Content-Type"] == "application/json":
        runjson = request.get_json()
    else:
        return redirect(url_for("home"))
    try: 
        print "Run JSON Request", runjson
        if "id" in runjson:
            run = Run.query.filter_by(id=runjson["id"]).first()
            run.time = runjson["time"]
        else:
            run = Run(runjson["time"])
        person = get_person(runjson["person"])
        run.person = person.id
        run.fetcher = person
        run.deadline = runjson["deadline"]
        run.cafe = runjson["cafe"]
        run.pickup = runjson["pickup"]
        run.status = runjson["status"]
        run.statusobj = Status.query.filter_by(id=runjson["status"]).first()
        if "id" not in runjson:
            db.session.add(run)
        db.session.commit()
        notify_newrun(run)
        return jsonify(msg="success", id=run.id, modified=run.jsondatetime("modified"))
    except:
        return jsonify(msg="error")

@app.route("/m/run/delete/", methods=["POST"])
def mobile_deleterun():
    if request.headers["Content-Type"] == "application/json":
        runjson = request.get_json()
    else:
        return redirect(url_for("home"))
    if "id" not in runjson:
        return jsonify(msg="error")
    run = Run.query.filter_by(id=runjson["id"]).first()
    db.session.delete(run)
    db.session.commit()
    return jsonify(msg="success", id=runjson["id"])

@app.route("/m/coffee/", methods=["POST"])
def mobile_synccoffee():
    # Parse JSON
    # Try to add
    # Return success or failure, with ID or error
    if request.headers["Content-Type"] == "application/json":
        coffeejson = request.get_json()
    else:
        return redirect(url_for("home"))
    try: 
        print "Coffee JSON Request", coffeejson
        if "id" in coffeejson:
            coffee = Coffee.query.filter_by(id=coffeejson["id"]).first()
        else:
            coffee = Coffee(coffeejson["coffeetype"])
        person = get_person(coffeejson["person"])
        coffee.person = person.id
        coffee.addict = person
        coffee.size = coffeejson["size"]
        coffee.sugar = coffeejson["sugar"]
        coffee.run = coffeejson["run"]
        coffee.runobj = Run.query.filter_by(id=coffeejson["run"]).first()
        if "id" not in coffeejson:
            db.session.add(coffee)
        db.session.commit()
        return jsonify(msg="success", id=coffee.id, modified=coffee.jsondatetime("modified"))
    except:
        return jsonify(msg="error")

@app.route("/m/coffee/delete/", methods=["POST"])
def mobile_deletecoffee():
    if request.headers["Content-Type"] == "application/json":
        coffeejson = request.get_json()
    else:
        return redirect(url_for("home"))
    if "id" not in coffeejson:
        return jsonify(msg="error")
    coffee = Coffee.query.filter_by(id=coffeejson["id"]).first()
    db.session.delete(coffee)
    db.session.commit()
    return jsonify(msg="success", id=coffeejson["id"])

@app.route("/m/regid/add/", methods=["POST"])
def mobile_addregid():
    if request.headers["Content-Type"] == "application/json":
        regjson = request.get_json()
    else:
        return redirect(url_for("home"))
    if "name" not in regjson:
        return jsonify(msg="error")
    user = User.query.filter_by(name=regjson["name"]).first()
    if not user:
        print "Adding new user"
        user = User(regjson["name"])
        db.session.add(user)
        db.session.commit()
    if "regid" not in regjson:
        return jsonify(msg="error")
    reg = RegistrationID(user.id, regjson["regid"])
    reg.user = user
    db.session.add(reg)
    db.session.commit()
    return jsonify(msg="success")

## Notifications

def notify_newrun(run):
    # Notify all users of the new run
    headers = {"Content-Type": "application/json", "Authorization":"key=%s" % app.config["API_KEY"]}
    regids = [r.regid for r in RegistrationID.query.all()]
    notifydata = {"msg": "New run added"}
    data = {"registration_ids": regids, "data": notifydata}
    print "Data", data
    url = "https://android.googleapis.com/gcm/send"
    r = requests.post(url, data=json.dumps(data))
    print "Text", r.text
    print "Status", r.status_code
    print "Headers", r.headers

def notify_newcoffee():
    # Get the run
    # Send notification to the person doing the run
    pass


## Error handlers
# Handle 404 errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Handle 500 errors
@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

