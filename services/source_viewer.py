import re
import base64
import mimetypes
from zipfile import ZipFile
from io import BytesIO
from utils.logging_config import source_logger as logger

def is_binary_file(filename):
    """Check if a file is binary based on its extension."""
    binary_extensions = {
        # Images
        'bmp', 'gif', 'ico', 'jpeg', 'jpg', 'png', 'psd', 'svg', 'tiff', 'webp',
        # Audio
        'mp3', 'ogg', 'wav', 'm4a',
        # Fonts
        'ttf', 'otf', 'woff', 'woff2', 'eot',
        # Other binary
        'pdf', 'zip', 'crx', 'exe', 'dll', 'so', 'dylib'
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

def process_binary_file(zip_info, zip_file):
    """Process a binary file and return its content as base64."""
    content = zip_file.read(zip_info)
    mime_type = mimetypes.guess_type(zip_info.filename)[0] or 'application/octet-stream'
    return {
        'content': base64.b64encode(content).decode('utf-8'),
        'mime_type': mime_type,
        'is_binary': True
    }

def process_text_file(zip_info, zip_file, offset=0, chunk_size=50000):
    """Process a text file and return its content with line information."""
    content = zip_file.read(zip_info).decode('utf-8')
    lines = content.splitlines()
    total_lines = len(lines)
    
    # Calculate line range
    start_line = 1
    current_pos = 0
    
    # Find the starting line number based on offset
    while current_pos < offset and current_pos < len(content):
        if content[current_pos] == '\n':
            start_line += 1
        current_pos += 1
    
    # Find a good breaking point (end of function or block)
    chunk_end = offset + chunk_size
    if chunk_end < len(content):
        # Look ahead for a good breaking point
        look_ahead = min(1000, len(content) - chunk_end)  # Look ahead up to 1000 chars
        for i in range(chunk_end, chunk_end + look_ahead):
            char = content[i]
            # Break at end of block/function or empty line
            if char == '}' or (char == '\n' and (i + 1 >= len(content) or content[i + 1] == '\n')):
                chunk_end = i + 1
                break
    
    chunk = content[offset:chunk_end]
    
    # Count lines in the chunk
    end_line = start_line + chunk.count('\n')
    if chunk and chunk[-1] != '\n':
        end_line += 1  # Account for last line if it doesn't end with newline
    
    return {
        'content': chunk,
        'is_binary': False,
        'has_more': chunk_end < len(content),
        'next_offset': chunk_end,
        'language': get_language_from_filename(zip_info.filename),
        'total_lines': total_lines,
        'start_line': start_line,
        'end_line': end_line
    }

def get_language_from_filename(filename):
    """Get the language for syntax highlighting based on file extension."""
    ext = filename.split('.')[-1].lower()
    language_map = {
        'js': 'javascript',
        'jsx': 'javascript',
        'ts': 'typescript',
        'tsx': 'typescript',
        'json': 'json',
        'css': 'css',
        'scss': 'scss',
        'less': 'less',
        'html': 'markup',
        'htm': 'markup',
        'xml': 'markup',
        'svg': 'markup',
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
        'md': 'markdown',
        'txt': 'plaintext'
    }
    return language_map.get(ext, 'plaintext') 