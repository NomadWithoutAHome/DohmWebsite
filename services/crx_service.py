import requests
import re
import struct
import json
from io import BytesIO
from zipfile import ZipFile
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
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    
    params = {
        'response': 'redirect',
        'prodversion': '102.0.5005.61',
        'acceptformat': 'crx2,crx3',
        'x': f'id={extension_id}&installsource=ondemand&uc'
    }
    
    logger.debug(f"Downloading CRX for extension: {extension_id}")
    try:
        response = requests.get(
            'https://clients2.google.com/service/update2/crx',
            params=params,
            headers=headers,
            timeout=30
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
            except Exception as e:
                logger.error(f"Error reading manifest.json: {str(e)}")
                return None
    except Exception as e:
        logger.error(f"Error reading ZIP content: {str(e)}")
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