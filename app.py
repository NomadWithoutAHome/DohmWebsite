from flask import Flask, request, jsonify, send_file
from io import BytesIO
from zipfile import ZipFile
from services.crx_service import extract_extension_id, safe_download_crx, crx_to_zip, get_extension_name
from utils.logging_config import app_logger as logger, set_debug_level
from routes.page_routes import pages
from routes.crx_routes import crx

app = Flask(__name__)

# Configure logging
set_debug_level(debug=True)  # Set to False in production

# Register blueprints
app.register_blueprint(pages)
app.register_blueprint(crx)

if __name__ == '__main__':
    app.run(debug=True) 