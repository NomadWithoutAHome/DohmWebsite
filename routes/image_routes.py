from flask import Blueprint, request, jsonify, redirect, render_template
from services.content_filter_service import ContentFilterService
from services.rate_limiter_service import RateLimiter
from utils.logging_config import app_logger as logger
import os
import uuid
import requests
from datetime import datetime, timedelta

image_routes = Blueprint('image_routes', __name__)
content_filter = ContentFilterService()
rate_limiter = RateLimiter()

# Configure upload settings
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Vercel Blob Storage configuration
BLOB_API_URL = "https://blob.vercel-storage.com"
BLOB_READ_WRITE_TOKEN = os.getenv('BLOB_READ_WRITE_TOKEN')
BLOB_STORE_ID = os.getenv('BLOB_STORE_ID', 'store_k15sVDOi4kFKp93Y')  # Fallback to your store ID

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_extension(filename):
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def upload_to_vercel_blob(file_data, filename, content_type):
    """Upload file to Vercel Blob Storage"""
    try:
        if not BLOB_READ_WRITE_TOKEN:
            raise ValueError("BLOB_READ_WRITE_TOKEN environment variable is not set")

        # Get upload URL from Vercel Blob
        payload = {
            "pathname": filename,
            "contentType": content_type
        }
        headers = {
            "Authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}",
            "x-store-id": BLOB_STORE_ID
        }
        
        logger.info(f"Requesting upload URL for {filename} from Vercel Blob Storage")
        
        # Get upload URL
        response = requests.post(
            f"{BLOB_API_URL}/upload",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        upload_info = response.json()
        
        # Upload file to the provided URL
        upload_url = upload_info.get('uploadUrl')
        if not upload_url:
            raise ValueError("No upload URL provided by Vercel Blob API")
            
        logger.info(f"Uploading file {filename} to Vercel Blob Storage")
        
        # Upload the file
        files = {'file': (filename, file_data, content_type)}
        upload_response = requests.post(upload_url, files=files)
        upload_response.raise_for_status()
        
        # Get and validate the URL
        file_url = upload_info.get('url')
        if not file_url:
            raise ValueError("No file URL returned by Vercel Blob API")
            
        logger.info(f"Successfully uploaded {filename} to Vercel Blob Storage: {file_url}")
        return file_url
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error uploading to Vercel Blob: {str(e)}", exc_info=True)
        raise ValueError("Failed to upload file to storage service")
    except Exception as e:
        logger.error(f"Error uploading to Vercel Blob: {str(e)}", exc_info=True)
        raise

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

@image_routes.route('/i/<filename>')
def serve_image(filename):
    """Serve uploaded images."""
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        logger.error(f"Error serving image: {str(e)}")
        return 'Image not found', 404

@image_routes.route('/delete/<filename>')
def delete_image(filename):
    """Delete an uploaded image."""
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'status': 'success', 'message': 'Image deleted'})
        return jsonify({'error': 'Image not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 