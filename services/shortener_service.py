import random
import string
import re
import os
from datetime import datetime, timedelta
from tinydb import TinyDB, Query
from utils.logging_config import app_logger as logger

# Initialize TinyDB with path relative to application root
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'urls.json')

def get_db():
    """Get database connection with context management."""
    try:
        db = TinyDB(db_path)
        return db
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}", exc_info=True)
        raise

def generate_random_path(length=6):
    """Generate a random path for shortened URLs."""
    characters = string.ascii_letters + string.digits
    with get_db() as db:
        urls = db.table('urls')
        URL = Query()
        while True:
            path = ''.join(random.choice(characters) for _ in range(length))
            if not urls.contains(URL.path == path):
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

def create_short_url(long_url, custom_path=None, expires_in_days=None):
    """Create a shortened URL."""
    if not is_valid_url(long_url):
        raise ValueError("Invalid URL format")

    with get_db() as db:
        urls = db.table('urls')
        URL = Query()

        if custom_path:
            if not is_valid_custom_path(custom_path):
                raise ValueError("Custom path can only contain letters, numbers, hyphens, and underscores")
            
            # Check for existing path case-insensitively
            if urls.contains(URL.path.test(lambda x: x.lower() == custom_path.lower())):
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
            urls.insert(url_doc)
            logger.info(f"Created short URL: {path} -> {long_url} (expires: {expires_at})")
            return path
        except Exception as e:
            logger.error(f"Error creating short URL: {str(e)}", exc_info=True)
            raise

def get_long_url(path):
    """Get the original URL from a shortened path."""
    with get_db() as db:
        urls = db.table('urls')
        URL = Query()
        
        try:
            # Clean up expired URLs
            cleanup_expired_urls()
            
            # Find URL document
            url_doc = urls.get(URL.path == path)
            if not url_doc:
                return None

            # Check if URL has expired
            if url_doc.get('expires_at'):
                expires_at = datetime.fromisoformat(url_doc['expires_at'])
                if datetime.utcnow() > expires_at:
                    urls.remove(URL.path == path)
                    logger.info(f"URL expired and removed: {path}")
                    return None

            # Update visit count
            urls.update({'visits': url_doc['visits'] + 1}, URL.path == path)
            logger.info(f"Redirecting {path} to {url_doc['long_url']} (visits: {url_doc['visits'] + 1})")
            return url_doc['long_url']
        except Exception as e:
            logger.error(f"Error retrieving URL: {str(e)}", exc_info=True)
            raise

def cleanup_expired_urls():
    """Remove expired URLs from the database."""
    with get_db() as db:
        urls = db.table('urls')
        URL = Query()
        
        try:
            now = datetime.utcnow()
            expired = urls.search(
                (URL.expires_at.exists()) & 
                (URL.expires_at != None) & 
                (URL.expires_at < now.isoformat())
            )
            for url in expired:
                urls.remove(doc_ids=[url.doc_id])
                logger.info(f"Cleaned up expired URL: {url['path']}")
        except Exception as e:
            logger.error(f"Error cleaning up expired URLs: {str(e)}", exc_info=True)
            raise 