import re
import base64
from utils.logging_config import source_logger as logger

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

def is_font_file(filename):
    """Check if file is a font file."""
    font_extensions = {'ttf', 'woff', 'woff2', 'otf', 'eot'}
    return filename.split('.')[-1].lower() in font_extensions

def get_generic_type(filename):
    """Get generic file type for categorization."""
    if filename == 'manifest.json':
        return ''  # Special case
    
    extension = filename.split('.')[-1].lower()
    
    # Code files
    if re.match(r'^(jsx?|tsx?|wat|coffee)$', extension):
        return 'code'
    
    # Image files
    if re.match(r'^(bmp|cur|gif|ico|jpe?g|png|psd|svg|tiff?|xcf|webp)$', extension):
        return 'images'
    
    # Markup files
    if re.match(r'^(css|sass|less|html?|xhtml|xml)$', extension):
        return 'markup'
    
    # Locales
    if filename.startswith('_locales/'):
        return 'locales'
    
    # Firefox specific
    if filename in ('chrome.manifest', 'install.rdf', 'package.json'):
        return ''
    
    if extension == 'jsm':
        return 'code'
    
    if extension in ('xbl', 'xul'):
        return 'markup'
    
    if re.match(r'locale\/.*\.(dtd|properties)$', filename, re.I):
        return 'locales'
    
    return 'misc'

def get_mime_type(filename):
    """Get MIME type for a file."""
    if re.match(r'^META-INF\/.*\.[ms]f$', filename):
        return 'text/plain'
        
    if re.match(r'(^|\/)(AUTHORS|CHANGELOG|COPYING|INSTALL|LICENSE|NEWS|README|THANKS)$', filename, re.I):
        return 'text/plain'
        
    extension = filename.split('.')[-1].lower()
    if extension in ('crx', 'nex', 'xpi'):
        return 'application/zip'
    if extension == 'md':
        return 'text/plain'
        
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

def format_file_size(size):
    """Format file size with appropriate units."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size/1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size/1024/1024:.1f} MB"
    return f"{size/1024/1024/1024:.1f} GB"

def get_file_metadata(zip_info):
    """Get enhanced file metadata."""
    return {
        'name': zip_info.filename,
        'size': zip_info.file_size,
        'size_formatted': format_file_size(zip_info.file_size),
        'compressed_size': zip_info.compress_size,
        'type': get_generic_type(zip_info.filename),
        'mime_type': get_mime_type(zip_info.filename),
        'is_binary': is_binary_file(zip_info.filename),
        'modified': zip_info.date_time
    }

def sort_files(files):
    """Sort files by type and name with proper categorization."""
    def get_sort_key(file):
        name = file['name']
        # Primary sort by file type
        if name == 'manifest.json':
            type_order = 0
        elif name.startswith('_locales/'):
            type_order = 1
        elif get_generic_type(name) == 'code':
            type_order = 2
        elif get_generic_type(name) == 'markup':
            type_order = 3
        elif get_generic_type(name) == 'images':
            type_order = 4
        else:
            type_order = 5
            
        # Secondary sort by directory depth
        depth = name.count('/')
        
        # Tertiary sort by name
        return (type_order, depth, name)
    
    return sorted(files, key=get_sort_key)

def process_binary_file(content, filename, mime_type):
    """Process binary file content (images, audio, fonts)."""
    logger.debug("Processing binary file: %s (%s)", filename, mime_type)
    
    content_type = mime_type
    data_url = f'data:{content_type};base64,{base64.b64encode(content).decode()}'
    
    response = {
        'content': data_url,
        'is_binary': True,
        'mime_type': mime_type,
        'type': get_generic_type(filename)
    }
    
    if mime_type.startswith('audio/'):
        response.update({
            'is_audio': True,
            'filename': filename,
            'custom_style': """
                audio::-webkit-media-controls-panel {
                    background-color: #1a1a1a;
                    border: 2px solid #f97316;
                }
                audio::-webkit-media-controls-current-time-display,
                audio::-webkit-media-controls-time-remaining-display {
                    color: #f97316;
                }
                audio::-webkit-media-controls-play-button,
                audio::-webkit-media-controls-mute-button {
                    filter: invert(60%) sepia(94%) saturate(3000%) hue-rotate(360deg);
                }
                audio::-webkit-media-controls-volume-slider,
                audio::-webkit-media-controls-timeline {
                    filter: hue-rotate(300deg) saturate(200%);
                }
            """
        })
    elif mime_type.startswith('image/'):
        response['is_image'] = True
    
    return response

def process_text_file(content, filename, chunk_start=0, chunk_size=500):
    """Process text file content with chunking support."""
    logger.debug("Processing text file: %s (chunk start: %d, size: %d)", 
                filename, chunk_start, chunk_size)
    
    try:
        text_content = content.decode('utf-8')
        lines = text_content.splitlines()
        total_lines = len(lines)
        end_line = min(chunk_start + chunk_size, total_lines)
        chunk_content = '\n'.join(lines[chunk_start:end_line])
        
        return {
            'content': chunk_content,
            'is_binary': False,
            'total_lines': total_lines,
            'mime_type': get_mime_type(filename),
            'type': get_generic_type(filename),
            'current_chunk': {
                'start': chunk_start,
                'end': end_line,
                'size': chunk_size
            }
        }
    except UnicodeDecodeError as e:
        logger.error("Failed to decode file content: %s", str(e))
        return None 