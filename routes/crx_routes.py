from flask import Blueprint, request, send_file, jsonify
from io import BytesIO
from zipfile import ZipFile
import base64

from services.crx_service import (
    extract_extension_id, safe_download_crx, crx_to_zip, 
    get_extension_name
)
from utils.file_utils import (
    is_binary_file, get_mime_type, get_generic_type,
    format_file_size
)

crx = Blueprint('crx', __name__)

@crx.route('/download-crx', methods=['POST'])
def download_crx():
    """Handle CRX download requests."""
    try:
        url_or_id = request.form.get('extension_id', '').strip()
        output_format = request.form.get('format', 'crx')
        
        extension_id = extract_extension_id(url_or_id)
        if not extension_id:
            return jsonify({'error': 'Invalid extension ID or URL'}), 400
            
        crx_content, error = safe_download_crx(extension_id)
        if error:
            return jsonify({'error': error}), 400
            
        if output_format == 'zip':
            zip_content, error = crx_to_zip(crx_content)
            if error:
                return jsonify({'error': error}), 400
            content = zip_content
            ext = 'zip'
        else:
            content = crx_content
            ext = 'crx'
            
        # Try to get extension name for filename
        name = None
        if output_format == 'zip':
            name = get_extension_name(content)
            
        filename = f"{name or extension_id}.{ext}"
        
        return send_file(
            BytesIO(content),
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@crx.route('/view-extension', methods=['POST'])
def view_extension():
    """Handle extension viewing requests."""
    try:
        data = request.get_json()
        extension_id = data.get('extension_id')
        
        if not extension_id:
            return jsonify({'error': 'Extension ID is required'}), 400
            
        # If list_files is True, return file list
        if data.get('list_files'):
            crx_content, error = safe_download_crx(extension_id)
            if error:
                return jsonify({'error': error}), 400
                
            zip_content, error = crx_to_zip(crx_content)
            if error:
                return jsonify({'error': error}), 400
                
            files = []
            with BytesIO(zip_content) as zip_buffer, ZipFile(zip_buffer) as z:
                for info in z.filelist:
                    if not info.filename.endswith('/'):  # Skip directories
                        files.append({
                            'name': info.filename,
                            'size': info.file_size,
                            'size_formatted': format_file_size(info.file_size),
                            'compress_size': info.compress_size,
                            'type': get_generic_type(info.filename),
                            'mime_type': get_mime_type(info.filename),
                            'is_binary': is_binary_file(info.filename),
                            'date_time': info.date_time
                        })
            return jsonify({'files': files})
            
        # Otherwise, return file content
        filename = data.get('filename')
        if not filename:
            return jsonify({'error': 'Filename is required'}), 400
            
        chunk_start = data.get('chunk_start', 0)
        chunk_size = min(data.get('chunk_size', 500), 1000)  # Limit chunk size
        
        crx_content, error = safe_download_crx(extension_id)
        if error:
            return jsonify({'error': error}), 400
            
        zip_content, error = crx_to_zip(crx_content)
        if error:
            return jsonify({'error': error}), 400
            
        with BytesIO(zip_content) as zip_buffer, ZipFile(zip_buffer) as z:
            try:
                info = z.getinfo(filename)
                content = z.read(filename)
                
                is_binary = is_binary_file(filename)
                mime_type = get_mime_type(filename)
                
                if is_binary:
                    if mime_type.startswith('image/'):
                        # For images, return base64 data URL
                        data_url = f"data:{mime_type};base64,{base64.b64encode(content).decode()}"
                        return jsonify({
                            'is_binary': True,
                            'is_image': True,
                            'content': data_url,
                            'mime_type': mime_type
                        })
                    elif mime_type.startswith('audio/'):
                        # For audio, return base64 data URL
                        data_url = f"data:{mime_type};base64,{base64.b64encode(content).decode()}"
                        return jsonify({
                            'is_binary': True,
                            'is_audio': True,
                            'content': data_url,
                            'mime_type': mime_type
                        })
                    else:
                        return jsonify({
                            'is_binary': True,
                            'error': 'Binary file cannot be displayed'
                        })
                
                # For text files, return the requested chunk
                try:
                    text_content = content.decode('utf-8')
                except UnicodeDecodeError:
                    return jsonify({'error': 'File encoding not supported'}), 400
                    
                lines = text_content.splitlines()
                total_lines = len(lines)
                
                end = min(chunk_start + chunk_size, total_lines)
                chunk = '\n'.join(lines[chunk_start:end])
                
                return jsonify({
                    'content': chunk,
                    'mime_type': mime_type,
                    'total_lines': total_lines,
                    'current_chunk': {
                        'start': chunk_start,
                        'end': end,
                        'size': chunk_size
                    }
                })
            except KeyError:
                return jsonify({'error': 'File not found in extension'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500 