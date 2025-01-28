import requests
import json
from datetime import datetime
from utils.logging_config import app_logger as logger
from services.shortener_service import redis

WEBHOOK_URL = "https://discord.com/api/webhooks/1333690401357299742/Fj1WLrs1r9oqq6pM3GR7U8hUA6ruwFXuxv7W4FhkIyt9MDg-pm6HC8jzXwGbUNKDiH1i"

class TrackingService:
    # Update path mapping to match exact routes
    PATH_NAMES = {
        '/': 'Home Page',
        '/tools/url-shortener': 'URL Shortener Tool',
        '/tools/chrome-downloader': 'Chrome Extension Downloader',
        '/tools/image-uploader': 'Image Uploader Tool',
        '/play': 'Emulator Page',
        '/bbs': 'BBS System',
        '/api/shorten': 'URL Shortener API',
        '/api/upload': 'Image Upload API',
        '/api/images/upload': 'Image Uploader API',
        'github': 'GitHub Profile',
        'linkedin': 'LinkedIn Profile',
        'twitter': 'Twitter Profile',
        'portfolio': 'Portfolio',
        'blog': 'Blog'
    }

    @staticmethod
    def get_friendly_path_name(path):
        """Convert raw paths to readable names"""
        return TrackingService.PATH_NAMES.get(path, path)

    @staticmethod
    def send_webhook(embed):
        try:
            payload = {"embeds": [embed]}
            response = requests.post(WEBHOOK_URL, json=payload)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send webhook: {str(e)}")

    @staticmethod
    def track_visitor(request, path):
        """Track new and returning visitors"""
        # Add debug logging
        logger.info(f"Tracking visit - Path: {path}, Referrer: {request.headers.get('Referer', 'Direct')}")
        
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', 'Unknown')
        referrer = request.headers.get('Referer', 'Direct')
        
        # Improved internal navigation detection with logging
        is_internal = False
        if referrer != 'Direct':
            is_internal = (
                referrer.startswith(request.host_url) or
                referrer.startswith('/') or
                'dohmboy64.com' in referrer or
                request.host in referrer
            )
            logger.info(f"Navigation type - Internal: {is_internal}, Referrer: {referrer}")
            
        navigation_type = "Internal Navigation" if is_internal else "External Visit"
        
        # Get friendly path name with logging
        friendly_path = TrackingService.get_friendly_path_name(path)
        logger.info(f"Path mapping - Raw: {path}, Friendly: {friendly_path}")
        
        # Check if this is an active session
        session_key = f"session:{ip}"
        is_active_session = redis.get(session_key)
        
        # Get visitor info from Redis
        visitor_key = f"visitor:{ip}"
        visitor_data = redis.get(visitor_key)
        
        # Get or update location data
        try:
            geo_response = requests.get(f"http://ip-api.com/json/{ip}")
            geo_data = geo_response.json()
            location = f"{geo_data.get('city', 'Unknown')}, {geo_data.get('country', 'Unknown')}"
        except:
            location = "Unknown"
        
        if visitor_data:
            # Returning visitor
            visitor = json.loads(visitor_data)
            previous_path = visitor.get('current_path')  # Store previous path before updating
            
            # Only increment visit count if this is a new session
            if not is_active_session:
                visitor['visit_count'] += 1
                # Set session key with 30 minute expiry
                redis.setex(session_key, 1800, 'active')
            
            visitor['last_visit'] = datetime.now().isoformat()
            visitor['paths'].append(friendly_path)
            visitor['location'] = location
            visitor['current_path'] = path  # Update current path
            
            # Send webhook for all page changes except refreshes
            if previous_path != path:
                embed = {
                    "title": f"🔄 {navigation_type}",
                    "color": 3447003,  # Blue
                    "fields": [
                        {"name": "IP Address", "value": ip, "inline": True},
                        {"name": "Location", "value": location, "inline": True},
                        {"name": "Visit Count", "value": str(visitor['visit_count']), "inline": True},
                        {"name": "Previous Page", "value": TrackingService.get_friendly_path_name(previous_path or 'None'), "inline": True},
                        {"name": "Current Page", "value": friendly_path, "inline": True},
                        {"name": "Referrer", "value": referrer, "inline": True},
                        {"name": "User Agent", "value": user_agent[:100], "inline": False}
                    ],
                    "timestamp": datetime.now().isoformat()
                }
                TrackingService.send_webhook(embed)
        else:
            # New visitor
            visitor = {
                'ip': ip,
                'first_visit': datetime.now().isoformat(),
                'last_visit': datetime.now().isoformat(),
                'visit_count': 1,
                'paths': [friendly_path],
                'current_path': path,
                'location': location
            }
            
            # Set initial session
            redis.setex(session_key, 1800, 'active')
            
            embed = {
                "title": "👋 New Visitor",
                "color": 5763719,  # Green
                "fields": [
                    {"name": "IP Address", "value": ip, "inline": True},
                    {"name": "Location", "value": location, "inline": True},
                    {"name": "First Page", "value": friendly_path, "inline": True},
                    {"name": "Navigation", "value": navigation_type, "inline": True},
                    {"name": "Referrer", "value": referrer, "inline": True},
                    {"name": "User Agent", "value": user_agent[:100], "inline": False}
                ],
                "timestamp": datetime.now().isoformat()
            }
            TrackingService.send_webhook(embed)
        
        # Store visitor data in Redis (24 hour expiry)
        redis.setex(visitor_key, 86400, json.dumps(visitor))

    @staticmethod
    def track_url_creation(request, short_path, long_url):
        """Track URL shortener usage"""
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        try:
            geo_response = requests.get(f"http://ip-api.com/json/{ip}")
            geo_data = geo_response.json()
            location = f"{geo_data.get('city', 'Unknown')}, {geo_data.get('country', 'Unknown')}"
        except:
            location = "Unknown"
            
        embed = {
            "title": "🔗 New Short URL Created",
            "color": 15105570,  # Orange
            "fields": [
                {"name": "Short Path", "value": short_path, "inline": True},
                {"name": "Creator IP", "value": ip, "inline": True},
                {"name": "Location", "value": location, "inline": True},
                {"name": "Original URL", "value": long_url[:1024], "inline": False}
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        TrackingService.send_webhook(embed)

    @staticmethod
    def track_outbound_click(request, destination, link_type):
        """Track when users click external links"""
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        referrer = request.headers.get('Referer', 'Direct')
        
        try:
            geo_response = requests.get(f"http://ip-api.com/json/{ip}")
            geo_data = geo_response.json()
            location = f"{geo_data.get('city', 'Unknown')}, {geo_data.get('country', 'Unknown')}"
        except:
            location = "Unknown"
            
        embed = {
            "title": "🔗 Outbound Click",
            "color": 10181046,  # Purple
            "fields": [
                {"name": "Link Type", "value": link_type, "inline": True},
                {"name": "Destination", "value": destination, "inline": True},
                {"name": "IP Address", "value": ip, "inline": True},
                {"name": "Location", "value": location, "inline": True},
                {"name": "From Page", "value": referrer, "inline": True}
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        TrackingService.send_webhook(embed) 