# cicero

Wed deployment of the Cicero project on AWS Lightsail.

###### This is Cicero, your powerful new travel companion! Cicero knows a lot about the world, and he wants to help you make the most out of your next holiday.

###### Have you ever booked a trip to an awesome destination, visited some popular places… But then felt that, if only you spent some more time researching… You could’ve done and seen much more?

----------------------------------------------------------------------------------------------------------------------------

### Python - SQLite - HTML - CSS
#### Flask - Flask-login - SQLAlchemy - Google Fonts - Bootstrap - ChatGPT

This version currently includes:
- OpenAI API ("gpt-3.5-turbo") for content generation, using stream.
- Local SQLite database for storage of user accounts and created trips.
- Registering with email address and password.
- Login with Google
- Apology() function for custom error return.
- Checking user input: email format, password security.
- Storing user trips, presenting them on the history page.
- Account page: change username, change password.

TODO:
- Password reset
- Handle case where user logs in with Google and then tries with local login