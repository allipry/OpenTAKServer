#!/usr/bin/env python3
"""
Event Model for MAGK Extension
Maps to the events table created in database migration
Manages tactical simulation events with WiFi configuration
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone
from opentakserver.extensions import db

class Event(db.Model):
    """
    Event model for managing tactical simulation events
    Maps to events table created in 06-events-schema.sql
    """
    __tablename__ = 'events'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Event information
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    event_type = Column(String(50), default='tactical_exercise')
    
    # Date range
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    
    # Location
    location = Column(String(255))
    
    # WiFi configuration
    wifi_ssid = Column(String(32))
    wifi_password = Column(String(63))
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Creator reference
    created_by = Column(Integer, ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    
    # Flexible metadata storage
    settings = Column(JSONB, default=dict)
    
    # Check constraint: end_date must be after start_date
    __table_args__ = (
        CheckConstraint('end_date > start_date', name='check_event_dates'),
    )
    
    # Relationships
    # Note: Using secondary table for many-to-many relationship with teams
    # Relationship defined through event_teams junction table
    
    def to_dict(self, include_teams=False, include_participant_count=False):
        """
        Convert Event instance to dictionary for JSON serialization
        
        Args:
            include_teams (bool): Whether to include associated teams
            include_participant_count (bool): Whether to include participant count
            
        Returns:
            dict: Event data as dictionary
        """
        # Get creator info if created_by exists
        creator_username = None
        if self.created_by:
            try:
                from opentakserver.models.user import User
                user = User.query.get(self.created_by)
                if user:
                    creator_username = user.username
            except:
                pass
        
        event_dict = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'event_type': self.event_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'location': self.location,
            'wifi_ssid': self.wifi_ssid,
            'wifi_password': self.wifi_password,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'creator_username': creator_username,
            'settings': self.settings
        }
        
        # Include teams if requested
        if include_teams:
            event_dict['teams'] = self.get_teams()
        
        # Include participant count if requested
        if include_participant_count:
            event_dict['participant_count'] = self.get_participant_count()
        
        return event_dict
    
    def __repr__(self):
        """String representation for debugging"""
        return f'<Event {self.id}: {self.name}>'
    
    def validate_dates(self):
        """
        Validate that end_date is after start_date
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not self.start_date or not self.end_date:
            return False, "Start date and end date are required"
        
        if self.end_date <= self.start_date:
            return False, "End date must be after start date"
        
        return True, None
    
    def is_currently_active(self):
        """
        Check if event is currently active (within date range and is_active=True)
        
        Returns:
            bool: True if event is currently active
        """
        if not self.is_active:
            return False
        
        now = datetime.now(timezone.utc)
        return self.start_date <= now <= self.end_date
    
    def get_participant_count(self):
        """
        Get total participant count for this event across all teams
        Uses database function get_event_participant_count()
        
        Returns:
            int: Total number of participants
        """
        try:
            from sqlalchemy import text
            result = db.session.execute(
                text("SELECT get_event_participant_count(:event_id)"),
                {'event_id': self.id}
            )
            count = result.scalar()
            return count if count is not None else 0
        except Exception as e:
            print(f"Error getting participant count: {e}")
            return 0
    
    def get_teams(self):
        """
        Get all teams associated with this event
        Uses database function get_event_teams()
        
        Returns:
            list: List of team dictionaries with participant counts
        """
        try:
            from sqlalchemy import text
            result = db.session.execute(
                text("SELECT * FROM get_event_teams(:event_id)"),
                {'event_id': self.id}
            )
            
            teams = []
            for row in result:
                teams.append({
                    'team_id': row[0],
                    'team_name': row[1],
                    'team_color': row[2],
                    'participant_count': row[3],
                    'max_participants': row[4]
                })
            
            return teams
        except Exception as e:
            print(f"Error getting event teams: {e}")
            return []
    
    def add_team(self, team_id, max_participants=None):
        """
        Add a team to this event
        
        Args:
            team_id (int): ID of team to add
            max_participants (int, optional): Maximum participants for this team in this event
            
        Returns:
            EventTeam: The created event_team association
        """
        from opentakserver.magk.models.event_team import EventTeam
        
        # Check if association already exists
        existing = EventTeam.query.filter_by(
            event_id=self.id,
            team_id=team_id
        ).first()
        
        if existing:
            # Update existing association
            existing.is_active = True
            if max_participants is not None:
                existing.max_participants = max_participants
            db.session.commit()
            return existing
        
        # Create new association
        event_team = EventTeam(
            event_id=self.id,
            team_id=team_id,
            max_participants=max_participants,
            is_active=True
        )
        
        db.session.add(event_team)
        db.session.commit()
        
        return event_team
    
    def remove_team(self, team_id):
        """
        Remove a team from this event (soft delete by setting is_active=False)
        
        Args:
            team_id (int): ID of team to remove
            
        Returns:
            bool: True if team was removed, False if not found
        """
        from opentakserver.magk.models.event_team import EventTeam
        
        event_team = EventTeam.query.filter_by(
            event_id=self.id,
            team_id=team_id
        ).first()
        
        if event_team:
            event_team.is_active = False
            db.session.commit()
            return True
        
        return False
    
    @classmethod
    def get_active_events(cls):
        """
        Get all active events
        
        Returns:
            list: List of active Event instances
        """
        return cls.query.filter_by(is_active=True).order_by(cls.start_date.desc()).all()
    
    @classmethod
    def get_current_events(cls):
        """
        Get events that are currently running (within date range and active)
        
        Returns:
            list: List of current Event instances
        """
        now = datetime.now(timezone.utc)
        return cls.query.filter(
            cls.is_active == True,
            cls.start_date <= now,
            cls.end_date >= now
        ).order_by(cls.start_date.desc()).all()
    
    @classmethod
    def get_upcoming_events(cls):
        """
        Get upcoming events (start_date in the future and active)
        
        Returns:
            list: List of upcoming Event instances
        """
        now = datetime.now(timezone.utc)
        return cls.query.filter(
            cls.is_active == True,
            cls.start_date > now
        ).order_by(cls.start_date.asc()).all()
    
    @classmethod
    def create_event(cls, name, start_date, end_date, description=None, location=None,
                    wifi_ssid=None, wifi_password=None, event_type='tactical_exercise',
                    created_by=None, settings=None):
        """
        Create a new event
        
        Args:
            name (str): Event name (must be unique)
            start_date (datetime): Event start date
            end_date (datetime): Event end date
            description (str, optional): Event description
            location (str, optional): Event location
            wifi_ssid (str, optional): WiFi SSID for event
            wifi_password (str, optional): WiFi password for event
            event_type (str, optional): Type of event (default: 'tactical_exercise')
            created_by (int, optional): User ID of creator
            settings (dict, optional): Additional settings as JSON
            
        Returns:
            Event: The created event instance
            
        Raises:
            ValueError: If validation fails
        """
        # Create event instance
        event = cls(
            name=name,
            description=description,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            location=location,
            wifi_ssid=wifi_ssid,
            wifi_password=wifi_password,
            created_by=created_by,
            settings=settings or {},
            is_active=True
        )
        
        # Validate dates
        is_valid, error_message = event.validate_dates()
        if not is_valid:
            raise ValueError(error_message)
        
        # Save to database
        db.session.add(event)
        db.session.commit()
        
        return event
