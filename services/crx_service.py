import requests
import re
import struct
import json
from io import BytesIO
from zipfile import ZipFile
from flask import send_file, make_response
from utils.logging_config import crx_logger as logger

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
            logger.error(f"Invalid CRX file: {error}")
            return None, error
        
        # Get ZIP start offset
        zip_offset = get_zip_offset(crx_content, version)
        logger.debug(f"ZIP data starts at offset: {zip_offset}")
        
        # Extract ZIP content
        zip_content = crx_content[zip_offset:]
        
        # Verify ZIP header
        if not zip_content.startswith(b'PK\x03\x04'):
            logger.error("Invalid ZIP header in CRX file")
            return None, "Invalid ZIP data in CRX"
        
        logger.debug(f"Successfully extracted ZIP content (size: {len(zip_content)} bytes)")
        return zip_content, None
    except Exception as e:
        logger.error(f"Error converting CRX to ZIP: {str(e)}", exc_info=True)
        return None, f"Error processing CRX: {str(e)}"

def extract_extension_id(url_or_id):
    """Extract extension ID from URL or return ID if valid."""
    logger.debug(f"Extracting extension ID from: {url_or_id}")
    if not url_or_id:
        return None
        
    # Clean the input
    url_or_id = url_or_id.strip()
    
    # New Chrome Web Store URL pattern
    url_pattern = r'chromewebstore\.google\.com/(?:detail|webstore/detail)/[^/]+/([a-z0-9]{32})'
    if match := re.search(url_pattern, url_or_id):
        return match.group(1)
    # If it's already just an ID (alphanumeric string), return it
    if re.match(r'^[a-z0-9]{32}$', url_or_id):
        return url_or_id
    return None

def safe_download_crx(extension_id):
    """Download CRX with proper headers and parameters."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    }
    
    # Use the working URL format and parameters
    url = f'https://clients2.google.com/service/update2/crx?response=redirect&acceptformat=crx2,crx3&prodversion=102.0.5005.61&x=id%3D{extension_id}%26installsource%3Dondemand%26uc'
    
    logger.debug(f"Downloading CRX for extension: {extension_id}")
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30,
            allow_redirects=True
        )
        
        logger.debug(f"Download response status: {response.status_code}")
        if response.status_code == 404:
            return None, 'Extension not found'
        if response.status_code == 401:
            return None, 'Extension access denied'
        if response.status_code != 200:
            return None, f'Failed to download (Status: {response.status_code})'
            
        content = response.content
        is_valid, version, error = validate_crx(content)
        
        if not is_valid:
            logger.error(f"Invalid CRX file: {error}")
            return None, error
            
        logger.info(f"Successfully downloaded CRX version {version}")
        return content, None
        
    except requests.exceptions.Timeout:
        logger.error("Download timed out")
        return None, 'Download timed out'
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error: {str(e)}")
        return None, f'Network error: {str(e)}'
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return None, f'Unexpected error: {str(e)}'

def get_extension_name(crx_content):
    """Extract extension name from manifest.json, handling localized names."""
    try:
        zip_content, error = crx_to_zip(crx_content)
        if not zip_content:
            logger.error(f"Failed to convert CRX to ZIP: {error}")
            return None
            
        with ZipFile(BytesIO(zip_content)) as zip_file:
            # Read manifest.json
            try:
                manifest = json.loads(zip_file.read('manifest.json').decode('utf-8'))
            except Exception as e:
                logger.error(f"Failed to read manifest.json: {e}")
                return None
                
            # Get name from manifest
            name = manifest.get('name', '')
            logger.debug(f"Raw name from manifest: {name}")
            
            # If name is not localized, return it directly
            if not name.startswith('__MSG_') or not name.endswith('__'):
                return name if name else None
                
            # Handle localized name
            locale_key = name[6:-2]  # Remove __MSG_ and __
            logger.debug(f"Found localized name key: {locale_key}")
            
            # Get default locale from manifest
            default_locale = manifest.get('default_locale', 'en')
            
            # Try multiple locales in order of preference
            locales_to_try = ['en', default_locale, 'en_US', 'en_GB']
            # Remove duplicates while preserving order
            locales_to_try = list(dict.fromkeys(locales_to_try))
            
            # Common message keys to try
            message_keys = [
                locale_key,  # Original key from manifest
                'extension_name',  # Common key
                'extensionName',   # Alternative format
                'app_name',        # For apps
                'appName',         # Alternative app format
                'name',           # Simple name
                'extName',        # Another common format
                locale_key.lower(),  # Lowercase version
                locale_key.upper(),  # Uppercase version
            ]
            
            # Try each locale with each message key
            for locale in locales_to_try:
                try:
                    locale_path = f'_locales/{locale}/messages.json'
                    logger.debug(f"Trying locale file: {locale_path}")
                    
                    try:
                        locale_data = json.loads(zip_file.read(locale_path).decode('utf-8'))
                    except:
                        continue
                    
                    # Try each message key in this locale
                    for key in message_keys:
                        if key in locale_data:
                            message = locale_data[key]
                            if isinstance(message, dict):
                                name = message.get('message', '')
                                if name:
                                    logger.debug(f"Found localized name using key '{key}' in locale '{locale}': {name}")
                                    return name
                                
                except Exception as e:
                    logger.debug(f"Error reading locale {locale}: {str(e)}")
                    continue
            
            # If we still haven't found a name, try searching all locales for any matching key
            try:
                for filename in zip_file.namelist():
                    if filename.startswith('_locales/') and filename.endswith('/messages.json'):
                        try:
                            locale_data = json.loads(zip_file.read(filename).decode('utf-8'))
                            for key in message_keys:
                                if key in locale_data:
                                    message = locale_data[key]
                                    if isinstance(message, dict):
                                        name = message.get('message', '')
                                        if name:
                                            logger.debug(f"Found name in {filename} using key '{key}': {name}")
                                            return name
                        except:
                            continue
            except Exception as e:
                logger.debug(f"Error searching all locales: {str(e)}")
            
            # If all else fails, return None
            logger.warning("Could not find localized name")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting extension name: {str(e)}", exc_info=True)
        return None

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

def is_binary_file(filename):
    """Check if a file is likely to be binary based on its extension."""
    binary_extensions = {
        # Images
        'png', 'jpg', 'jpeg', 'gif', 'bmp', 'ico', 'webp', 'svg',
        # Audio
        'mp3', 'wav', 'ogg', 'm4a',
        # Fonts
        'ttf', 'woff', 'woff2', 'otf', 'eot'
    }
    return filename.split('.')[-1].lower() in binary_extensions

def get_mime_type(filename):
    """Get MIME type for a file."""
    if re.match(r'^META-INF\/.*\.[ms]f$', filename):
        return 'text/plain'
        
    if re.match(r'(^|\/)(AUTHORS|CHANGELOG|COPYING|INSTALL|LICENSE|NEWS|README|THANKS)$', filename, re.I):
        return 'text/plain'
        
    extension = filename.split('.')[-1].lower()
    mime_types = {
        'js': 'application/javascript',
        'css': 'text/css',
        'html': 'text/html',
        'json': 'application/json',
        'txt': 'text/plain',
        'xml': 'text/xml',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'svg': 'image/svg+xml',
        'ttf': 'font/ttf',
        'woff': 'font/woff',
        'woff2': 'font/woff2',
        'otf': 'font/otf',
        'eot': 'application/vnd.ms-fontobject'
    }
    return mime_types.get(extension, 'application/octet-stream')

def get_language_from_filename(filename):
    """Get language for syntax highlighting based on file extension."""
    extension = filename.split('.')[-1].lower()
    language_map = {
        'js': 'javascript',
        'jsx': 'javascript',
        'ts': 'typescript',
        'tsx': 'typescript',
        'css': 'css',
        'scss': 'scss',
        'less': 'less',
        'html': 'html',
        'htm': 'html',
        'xml': 'xml',
        'json': 'json',
        'md': 'markdown',
        'py': 'python',
        'rb': 'ruby',
        'php': 'php',
        'java': 'java',
        'c': 'c',
        'cpp': 'cpp',
        'cs': 'csharp',
        'go': 'go',
        'rs': 'rust',
        'swift': 'swift',
        'kt': 'kotlin',
        'sh': 'bash',
        'yaml': 'yaml',
        'yml': 'yaml',
        'toml': 'toml',
        'ini': 'ini'
    }
    return language_map.get(extension, 'plaintext')

def get_file_metadata(zip_info):
    """Get enhanced file metadata."""
    filename = zip_info.filename
    size = zip_info.file_size
    
    # Format size for display
    if size < 1024:
        size_formatted = f"{size} B"
    elif size < 1024 * 1024:
        size_formatted = f"{size/1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        size_formatted = f"{size/1024/1024:.1f} MB"
    else:
        size_formatted = f"{size/1024/1024/1024:.1f} GB"
    
    # Get file type for categorization
    type = 'misc'
    if filename == 'manifest.json':
        type = 'manifest'
    elif filename.endswith(('.js', '.jsx', '.ts', '.tsx')):
        type = 'code'
    elif filename.endswith(('.html', '.htm', '.css', '.scss', '.less')):
        type = 'markup'
    elif filename.startswith('_locales/'):
        type = 'locales'
    elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico')):
        type = 'images'
    elif filename.endswith(('.mp3', '.wav', '.ogg', '.m4a')):
        type = 'audio'
    elif filename.endswith(('.ttf', '.woff', '.woff2', '.otf', '.eot')):
        type = 'font'
    
    return {
        'name': filename,
        'size': size,
        'size_formatted': size_formatted,
        'type': type
    } 

def download_extension(extension_id, format='crx'):
    """Download a Chrome extension and return it in the specified format."""
    try:
        crx_content, error = safe_download_crx(extension_id)
        if not crx_content:
            return error or "Failed to download extension", 404
            
        # Get extension name
        logger.debug("Attempting to extract extension name from manifest")
        extension_name = get_extension_name(crx_content)
        logger.debug(f"Extracted extension name: {extension_name}")
        
        # Create filename with extension name if available
        filename = f"{extension_name}-{extension_id}" if extension_name else extension_id
        logger.debug(f"Using filename: {filename}")
        
        if format == 'zip':
            zip_content, error = crx_to_zip(crx_content)
            if not zip_content:
                return error or "Failed to convert CRX to ZIP", 400
            content = zip_content
            mime_type = 'application/zip'
            filename = f"{filename}.zip"
        else:
            content = crx_content
            mime_type = 'application/x-chrome-extension'
            filename = f"{filename}.crx"
            
        logger.info(f"Successfully prepared {filename} for download")
            
        # Create response with file
        response = make_response(send_file(
            BytesIO(content),
            mimetype=mime_type,
            as_attachment=True,
            download_name=filename
        ))
        
        # Set Content-Disposition header with filename
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        logger.error(f"Error downloading extension: {e}")
        return str(e), 500 