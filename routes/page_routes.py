from flask import Blueprint, render_template, send_from_directory, request
from utils.logging_config import app_logger as logger
import os
import requests
import json
from services.tracking_service import TrackingService

pages = Blueprint('pages', __name__)

def notify_indexnow():
    """Notify IndexNow about our URLs."""
    key = "fa4b4c68399845f58e77f242e4ae6e40"
    domain = "www.dohmboy64.com"
    
    payload = {
        "host": domain,
        "key": key,
        "keyLocation": f"https://{domain}/{key}.txt",
        "urlList": [
            f"https://{domain}/",
            f"https://{domain}/tools/chrome-downloader",
            f"https://{domain}/tools/url-shortener"
        ]
    }
    
    headers = {
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    try:
        logger.info(f"Sending IndexNow request with payload: {json.dumps(payload, indent=2)}")
        response = requests.post(
            'https://api.indexnow.org/IndexNow',
            headers=headers,
            json=payload
        )
        logger.info(f"IndexNow response status: {response.status_code}")
        logger.info(f"IndexNow response content: {response.text}")
        
        if response.status_code != 200:
            logger.error(f"IndexNow request failed with status {response.status_code}: {response.text}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Failed to notify IndexNow: {str(e)}", exc_info=True)
        return False

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

@pages.route('/fa4b4c68399845f58e77f242e4ae6e40.txt')
def verify():
    """Serve verification file from root URL."""
    return send_from_directory(os.path.dirname(os.path.dirname(__file__)), 'fa4b4c68399845f58e77f242e4ae6e40.txt')

@pages.route('/notify-indexnow', methods=['POST'])
def trigger_indexnow():
    """Trigger IndexNow notification."""
    success = notify_indexnow()
    return {'success': success}, 200 if success else 500

@pages.before_request
def track_page_visit():
    TrackingService.track_visitor(request, request.path) 