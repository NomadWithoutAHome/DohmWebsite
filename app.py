from flask import Flask, render_template, request, send_file, jsonify
import requests
import os
import zipfile
from io import BytesIO
import re
import struct
import json
import base64
from zipfile import ZipFile

app = Flask(__name__)

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
    font_extensions = {'ttf', 'woff', 'woff2', 'otf', 'eot'}
    return filename.split('.')[-1].lower() in font_extensions

def get_extension_name(zip_content):
    """Extract extension name from manifest.json"""
    try:
        with BytesIO(zip_content) as zip_buffer, ZipFile(zip_buffer) as z:
            try:
                with z.open('manifest.json') as f:
                    manifest = json.loads(f.read().decode('utf-8'))
                    name = manifest.get('name', '').strip()
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

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/tools')
def tools():
    return render_template('tools.html')

@app.route('/download-crx', methods=['POST'])
def download_extension():
    url_or_id = request.form.get('extension_id')
    format_type = request.form.get('format', 'crx')
    
    if not url_or_id:
        return jsonify({'error': 'Extension ID or URL is required'}), 400
    
    extension_id = extract_extension_id(url_or_id)
    if not extension_id:
        return jsonify({'error': 'Invalid extension ID or URL'}), 400
    
    crx_content, error = safe_download_crx(extension_id)
    if error:
        return jsonify({'error': error}), 400
    
    if format_type == 'zip':
        # Convert CRX to ZIP
        zip_content, error = crx_to_zip(crx_content)
        if error:
            return jsonify({'error': error}), 400
        
        # Get extension name from manifest
        extension_name = get_extension_name(zip_content)
        filename = f"{extension_name}-{extension_id}.zip" if extension_name else f"{extension_id}.zip"
            
        return send_file(
            BytesIO(zip_content),
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
    else:
        # For CRX, also try to get the name
        zip_content, error = crx_to_zip(crx_content)
        extension_name = get_extension_name(zip_content) if not error else None
        filename = f"{extension_name}-{extension_id}.crx" if extension_name else f"{extension_id}.crx"
        
        return send_file(
            BytesIO(crx_content),
            mimetype='application/x-chrome-extension',
            as_attachment=True,
            download_name=filename
        )

@app.route('/view-extension', methods=['POST'])
def view_extension():
    try:
        data = request.get_json()
        url_or_id = data.get('extension_id')
        filename = data.get('filename')
        list_files = data.get('list_files', False)
        chunk_start = data.get('chunk_start', 0)
        chunk_size = data.get('chunk_size', 500)

        if not url_or_id:
            return jsonify({'error': 'No extension ID or URL provided'}), 400

        extension_id = extract_extension_id(url_or_id)
        if not extension_id:
            return jsonify({'error': 'Invalid extension ID or URL'}), 400

        crx_content, error = safe_download_crx(extension_id)
        if error:
            return jsonify({'error': error}), 400

        # Convert CRX to ZIP
        zip_content, error = crx_to_zip(crx_content)
        if error:
            return jsonify({'error': error}), 400

        with BytesIO(zip_content) as zip_buffer, ZipFile(zip_buffer) as z:
            if list_files:
                # Get enhanced metadata for all files
                files = [get_file_metadata(z.getinfo(f)) for f in z.namelist() if not f.endswith('/')]
                # Sort files using our new sorting function
                files = sort_files(files)
                return jsonify({'files': files}), 200

            if not filename:
                filename = 'manifest.json'

            try:
                with z.open(filename) as f:
                    content = f.read()
                    mime_type = get_mime_type(filename)
                    file_type = get_generic_type(filename)

                    if is_binary_file(filename):
                        # For binary files like images, fonts, etc.
                        content_type = mime_type
                        if mime_type.startswith('audio/'):
                            data_url = f'data:{content_type};base64,{base64.b64encode(content).decode()}'
                            return jsonify({
                                'content': data_url,
                                'is_binary': True,
                                'is_audio': True,
                                'mime_type': mime_type,
                                'type': file_type,
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
                            }), 200
                        else:
                            data_url = f'src="data:{content_type};base64,{base64.b64encode(content).decode()}"'
                            return jsonify({
                                'content': data_url,
                                'is_binary': True,
                                'is_image': mime_type.startswith('image/'),
                                'mime_type': mime_type,
                                'type': file_type
                            }), 200

                    # For text files
                    try:
                        content = content.decode('utf-8')
                    except UnicodeDecodeError:
                        return jsonify({'error': 'Failed to decode file content'}), 400

                    lines = content.splitlines()
                    total_lines = len(lines)
                    end_line = min(chunk_start + chunk_size, total_lines)
                    chunk_content = '\n'.join(lines[chunk_start:end_line])

                    if filename == 'manifest.json':
                        try:
                            parsed = json.loads(chunk_content)
                            chunk_content = json.dumps(parsed, indent=2)
                        except json.JSONDecodeError:
                            pass

                    return jsonify({
                        'content': chunk_content,
                        'is_binary': False,
                        'total_lines': total_lines,
                        'mime_type': mime_type,
                        'type': file_type,
                        'current_chunk': {
                            'start': chunk_start,
                            'end': end_line,
                            'size': chunk_size
                        }
                    }), 200

            except KeyError:
                return jsonify({'error': f'File not found: {filename}'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 