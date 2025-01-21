from flask import Blueprint, render_template, send_from_directory
from utils.logging_config import app_logger as logger
import os

pages = Blueprint('pages', __name__)

@pages.route('/')
def index():
    """Render the home page."""
    return render_template('index.html')

@pages.route('/tools/chrome-downloader')
def chrome_downloader():
    """Render the Chrome Extension Downloader page."""
    return render_template('tools.html')

@pages.route('/play')
def play():
    """Render the emulator page."""
    return render_template('emulator.html')

@pages.route('/robots.txt')
def robots():
    """Serve robots.txt from root URL."""
    return send_from_directory(os.path.dirname(os.path.dirname(__file__)), 'robots.txt')

@pages.route('/sitemap.xml')
def sitemap():
    """Serve sitemap.xml from root URL."""
    return send_from_directory(os.path.dirname(os.path.dirname(__file__)), 'sitemap.xml') 