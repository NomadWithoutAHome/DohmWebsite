import os
import requests
from better_profanity import Profanity
from urllib.parse import urlparse
import re
import string

class ContentFilterService:
    def __init__(self):
        self.safe_browsing_api_key = os.getenv('GOOGLE_SAFE_BROWSING_API_KEY')
        self.safe_browsing_url = 'https://safebrowsing.googleapis.com/v4/threatMatches:find'
        
        self.profanity = Profanity()
        # Add common leetspeak replacements
        self.leetspeak_map = {
            '0': 'o', '1': 'i', '3': 'e', '4': 'a',
            '5': 's', '6': 'g', '7': 't', '@': 'a',
            '$': 's', '!': 'i', '+': 't'
        }
        # Initialize with custom wordlist
        self.custom_words = {
            'porn', 'xxx', 'sex', 'adult', 'nsfw',
            'nude', 'naked', 'pussy', 'dick', 'cock',
            'ass', 'boob', 'tit', 'cum', 'wank',
            'fap', 'masturbat', 'hentai', 'fuck',
            'shit', 'bitch', 'cunt', 'slut', 'whore'
        }
        # Add variations of the words (uppercase, leetspeak, etc.)
        self.initialize_word_variations()
        
    def initialize_word_variations(self):
        """Create variations of banned words including leetspeak and common obfuscations"""
        expanded_words = set()
        for word in self.custom_words:
            # Add the original word
            expanded_words.add(word)
            # Add uppercase variations
            expanded_words.add(word.upper())
            # Add variations with random uppercase letters
            expanded_words.update(self.get_case_variations(word))
            # Add leetspeak variations
            expanded_words.update(self.get_leetspeak_variations(word))
            # Add variations with repeated characters
            expanded_words.update(self.get_repeated_char_variations(word))
            
        self.profanity.load_censor_words(expanded_words)
        
    def get_case_variations(self, word):
        """Generate common case variations of a word"""
        variations = {
            word.capitalize(),
            word.upper(),
            word.lower(),
            ''.join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(word))
        }
        return variations
        
    def get_leetspeak_variations(self, word):
        """Generate leetspeak variations of a word"""
        variations = set()
        word_lower = word.lower()
        
        # Generate all possible leetspeak combinations
        def generate_leetspeak(current, pos):
            if pos == len(word_lower):
                variations.add(current)
                return
            
            char = word_lower[pos]
            # Add normal character
            generate_leetspeak(current + char, pos + 1)
            # Add leetspeak replacement if available
            for leet_char, normal_char in self.leetspeak_map.items():
                if char == normal_char:
                    generate_leetspeak(current + leet_char, pos + 1)
        
        generate_leetspeak("", 0)
        return variations
        
    def get_repeated_char_variations(self, word):
        """Generate variations with repeated characters"""
        variations = set()
        for i, char in enumerate(word):
            if char in 'aeiou':  # Only duplicate vowels
                variation = word[:i] + char * 2 + word[i+1:]
                variations.add(variation)
        return variations
        
    def normalize_text(self, text):
        """Normalize text by removing spaces and converting leetspeak"""
        if not text:
            return ""
        # Convert to lowercase and remove spaces
        text = text.lower().replace(" ", "")
        # Replace leetspeak characters
        for leet, normal in self.leetspeak_map.items():
            text = text.replace(leet, normal)
        return text
        
    def contains_inappropriate_content(self, text):
        """Check if text contains inappropriate content"""
        if not text:
            return False
            
        # Normalize the text
        normalized = self.normalize_text(text)
        
        # Check original text
        if self.profanity.contains_profanity(text):
            return True
            
        # Check normalized text
        if self.profanity.contains_profanity(normalized):
            return True
            
        # Check for substrings that contain banned words
        for word in self.custom_words:
            if word in normalized:
                return True
                
        return False
        
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
        return not self.contains_inappropriate_content(path)

    def is_content_safe(self, url, custom_path=None):
        """Check if the URL and custom path are safe"""
        # Check URL
        if self.contains_inappropriate_content(url):
            return False
            
        # Check custom path if provided
        if custom_path and self.contains_inappropriate_content(custom_path):
            return False
            
        return True 