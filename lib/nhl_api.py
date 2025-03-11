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
        # Ensure logger is configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
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
            
            # Get the JSON response
            json_data = response.json()
            
            # Log the response for debugging
            self.logger.debug(f"API Response from {url}: {json_data}")
            
            # Check if the response is a dictionary
            if not isinstance(json_data, dict) and not isinstance(json_data, list):
                self.logger.error(f"Unexpected response type from {url}: {type(json_data)}")
                # Return appropriate empty structure
                if 'standings' in endpoint:
                    return {'standings': []}
                elif 'team' in endpoint or 'club-stats' in endpoint:
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
            
            return json_data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error making request to {url}: {e}")
            # Return empty data structure instead of raising exception
            if 'standings' in endpoint:
                return {'standings': []}
            elif 'team' in endpoint or 'club-stats' in endpoint:
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
        
        # Debug log the response structure
        self.logger.debug(f"API Response structure: {type(data)}")
        if isinstance(data, dict):
            self.logger.debug(f"API Response keys: {data.keys()}")
        
        teams = []
        
        # Handle the case where the API response structure is different than expected
        try:
            if isinstance(data, dict) and 'standings' in data:
                # Process each division to extract teams
                for division in data.get('standings', []):
                    self.logger.debug(f"Processing division: {division.get('divisionName', 'Unknown')}")
                    
                    # Get team data directly from the standings entry
                    team_name = division.get('teamName', {}).get('default', '')
                    team_abbrev = division.get('teamAbbrev', {}).get('default', '')
                    team_id = None
                    
                    # Try to extract team ID from various fields
                    if 'id' in division:
                        team_id = division.get('id')
                    
                    # If we couldn't find an ID, generate one based on the team abbreviation
                    if not team_id and team_abbrev:
                        # Use a simple hash of the team abbreviation as the ID
                        team_id = hash(team_abbrev) % 1000 + 1000  # Ensure positive and unique
                    
                    if team_id and team_abbrev and team_name:
                        # Map team ID to team code for future use
                        self.team_id_to_code[team_id] = team_abbrev
                        self.team_code_to_id[team_abbrev] = team_id
                        
                        # Create team object in the format expected by the sync manager
                        team_obj = {
                            'id': team_id,
                            'name': team_name,
                            'abbreviation': team_abbrev,
                            'teamName': team_name.split()[-1] if team_name else '',
                            'locationName': ' '.join(team_name.split()[:-1]) if team_name else '',
                            'division': {
                                'id': division.get('divisionId'),
                                'name': division.get('divisionName')
                            },
                            'conference': {
                                'id': division.get('conferenceId'),
                                'name': division.get('conferenceName')
                            },
                            'active': True  # Assuming all teams in standings are active
                        }
                        teams.append(team_obj)
            
            # If we couldn't extract teams from the API response or didn't get enough teams,
            # use a hardcoded list of teams as a fallback
            if len(teams) < 30:
                self.logger.warning(f"Only found {len(teams)} teams in API response, using hardcoded list as fallback")
                hardcoded_teams = [
                    {'id': 1, 'abbrev': 'NJD', 'name': 'New Jersey Devils'},
                    {'id': 2, 'abbrev': 'NYI', 'name': 'New York Islanders'},
                    {'id': 3, 'abbrev': 'NYR', 'name': 'New York Rangers'},
                    {'id': 4, 'abbrev': 'PHI', 'name': 'Philadelphia Flyers'},
                    {'id': 5, 'abbrev': 'PIT', 'name': 'Pittsburgh Penguins'},
                    {'id': 6, 'abbrev': 'BOS', 'name': 'Boston Bruins'},
                    {'id': 7, 'abbrev': 'BUF', 'name': 'Buffalo Sabres'},
                    {'id': 8, 'abbrev': 'MTL', 'name': 'Montreal Canadiens'},
                    {'id': 9, 'abbrev': 'OTT', 'name': 'Ottawa Senators'},
                    {'id': 10, 'abbrev': 'TOR', 'name': 'Toronto Maple Leafs'},
                    {'id': 12, 'abbrev': 'CAR', 'name': 'Carolina Hurricanes'},
                    {'id': 13, 'abbrev': 'FLA', 'name': 'Florida Panthers'},
                    {'id': 14, 'abbrev': 'TBL', 'name': 'Tampa Bay Lightning'},
                    {'id': 15, 'abbrev': 'WSH', 'name': 'Washington Capitals'},
                    {'id': 16, 'abbrev': 'CHI', 'name': 'Chicago Blackhawks'},
                    {'id': 17, 'abbrev': 'DET', 'name': 'Detroit Red Wings'},
                    {'id': 18, 'abbrev': 'NSH', 'name': 'Nashville Predators'},
                    {'id': 19, 'abbrev': 'STL', 'name': 'St. Louis Blues'},
                    {'id': 20, 'abbrev': 'CGY', 'name': 'Calgary Flames'},
                    {'id': 21, 'abbrev': 'COL', 'name': 'Colorado Avalanche'},
                    {'id': 22, 'abbrev': 'EDM', 'name': 'Edmonton Oilers'},
                    {'id': 23, 'abbrev': 'VAN', 'name': 'Vancouver Canucks'},
                    {'id': 24, 'abbrev': 'ANA', 'name': 'Anaheim Ducks'},
                    {'id': 25, 'abbrev': 'DAL', 'name': 'Dallas Stars'},
                    {'id': 26, 'abbrev': 'LAK', 'name': 'Los Angeles Kings'},
                    {'id': 28, 'abbrev': 'SJS', 'name': 'San Jose Sharks'},
                    {'id': 29, 'abbrev': 'CBJ', 'name': 'Columbus Blue Jackets'},
                    {'id': 30, 'abbrev': 'MIN', 'name': 'Minnesota Wild'},
                    {'id': 52, 'abbrev': 'WPG', 'name': 'Winnipeg Jets'},
                    {'id': 53, 'abbrev': 'ARI', 'name': 'Arizona Coyotes'},
                    {'id': 54, 'abbrev': 'VGK', 'name': 'Vegas Golden Knights'},
                    {'id': 55, 'abbrev': 'SEA', 'name': 'Seattle Kraken'},
                    {'id': 56, 'abbrev': 'UTA', 'name': 'Utah Hockey Club'}
                ]
                
                teams = []  # Reset teams list to use only hardcoded teams
                
                for team in hardcoded_teams:
                    team_id = team['id']
                    team_code = team['abbrev']
                    team_name = team['name']
                    
                    # Map team ID to team code for future use
                    self.team_id_to_code[team_id] = team_code
                    self.team_code_to_id[team_code] = team_id
                    
                    # Create team object in the format expected by the sync manager
                    team_obj = {
                        'id': team_id,
                        'name': team_name,
                        'abbreviation': team_code,
                        'teamName': team_name.split()[-1],
                        'locationName': ' '.join(team_name.split()[:-1]),
                        'division': {
                            'id': None,
                            'name': None
                        },
                        'conference': {
                            'id': None,
                            'name': None
                        },
                        'active': True
                    }
                    teams.append(team_obj)
        except Exception as e:
            self.logger.error(f"Error processing teams data: {e}", exc_info=True)
            # Return empty teams list to avoid further errors
            return []
        
        return teams
    
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
                # For league-wide schedule, we need to fetch multiple dates
                # to get all games for the season
                current_year = int(season[:4])
                next_year = int(season[4:])
                
                # NHL season typically runs from October to April
                # We'll fetch data for specific dates throughout the season
                # to ensure we get complete coverage
                
                # Generate a list of dates to check (one per week)
                import datetime
                
                # Start date: October 1st of the first year
                start_date = datetime.date(current_year, 10, 1)
                # End date: April 30th of the next year
                end_date = datetime.date(next_year, 4, 30)
                
                # Generate dates at weekly intervals
                dates = []
                current_date = start_date
                while current_date <= end_date:
                    dates.append(current_date.strftime("%Y-%m-%d"))
                    current_date += datetime.timedelta(days=7)
                
                self.logger.info(f"Fetching schedule for season {season} using {len(dates)} weekly dates")
                
                # Initialize with empty games array
                data = {"games": []}
                
                # Track game IDs to avoid duplicates
                game_ids = set()
                
                # Fetch data for each date
                for date in dates:
                    try:
                        self.logger.info(f"Fetching games for date {date}")
                        
                        # Use the date endpoint
                        date_data = self._make_request(f'schedule/{date}')
                        
                        # If we have games, add them to our collection (avoiding duplicates)
                        if 'games' in date_data and date_data['games']:
                            new_games = 0
                            for game in date_data['games']:
                                if 'id' in game and game['id'] not in game_ids:
                                    game_ids.add(game['id'])
                                    data['games'].append(game)
                                    new_games += 1
                            
                            self.logger.info(f"Found {new_games} new games for {date}")
                        else:
                            self.logger.info(f"No games found for {date}")
                    except Exception as e:
                        self.logger.error(f"Error fetching games for {date}: {e}")
                        continue
                
                self.logger.info(f"Found {len(data['games'])} games for season {season}")
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