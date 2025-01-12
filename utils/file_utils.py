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
    """Check if a file is a font file based on its extension."""
    font_extensions = {'ttf', 'woff', 'woff2', 'otf', 'eot'}
    return filename.split('.')[-1].lower() in font_extensions

def format_file_size(size):
    """Format file size with appropriate units."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size/1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size/1024/1024:.1f} MB"
    return f"{size/1024/1024/1024:.1f} GB"

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
        
    # Map common extensions to MIME types
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