"""
Forms for the NHL MySQL Sync web interface.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, NumberRange, Optional

class ConfigForm(FlaskForm):
    """Form for application configuration."""
    
    # Database configuration
    db_host = StringField('Database Host', validators=[DataRequired()])
    db_user = StringField('Database User', validators=[DataRequired()])
    db_password = PasswordField('Database Password', validators=[DataRequired()])
    db_name = StringField('Database Name', validators=[DataRequired()])
    db_port = StringField('Database Port', validators=[DataRequired()])
    
    # API configuration
    api_url = StringField('NHL API Base URL', validators=[DataRequired()])
    
    # Refresh intervals
    teams_interval = IntegerField('Teams Refresh Interval (seconds)', 
                                 validators=[DataRequired(), NumberRange(min=60)])
    players_interval = IntegerField('Players Refresh Interval (seconds)', 
                                   validators=[DataRequired(), NumberRange(min=60)])
    games_interval = IntegerField('Games Refresh Interval (seconds)', 
                                 validators=[DataRequired(), NumberRange(min=60)])
    stats_interval = IntegerField('Stats Refresh Interval (seconds)', 
                                 validators=[DataRequired(), NumberRange(min=60)])
    
    submit = SubmitField('Save Configuration')

class SyncForm(FlaskForm):
    """Form for manual synchronization."""
    
    data_type = SelectField('Data Type', 
                           choices=[
                               ('all', 'All Data'),
                               ('teams', 'Teams'),
                               ('players', 'Players'),
                               ('games', 'Games'),
                               ('stats', 'Statistics')
                           ],
                           validators=[DataRequired()])
    
    season = StringField('Season (YYYYYYYY format, e.g., 20222023)', validators=[Optional()])
    
    all_seasons = BooleanField('Sync All Seasons (from 2010-2011 to present)')
    
    submit = SubmitField('Start Synchronization')