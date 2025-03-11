"""
Routes for the NHL MySQL Sync web interface.
"""

import os
import json
import threading
from datetime import datetime
from flask import render_template, request, jsonify, redirect, url_for, flash
from web import app, socketio, scheduler
from web.forms import ConfigForm, SyncForm
from lib.database import DatabaseManager
from lib.nhl_api import NHLApiClient
from lib.sync_manager import SyncManager
import config

# Global variables to track sync status
sync_status = {
    'is_running': False,
    'current_task': None,
    'progress': 0,
    'last_run': None,
    'stats': {
        'teams_updated': 0,
        'players_updated': 0,
        'games_updated': 0,
        'stats_updated': 0
    }
}

# Initialize components
db_manager = None
api_client = None
sync_manager = None

def init_components():
    """Initialize the application components."""
    global db_manager, api_client, sync_manager
    db_manager = DatabaseManager(config.DB_CONFIG)
    api_client = NHLApiClient(config.NHL_API_BASE_URL)
    sync_manager = SyncManager(db_manager, api_client)
    
    # Override the sync manager's logger to emit socket events
    original_logger = sync_manager.logger
    
    class SocketLogger:
        def debug(self, message):
            original_logger.info(message)  # Use info level instead of debug
            socketio.emit('log_message', {'level': 'debug', 'message': message})
            
        def info(self, message):
            original_logger.info(message)
            socketio.emit('log_message', {'level': 'info', 'message': message})
            
        def warning(self, message):
            original_logger.warning(message)
            socketio.emit('log_message', {'level': 'warning', 'message': message})
            
        def error(self, message, exc_info=None):
            original_logger.error(message, exc_info=exc_info)
            socketio.emit('log_message', {'level': 'error', 'message': message})
    
    sync_manager.logger = SocketLogger()

# Initialize components on startup
init_components()

@app.route('/')
def index():
    """Render the dashboard page."""
    return render_template('dashboard.html', sync_status=sync_status)

@app.route('/config', methods=['GET', 'POST'])
def config_page():
    """Render the configuration page."""
    form = ConfigForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        # Update config values
        config.DB_CONFIG['host'] = form.db_host.data
        config.DB_CONFIG['user'] = form.db_user.data
        config.DB_CONFIG['password'] = form.db_password.data
        config.DB_CONFIG['database'] = form.db_name.data
        config.DB_CONFIG['port'] = int(form.db_port.data)
        
        config.NHL_API_BASE_URL = form.api_url.data
        
        config.REFRESH_INTERVALS['teams'] = int(form.teams_interval.data)
        config.REFRESH_INTERVALS['players'] = int(form.players_interval.data)
        config.REFRESH_INTERVALS['games'] = int(form.games_interval.data)
        config.REFRESH_INTERVALS['stats'] = int(form.stats_interval.data)
        
        # Reinitialize components with new config
        init_components()
        
        flash('Configuration updated successfully', 'success')
        return redirect(url_for('config_page'))
    
    # Pre-populate form with current values
    if request.method == 'GET':
        form.db_host.data = config.DB_CONFIG['host']
        form.db_user.data = config.DB_CONFIG['user']
        form.db_password.data = config.DB_CONFIG['password']
        form.db_name.data = config.DB_CONFIG['database']
        form.db_port.data = str(config.DB_CONFIG['port'])
        
        form.api_url.data = config.NHL_API_BASE_URL
        
        form.teams_interval.data = config.REFRESH_INTERVALS['teams']
        form.players_interval.data = config.REFRESH_INTERVALS['players']
        form.games_interval.data = config.REFRESH_INTERVALS['games']
        form.stats_interval.data = config.REFRESH_INTERVALS['stats']
    
    return render_template('config.html', form=form)

@app.route('/sync', methods=['GET', 'POST'])
def sync_page():
    """Render the sync page."""
    form = SyncForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        data_type = form.data_type.data
        all_seasons = form.all_seasons.data
        season = form.season.data if form.season.data and not all_seasons else None
        
        # Start sync in background thread
        thread = threading.Thread(target=run_sync, args=(data_type, season, all_seasons))
        thread.daemon = True
        thread.start()
        
        season_msg = "all seasons" if all_seasons else f"season {season if season else 'current'}"
        flash(f'Started synchronization of {data_type} data for {season_msg}', 'success')
        return redirect(url_for('sync_page'))
    
    return render_template('sync.html', form=form, sync_status=sync_status)

@app.route('/stats')
def stats_page():
    """Render the statistics page."""
    # Get database statistics
    db_stats = {}
    
    try:
        # Count records in each table
        tables = ['teams', 'players', 'games', 'player_stats', 'goalie_stats']
        for table in tables:
            count_query = f"SELECT COUNT(*) as count FROM {table}"
            result = db_manager.execute_query(count_query, fetch=True)
            db_stats[table] = result[0]['count'] if result else 0
        
        # Get last updated timestamps
        for table in tables:
            query = f"SELECT MAX(last_updated) as last_updated FROM {table}"
            result = db_manager.execute_query(query, fetch=True)
            timestamp = result[0]['last_updated'] if result and result[0]['last_updated'] else None
            db_stats[f"{table}_updated"] = timestamp.strftime('%Y-%m-%d %H:%M:%S') if timestamp else 'Never'
        
    except Exception as e:
        app.logger.error(f"Error fetching database statistics: {e}")
        db_stats = {'error': str(e)}
    
    return render_template('stats.html', db_stats=db_stats, sync_status=sync_status)

@app.route('/api/sync/status')
def get_sync_status():
    """API endpoint to get the current sync status."""
    return jsonify(sync_status)

@app.route('/api/sync/cancel', methods=['POST'])
def cancel_sync():
    """API endpoint to cancel the current sync operation."""
    global sync_status
    sync_status['is_running'] = False
    socketio.emit('sync_update', sync_status)
    return jsonify({'success': True, 'message': 'Sync operation cancelled'})

@app.route('/api/db/init', methods=['POST'])
def init_database():
    """API endpoint to initialize the database schema."""
    try:
        db_manager.init_schema()
        return jsonify({'success': True, 'message': 'Database schema initialized successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error initializing database: {str(e)}'})

def run_sync(data_type, season=None, all_seasons=False):
    """Run a synchronization operation in the background."""
    global sync_status
    
    # Update sync status
    sync_status['is_running'] = True
    sync_status['current_task'] = data_type
    sync_status['progress'] = 0
    sync_status['stats'] = {
        'teams_updated': 0,
        'players_updated': 0,
        'games_updated': 0,
        'stats_updated': 0
    }
    socketio.emit('sync_update', sync_status)
    
    try:
        # Generate list of seasons to process
        seasons_to_process = []
        
        if all_seasons:
            # Process seasons from 2010-2011 to present
            current_year = datetime.now().year
            for year in range(2010, current_year):
                seasons_to_process.append(str(year) + str(year + 1))
        else:
            # Determine single season to use if not provided
            if not season:
                current_year = datetime.now().year
                season = str(current_year - 1) + str(current_year)
            seasons_to_process.append(season)
        
        # Override the database manager's insert_or_update method to track progress
        original_insert_or_update = db_manager.insert_or_update
        
        def tracked_insert_or_update(table, data, key_fields):
            rows_affected = original_insert_or_update(table, data, key_fields)
            
            # Update stats based on table
            if table == 'teams':
                sync_status['stats']['teams_updated'] += rows_affected
            elif table == 'players':
                sync_status['stats']['players_updated'] += rows_affected
            elif table == 'games':
                sync_status['stats']['games_updated'] += rows_affected
            elif table in ['player_stats', 'goalie_stats']:
                sync_status['stats']['stats_updated'] += rows_affected
            
            # Update progress (simplified)
            sync_status['progress'] += 10
            if sync_status['progress'] > 100:
                sync_status['progress'] = 100
                
            socketio.emit('sync_update', sync_status)
            return rows_affected
        
        # Replace the method temporarily
        db_manager.insert_or_update = tracked_insert_or_update
        
        # Perform the requested sync operation
        if data_type == 'teams' or data_type == 'all':
            sync_status['current_task'] = 'Synchronizing teams'
            socketio.emit('sync_update', sync_status)
            sync_manager.sync_teams()
            
        if data_type == 'players' or data_type == 'all':
            sync_status['current_task'] = 'Synchronizing players'
            socketio.emit('sync_update', sync_status)
            sync_manager.sync_players()
            
        if data_type == 'games' or data_type == 'all':
            for season_to_process in seasons_to_process:
                if not sync_status['is_running']:
                    break  # Allow cancellation between seasons
                sync_status['current_task'] = f'Synchronizing games for season {season_to_process}'
                socketio.emit('sync_update', sync_status)
                sync_manager.sync_games(season_to_process)
            
        if data_type == 'stats' or data_type == 'all':
            for season_to_process in seasons_to_process:
                if not sync_status['is_running']:
                    break  # Allow cancellation between seasons
                sync_status['current_task'] = f'Synchronizing stats for season {season_to_process}'
                socketio.emit('sync_update', sync_status)
                sync_manager.sync_stats(season_to_process)
        
        # Restore the original method
        db_manager.insert_or_update = original_insert_or_update
        
        # Update final status
        sync_status['is_running'] = False
        sync_status['current_task'] = 'Completed'
        sync_status['progress'] = 100
        sync_status['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
    except Exception as e:
        app.logger.error(f"Error during sync: {e}")
        sync_status['is_running'] = False
        sync_status['current_task'] = f'Error: {str(e)}'
        
    socketio.emit('sync_update', sync_status)

@socketio.on('connect')
def handle_connect():
    """Handle client connection to socket."""
    socketio.emit('sync_update', sync_status)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection from socket."""
    pass