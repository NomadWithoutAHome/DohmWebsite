import os
import requests
from better_profanity import profanity
from urllib.parse import urlparse

class ContentFilterService:
    def __init__(self):
        self.safe_browsing_api_key = os.getenv('GOOGLE_SAFE_BROWSING_API_KEY')
        self.safe_browsing_url = 'https://safebrowsing.googleapis.com/v4/threatMatches:find'
        
        # Initialize profanity filter with custom words
        profanity.load_censor_words()
        # Add additional words specific to your needs
        custom_badwords = [
            # Add your custom bad words here
        ]
        profanity.add_censor_words(custom_badwords)

    def check_url_safety(self, url):
        """Check if URL is safe using Google Safe Browsing API"""
        if not self.safe_browsing_api_key:
            # If no API key, default to basic checks
            return self._basic_url_check(url)

        data = {
            'client': {
                'clientId': 'dohm-url-shortener',
                'clientVersion': '1.0.0'
            },
            'threatInfo': {
                'threatTypes': [
                    'MALWARE',
                    'SOCIAL_ENGINEERING',
                    'UNWANTED_SOFTWARE',
                    'POTENTIALLY_HARMFUL_APPLICATION'
                ],
                'platformTypes': ['ANY_PLATFORM'],
                'threatEntryTypes': ['URL'],
                'threatEntries': [{'url': url}]
            }
        }

        try:
            response = requests.post(
                f'{self.safe_browsing_url}?key={self.safe_browsing_api_key}',
                json=data
            )
            result = response.json()
            
            # If no matches found, the URL is safe
            return 'matches' not in result
        except Exception as e:
            print(f"Error checking URL safety: {e}")
            return False

    def _basic_url_check(self, url):
        """Basic URL check without API"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # List of known adult or malicious domains
        blocked_domains = [
            'porn', 'xxx', 'adult', 'sex',
            'malware', 'virus', 'hack',
            # Add more blocked domains as needed
        ]
        
        return not any(bad in domain for bad in blocked_domains)

    def check_custom_path(self, path):
        """Check if custom path contains inappropriate content"""
        return not profanity.contains_profanity(path)

    def is_content_safe(self, url, custom_path=None):
        """Check both URL and custom path for safety"""
        url_safe = self.check_url_safety(url)
        
        if not url_safe:
            return False
            
        if custom_path:
            path_safe = self.check_custom_path(custom_path)
            return path_safe
            
        return True 