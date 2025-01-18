# import logging
# from datetime import datetime
# from pathlib import Path

# def setup_logging():
#     """Setup logging to file"""
#     # Create logs directory if it doesn't exist
#     log_dir = Path(__file__).parent / "Logs"
#     log_dir.mkdir(exist_ok=True)
    
#     # Setup logging configuration
#     log_file = log_dir / "Editor.log"
#     logging.basicConfig(
#         level=logging.DEBUG,
#         format='%(asctime)s [%(levelname)s] %(message)s',
#         handlers=[
#             logging.FileHandler(log_file),
#             logging.StreamHandler()
#         ]
#     )
#     logging.info("="*50)
#     logging.info(f"Save Editor Started - {datetime.now()}")
#     logging.info("="*50)
#     return log_file

# def get_logger(name):
#     """Get a logger instance for a specific module"""
#     return logging.getLogger(name) 