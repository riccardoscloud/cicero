import openai
import os
import sqlalchemy
import requests
import json

from flask import Flask, redirect, render_template, request, url_for, Response
from flask_login import LoginManager, current_user, login_required, login_user, logout_user, UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from oauthlib.oauth2 import WebApplicationClient
from sqlalchemy import create_engine
from dotenv import load_dotenv
from datetime import datetime

from helpers import apology, email_check, password_check

# SETUP: Load .env
load_dotenv()

# SETUP: OpenAI
# - Define variables
openai.api_key = os.environ.get("OPENAI_API_KEY")
openai.Model.list()

# Define function for calling the API with custom prompt
def send_prompt(prompt):
    return openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Cicero, an experienced travel guide who has visited the whole world. Use a professional, but friendly tone."},
                {"role": "user", "content": f"{prompt}"}
            ],
            stream=True
        )

# SETUP: Google OAuth
# - Set variables
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = ("https://accounts.google.com/.well-known/openid-configuration")
client = WebApplicationClient(GOOGLE_CLIENT_ID)

# - Retrieve Google's provider configuration
def get_google_provider_cfg():
    try:
        return requests.get(GOOGLE_DISCOVERY_URL).json()
    except:
         return apology("google internal error", 500)


# SETUP: Application
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)

# SETUP: User session management
login_manager = LoginManager()
login_manager.init_app(app)

# SETUP: SQLAlchemy
db = create_engine("sqlite:///database.db")

# SETUP: Flask-Login
# - Define User class
class User(UserMixin):
    def __init__(self, id, name, email, profile_pic):
        self.id = id
        self.name = name
        self.email = email
        self.profile_pic = profile_pic

    # Method used by login_manager: retrieve user object by its id
    @staticmethod
    def get(user_id):

        # DB search
        stmt = sqlalchemy.text("SELECT * FROM users WHERE cicero_id = :id")
        try:
            with db.connect() as conn:
                rows = conn.execute(stmt, parameters={"id": user_id}).fetchall()
        except:
            return apology("db access error", 400)

        # Should get only one result
        if len(rows) != 1:
            return None

        # Load user from its DB entity
        user = User(rows[0][0], rows[0][2], rows[0][3], rows[0][4])

        return user

# - Helper to retrieve a user from db
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# APP ROUTES #
# Homepage
@app.route("/")
def index():
    # Simple GET page, with content displayed conditionally of session
    return render_template("/index.html")

# Register a new user
@app.route("/register", methods=["GET", "POST"])
def register():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure name was submitted
        if not request.form.get("name"):
            return apology("must provide name", 403)
        
        # Ensure username was submitted
        if not request.form.get("email"):
            return apology("must provide email", 403)
         
        # Check email is valid
        if not email_check(request.form.get("email")):
            return apology("not a valid email", 403)

        # Query database for email
        stmt1 = sqlalchemy.text("SELECT * FROM users WHERE email = :email")
        try:
            with db.connect() as conn:
                rows = conn.execute(stmt1, parameters={"email": request.form.get("email")}).fetchall()
        except:
            return apology("db access error", 400)

        # Ensure account with same email doesn't exist
        if len(rows) > 0:
            return apology("an account with this email already exists", 403)

        # Ensure password was submitted
        if not request.form.get("password") or request.form.get("password") != request.form.get("confirmation"):
            return apology("must provide two matching passwords", 403)
        
        # Ensure password is secure
        check = password_check(request.form.get("password"))
        if not check["password_ok"]:
            return apology("password needs min 10 characters, 1 digit, 1 symbol, 1 lower and 1 uppercase letter", 403)

        # Prepare variables for DB insert
        name = request.form.get("name")
        email = request.form.get("email")
        hash = generate_password_hash(request.form.get("password"))

        # DB insert new user
        try:
            with db.connect() as conn:
                stmt2 = sqlalchemy.text("INSERT INTO users (name, email, hash) VALUES (:name, :email, :hash)")
                conn.execute(stmt2, parameters={"name": name, "email": email, "hash": hash})
                conn.commit()
        except:
            return apology("db insert error", 400)

        # Redirect to login page
        return redirect(url_for("login"))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

# Login existing user
@app.route("/login", methods=["GET", "POST"])
def login():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure email was submitted
        if not request.form.get("email"):
            return apology("must provide email", 403)
        
        # Check email is valid
        if not email_check(request.form.get("email")):
            return apology("not a valid email", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for email
        stmt = sqlalchemy.text("SELECT * FROM users WHERE email = :email")
        try:
            with db.connect() as conn:
                rows = conn.execute(stmt, parameters={"email": request.form.get("email")}).fetchall()
        except:
            return apology("db access error", 400)

        # If user has a Google account and no password set
        if len(rows) == 1 and (not rows[0][5] or rows[0][5] == ""):
            return apology("password not set: login with google again", 403)

        # Check account exists and password hash matches
        if len(rows) != 1 or not check_password_hash(rows[0][5], request.form.get("password")):
            return apology("invalid email and/or password", 403)

        # Load account info into user object
        user = User(rows[0][0], rows[0][2], rows[0][3], rows[0][4])

        # Load user object into login manager
        login_user(user)

        # Redirect user to homepage
        return redirect(url_for("index"))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

# Google Oauth - User clicks on "Login with Google"
@app.route("/glogin", methods=["POST"])
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

# Google OAuth - Google sends back user's data
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
        return apology("user email not available or not verified by Google.", 400)
    
    # Find user if already in DB
    stmt1 = sqlalchemy.text("SELECT * FROM users WHERE email = :email")
    try:
        with db.connect() as conn:
            rows = conn.execute(stmt1, parameters={"email": users_email}).fetchall()
    except:
        return apology("db access error", 400)
    
    # If 1 user found
    if len(rows) == 1:

        # If DB record doesn't already have Google's info (was created locally)
        if not rows[0][1] or rows[0][1] == "":

            # Update it
            stmt2 = sqlalchemy.text("UPDATE users SET google_id = :g_id, profile_pic = :profile_pic WHERE email = :email")
            try:
                with db.connect() as conn:
                    conn.execute(stmt2, parameters={"g_id": unique_id, "profile_pic": picture, "email": users_email})
                    conn.commit()
            except:
                return apology("db access error", 400)



        # Load account info into user object
        user = User(rows[0][0], rows[0][2], rows[0][3], rows[0][4])
    
    # If no user found, create new entry
    elif len(rows) == 0:
        
        # Insert into DB
        try:
            with db.connect() as conn:
                stmt3 = sqlalchemy.text("INSERT INTO users (google_id, name, email, profile_pic) VALUES (:id, :name, :email, :profile_pic)")
                conn.execute(stmt3, parameters={"id": unique_id, "name": users_name, "email": users_email, "profile_pic": picture})
                conn.commit()
        except:
            return apology("db insert error", 400)
        
        # Retrieve from DB
        try:
            with db.connect() as conn:
                rows = conn.execute(stmt1, parameters={"email": users_email}).fetchall()
        except:
            return apology("db access error", 400)
        
        # If 1 user found, load account info into user object
        if len(rows) == 1:
            user = User(rows[0][0], rows[0][2], rows[0][3], rows[0][4])
        
    # Otherwise, return error
    else:
        return apology("db internal error", 400)
        
    # Load user object into login manager
    login_user(user)

    # Send user back to homepage
    return redirect(url_for("index"))

# Logout of current session
@app.route("/logout")
@login_required
def logout():

    # Logout using login manager
    logout_user()

    #Redirect to homepage
    return redirect(url_for("index"))

# Account management page
@app.route("/account")
@login_required
def account():
    # Simple GET page
    return render_template("/account.html")

# - Function for changing username
@app.route("/change_name", methods=["POST"])
@login_required
def change_name():
    
    # Initialize variables
    user_id = current_user.get_id()
    user_name = request.form.get("name")
    
    # Ensure user name was submitted
    if not user_name:
        return apology("must provide new user name", 403)
    
    # Update DB record
    stmt = sqlalchemy.text("UPDATE users SET name = :new_name WHERE cicero_id = :id;")
    try:
        with db.connect() as conn:
            conn.execute(stmt, parameters={"new_name": user_name, "id": user_id})
            conn.commit()
    except:
        return apology("db access error", 400)
    
    # Redirect to account page
    return redirect(url_for("account"))

# - Function for changing password
@app.route("/change_password", methods=["POST"])
@login_required
def change_password():

    # Initialize variables
    user_id = current_user.get_id()
    old_pass = request.form.get("old_password")
    new_pass_1 = request.form.get("new_password_1")
    new_pass_2 = request.form.get("new_password_2")

    # Check old password is submitted
    if not old_pass:
        return apology("must submit your current password", 403)
    
    # Check old password is valid
    stmt1 = sqlalchemy.text("SELECT * FROM users WHERE cicero_id = :id")
    try:
        with db.connect() as conn:
            rows = conn.execute(stmt1, parameters={"id": user_id}).fetchall()
    except:
        return apology("db access error", 400)

    if len(rows) != 1 or not check_password_hash(rows[0][5], old_pass):
        return apology("invalid password", 403)
    
    # Ensure new password was submitted and is confirmed
    if not new_pass_1 or new_pass_1 != new_pass_2:
        return apology("must provide two matching passwords", 403)
    
    # Check new password is different from old one
    if new_pass_1 == old_pass:
        return apology("new password must be different from old password", 403)

    # Check new password is secure
    check = password_check(new_pass_1)
    if not check["password_ok"]:
        return apology("password needs min 10 characters, 1 digit, 1 symbol, 1 lower and 1 uppercase letter", 403)

    # Hash new password
    hash = generate_password_hash(new_pass_1)

    # Update DB record
    stmt2 = sqlalchemy.text("UPDATE users SET hash = :new_hash WHERE cicero_id = :id;")
    try:
        with db.connect() as conn:
            conn.execute(stmt2, parameters={"new_hash": hash, "id": user_id})
            conn.commit()
    except:
        return apology("db access error", 400)

    # Redirect to account page
    return redirect(url_for("account"))

# Page for prompt generation
@app.route("/generate", methods=["GET", "POST"])
@login_required
def generate():
    
    # Set lists for input page
    INTERESTS = ["History, Culture and Arts", "Outdoor and Nature", "Food and Dining", "Shopping", "Entertainment and Nightlife", "Sports and Adventure", "Religious and Spiritual Interests", "Family-Friendly Activities", "Wellness and Relaxation"]
    MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    DURATION = ["1 week", "2 weeks", "3 weeks", "4 weeks"]

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Extract variables
        destination = request.form.get("destination")
        month = request.form.get("month")
        duration = request.form.get("duration")
        interests = request.form.getlist("interests")
        
        # Input validation
        if not destination:
            return apology("you must input a destination", 403)
        
        if month not in MONTHS:
                return apology("do not mess with the code please", 403)
        
        if duration not in DURATION:
                return apology("do not mess with the code please", 403)
        
        if not interests:
            return apology("you must select at least one interest", 403)
        
        # Validate interests input and combine in a single string
        interests_list = ""
        for i in interests:
            if i not in INTERESTS:
                return apology("do not mess with the code please", 403)    
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
            For example you would suggest attending the cherry trees blossom if I were to go to Tokio at the end of March.\
            Please output your response with HTML formatting, for example: the paragraph headers should be in H5, \
            you also should account for new lines.\
            Also, make sure to give your warm regards at the end."

        # Load stream page with necessary variables
        return render_template(
            "stream.html", 
            your_prompt=PROMPT, 
            your_destination=destination,
            your_month=month,
            your_duration=duration,
            )
    
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        # Load generate page with data for the form
        return render_template("/generate.html", interests=INTERESTS, months=MONTHS, duration=DURATION)

# Stream function for the GPT API
@app.route("/stream", methods=["POST"])
@login_required
def stream():

    # Extract body content from the POST fetch request
    data = request.get_json()

    # Extract variables from body
    prompt = data.get("prompt")
    destination = data.get("destination")
    month = data.get("month")
    duration = data.get("duration")   

    # Prepare other variables for DB insert
    user_id = current_user.get_id()
    timestamp = datetime.utcnow().strftime("%m-%d-%Y, %H:%M:%S")

    # Define the stream function
    def event_stream():

        # Init a list for all the collected text
        collected_text = []

        # For every partial API response
        for line in send_prompt(prompt):

            # Extract text
            bad_text = line.choices[0].delta.get("content", "")

            # Convert text into HTML friendly
            text = bad_text.replace("\n", '<br>')

            # Append to list of collected text
            collected_text.append(text)

            # If text is not empty > yield
            if len(text):
                yield text

        # Collect full API response in a single string
        full_output = ''.join(collected_text)

        # Insert trip into DB
        try:
            with db.connect() as conn:
                stmt = sqlalchemy.text("INSERT INTO trips (user_id, generation_ts, destination, month, duration, travel_plan) VALUES (:id, :ts, :destination, :month, :duration, :travel_plan)")
                conn.execute(stmt, parameters={"id": user_id, "ts": timestamp, "destination": destination, "month": month, "duration": duration, "travel_plan": full_output})
                conn.commit()
        except:
            return apology("db insert error", 400)
        
    # Stream API response into current page
    return Response(event_stream(), mimetype="text/event-stream")

# View previously generated trips
@app.route("/history", methods=["GET", "POST"])
@login_required
def history():
    
    # User clicked on "View trip" button
    if request.method == "POST":

        # Load trip from DB
        stmt2 = sqlalchemy.text("SELECT * FROM trips WHERE trip_id = :id")
        trip_id = request.form.get("trip_id")
        try:
            with db.connect() as conn:
                ROWS = conn.execute(stmt2, parameters={"id": trip_id}).fetchall()
        except:
            return apology("db access error", 400)
        
        # Should return only 1 trip per each trip_id
        if len(ROWS) != 1:
            return apology("db internal error", 400)
        
        # Setup variables for output page
        destination = ROWS[0][3]
        OUTPUT = ROWS[0][6]

        # Load output page to display selected trip
        return render_template("output.html", your_destination=destination, output=OUTPUT)
    
    # User reached route via GET (as by clicking a link or via redirect) 
    else:

        # Query DB for current user's trips
        stmt2 = sqlalchemy.text("SELECT * FROM trips WHERE user_id = :id ORDER BY trip_id DESC")
        id = current_user.get_id()
        try:
            with db.connect() as conn:
                TRIPS = conn.execute(stmt2, parameters={"id": id}).fetchall()
        except:
            return apology("db access error", 400)

        # Return history page with list of trips (dicts)
        return render_template("/history.html", trips=TRIPS)

# Simple FAQ page
@app.route("/faq")
def faq():
    # Simple GET page
    return render_template("/faq.html")

# Simple Privacy Policy page
@app.route("/privacy")
def privacy():
    # Simple GET page
    return render_template("/privacy.html")

# Simple T&Cs page
@app.route("/terms")
def terms():
    # Simple GET page
    return render_template("/terms.html")