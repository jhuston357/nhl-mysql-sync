"""
Web interface for NHL MySQL Sync.
Provides a GUI for configuration, manual sync, and monitoring.
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO
from flask_wtf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-in-production')
csrf = CSRFProtect(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Initialize logger
logger = logging.getLogger('nhl_sync.web')
# Ensure logger is configured
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Import routes after app is created to avoid circular imports
from web import routes