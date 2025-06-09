from flask import Blueprint, request, jsonify, render_template, send_file
from services.pdf_converter_service import PDFConverterService
from services.rate_limiter_service import RateLimiter
from utils.logging_config import app_logger as logger
import io

pdf_converter = Blueprint('pdf_converter', __name__)
rate_limiter = RateLimiter()

@pdf_converter.route('/converter')
def converter_page():
    """Render the PDF converter page"""
    return render_template('pdf_converter.html')

@pdf_converter.route('/convert', methods=['POST'])
async def convert_file():
    """Handle file conversion requests"""
    try:
        # Check rate limit
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        is_limited, reset_time = await rate_limiter.is_rate_limited(ip)
        if is_limited:
            return jsonify({
                'error': 'Rate limit exceeded',
                'reset_time': reset_time
            }), 429

        # Get file and target format
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        target_format = request.form.get('target_format', 'pdf')
        
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400
            
        # Read file data
        file_data = file.read()
        
        # Convert file
        result = await PDFConverterService.convert_file(
            file_data=file_data,
            filename=file.filename,
            target_format=target_format
        )
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in conversion route: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@pdf_converter.route('/download/<conversion_id>')
async def download_file(conversion_id):
    """Download converted file"""
    try:
        # Get converted file from Redis
        file_info = await PDFConverterService.get_converted_file(conversion_id)
        
        # Create file-like object from binary data
        file_obj = io.BytesIO(file_info['data'])
        
        # Determine content type
        content_type = 'application/pdf' if file_info['filename'].endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        
        return send_file(
            file_obj,
            mimetype=content_type,
            as_attachment=True,
            download_name=file_info['filename']
        )
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error in download route: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500 