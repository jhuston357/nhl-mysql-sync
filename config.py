import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'nhl_data'),
    'port': int(os.getenv('DB_PORT', '3306')),
}

# NHL API configuration
NHL_API_BASE_URL = 'https://api-web.nhle.com/v1'

# Data refresh settings (in seconds)
REFRESH_INTERVALS = {
    'teams': 86400,  # 24 hours
    'players': 86400,  # 24 hours
    'games': 3600,    # 1 hour
    'stats': 3600,    # 1 hour
}

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'nhl_sync.log')