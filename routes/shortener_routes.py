from flask import Blueprint, render_template, request, jsonify, redirect
from services.shortener_service import create_short_url, get_long_url
from services.content_filter_service import ContentFilterService
from services.rate_limiter_service import RateLimiter
from utils.logging_config import app_logger as logger
from urllib.parse import urlparse
import re
from datetime import datetime
from functools import lru_cache
from services.tracking_service import TrackingService

shortener = Blueprint('shortener', __name__)
content_filter = ContentFilterService()
rate_limiter = RateLimiter()

# Add more detailed error responses
ERROR_MESSAGES = {
    'invalid_url': {'error': 'Invalid URL format', 'code': 100},
    'invalid_path': {'error': 'Invalid custom path', 'code': 101},
    'rate_limit': {'error': 'Rate limit exceeded', 'code': 429},
    'unsafe_content': {'error': 'Content violation', 'code': 403}
}

@shortener.route('/tools/url-shortener')
def url_shortener_page():
    """Render the URL shortener page."""
    return render_template('url_shortener.html')

@shortener.route('/api/shorten', methods=['POST'])
async def shorten_url():
    """Create a shortened URL."""
    try:
        # Get client IP
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # Check rate limit
        is_limited, reset_time = await rate_limiter.is_rate_limited(client_ip)
        if is_limited:
            remaining_time = reset_time if reset_time else 3600
            return jsonify({
                'error': 'Rate limit exceeded',
                'reset_in_seconds': remaining_time,
                'message': f'Please try again in {remaining_time//60} minutes'
            }), 429

        data = request.get_json()
        long_url = data.get('url')
        custom_path = data.get('custom_path')
        expires_in_days = data.get('expires_in_days')
        
        # Check if URL is provided before doing content check
        if not long_url or not long_url.strip():
            return jsonify({'error': 'URL is required'}), 400
            
        # Validate URL format
        if not urlparse(long_url).scheme:
            return jsonify(ERROR_MESSAGES['invalid_url']), 400

        # Validate custom path format
        if custom_path and not re.match(r'^[a-zA-Z0-9_-]{3,20}$', custom_path):
            return jsonify(ERROR_MESSAGES['invalid_path']), 400
            
        # Now check content safety
        if not content_filter.is_content_safe(long_url, custom_path):
            return jsonify(ERROR_MESSAGES['unsafe_content']), 403
            
        short_url = create_short_url(long_url, custom_path, expires_in_days)
        
        # Add tracking
        TrackingService.track_url_creation(request, short_url, long_url)
        
        # Get remaining requests
        remaining = rate_limiter.get_remaining_requests(client_ip)
        
        return jsonify({
            'short_url': short_url,
            'remaining_requests': remaining
        })
        
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
            # Log the click
            logger.info(f"Redirect: {path} => {long_url}")
            # Add analytics recording here
            return redirect(long_url)
        return 'URL not found', 404
    except Exception as e:
        logger.error(f"Redirect error: {str(e)}")
        return 'Error redirecting', 500

@shortener.route('/api/check-content', methods=['POST'])
def check_content():
    """Check if the URL and custom path are safe"""
    data = request.get_json()
    url = data.get('url')
    custom_path = data.get('custom_path')

    if not url:
        return jsonify({'error': 'URL is required', 'is_safe': False}), 400

    is_safe, reason = content_filter.is_content_safe(url, custom_path)
    return jsonify({'is_safe': is_safe, 'reason': reason})

@shortener.route('/api/preview/<path>')
def url_preview(path):
    long_url = get_long_url(path)
    if long_url:
        return jsonify({
            'long_url': long_url,
            'safe': content_filter.is_content_safe(long_url)
        })
    return jsonify({'error': 'Not found'}), 404

@lru_cache(maxsize=1024)
def get_long_url(path):
    """Retrieve long URL from storage with caching"""
    try:
        # Example implementation - replace with your actual data source access
        from services.shortener_service import get_long_url as service_get_long_url
        return service_get_long_url(path)
    except Exception as e:
        logger.error(f"Error retrieving URL for path {path}: {str(e)}")
        return None 