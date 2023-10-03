import openai
import os
import json
import requests
import sqlalchemy

from flask import Flask, redirect, render_template, request, url_for, make_response, Response
from flask_login import LoginManager, current_user, login_required, login_user, logout_user, UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
#from oauthlib.oauth2 import WebApplicationClient
from sqlalchemy import create_engine
from dotenv import load_dotenv
from datetime import datetime

from helpers import apology, email_check, password_check


# OpenAI setup
openai.api_key = os.environ.get("OPENAI_API_KEY")
openai.Model.list()

"""
# Google OAuth setup
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = ("https://accounts.google.com/.well-known/openid-configuration")
client = WebApplicationClient(GOOGLE_CLIENT_ID)
"""

# Application setup
app = Flask(__name__)
load_dotenv()
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

if __name__ == "__main__":
    app.run(host='0.0.0.0')

# User session management setup
login_manager = LoginManager()
login_manager.init_app(app)

# SQLAlchemy setup
# Generate the engine
db = create_engine("sqlite:///database.db")

# Define User class
class User(UserMixin):
    def __init__(self, id, name, email, profile_pic):
        self.id = id
        self.name = name
        self.email = email
        self.profile_pic = profile_pic

    @staticmethod
    def get(user_id):

        stmt = sqlalchemy.text("SELECT * FROM users WHERE cicero_id = :id")
        try:
            with db.connect() as conn:
                rows = conn.execute(stmt, parameters={"id": user_id}).fetchall()
        except Exception as e:
            return apology("db access error", 400)

        if len(rows) != 1:
            return None

        user = User(rows[0][0], rows[0][2], rows[0][3], rows[0][4])

        return user

# Flask-Login helper to retrieve a user from db
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

"""
# Retrieve Google's provider configuration
def get_google_provider_cfg():
    try:
        return requests.get(GOOGLE_DISCOVERY_URL).json()
    except:
         return apology("google error", 400)
"""


@app.route("/")
def index():
    # Simple GET page, with content displayed conditionally of session
    return render_template("/index.html")

"""
@app.route("/glogin")
def glogin():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

#db: sqlalchemy.engine.base.Engine
@app.route("/glogin/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")

    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send a request to get tokens
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Find and hit the URL from Google that gives the user's profile information
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    # Confirm email is verified, then gather user information
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return apology("User email not available or not verified by Google.", 400)
    
    # Find user if already in db
    stmt1 = sqlalchemy.text("SELECT * FROM users WHERE id = :id")
    try:
        with db.connect() as conn:
            rows = conn.execute(stmt1, parameters={"id": unique_id}).fetchall()
    except Exception as e:
        return apology("db search error", 400)
    
    # If 1 user found, use it
    if len(rows) == 1:
        user = User(rows[0][1], rows[0][2], rows[0][3], rows[0][4])
    
    # If no user found, create new entry
    elif len(rows) == 0:
        user = User(id=unique_id, name=users_name, email=users_email, profile_pic=picture)
        try:
            with db.connect() as conn:
                stmt2 = sqlalchemy.text("INSERT INTO users (id, name, email, profile_pic) VALUES (:id, :name, :email, :profile_pic)")
                conn.execute(stmt2, parameters={"id": unique_id, "name": users_name, "email": users_email, "profile_pic": picture})
                conn.commit()
        except Exception as e:
            return apology("db insert error", 400)
        
    # Otherwise, return error
    else:
        return apology("db error", 400)
        
    # Begin user session by logging the user in
    login_user(user)

    # Send user back to homepage
    return redirect(url_for("index"))
"""


@app.route("/register", methods=["GET", "POST"])
def register():

    # Register user

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure name was submitted
        if not request.form.get("name"):
            return apology("must provide name", 400)
        
        # Ensure username was submitted
        if not request.form.get("email"):
            return apology("must provide email", 400)
         
        # Check email is valid
        if not email_check(request.form.get("email")):
            return apology("not a valid email", 400)


        # Query database for email
        stmt1 = sqlalchemy.text("SELECT * FROM users WHERE email = :email")
        try:
            with db.connect() as conn:
                rows = conn.execute(stmt1, parameters={"email": request.form.get("email")}).fetchall()
        except Exception as e:
            return apology("db access error", 400)

        # Ensure username doesn't exist
        if len(rows) > 0:
            return apology("an account with this email already exists", 400)

        # Ensure password was submitted
        if not request.form.get("password") or request.form.get("password") != request.form.get("confirmation"):
            return apology("must provide two matching passwords", 400)
        
        # Ensure password is secure
        check = password_check(request.form.get("password"))
        if not check["password_ok"]:
            return apology("password needs min 10 characters, 1 digit, 1 symbol, 1 lower and 1 uppercase letter", 400)

        name = request.form.get("name")
        email = request.form.get("email")
        hash = generate_password_hash(request.form.get("password"))

        try:
            with db.connect() as conn:
                stmt2 = sqlalchemy.text("INSERT INTO users (name, email, hash) VALUES (:name, :email, :hash)")
                conn.execute(stmt2, parameters={"name": name, "email": email, "hash": hash})
                conn.commit()
        except Exception as e:
            return apology("db insert error", 400)

        # Redirect user to home page
        return redirect(url_for("login"))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure email was submitted
        if not request.form.get("email"):
            return apology("must provide email", 403)
        
        # Check email is valid
        if not email_check(request.form.get("email")):
            return apology("not a valid email", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for email
        stmt = sqlalchemy.text("SELECT * FROM users WHERE email = :email")
        try:
            with db.connect() as conn:
                rows = conn.execute(stmt, parameters={"email": request.form.get("email")}).fetchall()
        except Exception as e:
            return apology("db access error", 400)

        if len(rows) != 1 or not check_password_hash(rows[0][5], request.form.get("password")):
            return apology("invalid email and/or password", 403)

        user = User(rows[0][0], rows[0][2], rows[0][3], rows[0][4])

        # Remember which user has logged in
        login_user(user)

        # Redirect user to home page
        return redirect(url_for("index"))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/generate", methods=["GET", "POST"])
@login_required
def generate():
    
    # Set lists for input page
    INTERESTS = ["History, Culture and Arts", "Outdoor and Nature", "Food and Dining", "Shopping", "Entertainment and Nightlife", "Sports and Adventure", "Religious and Spiritual Interests", "Family-Friendly Activities", "Wellness and Relaxation"]
    MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    DURATION = ["1 week", "2 weeks", "3 weeks", "4 weeks"]

    # If POST
    if request.method == "POST":

        # Extract variables
        destination = request.form.get("destination")
        month = request.form.get("month")
        duration = request.form.get("duration")
        interests = request.form.getlist("interests")
        
        # Input validation
        if not destination:
            return apology("you must input a destination", 400)
        
        if month not in MONTHS:
                return apology("do not mess with the code please", 400)
        
        if duration not in DURATION:
                return apology("do not mess with the code please", 400)
        
        if not interests:
            return apology("you must select at least one interest", 400)
        
        # Extract variables
        interests_list = ""
        for i in interests:
            
            # Input validation
            if i not in INTERESTS:
                return apology("do not mess with the code please", 400)
            
            interests_list += i + ", "
        interests_list = interests_list.rstrip(", ")


        # Prompt generation        
        PROMPT = f"Please provide me with personalized advice for my next holiday to {destination}.\
            I will be there in {month} for {duration}.\
            My interests are: {interests}.\
            The advice should be structured as follows:\
            1. A first paragraph with general advice regarding {destination}, must-view places and hidden gems.\
            2. One paragraph for each of the interests I've expressed, with each destination on a seperate bullet point, for example:\
            Shopping, brief introduction about shopping in {destination}.\
            - relevant shopping place #1, description;\
            - relevant shopping place #2, description;\
            - etc..\
            3. A final paragraph with a proposed schedule for my trip, which must be relevant to my interests.\
            All of the above should also be relevant to the moment of the year I'm visiting.\
            For example you would suggest attending the cherry trees blossom if I were to go to Tokio at the end of March."

        # Query ChatGPT API        
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Cicero, an experienced travel guide who has visited the whole world. Use a professional, but friendly tone."},
                {"role": "user", "content": f"{PROMPT}"}
            ]
        )

        # Cleanup output
        bad_output = completion.choices[0].message.content
        OUTPUT = bad_output.replace("\n", '<br>')

        # Set some variables
        user_id = current_user.get_id()
        timestamp = datetime.utcnow().strftime("%m-%d-%Y, %H:%M:%S")

        # Insert trip into database
        try:
            with db.connect() as conn:
                stmt = sqlalchemy.text("INSERT INTO trips (user_id, generation_ts, destination, month, duration, travel_plan) VALUES (:id, :ts, :destination, :month, :duration, :travel_plan)")
                conn.execute(stmt, parameters={"id": user_id, "ts": timestamp, "destination": destination, "month": month, "duration": duration, "travel_plan": OUTPUT})
                conn.commit()
        except Exception as e:
            return apology("db insert error", 400)

        
        return render_template("/output.html", your_destination=destination, output=OUTPUT)

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        return render_template("/generate.html", interests=INTERESTS, months=MONTHS, duration=DURATION)


@app.route("/faq")
def faq():
    # Simple GET page
    return render_template("/faq.html")


@app.route("/privacy")
def privacy():
    # Simple GET page
    return render_template("/privacy.html")


@app.route("/terms")
def terms():
    # Simple GET page
    return render_template("/terms.html")