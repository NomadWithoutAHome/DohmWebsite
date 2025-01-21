from flask import Flask, send_from_directory
from utils.logging_config import app_logger as logger, set_debug_level
from routes.page_routes import pages
from routes.crx_routes import crx
from routes.shortener_routes import shortener
import mimetypes
# from routes.converter_routes import converter

# Add proper MIME types
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('application/wasm', '.wasm')

app = Flask(__name__)

# Configure logging
set_debug_level(debug=True)  # Set to False in production

# Register blueprints
app.register_blueprint(pages)
app.register_blueprint(crx)
app.register_blueprint(shortener)
#app.register_blueprint(converter)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True) 