from flask import Blueprint, request, jsonify, send_file
from io import BytesIO
from zipfile import ZipFile
from services.crx_service import (
    extract_extension_id, safe_download_crx, crx_to_zip,
    get_extension_name, get_file_metadata, is_binary_file,
    get_mime_type, get_language_from_filename
)
from utils.logging_config import crx_logger as logger

crx = Blueprint('crx', __name__)

@crx.route('/download-extension', methods=['POST'])
def download_extension():
    try:
        data = request.get_json()
        logger.debug(f"Download request data: {data}")
        
        extension_id = extract_extension_id(data.get('extension_id'))
        format = data.get('format', 'crx')
        
        if not extension_id:
            logger.error("Invalid extension ID provided")
            return 'Invalid extension ID', 400
            
        logger.debug(f"Downloading extension {extension_id} in {format} format")
        crx_content, error = safe_download_crx(extension_id)
        if error:
            logger.error(f"Error downloading CRX: {error}")
            return error, 400
            
        if format == 'zip':
            logger.debug("Converting CRX to ZIP")
            zip_content, error = crx_to_zip(crx_content)
            if error:
                logger.error(f"Error converting to ZIP: {error}")
                return error, 400
            content = zip_content
            mime_type = 'application/zip'
        else:
            content = crx_content
            mime_type = 'application/x-chrome-extension'
        
        # Get extension name for filename
        name = None
        if format == 'zip':
            name = get_extension_name(content)
            logger.debug(f"Got extension name: {name}")
        
        filename = f"{name or extension_id}.{format}"
        logger.info(f"Successfully prepared {filename} for download")
        
        return send_file(
            BytesIO(content),
            mimetype=mime_type,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Unexpected error in download_extension: {str(e)}", exc_info=True)
        return 'Internal server error', 500

@crx.route('/view-extension', methods=['POST'])
def view_extension():
    try:
        data = request.get_json()
        logger.debug(f"View request data: {data}")
        
        url_or_id = data.get('id')
        logger.debug(f"Extracting extension ID from: {url_or_id}")
        extension_id = extract_extension_id(url_or_id)
        filename = data.get('filename')
        offset = data.get('offset', 0)
        
        if not extension_id:
            logger.error("Invalid extension ID provided")
            return 'Invalid extension ID', 400
            
        # If no filename, return file list
        if not filename:
            logger.debug(f"Getting file list for extension {extension_id}")
            crx_content, error = safe_download_crx(extension_id)
            if error:
                logger.error(f"Error downloading CRX: {error}")
                return error, 400
                
            zip_content, error = crx_to_zip(crx_content)
            if error:
                logger.error(f"Error converting to ZIP: {error}")
                return error, 400
                
            with BytesIO(zip_content) as bio, ZipFile(bio) as z:
                files = [get_file_metadata(info) for info in z.filelist]
                logger.info(f"Found {len(files)} files in extension")
                return jsonify({'files': files})
        
        # If filename provided, return file content
        logger.debug(f"Getting content for file: {filename}")
        try:
            crx_content, error = safe_download_crx(extension_id)
            if error:
                logger.error(f"Error downloading CRX: {error}")
                return error, 400
                
            zip_content, error = crx_to_zip(crx_content)
            if error:
                logger.error(f"Error converting to ZIP: {error}")
                return error, 400
                
            with BytesIO(zip_content) as bio, ZipFile(bio) as z:
                with z.open(filename) as f:
                    content = f.read()
                    
                if is_binary_file(filename):
                    logger.debug(f"File {filename} is binary")
                    return jsonify({
                        'is_binary': True,
                        'mime_type': get_mime_type(filename)
                    })
                    
                # Handle text files
                text_content = content.decode('utf-8')
                if offset:
                    text_content = text_content[offset:]
                    
                logger.debug(f"Returning content for {filename} (offset: {offset})")
                return jsonify({
                    'is_binary': False,
                    'content': text_content,
                    'language': get_language_from_filename(filename),
                    'has_more': len(text_content) >= 50000,
                    'next_offset': offset + 50000 if len(text_content) >= 50000 else None
                })
        except Exception as e:
            logger.error(f"Error reading file {filename}: {str(e)}", exc_info=True)
            return str(e), 500
    except Exception as e:
        logger.error(f"Unexpected error in view_extension: {str(e)}", exc_info=True)
        return 'Internal server error', 500 