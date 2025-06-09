from upstash_redis import Redis
import os
import json
import uuid
from datetime import datetime, timedelta
from utils.logging_config import app_logger as logger
from pdf2docx import Converter
from docx2pdf import convert as docx2pdf_convert
import base64

# Initialize Redis client
redis = Redis(
    url="https://proven-warthog-57623.upstash.io",
    token="AeEXAAIjcDExOWJiMzhkOTZkMTI0ODE4YjI5NWFhMzUyMDkxZTEwY3AxMA"
)

class PDFConverterService:
    @staticmethod
    async def convert_file(file_data, filename, target_format):
        """Convert file between PDF and DOCX formats using Redis for temporary storage"""
        try:
            # Generate unique ID for this conversion
            conversion_id = str(uuid.uuid4())
            
            # Store original file in Redis
            redis_key = f"pdf_converter:{conversion_id}"
            redis.setex(
                redis_key,
                3600,  # 1 hour expiration
                json.dumps({
                    'filename': filename,
                    'data': base64.b64encode(file_data).decode('utf-8'),
                    'target_format': target_format,
                    'created_at': datetime.utcnow().isoformat()
                })
            )
            
            # Perform conversion
            if filename.lower().endswith('.pdf') and target_format.lower() == 'docx':
                # PDF to DOCX conversion
                cv = Converter(file_data)
                output_data = cv.convert()
                cv.close()
            elif filename.lower().endswith('.docx') and target_format.lower() == 'pdf':
                # DOCX to PDF conversion
                output_data = docx2pdf_convert(file_data)
            else:
                raise ValueError("Unsupported file format or conversion direction")
            
            # Store converted file in Redis
            output_filename = f"converted_{os.path.splitext(filename)[0]}.{target_format.lower()}"
            output_key = f"pdf_converter:output:{conversion_id}"
            redis.setex(
                output_key,
                3600,  # 1 hour expiration
                json.dumps({
                    'filename': output_filename,
                    'data': base64.b64encode(output_data).decode('utf-8'),
                    'created_at': datetime.utcnow().isoformat()
                })
            )
            
            return {
                'conversion_id': conversion_id,
                'output_filename': output_filename
            }
            
        except Exception as e:
            logger.error(f"Error in file conversion: {str(e)}", exc_info=True)
            raise ValueError(f"Conversion failed: {str(e)}")
    
    @staticmethod
    async def get_converted_file(conversion_id):
        """Retrieve converted file from Redis"""
        try:
            output_key = f"pdf_converter:output:{conversion_id}"
            output_data = redis.get(output_key)
            
            if not output_data:
                raise ValueError("Converted file not found or has expired")
                
            file_info = json.loads(output_data)
            return {
                'filename': file_info['filename'],
                'data': base64.b64decode(file_info['data']),
                'created_at': file_info['created_at']
            }
            
        except Exception as e:
            logger.error(f"Error retrieving converted file: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to retrieve converted file: {str(e)}")
    
    @staticmethod
    async def cleanup_expired_files():
        """Clean up expired files from Redis"""
        try:
            # Redis automatically handles expiration, but we can add additional cleanup if needed
            pass
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}", exc_info=True) 