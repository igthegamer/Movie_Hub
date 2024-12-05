from nextfix_app import app  # Import the Flask app instance from __init__.py
from server import *

if __name__ == '__main__':
    app.run(debug=True)
