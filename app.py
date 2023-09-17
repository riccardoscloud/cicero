import openai
import os
import json
import sqlite3
import requests

from flask import Flask, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from oauthlib.oauth2 import WebApplicationClient

from helpers import apology
from db import init_db_command
from user import User

# Setup Google client
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = ("https://accounts.google.com/.well-known/openid-configuration")

# Setup OpenAI env
openai.api_key = os.environ.get("OPENAI_API_KEY")
openai.Model.list()

# Configure application
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

# User session management setup
# https://flask-login.readthedocs.io/en/latest
login_manager = LoginManager()
login_manager.init_app(app)

# Database setup
try:
    init_db_command()
except sqlite3.OperationalError:
    # Assume it's already been created
    pass

# OAuth 2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


# Retrieve Google's provider configuration
def get_google_provider_cfg():
    try:
        return requests.get(GOOGLE_DISCOVERY_URL).json()
    except:
         return apology("google error", 400)

@app.route("/")
def index():
    # Simple GET page, with content displayed conditionally of session
    return render_template("/index.html")


@app.route("/login")
def login():
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


@app.route("/login/callback")
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
    
    # Create a user in the db with the information provided by Google
    user = User(
        id_=unique_id, name=users_name, email=users_email, profile_pic=picture
    )

    # Doesn't exist? Add it to the database.
    if not User.get(unique_id):
        User.create(unique_id, users_name, users_email, picture)

    # Begin user session by logging the user in
    login_user(user)

    # Send user back to homepage
    return redirect(url_for("index"))


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
def faq():
    # Simple GET page
    return render_template("/terms.html")