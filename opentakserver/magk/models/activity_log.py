#!/usr/bin/env python3
"""
ActivityLog Model for MAGK Extension
Maps to the activity_log table created in database migration
Tracks user activities and system events
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import INET, JSONB
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

# Get db instance from Flask app
db = SQLAlchemy()

class ActivityLog(db.Model):
    """
    ActivityLog model for tracking user activities and system events
    Maps to activity_log table created in 05-activity-log-schema.sql
    """
    __tablename__ = 'activity_log'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # User reference (nullable for system activities)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    
    # Activity information
    activity_type = Column(String(50), nullable=False)
    activity_description = Column(Text)
    
    # Request information
    ip_address = Column(INET)
    user_agent = Column(Text)
    request_method = Column(String(10))
    request_path = Column(Text)
    status_code = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Flexible metadata storage (using activity_metadata to avoid SQLAlchemy reserved name)
    activity_metadata = Column('metadata', JSONB, default=dict)
    
    # Session tracking
    session_id = Column(String(255))
    
    # Resource tracking
    resource_type = Column(String(50))
    resource_id = Column(Integer)
    
    # Result tracking
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Relationship to User model (Flask-Security)
    user = relationship('User', foreign_keys=[user_id], backref='activity_logs')
    
    def to_dict(self):
        """
        Convert ActivityLog instance to dictionary for JSON serialization
        Handles null user references (deleted users)
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'user_email': self.user.email if self.user else None,
            'activity_type': self.activity_type,
            'activity_description': self.activity_description,
            'ip_address': str(self.ip_address) if self.ip_address else None,
            'user_agent': self.user_agent,
            'request_method': self.request_method,
            'request_path': self.request_path,
            'status_code': self.status_code,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'metadata': self.activity_metadata,
            'session_id': self.session_id,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'success': self.success,
            'error_message': self.error_message
        }
    
    def __repr__(self):
        """String representation for debugging"""
        return f'<ActivityLog {self.id}: {self.activity_type} by user {self.user_id}>'
