#!/usr/bin/env python3
"""
NHL MySQL Sync - Main application file
Fetches data from the NHL API and synchronizes it with a MySQL database.
"""

import argparse
import logging
import time
import schedule
import sys
import threading
from datetime import datetime

from config import DB_CONFIG, NHL_API_BASE_URL, REFRESH_INTERVALS, LOG_LEVEL, LOG_FILE
from lib.database import DatabaseManager
from lib.nhl_api import NHLApiClient
from lib.sync_manager import SyncManager

def setup_logging():
    """Configure logging for the application."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=log_format,
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger('nhl_sync')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='NHL MySQL Sync - Synchronize NHL data with MySQL database')
    parser.add_argument('--init', action='store_true', help='Initialize the database schema')
    parser.add_argument('--sync', choices=['teams', 'players', 'games', 'stats', 'all'], 
                        default='all', help='Specify which data to synchronize')
    parser.add_argument('--season', type=str, help='Specify season (format: YYYYYYYY, e.g., 20222023)')
    parser.add_argument('--daemon', action='store_true', help='Run as a daemon with scheduled updates')
    parser.add_argument('--web', action='store_true', help='Start the web interface')
    parser.add_argument('--port', type=int, default=7443, help='Port for the web interface (default: 7443)')
    return parser.parse_args()

def start_web_server(port):
    """Start the web interface in a separate thread."""
    from web_server import main as web_main
    
    # Create a thread for the web server
    web_thread = threading.Thread(
        target=lambda: sys.argv.extend(['--port', str(port)]) or web_main(),
        daemon=True
    )
    web_thread.start()
    
    print(f"Web interface started on http://localhost:{port}")
    return web_thread

def main():
    """Main application entry point."""
    args = parse_args()
    logger = setup_logging()
    
    logger.info("Starting NHL MySQL Sync")
    
    # Start web interface if requested
    if args.web:
        web_thread = start_web_server(args.port)
    
    try:
        # Initialize components
        db_manager = DatabaseManager(DB_CONFIG)
        api_client = NHLApiClient(NHL_API_BASE_URL)
        sync_manager = SyncManager(db_manager, api_client)
        
        # Initialize database if requested
        if args.init:
            logger.info("Initializing database schema")
            db_manager.init_schema()
        
        # Determine season to use
        season = args.season or str(datetime.now().year - 1) + str(datetime.now().year)
        
        # Perform initial sync
        if args.sync == 'all' or args.sync == 'teams':
            logger.info("Synchronizing teams data")
            sync_manager.sync_teams()
            
        if args.sync == 'all' or args.sync == 'players':
            logger.info("Synchronizing players data")
            sync_manager.sync_players()
            
        if args.sync == 'all' or args.sync == 'games':
            logger.info(f"Synchronizing games data for season {season}")
            sync_manager.sync_games(season)
            
        if args.sync == 'all' or args.sync == 'stats':
            logger.info(f"Synchronizing stats data for season {season}")
            sync_manager.sync_stats(season)
        
        # Run as daemon if requested
        if args.daemon:
            logger.info("Running in daemon mode with scheduled updates")
            
            # Schedule regular updates
            schedule.every(REFRESH_INTERVALS['teams']).seconds.do(sync_manager.sync_teams)
            schedule.every(REFRESH_INTERVALS['players']).seconds.do(sync_manager.sync_players)
            schedule.every(REFRESH_INTERVALS['games']).seconds.do(
                lambda: sync_manager.sync_games(season))
            schedule.every(REFRESH_INTERVALS['stats']).seconds.do(
                lambda: sync_manager.sync_stats(season))
            
            # Run the scheduler
            while True:
                schedule.run_pending()
                time.sleep(1)
        
        # If web interface is running but not in daemon mode, keep the main thread alive
        if args.web and not args.daemon:
            logger.info("Web interface is running. Press Ctrl+C to exit.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt. Exiting.")
        
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        return 1
    
    logger.info("NHL MySQL Sync completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())