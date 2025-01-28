import requests
import json
from datetime import datetime
from utils.logging_config import app_logger as logger
from services.shortener_service import redis

WEBHOOK_URL = "https://discord.com/api/webhooks/1333690401357299742/Fj1WLrs1r9oqq6pM3GR7U8hUA6ruwFXuxv7W4FhkIyt9MDg-pm6HC8jzXwGbUNKDiH1i"

class TrackingService:
    # Add path mapping
    PATH_NAMES = {
        '/': 'Home Page',
        '/tools/url-shortener': 'URL Shortener Tool',
        '/tools/chrome-downloader': 'Chrome Extension Downloader',
        '/play': 'Emulator Page',
        '/bbs': 'BBS System'
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
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', 'Unknown')
        referrer = request.headers.get('Referer', 'Direct')
        
        # Determine if navigation is internal or external
        is_internal = referrer.startswith(request.host_url) if referrer != 'Direct' else False
        navigation_type = "Internal Navigation" if is_internal else "External Visit"
        
        # Get friendly path name
        friendly_path = TrackingService.get_friendly_path_name(path)
        
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
            visitor['visit_count'] += 1
            visitor['last_visit'] = datetime.now().isoformat()
            visitor['paths'].append(friendly_path)
            visitor['location'] = location  # Update location
            
            # Only send webhook for page changes
            if visitor.get('current_path') != path:
                embed = {
                    "title": f"🔄 {navigation_type}",
                    "color": 3447003,  # Blue
                    "fields": [
                        {"name": "IP Address", "value": ip, "inline": True},
                        {"name": "Location", "value": location, "inline": True},
                        {"name": "Visit Count", "value": str(visitor['visit_count']), "inline": True},
                        {"name": "Previous Page", "value": TrackingService.get_friendly_path_name(visitor.get('current_path', 'None')), "inline": True},
                        {"name": "Current Page", "value": friendly_path, "inline": True},
                        {"name": "Referrer", "value": referrer, "inline": True},
                        {"name": "User Agent", "value": user_agent[:100], "inline": False}
                    ],
                    "timestamp": datetime.now().isoformat()
                }
                TrackingService.send_webhook(embed)
            
            visitor['current_path'] = path
            
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