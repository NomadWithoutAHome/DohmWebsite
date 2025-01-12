from flask import Flask, render_template, request, send_file, jsonify
import requests
import os
import zipfile
from io import BytesIO
import re
import struct
import json

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
        'png', 'jpg', 'jpeg', 'gif', 'ico', 'webp', 'bmp',  # Images
        'pdf', 'doc', 'docx',  # Documents
        'zip', 'rar', '7z',    # Archives
        'exe', 'dll',          # Executables
        'ttf', 'woff', 'woff2' # Fonts
    }
    return filename.split('.')[-1].lower() in binary_extensions

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
            
        return send_file(
            BytesIO(zip_content),
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{extension_id}.zip'
        )
    else:
        # Send as CRX
        return send_file(
            BytesIO(crx_content),
            mimetype='application/x-chrome-extension',
            as_attachment=True,
            download_name=f'{extension_id}.crx'
        )

@app.route('/view-extension', methods=['POST'])
def view_extension():
    try:
        data = request.get_json()
        url_or_id = data.get('extension_id')
        filename = data.get('filename')
        list_files = data.get('list_files', False)
        chunk_start = data.get('chunk_start', 0)  # Line number to start from
        chunk_size = data.get('chunk_size', 1000)  # Number of lines per chunk
        
        if not url_or_id:
            return jsonify({'error': 'Extension ID or URL is required'}), 400

        extension_id = extract_extension_id(url_or_id)
        if not extension_id:
            return jsonify({'error': 'Invalid extension ID or URL'}), 400

        crx_content, error = safe_download_crx(extension_id)
        if error:
            return jsonify({'error': error}), 400

        zip_content, error = crx_to_zip(crx_content)
        if error:
            return jsonify({'error': error}), 400
            
        try:
            with zipfile.ZipFile(BytesIO(zip_content)) as z:
                if list_files:
                    files = [f for f in z.namelist() if not f.endswith('/')]
                    def file_sort_key(f):
                        if f == 'manifest.json':
                            return (0, f)
                        is_binary = is_binary_file(f)
                        ext = f.split('.')[-1].lower()
                        type_order = {
                            'js': 1, 
                            'html': 2, 'htm': 2,
                            'css': 3
                        }
                        return (type_order.get(ext, 5 if is_binary else 4), f)
                    
                    files.sort(key=file_sort_key)
                    
                    # Get file sizes
                    file_sizes = {f: z.getinfo(f).file_size for f in files}
                    
                    manifest = z.read('manifest.json').decode('utf-8')
                    manifest_dict = json.loads(manifest)
                    formatted_manifest = json.dumps(manifest_dict, indent=2)
                    
                    return jsonify({
                        'files': files,
                        'source': formatted_manifest,
                        'file_types': {f: 'binary' if is_binary_file(f) else 'text' for f in files},
                        'file_sizes': file_sizes
                    })
                
                if filename:
                    if filename not in z.namelist():
                        return jsonify({'error': f'File {filename} not found'}), 404
                    
                    if is_binary_file(filename):
                        file_content = z.read(filename)
                        if filename.split('.')[-1].lower() in ['png', 'jpg', 'jpeg', 'gif', 'ico', 'webp', 'bmp']:
                            import base64
                            b64_content = base64.b64encode(file_content).decode()
                            return jsonify({
                                'source': f'<img src="data:image/{filename.split(".")[-1]};base64,{b64_content}" alt="{filename}" style="max-width: 100%; height: auto;">',
                                'is_binary': True,
                                'is_image': True
                            })
                        return jsonify({
                            'source': '[Binary file content not displayed]',
                            'is_binary': True,
                            'is_image': False
                        })
                    
                    # For text files, implement chunked reading
                    content = z.read(filename).decode('utf-8')
                    lines = content.splitlines()
                    total_lines = len(lines)
                    
                    # Calculate chunk information
                    start_line = max(0, min(chunk_start, total_lines))
                    end_line = min(start_line + chunk_size, total_lines)
                    chunk_content = '\n'.join(lines[start_line:end_line])
                    
                    # Format JSON if needed
                    if filename.endswith('.json') and chunk_start == 0:  # Only format if it's the first chunk
                        try:
                            content_dict = json.loads(chunk_content)
                            chunk_content = json.dumps(content_dict, indent=2)
                        except json.JSONDecodeError:
                            pass
                    
                    return jsonify({
                        'source': chunk_content,
                        'is_binary': False,
                        'total_lines': total_lines,
                        'current_chunk': {
                            'start': start_line,
                            'end': end_line,
                            'size': chunk_size
                        }
                    })
                
                manifest = z.read('manifest.json').decode('utf-8')
                manifest_dict = json.loads(manifest)
                formatted_manifest = json.dumps(manifest_dict, indent=2)
                return jsonify({
                    'source': formatted_manifest,
                    'is_binary': False
                })
                
        except Exception as e:
            return jsonify({'error': f'Failed to read file: {str(e)}'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 