from flask import Blueprint, render_template

pages = Blueprint('pages', __name__)

@pages.route('/')
def index():
    """Render the home page."""
    return render_template('index.html')

@pages.route('/tools')
def tools():
    """Render the tools page."""
    return render_template('tools.html') 