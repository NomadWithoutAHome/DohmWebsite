import re
import struct
import requests
import json
from io import BytesIO
from zipfile import ZipFile

def validate_crx(content):
    """Validate CRX file format and return version."""
    if len(content) < 16:
        return False, None, "CRX file too small"
    
    # Check magic number ('Cr24')
    if content[:4] != b'Cr24':
        return False, None, "Invalid CRX header: Not a valid CRX file"
    
    # Get CRX version (supported: 2 or 3)
    version = struct.unpack('<I', content[4:8])[0]
    if version not in (2, 3):
        return False, None, f"Unsupported CRX version: {version}"
    
    return True, version, None

def get_zip_offset(content, version):
    """Get the offset where the ZIP data starts based on CRX version."""
    if version == 2:
        # CRX2 format: header + public key length + signature length
        public_key_length = struct.unpack('<I', content[8:12])[0]
        signature_length = struct.unpack('<I', content[12:16])[0]
        return 16 + public_key_length + signature_length
    else:  # version == 3
        # CRX3 format: header + header length
        header_length = struct.unpack('<I', content[8:12])[0]
        return 12 + header_length

def crx_to_zip(crx_content):
    """Convert CRX to ZIP, handling both CRX2 and CRX3 formats."""
    try:
        is_valid, version, error = validate_crx(crx_content)
        if not is_valid:
            return None, error
        
        # Get ZIP start offset
        zip_offset = get_zip_offset(crx_content, version)
        
        # Extract ZIP content
        zip_content = crx_content[zip_offset:]
        
        # Verify ZIP header
        if not zip_content.startswith(b'PK\x03\x04'):
            return None, "Invalid ZIP data in CRX"
        
        return zip_content, None
    except Exception as e:
        return None, f"Error processing CRX: {str(e)}"

def extract_extension_id(url_or_id):
    """Extract extension ID from URL or return ID if valid."""
    # New Chrome Web Store URL pattern
    url_pattern = r'chromewebstore\.google\.com/detail/[^/]+/([a-z0-9]{32})'
    if match := re.search(url_pattern, url_or_id):
        return match.group(1)
    # If it's already just an ID (alphanumeric string), return it
    if re.match(r'^[a-z0-9]{32}$', url_or_id):
        return url_or_id
    return None

def safe_download_crx(extension_id):
    """Safely download and validate CRX file."""
    try:
        # Using the modern Chrome version to avoid 204 responses
        crx_url = f"https://clients2.google.com/service/update2/crx?response=redirect&acceptformat=crx2,crx3&prodversion=102.0.5005.61&x=id%3D{extension_id}%26installsource%3Dondemand%26uc"
        response = requests.get(crx_url)
        
        if response.status_code != 200:
            return None, f"Failed to download extension (Status: {response.status_code})"
        
        content = response.content
        is_valid, version, error = validate_crx(content)
        
        if not is_valid:
            return None, error
            
        return content, None
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def get_localized_message(z, message_name):
    """Get localized message from _locales directory."""
    try:
        # Try English first
        locales = ['en', 'en_US', 'en_GB']
        for locale in locales:
            try:
                with z.open(f'_locales/{locale}/messages.json') as f:
                    messages = json.loads(f.read().decode('utf-8'))
                    if message_name in messages:
                        return messages[message_name]['message']
            except:
                continue
                
        # If English not found, try any available locale
        for filename in z.namelist():
            if filename.startswith('_locales/') and filename.endswith('/messages.json'):
                with z.open(filename) as f:
                    messages = json.loads(f.read().decode('utf-8'))
                    if message_name in messages:
                        return messages[message_name]['message']
        return None
    except:
        return None

def get_extension_name(zip_content):
    """Extract extension name from manifest.json"""
    try:
        with BytesIO(zip_content) as zip_buffer, ZipFile(zip_buffer) as z:
            try:
                with z.open('manifest.json') as f:
                    manifest = json.loads(f.read().decode('utf-8'))
                    name = manifest.get('name', '').strip()
                    
                    # Check if name is a message placeholder
                    if name.startswith('__MSG_') and name.endswith('__'):
                        message_name = name[6:-2]  # Remove __MSG_ and __
                        localized_name = get_localized_message(z, message_name)
                        if localized_name:
                            name = localized_name
                    
                    # Remove special characters and spaces, keep alphanumeric and dashes
                    sanitized_name = re.sub(r'[^\w\-]', '-', name)
                    # Remove multiple consecutive dashes
                    sanitized_name = re.sub(r'-+', '-', sanitized_name)
                    # Remove leading/trailing dashes
                    sanitized_name = sanitized_name.strip('-')
                    return sanitized_name if sanitized_name else None
            except (KeyError, json.JSONDecodeError):
                return None
    except Exception:
        return None 