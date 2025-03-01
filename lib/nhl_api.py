"""
NHL API client for NHL MySQL Sync.
Handles fetching data from the NHL API.
"""

import logging
import requests
from datetime import datetime

class NHLApiClient:
    """Client for interacting with the NHL API."""
    
    def __init__(self, base_url):
        """Initialize the NHL API client with the base URL."""
        self.base_url = base_url
        self.logger = logging.getLogger('nhl_sync.api')
    
    def _make_request(self, endpoint, params=None):
        """Make a request to the NHL API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error making request to {url}: {e}")
            raise
    
    def get_teams(self):
        """Get all NHL teams."""
        self.logger.info("Fetching teams from NHL API")
        data = self._make_request('teams')
        return data.get('teams', [])
    
    def get_team(self, team_id):
        """Get a specific NHL team."""
        self.logger.info(f"Fetching team {team_id} from NHL API")
        data = self._make_request(f'teams/{team_id}')
        return data.get('teams', [{}])[0]
    
    def get_team_roster(self, team_id):
        """Get the roster for a specific team."""
        self.logger.info(f"Fetching roster for team {team_id} from NHL API")
        data = self._make_request(f'teams/{team_id}/roster')
        return data.get('roster', [])
    
    def get_player(self, player_id):
        """Get details for a specific player."""
        self.logger.info(f"Fetching player {player_id} from NHL API")
        data = self._make_request(f'people/{player_id}')
        return data.get('people', [{}])[0]
    
    def get_schedule(self, start_date=None, end_date=None, team_id=None, season=None):
        """Get the NHL schedule for a given date range, team, or season."""
        params = {}
        
        if start_date:
            params['startDate'] = start_date
        
        if end_date:
            params['endDate'] = end_date
        
        if team_id:
            params['teamId'] = team_id
        
        if season:
            # Format: YYYYYYYY (e.g., 20222023)
            endpoint = f'schedule?season={season}'
        else:
            endpoint = 'schedule'
        
        self.logger.info(f"Fetching schedule from NHL API with params: {params}")
        data = self._make_request(endpoint, params)
        return data.get('dates', [])
    
    def get_game(self, game_id):
        """Get details for a specific game."""
        self.logger.info(f"Fetching game {game_id} from NHL API")
        data = self._make_request(f'game/{game_id}/feed/live')
        return data
    
    def get_game_boxscore(self, game_id):
        """Get boxscore for a specific game."""
        self.logger.info(f"Fetching boxscore for game {game_id} from NHL API")
        data = self._make_request(f'game/{game_id}/boxscore')
        return data
    
    def get_player_stats(self, player_id, season=None):
        """Get stats for a specific player."""
        params = {}
        
        if season:
            params['season'] = season
        
        self.logger.info(f"Fetching stats for player {player_id} from NHL API")
        data = self._make_request(f'people/{player_id}/stats', params=params)
        return data.get('stats', [])