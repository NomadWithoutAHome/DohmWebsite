from upstash_redis import Redis
import os
import json
import uuid
import tempfile
from datetime import datetime, timedelta
from utils.logging_config import app_logger as logger
from pdf2docx import Converter
from docx2pdf import convert as docx2pdf_convert
import base64
import time
import psutil
import subprocess
import shutil
import asyncio
from typing import Optional
from pathlib import Path

#pdf2docx==0.5.6
#docx2pdf==0.1.8

# Initialize Redis client
redis = Redis(
    url="https://proven-warthog-57623.upstash.io",
    token="AeEXAAIjcDExOWJiMzhkOTZkMTI0ODE4YjI5NWFhMzUyMDkxZTEwY3AxMA"
)

class PDFConverterService:
    @staticmethod
    def kill_word_processes():
        """Kill any running Word processes"""
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and 'WINWORD.EXE' in proc.info['name'].upper():
                    proc.kill()
        except Exception as e:
            logger.error(f"Error killing Word processes: {str(e)}", exc_info=True)

    @staticmethod
    async def cleanup_file(filepath: str, delay: int = 1):
        """Clean up file after a delay"""
        await asyncio.sleep(delay)
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except Exception as e:
            logger.error(f"Error cleaning up file {filepath}: {str(e)}", exc_info=True)

    @staticmethod
    async def convert_file(file_data, filename, target_format):
        """Convert file between PDF and DOCX formats using Redis for temporary storage"""
        temp_path = None
        output_path = None
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
            
            # Create a temporary file to store the upload
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
                temp_file.write(file_data)
                temp_path = temp_file.name
                logger.info(f"Created temporary file at: {temp_path}")

            # Create output filename and path
            output_filename = f"converted_{os.path.splitext(filename)[0]}.{target_format.lower()}"
            output_path = os.path.join(tempfile.gettempdir(), output_filename)
            logger.info(f"Output will be saved to: {output_path}")

            # Perform conversion
            if filename.lower().endswith('.pdf') and target_format.lower() == 'docx':
                # PDF to DOCX conversion using pdf2docx
                logger.info("Starting PDF to DOCX conversion using pdf2docx")
                try:
                    cv = Converter(temp_path)
                    cv.convert(output_path, start=0, end=None)
                    cv.close()
                    logger.info("PDF to DOCX conversion completed")
                except Exception as e:
                    logger.error(f"PDF to DOCX conversion failed: {str(e)}")
                    raise ValueError(f"PDF to DOCX conversion failed: {str(e)}")
                    
            elif filename.lower().endswith('.docx') and target_format.lower() == 'pdf':
                # DOCX to PDF conversion using docx2pdf
                logger.info("Starting DOCX to PDF conversion using docx2pdf")
                try:
                    docx2pdf_convert(temp_path, output_path)
                    logger.info("DOCX to PDF conversion completed")
                except Exception as e:
                    logger.error(f"DOCX to PDF conversion failed: {str(e)}")
                    raise ValueError(f"DOCX to PDF conversion failed: {str(e)}")
                    
            elif filename.lower().endswith(f'.{target_format.lower()}'):
                # If the file is already in the target format, just copy it
                logger.info("File already in target format, copying...")
                shutil.copy2(temp_path, output_path)
            else:
                raise ValueError("Unsupported file format or conversion direction.")

            # Verify the output file exists before sending
            if not os.path.exists(output_path):
                raise ValueError("Conversion failed - output file not found")
                
            if os.path.getsize(output_path) == 0:
                raise ValueError("Conversion failed - output file is empty")

            # Read converted file
            with open(output_path, 'rb') as f:
                output_data = f.read()
            
            # Store converted file in Redis
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
        finally:
            # Clean up temporary files
            try:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)
                if output_path and os.path.exists(output_path):
                    os.unlink(output_path)
            except Exception as e:
                logger.error(f"Error cleaning up temporary files: {str(e)}", exc_info=True)

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