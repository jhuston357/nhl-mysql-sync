"""
NHL API client for NHL MySQL Sync.
Handles fetching data from the NHL API using the new api-web.nhle.com/v1 endpoint.
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
        
        # Map team IDs to team codes for the new API
        self.team_id_to_code = {}
        self.team_code_to_id = {}
        self._initialize_team_mappings()
    
    def _initialize_team_mappings(self):
        """Initialize team ID to team code mappings."""
        # This will be populated when get_teams is first called
        pass
    
    def _make_request(self, endpoint, params=None):
        """Make a request to the NHL API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error making request to {url}: {e}")
            # Return empty data structure instead of raising exception
            if 'team' in endpoint or 'club-stats' in endpoint:
                return {'teams': []}
            elif 'player' in endpoint:
                return {'players': []}
            elif 'schedule' in endpoint:
                return {'gameWeek': []}
            elif 'gamecenter' in endpoint and 'boxscore' in endpoint:
                return {'boxscore': {'teamStats': {}, 'playerByGameStats': {'homeTeam': [], 'awayTeam': []}}}
            elif 'gamecenter' in endpoint:
                return {'awayTeam': {}, 'homeTeam': {}, 'summary': {'scoring': []}}
            else:
                return {}
    
    def get_teams(self):
        """Get all NHL teams."""
        self.logger.info("Fetching teams from NHL API")
        # The new API doesn't have a direct endpoint for all teams
        # We'll use the standings endpoint which includes all teams
        data = self._make_request('standings/now')
        
        teams = []
        if 'standings' in data:
            # Process each division to extract teams
            for division in data.get('standings', []):
                for team_data in division.get('teamRecords', []):
                    team = team_data.get('team', {})
                    
                    # Map team ID to team code for future use
                    team_id = team.get('id')
                    team_code = team.get('abbrev')
                    if team_id and team_code:
                        self.team_id_to_code[team_id] = team_code
                        self.team_code_to_id[team_code] = team_id
                    
                    # Create team object in the format expected by the sync manager
                    team_obj = {
                        'id': team.get('id'),
                        'name': team.get('name'),
                        'abbreviation': team.get('abbrev'),
                        'teamName': team.get('name', '').split()[-1] if team.get('name') else '',
                        'locationName': ' '.join(team.get('name', '').split()[:-1]) if team.get('name') else '',
                        'division': {
                            'id': division.get('id'),
                            'name': division.get('name')
                        },
                        'conference': {
                            'id': division.get('conference', {}).get('id'),
                            'name': division.get('conference', {}).get('name')
                        },
                        'active': True  # Assuming all teams in standings are active
                    }
                    teams.append(team_obj)
        
        return {'teams': teams}
    
    def get_team(self, team_id):
        """Get a specific NHL team."""
        self.logger.info(f"Fetching team {team_id} from NHL API")
        
        # Convert team_id to team code if we have the mapping
        team_code = self.team_id_to_code.get(team_id)
        if not team_code:
            # If we don't have the mapping yet, get all teams first
            self.get_teams()
            team_code = self.team_id_to_code.get(team_id)
        
        if not team_code:
            self.logger.error(f"Could not find team code for team ID {team_id}")
            return {}
        
        # Get team stats which includes team information
        data = self._make_request(f'club-stats/{team_code}/now')
        
        if 'teamStats' in data:
            team_info = data.get('teamStats', {}).get('teamInfo', {})
            
            # Create team object in the format expected by the sync manager
            team_obj = {
                'id': team_id,
                'name': team_info.get('name'),
                'abbreviation': team_info.get('triCode'),
                'teamName': team_info.get('name', '').split()[-1] if team_info.get('name') else '',
                'locationName': ' '.join(team_info.get('name', '').split()[:-1]) if team_info.get('name') else '',
                'division': {
                    'id': team_info.get('divisionId'),
                    'name': team_info.get('divisionName')
                },
                'conference': {
                    'id': team_info.get('conferenceId'),
                    'name': team_info.get('conferenceName')
                },
                'active': True  # Assuming all teams in the API are active
            }
            return team_obj
        
        return {}
    
    def get_team_roster(self, team_id):
        """Get the roster for a specific team."""
        self.logger.info(f"Fetching roster for team {team_id} from NHL API")
        
        # Convert team_id to team code if we have the mapping
        team_code = self.team_id_to_code.get(team_id)
        if not team_code:
            # If we don't have the mapping yet, get all teams first
            self.get_teams()
            team_code = self.team_id_to_code.get(team_id)
        
        if not team_code:
            self.logger.error(f"Could not find team code for team ID {team_id}")
            return []
        
        # Get current roster
        data = self._make_request(f'roster/{team_code}/current')
        
        roster = []
        if 'forwards' in data and 'defensemen' in data and 'goalies' in data:
            # Process forwards, defensemen, and goalies
            for player_type in ['forwards', 'defensemen', 'goalies']:
                for player in data.get(player_type, []):
                    roster_entry = {
                        'person': {
                            'id': player.get('id'),
                            'fullName': player.get('fullName')
                        },
                        'jerseyNumber': player.get('sweaterNumber'),
                        'position': {
                            'code': player.get('positionCode'),
                            'name': player.get('position')
                        }
                    }
                    roster.append(roster_entry)
        
        return {'roster': roster}
    
    def get_player(self, player_id):
        """Get details for a specific player."""
        self.logger.info(f"Fetching player {player_id} from NHL API")
        
        # Get player details
        data = self._make_request(f'player/{player_id}/landing')
        
        if 'firstName' in data and 'lastName' in data:
            # Create player object in the format expected by the sync manager
            player_obj = {
                'id': player_id,
                'fullName': f"{data.get('firstName')} {data.get('lastName')}",
                'firstName': data.get('firstName'),
                'lastName': data.get('lastName'),
                'primaryNumber': data.get('sweaterNumber'),
                'birthDate': data.get('birthDate'),
                'currentTeam': {
                    'id': self.team_code_to_id.get(data.get('currentTeamAbbrev'))
                },
                'primaryPosition': {
                    'name': data.get('position')
                },
                'shootsCatches': data.get('shootsCatches'),
                'height': data.get('heightInInches'),
                'weight': data.get('weightInPounds'),
                'nationality': data.get('birthCountry'),
                'active': True,  # Assuming all players in the API are active
                'rookie': data.get('rookie', False)
            }
            return player_obj
        
        return {}
    
    def get_schedule(self, start_date=None, end_date=None, team_id=None, season=None):
        """Get the NHL schedule for a given date range, team, or season."""
        params = {}
        
        if team_id:
            # Convert team_id to team code if we have the mapping
            team_code = self.team_id_to_code.get(team_id)
            if not team_code:
                # If we don't have the mapping yet, get all teams first
                self.get_teams()
                team_code = self.team_id_to_code.get(team_id)
            
            if not team_code:
                self.logger.error(f"Could not find team code for team ID {team_id}")
                return []
            
            if season:
                # Format: YYYYYYYY (e.g., 20222023)
                self.logger.info(f"Fetching schedule for team {team_code} and season {season}")
                data = self._make_request(f'club-schedule-season/{team_code}/{season}')
            else:
                self.logger.info(f"Fetching current schedule for team {team_code}")
                data = self._make_request(f'club-schedule-season/{team_code}/now')
        else:
            if season:
                # For league-wide schedule, we'll use the date-based endpoint
                # since there's no direct season endpoint
                current_year = int(season[:4])
                next_year = int(season[4:])
                
                # Use a date in the middle of the season (January 1st)
                date = f"{next_year}-01-01"
                self.logger.info(f"Fetching schedule for date {date} (season {season})")
                data = self._make_request(f'schedule/{date}')
            else:
                self.logger.info("Fetching current schedule")
                data = self._make_request('schedule/now')
        
        # Transform the data to match the expected format
        dates = []
        if 'games' in data:
            # Group games by date
            games_by_date = {}
            for game in data.get('games', []):
                game_date = game.get('startTimeUTC', '').split('T')[0]
                if game_date not in games_by_date:
                    games_by_date[game_date] = []
                
                # Transform game data to match expected format
                transformed_game = {
                    'gamePk': game.get('id'),
                    'gameType': game.get('gameType', '2'),  # Default to regular season
                    'gameDate': game.get('startTimeUTC'),
                    'teams': {
                        'away': {
                            'team': {
                                'id': self.team_code_to_id.get(game.get('awayTeam', {}).get('abbrev'))
                            },
                            'score': game.get('awayTeam', {}).get('score', 0)
                        },
                        'home': {
                            'team': {
                                'id': self.team_code_to_id.get(game.get('homeTeam', {}).get('abbrev'))
                            },
                            'score': game.get('homeTeam', {}).get('score', 0)
                        }
                    },
                    'venue': {
                        'name': game.get('venue', {}).get('default')
                    },
                    'status': {
                        'detailedState': game.get('gameState')
                    }
                }
                games_by_date[game_date].append(transformed_game)
            
            # Create dates array
            for date, games in games_by_date.items():
                dates.append({
                    'date': date,
                    'games': games
                })
        
        return dates
    
    def get_game(self, game_id):
        """Get details for a specific game."""
        self.logger.info(f"Fetching game {game_id} from NHL API")
        
        # Get game landing data
        data = self._make_request(f'gamecenter/{game_id}/landing')
        
        # Transform to match expected format
        if 'awayTeam' in data and 'homeTeam' in data:
            transformed_data = {
                'gameData': {
                    'teams': {
                        'away': {
                            'id': self.team_code_to_id.get(data.get('awayTeam', {}).get('abbrev')),
                            'name': data.get('awayTeam', {}).get('name'),
                            'abbreviation': data.get('awayTeam', {}).get('abbrev')
                        },
                        'home': {
                            'id': self.team_code_to_id.get(data.get('homeTeam', {}).get('abbrev')),
                            'name': data.get('homeTeam', {}).get('name'),
                            'abbreviation': data.get('homeTeam', {}).get('abbrev')
                        }
                    },
                    'status': {
                        'detailedState': data.get('gameState')
                    },
                    'venue': {
                        'name': data.get('venue', {}).get('default')
                    }
                },
                'liveData': {
                    'boxscore': {
                        'teams': {
                            'away': {
                                'team': {
                                    'id': self.team_code_to_id.get(data.get('awayTeam', {}).get('abbrev')),
                                    'name': data.get('awayTeam', {}).get('name')
                                },
                                'players': {}
                            },
                            'home': {
                                'team': {
                                    'id': self.team_code_to_id.get(data.get('homeTeam', {}).get('abbrev')),
                                    'name': data.get('homeTeam', {}).get('name')
                                },
                                'players': {}
                            }
                        }
                    }
                }
            }
            return transformed_data
        
        return {}
    
    def get_game_boxscore(self, game_id):
        """Get boxscore for a specific game."""
        self.logger.info(f"Fetching boxscore for game {game_id} from NHL API")
        
        # Get game boxscore data
        data = self._make_request(f'gamecenter/{game_id}/boxscore')
        
        # Transform to match expected format
        transformed_data = {
            'teams': {
                'away': {
                    'team': {
                        'id': self.team_code_to_id.get(data.get('awayTeam', {}).get('abbrev')),
                        'name': data.get('awayTeam', {}).get('name')
                    },
                    'players': {}
                },
                'home': {
                    'team': {
                        'id': self.team_code_to_id.get(data.get('homeTeam', {}).get('abbrev')),
                        'name': data.get('homeTeam', {}).get('name')
                    },
                    'players': {}
                }
            }
        }
        
        # Process player stats
        if 'playerByGameStats' in data:
            # Process away team players
            for player in data.get('playerByGameStats', {}).get('awayTeam', []):
                player_id = player.get('playerId')
                if player_id:
                    player_key = f"ID{player_id}"
                    transformed_data['teams']['away']['players'][player_key] = {
                        'person': {
                            'id': player_id,
                            'fullName': player.get('name', {}).get('default')
                        },
                        'position': {
                            'code': player.get('positionCode')
                        },
                        'stats': {}
                    }
                    
                    # Add skater or goalie stats
                    if player.get('positionCode') == 'G':
                        transformed_data['teams']['away']['players'][player_key]['stats']['goalieStats'] = {
                            'shots': player.get('shotsAgainst', 0),
                            'saves': player.get('saves', 0),
                            'goals': player.get('goalsAgainst', 0),
                            'timeOnIce': player.get('toi'),
                            'decision': player.get('decision')
                        }
                    else:
                        transformed_data['teams']['away']['players'][player_key]['stats']['skaterStats'] = {
                            'goals': player.get('goals', 0),
                            'assists': player.get('assists', 0),
                            'shots': player.get('shots', 0),
                            'hits': player.get('hits', 0),
                            'blocked': player.get('blockedShots', 0),
                            'penaltyMinutes': player.get('pim', 0),
                            'timeOnIce': player.get('toi')
                        }
            
            # Process home team players
            for player in data.get('playerByGameStats', {}).get('homeTeam', []):
                player_id = player.get('playerId')
                if player_id:
                    player_key = f"ID{player_id}"
                    transformed_data['teams']['home']['players'][player_key] = {
                        'person': {
                            'id': player_id,
                            'fullName': player.get('name', {}).get('default')
                        },
                        'position': {
                            'code': player.get('positionCode')
                        },
                        'stats': {}
                    }
                    
                    # Add skater or goalie stats
                    if player.get('positionCode') == 'G':
                        transformed_data['teams']['home']['players'][player_key]['stats']['goalieStats'] = {
                            'shots': player.get('shotsAgainst', 0),
                            'saves': player.get('saves', 0),
                            'goals': player.get('goalsAgainst', 0),
                            'timeOnIce': player.get('toi'),
                            'decision': player.get('decision')
                        }
                    else:
                        transformed_data['teams']['home']['players'][player_key]['stats']['skaterStats'] = {
                            'goals': player.get('goals', 0),
                            'assists': player.get('assists', 0),
                            'shots': player.get('shots', 0),
                            'hits': player.get('hits', 0),
                            'blocked': player.get('blockedShots', 0),
                            'penaltyMinutes': player.get('pim', 0),
                            'timeOnIce': player.get('toi')
                        }
        
        return transformed_data
    
    def get_player_stats(self, player_id, season=None):
        """Get stats for a specific player."""
        self.logger.info(f"Fetching stats for player {player_id} from NHL API")
        
        if season:
            # Get player game log for the season
            data = self._make_request(f'player/{player_id}/game-log/{season}/2')  # 2 is for regular season
        else:
            # Get current player game log
            data = self._make_request(f'player/{player_id}/game-log/now')
        
        # Transform to match expected format
        stats = []
        if 'gameLog' in data:
            stats_data = {
                'splits': []
            }
            
            for game in data.get('gameLog', []):
                split = {
                    'season': game.get('season'),
                    'stat': {
                        'goals': game.get('goals', 0),
                        'assists': game.get('assists', 0),
                        'points': game.get('points', 0),
                        'shots': game.get('shots', 0),
                        'hits': game.get('hits', 0),
                        'blocked': game.get('blockedShots', 0),
                        'timeOnIce': game.get('toi')
                    }
                }
                stats_data['splits'].append(split)
            
            stats.append(stats_data)
        
        return {'stats': stats}