# NHL MySQL Sync

A Python application to populate and synchronize a MySQL database with hockey data from the NHL API.

## Overview

This application fetches data from the NHL API and stores it in a MySQL database, keeping the database synchronized with the latest NHL data. It can be used for hockey analytics, statistics tracking, and data visualization projects.

## Features

- Fetch team, player, game, and statistics data from the NHL API
- Store data in a structured MySQL database
- Synchronize database with the latest NHL data
- Configurable data refresh intervals
- Support for historical and current season data
- Web-based GUI for configuration, manual sync, and monitoring

## Requirements

- Python 3.8+
- MySQL 5.7+ or MariaDB 10.3+
- Required Python packages (see requirements.txt)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/jhuston357/nhl-mysql-sync.git
   cd nhl-mysql-sync
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Configure your database settings in `config.py` or through the web interface

## Usage

### Command Line Interface

Basic usage:
```
python nhl_sync.py
```

Initialize database schema:
```
python nhl_sync.py --init
```

Sync specific data:
```
python nhl_sync.py --sync teams
python nhl_sync.py --sync players
python nhl_sync.py --sync games --season 20222023
```

Run as a daemon with scheduled updates:
```
python nhl_sync.py --daemon
```

For more options:
```
python nhl_sync.py --help
```

### Web Interface

Start the web interface:
```
python nhl_sync.py --web
```

Or run the web server directly:
```
python web_server.py
```

The web interface will be available at http://localhost:7443 by default.

You can specify a different port:
```
python nhl_sync.py --web --port 8080
```

Run with both web interface and daemon mode:
```
python nhl_sync.py --web --daemon
```

## Web Interface Features

- **Dashboard**: Overview of sync status and database statistics
- **Configuration**: Update database and API settings
- **Sync**: Manually trigger synchronization with progress tracking
- **Statistics**: View detailed database statistics and visualizations

## License

MIT

## Docker Deployment

You can easily deploy this application using Docker:

### Using Docker Compose (Recommended)

1. Clone the repository and navigate to the project directory:
   ```
   git clone https://github.com/jhuston357/nhl-mysql-sync.git
   cd nhl-mysql-sync
   ```

2. Start the application with Docker Compose:
   ```
   docker-compose up -d
   ```

3. Access the web interface at http://localhost:7443

### Using Docker Directly

1. Build the Docker image:
   ```
   docker build -t nhl-mysql-sync .
   ```

2. Run the container:
   ```
   docker run -d -p 7443:7443 \
     -e DB_HOST=your-mysql-host \
     -e DB_USER=your-mysql-user \
     -e DB_PASSWORD=your-mysql-password \
     -e DB_NAME=nhl_data \
     nhl-mysql-sync
   ```

3. Access the web interface at http://localhost:7443

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.