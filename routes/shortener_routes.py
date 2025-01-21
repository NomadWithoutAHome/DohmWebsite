from flask import Blueprint, render_template, request, jsonify, redirect
from services.shortener_service import create_short_url, get_long_url
from utils.logging_config import app_logger as logger

shortener = Blueprint('shortener', __name__)

@shortener.route('/tools/url-shortener')
def url_shortener_page():
    """Render the URL shortener page."""
    return render_template('url_shortener.html')

@shortener.route('/api/shorten', methods=['POST'])
def shorten_url():
    """Create a shortened URL."""
    try:
        data = request.get_json()
        long_url = data.get('url')
        custom_path = data.get('custom_path')
        expires_in_days = data.get('expires_in_days')
        
        if not long_url:
            return jsonify({'error': 'URL is required'}), 400
            
        short_url = create_short_url(long_url, custom_path, expires_in_days)
        return jsonify({'short_url': short_url})
        
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error shortening URL: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@shortener.route('/<path>')
def redirect_to_url(path):
    """Redirect short URL to original URL."""
    try:
        long_url = get_long_url(path)
        if long_url:
            return redirect(long_url)
        return 'URL not found or has expired', 404
        
    except Exception as e:
        logger.error(f"Error redirecting URL: {str(e)}", exc_info=True)
        return 'Error redirecting URL', 500 