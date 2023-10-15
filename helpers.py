import re

from flask import render_template


# Render message as an apology to user
def apology(message, code=400):
    
    def escape(s):      
        # Escape special characters.
        # https://github.com/jacebrowning/memegen#special-characters
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    # Generate the apology page with text for the meme and error code
    return render_template("apology.html", top=code, bottom=escape(message)), code

# Checks input is a valid email format
def email_check(email):

    # Define regex for validating email
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    if re.match(regex, email):
        return True
    else:
        return False

# Checks input is a strong password
def password_check(password):

    """
    Verify the strength of 'password'
    Returns a dict indicating the wrong criteria
    A password is considered strong if:
        10 characters length or more
        1 digit or more
        1 symbol or more
        1 uppercase letter or more
        1 lowercase letter or more
    """

    # Calculating the length
    length_error = len(password) < 10

    # Searching for digits
    digit_error = re.search(r"\d", password) is None

    # Searching for uppercase
    uppercase_error = re.search(r"[A-Z]", password) is None

    # Searching for lowercase
    lowercase_error = re.search(r"[a-z]", password) is None

    # Searching for symbols
    symbol_error = re.search(r"\W", password) is None

    # Overall result
    password_ok = not ( length_error or digit_error or uppercase_error or lowercase_error or symbol_error )

    return {
        'password_ok' : password_ok,
        'length_error' : length_error,
        'digit_error' : digit_error,
        'uppercase_error' : uppercase_error,
        'lowercase_error' : lowercase_error,
        'symbol_error' : symbol_error,
    }