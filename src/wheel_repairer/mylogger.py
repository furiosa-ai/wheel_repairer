import logging

# Global variable to store the logger
_logger = None

def setup_logger(name='wheel_repairer', level=logging.INFO):
    """Function to set up a logger with both file and console handlers."""
    global _logger
    
    if _logger is not None:
        return _logger  # Logger is already set up
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)  # Console logging level as per argument

    # Logger
    _logger = logging.getLogger(name)
    _logger.setLevel(logging.DEBUG)  # Set root logger to lowest level
    _logger.addHandler(console_handler)

    return _logger

def get_logger():
    """Function to get the logger instance."""
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger