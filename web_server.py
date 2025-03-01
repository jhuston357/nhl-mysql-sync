#!/usr/bin/env python3
"""
Web server for NHL MySQL Sync.
Provides a GUI for configuration, manual sync, and monitoring.
"""

import os
import argparse
import logging
from web import app, socketio

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='NHL MySQL Sync Web Server')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to bind the server to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=54704,
                        help='Port to bind the server to (default: 54704)')
    parser.add_argument('--debug', action='store_true',
                        help='Run in debug mode')
    return parser.parse_args()

def setup_jinja_filters():
    """Set up custom Jinja2 filters."""
    @app.template_filter('now')
    def _jinja2_filter_now(fmt='%Y'):
        """Return the current year or formatted date."""
        from datetime import datetime
        if fmt == 'year':
            return datetime.now().year
        return datetime.now().strftime(fmt)

def main():
    """Main entry point for the web server."""
    args = parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set up Jinja2 filters
    setup_jinja_filters()
    
    # Print startup message
    print(f"NHL MySQL Sync Web Server starting on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop the server")
    
    # Start the server with CORS support
    from flask_cors import CORS
    CORS(app)
    socketio.run(app, host=args.host, port=args.port, debug=args.debug, allow_unsafe_werkzeug=True)

if __name__ == "__main__":
    main()