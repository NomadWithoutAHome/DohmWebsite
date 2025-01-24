from flask import Blueprint, request, jsonify, redirect, render_template, send_from_directory
from services.content_filter_service import ContentFilterService
from services.rate_limiter_service import RateLimiter
from utils.logging_config import app_logger as logger
from vercel_blob import VercelBlob
import os
import uuid
from datetime import datetime, timedelta

image_routes = Blueprint('image_routes', __name__)
content_filter = ContentFilterService()
rate_limiter = RateLimiter()

# Configure upload settings
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Vercel Blob Storage configuration
BLOB_READ_WRITE_TOKEN = os.getenv('BLOB_READ_WRITE_TOKEN', 'vercel_blob_rw_k15sVDOi4kFKp93Y_8LGewIV8N710hke0w2iVjug87VOv5r')

# Initialize Vercel Blob client
blob_client = VercelBlob(BLOB_READ_WRITE_TOKEN)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_extension(filename):
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def upload_to_vercel_blob(file_data, filename, content_type):
    """Upload file to Vercel Blob Storage"""
    try:
        if not BLOB_READ_WRITE_TOKEN:
            raise ValueError("BLOB_READ_WRITE_TOKEN environment variable is not set")
        
        logger.info(f"Uploading file {filename} to Vercel Blob Storage")
        
        # Upload file using the vercel_blob client
        result = blob_client.upload(
            file=file_data,
            filename=filename,
            content_type=content_type,
            access='public'
        )
        
        logger.info(f"Successfully uploaded {filename} to Vercel Blob Storage: {result.url}")
        return result.url
        
    except Exception as e:
        logger.error(f"Error uploading to Vercel Blob: {str(e)}", exc_info=True)
        raise ValueError("Failed to upload file to storage service")

@image_routes.route('/tools/image-uploader')
def image_uploader_page():
    """Render the image uploader documentation page."""
    return render_template('image_uploader.html')

@image_routes.route('/api/upload/image', methods=['POST'])
async def upload_image():
    """Handle image upload from ShareX or direct API calls."""
    try:
        # Get client IP
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # Check rate limit
        is_limited, reset_time = await rate_limiter.is_rate_limited(client_ip)
        if is_limited:
            remaining_time = reset_time if reset_time else 3600
            return jsonify({
                'error': 'Rate limit exceeded',
                'reset_in_seconds': remaining_time
            }), 429

        # Check if file was uploaded
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
            
        file = request.files['image']
        
        # Check if a file was selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        # Check file size
        if request.content_length > MAX_FILE_SIZE:
            return jsonify({'error': f'File size exceeds maximum limit of {MAX_FILE_SIZE // (1024 * 1024)}MB'}), 400
            
        # Check if file type is allowed
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
            
        # Generate unique filename
        extension = get_file_extension(file.filename)
        unique_filename = f"{uuid.uuid4().hex}.{extension}"
        
        # Upload to Vercel Blob Storage
        file_url = upload_to_vercel_blob(
            file.read(),
            unique_filename,
            file.content_type
        )
        
        # Get remaining requests
        remaining = rate_limiter.get_remaining_requests(client_ip)
        
        return jsonify({
            'status': 'success',
            'url': file_url,
            'remaining_requests': remaining
        })
        
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500 