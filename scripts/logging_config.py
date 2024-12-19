import logging
import os
from datetime import datetime


def setup_logging(script_name, level=logging.INFO):
    """
    Configures logging to output to both console and a log file in the /logs/ directory.
    Naming convention does not support parallel triggers!

    Args:
        script_name (str): The name of the script without extension.
        level (int): Logging verbosity level.

    Returns:
        None
    """
    # Determine the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..'))
    logs_dir= os.path.join(project_root, 'logs')

    # Ensure the 'logs' directory exists
    os.makedirs(logs_dir, exist_ok=True)

    # Get the current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Create the log filename
    log_filename = f"{timestamp}_{script_name}.log"
    log_file_path = os.path.join(logs_dir, log_filename)

    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler()
        ]
    )
