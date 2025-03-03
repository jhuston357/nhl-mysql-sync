"""
Sync manager for NHL MySQL Sync.
Handles synchronization between NHL API and MySQL database.
"""

import logging
from datetime import datetime
from tqdm import tqdm

class SyncManager:
    """Manages synchronization between NHL API and database."""
    
    def __init__(self, db_manager, api_client):
        """Initialize the sync manager with database and API clients."""
        self.db = db_manager
        self.api = api_client
        self.logger = logging.getLogger('nhl_sync.sync')
    
    def sync_teams(self):
        """Synchronize teams data."""
        self.logger.info("Starting teams synchronization")
        
        # Fetch teams from API
        teams_data = self.api.get_teams()
        
        # Check if teams_data is a dictionary with 'teams' key (old API format)
        if isinstance(teams_data, dict) and 'teams' in teams_data:
            teams_data = teams_data.get('teams', [])
        
        # Transform data for database
        teams_to_insert = []
        for team in teams_data:
            # Ensure team is a dictionary
            if not isinstance(team, dict):
                self.logger.error(f"Team data is not a dictionary: {team}")
                continue
                
            # Log team data for debugging
            self.logger.debug(f"Processing team: {team}")
            
            # Extract team data with proper error handling
            try:
                team_record = {
                    'id': team.get('id'),
                    'name': team.get('name', ''),
                    'abbreviation': team.get('abbreviation', ''),
                    'team_name': team.get('teamName', ''),
                    'location_name': team.get('locationName', ''),
                    'division_id': team.get('division', {}).get('id') if isinstance(team.get('division'), dict) else None,
                    'division_name': team.get('division', {}).get('name') if isinstance(team.get('division'), dict) else None,
                    'conference_id': team.get('conference', {}).get('id') if isinstance(team.get('conference'), dict) else None,
                    'conference_name': team.get('conference', {}).get('name') if isinstance(team.get('conference'), dict) else None,
                    'active': team.get('active', True)
                }
                
                # Validate required fields
                if team_record['id'] is None:
                    self.logger.error(f"Team is missing required 'id' field: {team}")
                    continue
                    
                teams_to_insert.append(team_record)
            except Exception as e:
                self.logger.error(f"Error processing team data: {e}", exc_info=True)
                continue
        
        # Insert or update in database
        if teams_to_insert:
            rows_affected = self.db.insert_or_update('teams', teams_to_insert, ['id'])
            self.logger.info(f"Teams synchronization completed: {rows_affected} rows affected")
        else:
            self.logger.warning("No teams data to synchronize")
    
    def sync_players(self):
        """Synchronize players data."""
        self.logger.info("Starting players synchronization")
        
        # Get all teams
        teams_data = self.api.get_teams()
        
        # Check if teams_data is a dictionary with 'teams' key (old API format)
        if isinstance(teams_data, dict) and 'teams' in teams_data:
            teams_data = teams_data.get('teams', [])
        
        players_to_insert = []
        
        # For each team, get roster and player details
        for team in tqdm(teams_data, desc="Fetching team rosters"):
            # Ensure team is a dictionary
            if not isinstance(team, dict):
                self.logger.error(f"Team data is not a dictionary: {team}")
                continue
                
            # Get team ID with error handling
            try:
                team_id = team.get('id')
                if team_id is None:
                    self.logger.error(f"Team is missing required 'id' field: {team}")
                    continue
                    
                # Get roster for the team
                roster_data = self.api.get_team_roster(team_id)
                
                # Check if roster_data is in the expected format
                if isinstance(roster_data, dict) and 'roster' in roster_data:
                    roster = roster_data.get('roster', [])
                elif isinstance(roster_data, dict) and ('forwards' in roster_data or 'defensemen' in roster_data or 'goalies' in roster_data):
                    # New API format with player types
                    roster = []
                    for player_type in ['forwards', 'defensemen', 'goalies']:
                        if player_type in roster_data:
                            for player in roster_data.get(player_type, []):
                                # Convert to the expected format
                                roster.append({
                                    'person': {
                                        'id': player.get('id'),
                                        'fullName': f"{player.get('firstName', {}).get('default', '')} {player.get('lastName', {}).get('default', '')}"
                                    },
                                    'jerseyNumber': player.get('sweaterNumber'),
                                    'position': {
                                        'code': player.get('positionCode'),
                                        'name': player.get('position', player.get('positionCode', ''))
                                    }
                                })
                else:
                    roster = []
                
                # Process each player in the roster
                for player in roster:
                    # Ensure player is a dictionary
                    if not isinstance(player, dict):
                        self.logger.error(f"Player data is not a dictionary: {player}")
                        continue
                        
                    # Get player ID with error handling
                    try:
                        if 'person' in player and isinstance(player['person'], dict):
                            player_id = player['person'].get('id')
                        else:
                            player_id = player.get('id')
                            
                        if player_id is None:
                            self.logger.error(f"Player is missing required 'id' field: {player}")
                            continue
                            
                        # Get detailed player info
                        player_data = self.api.get_player(player_id)
                        
                        # Ensure player_data is a dictionary
                        if not isinstance(player_data, dict):
                            self.logger.error(f"Player data is not a dictionary: {player_data}")
                            continue
                            
                        # Transform data for database with error handling
                        try:
                            # Extract position safely - This is the key fix:
                            position = None
                            if isinstance(player_data.get('primaryPosition'), dict):
                                position = player_data.get('primaryPosition', {}).get('name')
                            elif isinstance(player.get('position'), dict):
                                position = player.get('position', {}).get('name')
                            
                            player_record = {
                                'id': player_data.get('id', player_id),
                                'full_name': player_data.get('fullName', ''),
                                'first_name': player_data.get('firstName', ''),
                                'last_name': player_data.get('lastName', ''),
                                'primary_number': player_data.get('primaryNumber', player.get('jerseyNumber')),
                                'birth_date': player_data.get('birthDate'),
                                'current_team_id': team_id,
                                'position': position,  # Use the safely extracted position
                                'shooter': player_data.get('shootsCatches'),
                                'height': player_data.get('height', player_data.get('heightInInches')),
                                'weight': player_data.get('weight', player_data.get('weightInPounds')),
                                'nationality': player_data.get('nationality', player_data.get('birthCountry')),
                                'active': player_data.get('active', True),
                                'rookie': player_data.get('rookie', False)
                            }
                            
                            # Validate required fields
                            if player_record['id'] is None:
                                self.logger.error(f"Player record is missing required 'id' field: {player_record}")
                                continue
                                
                            players_to_insert.append(player_record)
                        except Exception as e:
                            self.logger.error(f"Error creating player record: {e}", exc_info=True)
                            continue
                    except Exception as e:
                        self.logger.error(f"Error processing player: {e}", exc_info=True)
                        continue
            except Exception as e:
                self.logger.error(f"Error processing team: {e}", exc_info=True)
                continue
        
        # Insert or update in database
        if players_to_insert:
            rows_affected = self.db.insert_or_update('players', players_to_insert, ['id'])
            self.logger.info(f"Players synchronization completed: {rows_affected} rows affected")
        else:
            self.logger.warning("No players data to synchronize")
    
    def sync_games(self, season):
        """Synchronize games data for a specific season."""
        self.logger.info(f"Starting games synchronization for season {season}")
        
        # Fetch schedule from API
        schedule_data = self.api.get_schedule(season=season)
        
        games_to_insert = []
        
        # Process each date in the schedule
        for date_info in schedule_data:
            for game in date_info.get('games', []):
                # Transform data for database
                game_record = {
                    'id': game['gamePk'],
                    'season': season,
                    'game_type': game['gameType'],
                    'date_time': game['gameDate'],
                    'away_team_id': game['teams']['away']['team']['id'],
                    'home_team_id': game['teams']['home']['team']['id'],
                    'venue': game.get('venue', {}).get('name'),
                    'status': game['status']['detailedState'],
                    'away_score': game['teams']['away'].get('score', 0),
                    'home_score': game['teams']['home'].get('score', 0)
                }
                games_to_insert.append(game_record)
        
        # Insert or update in database
        if games_to_insert:
            rows_affected = self.db.insert_or_update('games', games_to_insert, ['id'])
            self.logger.info(f"Games synchronization completed: {rows_affected} rows affected")
        else:
            self.logger.warning(f"No games data to synchronize for season {season}")
    
    def sync_stats(self, season):
        """Synchronize player and goalie stats for a specific season."""
        self.logger.info(f"Starting stats synchronization for season {season}")
        
        # Get completed games that need stats
        games_query = """
            SELECT id FROM games 
            WHERE season = %s 
            AND status IN ('Final', 'Official')
        """
        games = self.db.execute_query(games_query, (season,), fetch=True)
        
        player_stats_to_insert = []
        goalie_stats_to_insert = []
        
        # For each game, get boxscore and extract stats
        for game in tqdm(games, desc="Fetching game stats"):
            game_id = game['id']
            boxscore = self.api.get_game_boxscore(game_id)
            
            # Process home and away teams
            for team_type in ['home', 'away']:
                team_data = boxscore['teams'][team_type]
                team_id = team_data['team']['id']
                
                # Process player stats
                for player_id, player_data in team_data['players'].items():
                    # Skip non-player entries
                    if not player_id.startswith('ID'):
                        continue
                    
                    player_id = int(player_id.replace('ID', ''))
                    stats = player_data.get('stats', {})
                    
                    # Process skater stats
                    if 'skaterStats' in stats:
                        skater_stats = stats['skaterStats']
                        player_stat_record = {
                            'player_id': player_id,
                            'game_id': game_id,
                            'team_id': team_id,
                            'position': player_data.get('position', {}).get('code'),
                            'goals': skater_stats.get('goals', 0),
                            'assists': skater_stats.get('assists', 0),
                            'shots': skater_stats.get('shots', 0),
                            'hits': skater_stats.get('hits', 0),
                            'blocked_shots': skater_stats.get('blocked', 0),
                            'penalty_minutes': skater_stats.get('penaltyMinutes', 0),
                            'time_on_ice': skater_stats.get('timeOnIce')
                        }
                        player_stats_to_insert.append(player_stat_record)
                    
                    # Process goalie stats
                    if 'goalieStats' in stats:
                        goalie_stats = stats['goalieStats']
                        save_pct = 0
                        shots = goalie_stats.get('shots', 0)
                        if shots > 0:
                            save_pct = (shots - goalie_stats.get('goals', 0)) / shots
                            
                        goalie_stat_record = {
                            'player_id': player_id,
                            'game_id': game_id,
                            'team_id': team_id,
                            'shots_against': goalie_stats.get('shots', 0),
                            'saves': goalie_stats.get('saves', 0),
                            'goals_against': goalie_stats.get('goals', 0),
                            'time_on_ice': goalie_stats.get('timeOnIce'),
                            'decision': goalie_stats.get('decision'),
                            'save_percentage': save_pct
                        }
                        goalie_stats_to_insert.append(goalie_stat_record)
        
        # Insert or update player stats in database
        if player_stats_to_insert:
            rows_affected = self.db.insert_or_update(
                'player_stats', player_stats_to_insert, ['player_id', 'game_id'])
            self.logger.info(f"Player stats synchronization completed: {rows_affected} rows affected")
        else:
            self.logger.warning(f"No player stats to synchronize for season {season}")
        
        # Insert or update goalie stats in database
        if goalie_stats_to_insert:
            rows_affected = self.db.insert_or_update(
                'goalie_stats', goalie_stats_to_insert, ['player_id', 'game_id'])
            self.logger.info(f"Goalie stats synchronization completed: {rows_affected} rows affected")
        else:
            self.logger.warning(f"No goalie stats to synchronize for season {season}")
