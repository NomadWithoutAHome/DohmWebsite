from flask import Blueprint, request, jsonify, send_file
from io import BytesIO
from services.crx_service import (
    extract_extension_id, safe_download_crx, crx_to_zip,
    get_extension_name
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