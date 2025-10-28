#!/usr/bin/env python3
"""
EventTeam Model for MAGK Extension
Maps to the event_teams junction table created in database migration
Manages many-to-many relationships between events and teams
"""

from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime, timezone
from opentakserver.extensions import db

class EventTeam(db.Model):
    """
    EventTeam model for event-team associations
    Maps to event_teams table created in 06-events-schema.sql
    Junction table for many-to-many relationship between events and teams
    """
    __tablename__ = 'event_teams'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Foreign keys
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False)
    
    # Configuration
    max_participants = Column(Integer, nullable=True)  # NULL means unlimited
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Unique constraint: one event-team combination
    __table_args__ = (
        UniqueConstraint('event_id', 'team_id', name='uq_event_team'),
    )
    
    def to_dict(self, include_event=False, include_team=False):
        """
        Convert EventTeam instance to dictionary for JSON serialization
        
        Args:
            include_event (bool): Whether to include event details
            include_team (bool): Whether to include team details
            
        Returns:
            dict: EventTeam data as dictionary
        """
        event_team_dict = {
            'id': self.id,
            'event_id': self.event_id,
            'team_id': self.team_id,
            'max_participants': self.max_participants,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        # Include event details if requested
        if include_event:
            from opentakserver.magk.models.event import Event
            event = Event.query.get(self.event_id)
            if event:
                event_team_dict['event'] = {
                    'id': event.id,
                    'name': event.name,
                    'start_date': event.start_date.isoformat() if event.start_date else None,
                    'end_date': event.end_date.isoformat() if event.end_date else None
                }
        
        # Include team details if requested
        if include_team:
            # Import here to avoid circular imports
            try:
                from opentakserver.models.team import Team
                team = Team.query.get(self.team_id)
                if team:
                    event_team_dict['team'] = {
                        'id': team.id,
                        'name': team.name,
                        'color': team.color if hasattr(team, 'color') else None
                    }
            except ImportError:
                # Team model might not exist yet
                pass
        
        return event_team_dict
    
    def __repr__(self):
        """String representation for debugging"""
        return f'<EventTeam event_id={self.event_id} team_id={self.team_id}>'
    
    def get_participant_count(self):
        """
        Get current participant count for this team in this event
        
        Returns:
            int: Number of participants
        """
        try:
            from sqlalchemy import text
            result = db.session.execute(
                text("""
                    SELECT COUNT(DISTINCT ut.user_id)
                    FROM user_teams ut
                    WHERE ut.team_id = :team_id
                    AND ut.is_active = true
                """),
                {'team_id': self.team_id}
            )
            count = result.scalar()
            return count if count is not None else 0
        except Exception as e:
            print(f"Error getting participant count: {e}")
            return 0
    
    def is_full(self):
        """
        Check if this team has reached max_participants for this event
        
        Returns:
            bool: True if team is full, False otherwise
        """
        if self.max_participants is None:
            return False  # Unlimited participants
        
        current_count = self.get_participant_count()
        return current_count >= self.max_participants
    
    def can_add_participant(self):
        """
        Check if a new participant can be added to this team for this event
        
        Returns:
            bool: True if participant can be added, False otherwise
        """
        return self.is_active and not self.is_full()
    
    @classmethod
    def get_teams_for_event(cls, event_id, active_only=True):
        """
        Get all teams associated with an event
        
        Args:
            event_id (int): Event ID
            active_only (bool): Whether to return only active associations (default: True)
            
        Returns:
            list: List of EventTeam instances
        """
        query = cls.query.filter_by(event_id=event_id)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        return query.all()
    
    @classmethod
    def get_events_for_team(cls, team_id, active_only=True):
        """
        Get all events associated with a team
        
        Args:
            team_id (int): Team ID
            active_only (bool): Whether to return only active associations (default: True)
            
        Returns:
            list: List of EventTeam instances
        """
        query = cls.query.filter_by(team_id=team_id)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        return query.all()
    
    @classmethod
    def create_association(cls, event_id, team_id, max_participants=None):
        """
        Create a new event-team association
        
        Args:
            event_id (int): Event ID
            team_id (int): Team ID
            max_participants (int, optional): Maximum participants for this team in this event
            
        Returns:
            EventTeam: The created association
            
        Raises:
            ValueError: If association already exists
        """
        # Check if association already exists
        existing = cls.query.filter_by(
            event_id=event_id,
            team_id=team_id
        ).first()
        
        if existing:
            raise ValueError(f"Association between event {event_id} and team {team_id} already exists")
        
        # Create new association
        event_team = cls(
            event_id=event_id,
            team_id=team_id,
            max_participants=max_participants,
            is_active=True
        )
        
        db.session.add(event_team)
        db.session.commit()
        
        return event_team
    
    @classmethod
    def update_association(cls, event_id, team_id, max_participants=None, is_active=None):
        """
        Update an existing event-team association
        
        Args:
            event_id (int): Event ID
            team_id (int): Team ID
            max_participants (int, optional): New maximum participants
            is_active (bool, optional): New active status
            
        Returns:
            EventTeam: The updated association
            
        Raises:
            ValueError: If association doesn't exist
        """
        event_team = cls.query.filter_by(
            event_id=event_id,
            team_id=team_id
        ).first()
        
        if not event_team:
            raise ValueError(f"Association between event {event_id} and team {team_id} not found")
        
        # Update fields if provided
        if max_participants is not None:
            event_team.max_participants = max_participants
        
        if is_active is not None:
            event_team.is_active = is_active
        
        db.session.commit()
        
        return event_team
