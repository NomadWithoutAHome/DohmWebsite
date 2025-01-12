import logging
import sys

# Create loggers
app_logger = logging.getLogger('app')
crx_logger = logging.getLogger('crx')
source_logger = logging.getLogger('source')

def set_debug_level(debug=False):
    """Configure logging levels and handlers."""
    # Set log level
    level = logging.DEBUG if debug else logging.INFO
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    # Configure app logger
    app_logger.setLevel(level)
    app_logger.addHandler(console_handler)
    
    # Configure crx logger
    crx_logger.setLevel(level)
    crx_logger.addHandler(console_handler)
    
    # Configure source logger
    source_logger.setLevel(level)
    source_logger.addHandler(console_handler)
    
    # Prevent duplicate messages
    app_logger.propagate = False
    crx_logger.propagate = False
    source_logger.propagate = False 