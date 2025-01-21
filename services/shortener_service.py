import random
import string
import re
import os
import json
from datetime import datetime, timedelta
from utils.logging_config import app_logger as logger
from upstash_redis import Redis

# Initialize Redis client with credentials
redis = Redis(
    url="https://proven-warthog-57623.upstash.io",
    token="AeEXAAIjcDExOWJiMzhkOTZkMTI0ODE4YjI5NWFhMzUyMDkxZTEwY3AxMA"
)

def generate_random_path(length=6):
    """Generate a random path for shortened URLs."""
    characters = string.ascii_letters + string.digits
    while True:
        path = ''.join(random.choice(characters) for _ in range(length))
        # Check if path exists in Redis
        if not redis.get(f"url:{path}"):
            return path

def is_valid_custom_path(path):
    """Check if a custom path is valid."""
    # Only allow alphanumeric characters, hyphens, and underscores
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', path))

def is_valid_url(url):
    """Basic URL validation."""
    # Basic URL pattern matching
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

async def create_short_url(long_url, custom_path=None, expires_in_days=None):
    """Create a shortened URL."""
    if not is_valid_url(long_url):
        raise ValueError("Invalid URL format")

    if custom_path:
        if not is_valid_custom_path(custom_path):
            raise ValueError("Custom path can only contain letters, numbers, hyphens, and underscores")
        
        # Check for existing path case-insensitively
        existing_url = await redis.get(f"url:{custom_path.lower()}")
        if existing_url:
            raise ValueError(f"The custom path '{custom_path}' is already in use. Please choose a different one.")
        path = custom_path
    else:
        path = generate_random_path()

    # Calculate expiration date if provided
    expires_at = None
    if expires_in_days is not None:
        try:
            expires_in_days = int(expires_in_days)
            if expires_in_days < 0:
                raise ValueError("Expiration days must be positive")
            expires_at = (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()
        except ValueError as e:
            raise ValueError("Invalid expiration days") from e

    # Create URL document
    url_doc = {
        'path': path,
        'long_url': long_url,
        'created_at': datetime.utcnow().isoformat(),
        'expires_at': expires_at,
        'visits': 0
    }
    
    try:
        # Store in Redis with path as key
        key = f"url:{path.lower()}"
        await redis.set(key, json.dumps(url_doc))
        
        # Set expiration in Redis if specified
        if expires_at:
            expires_timestamp = datetime.fromisoformat(expires_at).timestamp()
            await redis.expireat(key, int(expires_timestamp))
            
        logger.info(f"Created short URL: {path} -> {long_url} (expires: {expires_at})")
        return path
    except Exception as e:
        logger.error(f"Error creating short URL: {str(e)}", exc_info=True)
        raise

async def get_long_url(path):
    """Get the original URL from a shortened path."""
    try:
        # Get URL document from Redis
        url_doc_str = await redis.get(f"url:{path.lower()}")
        if not url_doc_str:
            return None

        url_doc = json.loads(url_doc_str)

        # Check if URL has expired (Redis will automatically remove expired keys)
        if url_doc.get('expires_at'):
            expires_at = datetime.fromisoformat(url_doc['expires_at'])
            if datetime.utcnow() > expires_at:
                return None

        # Update visit count
        url_doc['visits'] += 1
        await redis.set(f"url:{path.lower()}", json.dumps(url_doc))
        
        logger.info(f"Redirecting {path} to {url_doc['long_url']} (visits: {url_doc['visits']})")
        return url_doc['long_url']
    except Exception as e:
        logger.error(f"Error retrieving URL: {str(e)}", exc_info=True)
        raise

async def cleanup_expired_urls():
    """
    Note: With Redis, we don't need manual cleanup as Redis automatically removes expired keys.
    This function is kept for compatibility but does nothing.
    """
    pass 