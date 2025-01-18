# from flask import Blueprint, render_template, request, jsonify, send_file
# import os
# import tempfile
# import json
# from io import BytesIO
# from services.crypto_service import SaveCrypto
# from services.crypto_string_service import StringCrypto
# from utils.logging_config import app_logger as logger
# from utils.file_utils import serialize_json

# converter = Blueprint('converter', __name__)

# @converter.route('/convert')
# def convert_page():
#     """Render the save converter page."""
#     return render_template('converter.html')

# @converter.route('/convert/upload', methods=['POST'])
# def upload_save():
#     """Handle save file upload and decryption."""
#     if 'file' not in request.files:
#         return jsonify({'error': 'No file part'}), 400
    
#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({'error': 'No selected file'}), 400
        
#     if not file.filename.lower().endswith('.txt'):
#         return jsonify({'error': 'Only .txt files are allowed'}), 400

#     try:
#         # Create temporary file
#         temp_dir = tempfile.gettempdir()
#         temp_fd, temp_path = tempfile.mkstemp(dir=temp_dir)
#         os.close(temp_fd)
        
#         try:
#             # Save uploaded file to temp location
#             file.save(temp_path)
            
#             # Read the encrypted data
#             with open(temp_path, 'rb') as f:
#                 encrypted_data = f.read()
            
#             # Decrypt the save data
#             decrypted_json = SaveCrypto.decrypt(encrypted_data)
#             data = json.loads(decrypted_json)
#             return jsonify({'data': data})
                
#         finally:
#             # Clean up temp file
#             try:
#                 os.unlink(temp_path)
#             except Exception as e:
#                 logger.error(f"Error cleaning up temp file: {str(e)}")
    
#     except Exception as e:
#         logger.error(f"Error processing file: {str(e)}", exc_info=True)
#         return jsonify({'error': str(e)}), 500

# @converter.route('/convert/wsref/upload', methods=['POST'])
# def upload_wsref():
#     """Handle WSRef file upload and decryption."""
#     if 'file' not in request.files:
#         return jsonify({'error': 'No file part'}), 400
    
#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({'error': 'No selected file'}), 400
        
#     if not file.filename.lower().endswith('.assets'):
#         return jsonify({'error': 'Only .assets files are allowed'}), 400

#     try:
#         # Create temporary file
#         temp_dir = tempfile.gettempdir()
#         temp_fd, temp_path = tempfile.mkstemp(dir=temp_dir)
#         os.close(temp_fd)
        
#         try:
#             # Save uploaded file to temp location
#             file.save(temp_path)
            
#             # Extract and decrypt the WSRef data
#             data = SaveCrypto.extract_refdata(temp_path)
#             return jsonify({'data': data})
                
#         finally:
#             # Clean up temp file
#             try:
#                 os.unlink(temp_path)
#             except Exception as e:
#                 logger.error(f"Error cleaning up temp file: {str(e)}")
    
#     except Exception as e:
#         logger.error(f"Error processing WSRef file: {str(e)}", exc_info=True)
#         return jsonify({'error': str(e)}), 500

# @converter.route('/convert/wsdir/upload', methods=['POST'])
# def upload_wsdir():
#     """Handle WSDir file upload and decryption."""
#     if 'file' not in request.files:
#         return jsonify({'error': 'No file part'}), 400
    
#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({'error': 'No selected file'}), 400
        
#     if not file.filename.lower().endswith('.txt'):
#         return jsonify({'error': 'Only .txt files are allowed'}), 400

#     try:
#         # Create temporary file
#         temp_dir = tempfile.gettempdir()
#         temp_fd, temp_path = tempfile.mkstemp(dir=temp_dir)
#         os.close(temp_fd)
        
#         try:
#             # Save uploaded file to temp location
#             file.save(temp_path)
            
#             # Load and decrypt the WSDir data using StringCrypto
#             data = StringCrypto.load_wsdir(temp_path)
#             return jsonify({'data': data})
                
#         finally:
#             # Clean up temp file
#             try:
#                 os.unlink(temp_path)
#             except Exception as e:
#                 logger.error(f"Error cleaning up temp file: {str(e)}")
    
#     except Exception as e:
#         logger.error(f"Error processing WSDir file: {str(e)}", exc_info=True)
#         return jsonify({'error': str(e)}), 500

# @converter.route('/convert/wsdir/save', methods=['POST'])
# def save_wsdir():
#     """Handle WSDir file saving."""
#     try:
#         data = request.json.get('data')
#         filename = request.json.get('filename', 'WSDir.txt')
        
#         if not data:
#             return jsonify({'error': 'No data provided'}), 400
            
#         # Create temporary file
#         temp_dir = tempfile.gettempdir()
#         temp_fd, temp_path = tempfile.mkstemp(dir=temp_dir)
#         os.close(temp_fd)
        
#         try:
#             # Save the WSDir data using StringCrypto
#             StringCrypto.save_wsdir(data, temp_path)
            
#             # Send the file
#             return send_file(
#                 temp_path,
#                 as_attachment=True,
#                 download_name=filename,
#                 mimetype='application/octet-stream'
#             )
            
#         finally:
#             # Clean up temp file
#             try:
#                 os.unlink(temp_path)
#             except Exception as e:
#                 logger.error(f"Error cleaning up temp file: {str(e)}")
            
#     except Exception as e:
#         logger.error(f"Error saving WSDir file: {str(e)}", exc_info=True)
#         return jsonify({'error': str(e)}), 500

# @converter.route('/convert/save', methods=['POST'])
# def save_file():
#     """Handle save file encryption and download."""
#     try:
#         data = request.json.get('data')
#         filename = request.json.get('filename', 'save.txt')
        
#         if not data:
#             return jsonify({'error': 'No data provided'}), 400
            
#         # Create temporary file
#         temp_dir = tempfile.gettempdir()
#         temp_fd, temp_path = tempfile.mkstemp(dir=temp_dir)
#         os.close(temp_fd)
        
#         try:
#             # Convert data to JSON string
#             json_str = serialize_json(data)
            
#             # Encrypt the data
#             encrypted_data = SaveCrypto.encrypt(json_str)
            
#             # Write encrypted data to temp file
#             with open(temp_path, 'wb') as f:
#                 f.write(encrypted_data)
            
#             # Send the file
#             return send_file(
#                 temp_path,
#                 as_attachment=True,
#                 download_name=filename,
#                 mimetype='application/octet-stream'
#             )
            
#         finally:
#             # Clean up temp file
#             try:
#                 os.unlink(temp_path)
#             except Exception as e:
#                 logger.error(f"Error cleaning up temp file: {str(e)}")
            
#     except Exception as e:
#         logger.error(f"Error saving file: {str(e)}", exc_info=True)
#         return jsonify({'error': str(e)}), 500 