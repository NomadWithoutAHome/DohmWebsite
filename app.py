from flask import Flask
from utils.logging_config import app_logger as logger, set_debug_level
from routes.page_routes import pages
from routes.crx_routes import crx
from routes.converter_routes import converter

app = Flask(__name__)

# Configure logging
set_debug_level(debug=True)  # Set to False in production

# Register blueprints
app.register_blueprint(pages)
app.register_blueprint(crx)
app.register_blueprint(converter)

if __name__ == '__main__':
    app.run(debug=True) 