import json
import math
import os
import pickle
import re as reg

import numpy as np
import requests as re
import MySQLdb.cursors
import pandas as pd
import plotly
import plotly.express as ex
from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify
from flask_bcrypt import Bcrypt
from flask_login import current_user
from flask_mysqldb import MySQL
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from wtforms import StringField, PasswordField, SubmitField, EmailField
from wtforms.validators import InputRequired, Length
import sklearn

app = Flask(__name__)
bcrypy = Bcrypt(app)
UPLOAD_FOLDER = '/flask_app/static/images'

app.config['SECRET_KEY'] = 'supermanissuperman'
app.config['SQL_ALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:destination786@localhost/autotrader'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'destination786'
app.config['MYSQL_DB'] = 'autotrader'
app.config['UPLOAD_FOLDER'] = "static"

## mysql inherit the application
mysql = MySQL(app)


## Method to query the database
def sql_db(query, placeholder):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute(query, placeholder)
    result = cur.fetchone()
    return result


class RegisterForm(FlaskForm):
    fullname = StringField(validators=[InputRequired(), Length(min=2, max=50)], render_kw={"placeholder": "Full Name"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})

    email = EmailField(render_kw={"placeholder": "Email"})
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    email = StringField(validators=[InputRequired(), Length(min=4, max=100)], render_kw={"placeholder": "Email"})

    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField("Login")


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == "POST":
        details = request.form
        firstName = details['fname']
        lastName = details['lname']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO myusers(firstname, lastname) VALUES (%s, %s)", (firstName, lastName))
        mysql.connection.commit()
        cur.close()
        return "done"

    return render_template('index.html')


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        form_content = request.form
        user_email = form_content["email"]
        password = form_content["password"]

        user_by_email = sql_db("select * from users where email = %s", (user_email,))

        if user_by_email is not None:
            hashed_password = user_by_email["password"]
            pass_check = check_password_hash(hashed_password, password)
            if pass_check:
                session['loggedin'] = True
                session['id'] = user_by_email["id"]
                session['username'] = user_by_email["fullname"]

                # Redirect to home page
                return redirect(url_for("cars"))
            else:
                flash("incorrect password")
                return redirect(url_for('login'))

    form = LoginForm()
    form2 = RegisterForm()
    return render_template('login.html', form=form, form2=form2)


@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('id', None)
    # Redirect to login page
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    cur = mysql.connection.cursor()
    user = current_user

    form = RegisterForm()

    if request.method == "POST":
        details = request.form
        user_email = details["email"]
        users = sql_db("select * from users where email = %s", (user_email,))

        if users:
            flash("Email already exist please use valid email")
            return redirect(url_for("login"))

        else:
            flash("Welcome you can sign in")
            hashed_password = generate_password_hash(details["password"])
            email = details["email"]
            fullname = details["fullname"]

            list = [fullname, hashed_password, email]
            cur.execute("insert into users(fullname, password, email) values(%s, %s, %s)",
                        (fullname, hashed_password, email))
            mysql.connection.commit()
            cur.close()

            return redirect(url_for("login"))

    return render_template('details.html', form=form)


@app.route('/cars', defaults={'page': 1}, methods=['GET', 'POST'])
@app.route('/cars/<int:page>', methods=['GET', 'POST'])
def cars(page):
    if 'loggedin' in session:
        limit = 20
        username = session["username"]
        id = session["id"]
        offset = page * limit - limit
        curr = mysql.connect.cursor()
        curr.execute(
            'select cm.make, cm.model, year, cspec.bhp, cspec.transmission, cspec.fuel, cat.category_type,'
            'uc.image_link, loc.town , sel.seller_name, price, milage, ulez, owners from used_cars uc inner join '
            'category cat on cat.category_id = uc.category_id inner join car_make cm on cm.make_id = uc.make_id inner '
            'join  seller sel on sel.seller_id = uc.seller_id inner join location loc on loc.location_id = '
            'sel.location_id inner join used_cars_specs ucs on ucs.car_id = uc.car_id inner join car_specifications '
            'cspec on cspec.spec_id = ucs.spec_id')
        data = curr.fetchall()
        total_row = curr.rowcount
        total_page = math.ceil(total_row / limit)
        next = page + 1
        prev = page - 1
        result = curr.execute(
            "select  cm.make, cm.model, year, cspec.bhp, cspec.transmission, cspec.fuel, cat.category_type,"
            "uc.image_link, loc.town , sel.seller_name, price, milage, ulez, owners,uc.car_id from used_cars uc inner "
            "join category cat on cat.category_id = uc.category_id inner join car_make cm on cm.make_id = uc.make_id "
            "inner join  seller sel on sel.seller_id = uc.seller_id inner join location loc on loc.location_id = "
            "sel.location_id inner join used_cars_specs ucs on ucs.car_id = uc.car_id inner join car_specifications "
            "cspec on cspec.spec_id = ucs.spec_id LIMIT %s OFFSET %s",
            (limit, offset))
        result = curr.fetchall()
        image = sql_db("select image from users where id = %s", (id,))
        make = curr.execute(
            'select distinct cm.make,  cm.model, year, cspec.bhp, cspec.transmission, cspec.fuel, cat.category_type,'
            'uc.image_link, loc.town , sel.seller_name, price, milage, ulez, owners from used_cars uc inner join '
            'category cat on cat.category_id = uc.category_id inner join car_make cm on cm.make_id = uc.make_id inner '
            'join  seller sel on sel.seller_id = uc.seller_id inner join location loc on loc.location_id = '
            'sel.location_id inner join used_cars_specs ucs on ucs.car_id = uc.car_id inner join car_specifications '
            'cspec on cspec.spec_id = ucs.spec_id')
        # select car make select list
        curr.execute('select distinct make from car_make order by make')
        make_select = curr.fetchall()

        if curr.rowcount > 0:
            return render_template('test2.html', data=result, page=total_page, next=next, prev=prev, username=username,
                                   image=image, make=make, make_select=make_select)
        # page = int(request.args.get("page", 1))
        # paginate = Pagination(page=page, total=10)
        # return render_template('test2.html', data=data[:100], paginate=paginate)
    else:
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route('/search', defaults={'page': 1, "make": "make", "model": "model", "fuel": "fuel"}, methods=["POST", "GET"])
@app.route('/search/<make>/<model>/<fuel>/<int:page>', methods=["POST", "GET"])
def search(page, make, model, fuel):
    if 'loggedin' in session:
        content = request.form
        if make == "make":
            search = content["search"]
            print(search)
        else:
            search = make
        if model == "model":
            search_model = "[w]*"
            print("yes")

        else:
            search_model = model
        if fuel == "fuel":
            fuel_search = "[w]*"
            print(fuel_search)
        else:
            fuel_search = fuel

        limit = 20
        username = session['username']
        offset = page * limit - limit
        curr = mysql.connect.cursor()


        curr.execute('select cm.make, cm.model, year, cspec.bhp, cspec.transmission, cspec.fuel, cat.category_type,'
                     'uc.image_link, loc.town , sel.seller_name, price, milage, ulez, owners from used_cars uc inner '
                     'join category cat on cat.category_id = uc.category_id inner join car_make cm on cm.make_id = '
                     'uc.make_id inner join  seller sel on sel.seller_id = uc.seller_id inner join location loc on '
                     'loc.location_id = sel.location_id inner join used_cars_specs ucs on ucs.car_id = uc.car_id '
                     'inner join car_specifications cspec on cspec.spec_id = ucs.spec_id where cm.make REGEXP %s AND '
                     'cm.model REGEXP %s and cspec.fuel REGEXP %s', (search, search_model, fuel_search))

        total_row = curr.rowcount
        print(total_row)
        total_page = math.ceil(total_row / limit)
        next = page + 1
        prev = page - 1

        curr.execute("select cm.make, cm.model, year, cspec.bhp, cspec.transmission, cspec.fuel, cat.category_type,"
                     "uc.image_link, loc.town , sel.seller_name, price, milage, ulez, owners, uc.car_id from "
                     "used_cars uc inner join category cat on cat.category_id = uc.category_id inner join car_make cm "
                     "on cm.make_id = uc.make_id inner join  seller sel on sel.seller_id = uc.seller_id inner join "
                     "location loc on loc.location_id = sel.location_id inner join used_cars_specs ucs on ucs.car_id "
                     "= uc.car_id inner join car_specifications cspec on cspec.spec_id = ucs.spec_id where cm.make REGEXP %s "
                     "AND cm.model REGEXP %s and cspec.fuel REGEXP %s LIMIT %s OFFSET %s", (search, search_model,fuel_search, limit, offset))
        result = curr.fetchall()
        make = search
        if search_model =="[w]*":
            search_model="model"
        curr.execute('select distinct make from car_make order by make')
        make_select = curr.fetchall()

        if curr.rowcount > 0:
            return render_template('search.html', data=result, page=total_page, next=next, prev=prev, make=make,
                                   username=username, make_select=make_select, model=search_model, fuel=fuel)
        # page = int(request.args.get("page", 1))
        # paginate = Pagination(page=page, total=10)
        # return render_template('test2.html', data=data[:100], paginate=paginate)
    else:
        return redirect(url_for("login"))

    return render_template("login.html")


# Route for index page
@app.route('/index', methods=["GET", "POST"])
def index1():
    if 'loggedin' in session:
        username = session["username"]
        return render_template("index.html", username=username)
    return redirect(url_for("login"))


# Route for the charts
@app.route('/charts')
def chart():
    return render_template('charts.html')


# Route for the details of the car
@app.route('/details/<id>', methods=["GET", "POST"])
def details(id):
    if 'loggedin' in session:
        curr = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        curr.execute(
            "select cm.make, cm.model, year, cspec.bhp, cspec.transmission,cspec.engine, cspec.fuel, "
            "cat.category_type,uc.image_link, loc.town, loc.country , sel.seller_name, price, milage, ulez, "
            "owners from used_cars uc inner join category cat on cat.category_id = uc.category_id inner join car_make "
            "cm on cm.make_id = uc.make_id inner join  seller sel on sel.seller_id = uc.seller_id inner join location "
            "loc on loc.location_id = sel.location_id inner join used_cars_specs ucs on ucs.car_id = uc.car_id inner "
            "join car_specifications cspec on cspec.spec_id = ucs.spec_id where uc.car_id=%s",
            (id,))
        result = curr.fetchone()
        curr.close()
        return render_template("details.html", result=result)
    return redirect(url_for('login'))


# Route for ulloading of image file
@app.route('/uploader', methods=['GET', 'POST'])
def upload_file():
    if 'loggedin' in session:
        if request.method == 'POST':
            f = request.files['file']
            filename = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], "images", filename))
            id = session['id']
            username = session["username"]
            upload_url = f"/static/images/{f.filename}"
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cur.execute("update users set image = %s  where id = %s", (upload_url, id,))
            cur.close()
            mysql.connection.commit()
            msg = 'The pic is uploaded'

            return render_template('setting.html', msg=msg)
    return redirect(url_for('login'))


# route for the settings
@app.route('/setting', methods=["GET", "POST"])
def setting():
    if 'loggedin' in session:
        if request.method == "POST":
            id = session['id']
            username = session["username"]
            upload_url = request.form["upload"]
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cur.execute("update users set image = %s  where id = %s", (upload_url, id,))
            mysql.connection.commit()
            cur.close()

            result = sql_db("select image from users where id = %s", (id,))

            return render_template('setting.html', usename=username, image=result["image"])

        username = session['username']
        id = session['id']
        result = sql_db("select image from users where id = %s", (id,))

        return render_template('setting.html', username=username, image=result["image"])
    return redirect(url_for("login"))


# Route for the user profile
@app.route('/profile')
def profile():
    if 'loggedin' in session:
        username = session['username']
        id = session['id']
        id = session['id']
        result = sql_db("select * from users where id = %s", (id,))
        return render_template('profile.html', username=username, result=result)
    return redirect(url_for('login'))


#
@app.route('/sort', methods=['GET', 'POST'])
def sort():
    if 'loggedin' in session:
        if request.method == "POST":
            sort_by = request.form.get('sort')
            curr = mysql.connect.cursor()
            curr.execute('select cm.make, cm.model, year, cspec.bhp, cspec.transmission, cspec.fuel, '
                         'cat.category_type,uc.image_link, loc.town , sel.seller_name, price, milage,'
                         ' ulez, owners from used_cars uc inner join category cat on cat.category_id = uc.category_id '
                         'inner join car_make cm on cm.make_id = uc.make_id inner join  seller sel on '
                         'sel.seller_id = uc.seller_id inner join location loc on loc.location_id = sel.location_id '
                         'inner join used_cars_specs ucs on ucs.car_id = uc.car_id '
                         'inner join car_specifications cspec on cspec.spec_id = ucs.spec_id sort_by %s ASC',
                         (sort_by,))
            result = curr.fetchall()
            curr.close()
            return render_template('test2.html', result=result)


# model class to get data from database and pass to the json query

@app.route('/callback/<string:make>', methods=['GET', 'POST'])
def model(make=None, model=None):
    if request.method == 'GET':
        if make and model == None:
            curr = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            curr.execute('select model from car_make where make=%s order by model', (make,))
            # row_header=[x[0] for x in curr.description]
            sql_result = curr.fetchall()
            curr.close()
            # mysql.connection.close()

            result = jsonify(sql_result)
            return result


@app.route('/fuel/<string:make>/<string:model>', methods=['GET', 'POST'])
def fuel(make=None, model=None):
    if request.method == 'GET':
        if make != None and model != None:
            curr = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            curr.execute(
                'select distinct fuel from car_specifications inner join used_cars_specs as c on c.spec_id = '
                'car_specifications.spec_id '
                'inner join used_cars as uc on uc.car_id = c.car_id '
                'inner join car_make as cm on cm.make_id = uc.make_id '
                'where cm.make=%s and cm.model=%s;', (make, model,))
            # row_header=[x[0] for x in curr.description]
            sql_result = curr.fetchall()
            curr.close()
            # mysql.connection.close()
            result = jsonify(sql_result)
            print(result)
            return result


# method to extract data from data base
def get_sql_dict(query, placeholder):
    conn = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    conn.execute(query, placeholder)
    result = conn.fetchall()

    return result


# Route for the bar chart html
@app.route('/graphs')
def graphs():
    if 'loggedin' in session:
        make = "[\w]*"
        model = "[\w]*"
        bar = create_plot(make, model)

        return render_template("graphs.html", plot=bar)


def create_plot(make, model):
    data = get_sql_dict(
        "select make, model, count(car_id) from used_cars uc inner join car_make cm on cm.make_id = uc.make_id where "
        "make REGEXP %s and  model REGEXP %s group by model order by %s , %s;",
        (make, model, "make", "model",))
    car_data = pd.DataFrame(data)
    total_count = car_data.shape[0]

    car_make = car_data["make"]
    z = car_data["model"]
    y = car_data["count(car_id)"]

    df = pd.DataFrame({'car_make': car_make, 'number_of_cars': y, 'z': z})  # creating a sample dataframe

    fig = ex.bar(
        x=df['car_make'],  # assign x as the dataframe column 'x'
        y=df['number_of_cars'], color=df['z'], title="Available cars in UK")

    data = [fig]

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON


@app.route('/map', methods=["POST", "GET"])
def map():
    if 'loggedin' in session:
        curr = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        curr.execute('select distinct make from car_make order by make')
        make_select = curr.fetchall()
        if request.method == "POST":
            make = request.form["make"]
            model = request.form["model"]

            map = create_map(make, model)
            return render_template("map.html", map=map)

        make = "[\w]*"
        model = "[\w]*"
        map = create_map(make, model)
        return render_template('map.html', map=map, make_select=make_select)


def create_map(make, model):
    query = get_sql_dict(
        "select make, model, milage, price, town, country, latitude, longitude from used_cars uc inner join  car_make "
        "cm on cm.make_id = uc.make_id inner join seller s on s.seller_id = uc.seller_id inner join location loc on "
        "loc.location_id = s.location_id where make REGEXP %s AND model REGEXP %s;",
        (make, model,))
    df = pd.DataFrame(query)
    ex.set_mapbox_access_token(
        "pk.eyJ1IjoieWFtaW5oYXNzYW4iLCJhIjoiY2t5cDF4am9wMDYyYjJxcHQ5MG5zMnI4eCJ9.o1pK52Thw28YjKTM9sXXYg")
    fig = ex.scatter_mapbox(df, lat="latitude", lon="longitude", hover_data=["make", "price", "model"],
                            zoom=5, height=500, template="plotly_dark")
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    mapJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return mapJSON


@app.route('/dashboard', methods=["POST", "GET"])
def dashboard():
    curr = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    curr.execute(f'select admin from users where id={session["id"]}')
    print(session["id"])
    result=curr.fetchall()
    admin=[x["admin"] for x in result]
    print(admin[0])
    if 'loggedin' in session and admin[0] == "y":
        pie = createPie()
        heatmaps = heatmap()
        barcharts = barchart()
        scatterChart = scatter()
        correlations = correlation()
        bar = create_plot("[\w]*", "[\w]*")
        return render_template('dashboard.html', pie=pie, bar=bar, heat=heatmaps, barchart=barcharts, scatter=scatterChart,
                               correlation=correlations)
    else:
        return render_template("index.html")

def createPie():
    make = "[\w]*"
    model = "[\w]*"
    query = get_sql_dict("select loc.country,count(uc.ulez), count(uc.ulez) from used_cars uc left join car_make cm"
                         " on cm.make_id = uc.make_id inner join seller sel on sel.seller_id = uc.seller_id "
                         "inner join location loc on loc.location_id = sel.location_id where uc.ulez = 'Yes' and"
                         " cm.make REGEXP %s and cm.model REGEXP %s group by loc.country;", (make, model,))

    df = pd.DataFrame(query)
    fig = ex.pie(df, values="count(uc.ulez)", names="country", title="Ulez cars by Region", template="plotly_dark")

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON


@app.route("/data", methods=["GET", "POST"])
def data():
    make = request.args.get("make")
    model = request.args.get("model")
    map = create_map(make, model)
    return map


@app.route('/predict', methods=["GET", "POST"])
def prdict():
    model=pickle.load(open("static/predict_price1", "rb"))

    make_=[x for x in model.feature_names_in_ if reg.search("make", x) ]
    transmission_=[x for x in model.feature_names_in_ if reg.search("transmission", x) ]
    fuel_=[x for x in model.feature_names_in_ if reg.search("fuel", x) ]
    for a in make_:
        print(a)


    if request.method == "POST":
        details = request.form
        make=details["make"]
        engine_=details["engine"]
        transmission=details["transmission"]
        fuel=details["fuel"]
        age_=details["age"]
        mileage_=details["mileage"]

        print(make,engine_,transmission,fuel,age_,mileage_)

        predict_val=pd.DataFrame(np.zeros((1,55)),columns=model.feature_names_in_)
        print(predict_val.columns)

        predict_val.at[0,make]=1
        predict_val.at[0,transmission_]=1
        predict_val.at[0,fuel]=1
        predict_val.at[0,"age"]=age_
        predict_val.at[0,"milage"]=mileage_
        predict_val.at[0,"engine"]=engine_
        predict_val.fillna(0)
        print(predict_val[make])

        result = round(model.predict(predict_val)[0])
        flash(f"The predicted car price is £{result}")

        return render_template('predict.html', make_=make_, fuel_=fuel_, transmission_=transmission_)
    return render_template("predict.html", make_=make_, fuel_=fuel_, transmission_=transmission_)


def heatmap():
    conn = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    conn.execute(
        'select cm.make, cm.model, year, cspec.bhp, cspec.transmission, cspec.fuel, cat.category_type,uc.image_link, '
        'loc.town , sel.seller_name, price, milage, ulez, owners from used_cars uc inner join category cat on '
        'cat.category_id = uc.category_id inner join car_make cm on cm.make_id = uc.make_id inner join  seller sel on '
        'sel.seller_id = uc.seller_id inner join location loc on loc.location_id = sel.location_id inner join '
        'used_cars_specs ucs on ucs.car_id = uc.car_id inner join car_specifications cspec on cspec.spec_id = '
        'ucs.spec_id where milage < 500000')
    result = conn.fetchall()
    df = pd.DataFrame(result)
    fig = ex.scatter_3d(df, "price", "milage", "year", color='make', symbol='model',
                        title="Scatter 3D Price Milage and Year", template="plotly_dark")

    heatmap = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return heatmap


def barchart():
    conn = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    conn.execute(
        'select cm.make, cm.model, year, cspec.bhp, cspec.transmission, cspec.fuel, cat.category_type,uc.image_link, '
        'loc.town , sel.seller_name, price, milage, ulez, owners from used_cars uc inner join category cat on '
        'cat.category_id = uc.category_id inner join car_make cm on cm.make_id = uc.make_id inner join  seller sel on '
        'sel.seller_id = uc.seller_id inner join location loc on loc.location_id = sel.location_id inner join '
        'used_cars_specs ucs on ucs.car_id = uc.car_id inner join car_specifications cspec on cspec.spec_id = '
        'ucs.spec_id')
    result = conn.fetchall()
    df = pd.DataFrame(result)
    fig = ex.box(df, "make", "price", title="Box plot of cars prices by Make", notched=True, color="make",
                 template="plotly_dark")
    barchart = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return barchart


def scatter():
    conn = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    conn.execute(
        'select cm.make, cm.model, year, cspec.bhp, cspec.transmission, cspec.fuel, cat.category_type,uc.image_link, '
        'loc.town , sel.seller_name, price, milage, ulez, owners from used_cars uc inner join category cat on '
        'cat.category_id = uc.category_id inner join car_make cm on cm.make_id = uc.make_id inner join  seller sel on '
        'sel.seller_id = uc.seller_id inner join location loc on loc.location_id = sel.location_id inner join '
        'used_cars_specs ucs on ucs.car_id = uc.car_id inner join car_specifications cspec on cspec.spec_id = '
        'ucs.spec_id where milage < 500000')
    result = conn.fetchall()
    df = pd.DataFrame(result)
    fig = ex.scatter(df, "year", "price", size="price", template="plotly_dark", color="milage")
    scatter = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return scatter


def correlation():
    conn = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    conn.execute(
        'select cm.make, cm.model, year, cspec.bhp, cspec.transmission, cspec.fuel, cat.category_type,uc.image_link, '
        'loc.town , sel.seller_name, price, milage, ulez, owners from used_cars uc inner join category cat on '
        'cat.category_id = uc.category_id inner join car_make cm on cm.make_id = uc.make_id inner join  seller sel on '
        'sel.seller_id = uc.seller_id inner join location loc on loc.location_id = sel.location_id inner join '
        'used_cars_specs ucs on ucs.car_id = uc.car_id inner join car_specifications cspec on cspec.spec_id = '
        'ucs.spec_id where milage < 500000')
    result = conn.fetchall()
    df = pd.DataFrame(result)
    df1 = df[["make", "milage", "price", "year"]]

    fig = ex.scatter_matrix(df1, template="plotly_dark", title="Correlation matrix", color="make")
    figure = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return figure


if __name__ == '__main__':
    app.run(debug=True)
