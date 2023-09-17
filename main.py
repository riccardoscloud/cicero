import openai
import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session

from helpers import apology

# Setup OpenAI env
openai.api_key = os.environ.get("OPENAI_API_KEY")
openai.Model.list()

# Configure application
app = Flask(__name__)

# Configure CS50 Library to use SQLite database
#db = SQL("sqlite:///project.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    # Simple GET page, with content displayed conditionally of session
    return render_template("/index.html")


@app.route("/generate", methods=["GET", "POST"])
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