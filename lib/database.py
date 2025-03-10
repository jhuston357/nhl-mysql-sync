"""
Database manager for NHL MySQL Sync.
Handles database connections and schema management.
"""

import logging
import mysql.connector
from mysql.connector import Error

class MockCursor:
    """Mock cursor for development/testing without a real database."""
    
    def __init__(self, dictionary=False):
        self.dictionary = dictionary
        self.rowcount = 0
    
    def execute(self, query, params=None):
        """Mock execute method."""
        return 0
    
    def executemany(self, query, params=None):
        """Mock executemany method."""
        self.rowcount = len(params) if params else 0
        return 0
    
    def fetchall(self):
        """Mock fetchall method."""
        return []
    
    def close(self):
        """Mock close method."""
        pass

class MockConnection:
    """Mock connection for development/testing without a real database."""
    
    def __init__(self):
        pass
    
    def cursor(self, dictionary=False):
        """Return a mock cursor."""
        return MockCursor(dictionary=dictionary)
    
    def commit(self):
        """Mock commit method."""
        pass
    
    def rollback(self):
        """Mock rollback method."""
        pass
    
    def close(self):
        """Mock close method."""
        pass
    
    def is_connected(self):
        """Mock is_connected method."""
        return True

class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, db_config):
        """Initialize the database manager with configuration."""
        self.db_config = db_config
        self.logger = logging.getLogger('nhl_sync.database')
    
    def get_connection(self):
        """Create and return a database connection."""
        try:
            connection = mysql.connector.connect(**self.db_config)
            if connection.is_connected():
                self.logger.debug("Connected to MySQL database")
                return connection
        except Error as e:
            self.logger.error(f"Error connecting to MySQL database: {e}")
            # Create a mock connection for development/testing
            self.logger.warning("Using mock database connection for development")
            return MockConnection()
    
    def init_schema(self):
        """Initialize the database schema."""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            # Create teams table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teams (
                    id INT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    abbreviation VARCHAR(10) NOT NULL,
                    team_name VARCHAR(100) NOT NULL,
                    location_name VARCHAR(100) NOT NULL,
                    division_id INT,
                    division_name VARCHAR(100),
                    conference_id INT,
                    conference_name VARCHAR(100),
                    active BOOLEAN DEFAULT TRUE,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            # Create players table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id INT PRIMARY KEY,
                    full_name VARCHAR(100) NOT NULL,
                    first_name VARCHAR(50) NOT NULL,
                    last_name VARCHAR(50) NOT NULL,
                    primary_number VARCHAR(10),
                    birth_date DATE,
                    current_team_id INT,
                    position VARCHAR(50),
                    shooter VARCHAR(10),
                    height VARCHAR(10),
                    weight INT,
                    nationality VARCHAR(50),
                    active BOOLEAN DEFAULT TRUE,
                    rookie BOOLEAN DEFAULT FALSE,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (current_team_id) REFERENCES teams(id)
                )
            """)
            
            # Create games table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id INT PRIMARY KEY,
                    season VARCHAR(10) NOT NULL,
                    game_type VARCHAR(10) NOT NULL,
                    date_time DATETIME NOT NULL,
                    away_team_id INT NOT NULL,
                    home_team_id INT NOT NULL,
                    venue VARCHAR(100),
                    status VARCHAR(50) NOT NULL,
                    away_score INT DEFAULT 0,
                    home_score INT DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (away_team_id) REFERENCES teams(id),
                    FOREIGN KEY (home_team_id) REFERENCES teams(id)
                )
            """)
            
            # Create player_stats table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_stats (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    player_id INT NOT NULL,
                    game_id INT NOT NULL,
                    team_id INT NOT NULL,
                    position VARCHAR(10),
                    goals INT DEFAULT 0,
                    assists INT DEFAULT 0,
                    shots INT DEFAULT 0,
                    hits INT DEFAULT 0,
                    blocked_shots INT DEFAULT 0,
                    penalty_minutes INT DEFAULT 0,
                    time_on_ice VARCHAR(10),
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (player_id) REFERENCES players(id),
                    FOREIGN KEY (game_id) REFERENCES games(id),
                    FOREIGN KEY (team_id) REFERENCES teams(id),
                    UNIQUE KEY player_game (player_id, game_id)
                )
            """)
            
            # Create goalie_stats table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS goalie_stats (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    player_id INT NOT NULL,
                    game_id INT NOT NULL,
                    team_id INT NOT NULL,
                    shots_against INT DEFAULT 0,
                    saves INT DEFAULT 0,
                    goals_against INT DEFAULT 0,
                    time_on_ice VARCHAR(10),
                    decision VARCHAR(10),
                    save_percentage DECIMAL(5,3),
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (player_id) REFERENCES players(id),
                    FOREIGN KEY (game_id) REFERENCES games(id),
                    FOREIGN KEY (team_id) REFERENCES teams(id),
                    UNIQUE KEY goalie_game (player_id, game_id)
                )
            """)
            
            connection.commit()
            self.logger.info("Database schema initialized successfully")
            
        except Error as e:
            self.logger.error(f"Error initializing database schema: {e}")
            raise
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def execute_query(self, query, params=None, fetch=False):
        """Execute a SQL query and optionally fetch results."""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        result = None
        
        try:
            cursor.execute(query, params or ())
            
            if fetch:
                result = cursor.fetchall()
            else:
                connection.commit()
                result = cursor.rowcount
                
            return result
        except Error as e:
            self.logger.error(f"Error executing query: {e}")
            connection.rollback()
            raise
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def insert_or_update(self, table, data, key_fields):
        """Insert or update records in a table."""
        if not data:
            return 0
        print("insert or update before set fields")    
        # Extract field names from the first record
        fields = list(data[0].keys())
        print("insert or update after set fields") 
        # Prepare the base INSERT statement
        placeholders = ', '.join(['%s'] * len(fields))
        columns = ', '.join(fields)
        print("IOU1") 
        # Prepare the ON DUPLICATE KEY UPDATE part
        update_stmt = ', '.join([f"{field} = VALUES({field})" for field in fields 
                                if field not in key_fields])
        print("IOU2")
        # Construct the full query
        query = f"""
            INSERT INTO {table} ({columns}) 
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_stmt}
        """
        print("IOU3")
        # Prepare the values
        values = []
        for record in data:
            print("IOUforloop1")
            # Convert any None values to NULL and ensure proper type conversion
            row = tuple(record[field] if field in record else None for field in fields)
            values.append(row)
        print("IOU4")
        # Execute the query
        connection = self.get_connection()
        cursor = connection.cursor()
        print("IOU5")
        try:
            print("IOU6")
            cursor.executemany(query, values)
            connection.commit()
            print("IOU7")
            return cursor.rowcount
        except Error as e:
            print("IOU8")
            self.logger.error(f"Error in insert_or_update: {e}")
            connection.rollback()
            raise
        finally:
            print("IOU9")
            if connection.is_connected():
                print("IOU10")
                cursor.close()
                connection.close()
