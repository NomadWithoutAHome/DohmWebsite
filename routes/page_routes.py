from flask import Blueprint, render_template
from utils.logging_config import app_logger as logger

pages = Blueprint('pages', __name__)

@pages.route('/')
def index():
    """Render the home page."""
    return render_template('index.html')

@pages.route('/tools')
def tools():
    """Render the tools page."""
    return render_template('tools.html')

@pages.route('/play')
def play():
    """Render the emulator page."""
    return render_template('emulator.html') 