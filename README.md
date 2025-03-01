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

3. Configure your database settings in `config.py`

## Usage

Basic usage:
```
python nhl_sync.py
```

For more options:
```
python nhl_sync.py --help
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.