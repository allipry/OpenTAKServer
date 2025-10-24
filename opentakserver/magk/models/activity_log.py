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
from opentakserver.extensions import db

class ActivityLog(db.Model):
    """
    ActivityLog model for tracking user activities and system events
    Maps to activity_log table created in 05-activity-log-schema.sql
    """
    __tablename__ = 'activity_log'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # User reference (nullable for system activities)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=True)
    
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
    # Note: Relationship removed to avoid mapper initialization issues
    # Use user_id directly and query User model separately if needed
    
    def to_dict(self):
        """
        Convert ActivityLog instance to dictionary for JSON serialization
        Handles null user references (deleted users)
        """
        # Get user info if user_id exists
        username = None
        user_email = None
        if self.user_id:
            try:
                from opentakserver.models.user import User
                user = User.query.get(self.user_id)
                if user:
                    username = user.username
                    user_email = user.email
            except:
                pass
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': username,
            'user_email': user_email,
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
    
    @classmethod
    def get_activity_summary(cls, days=7):
        """
        Get activity summary statistics for the specified number of days
        
        Args:
            days (int): Number of days to include in summary (default: 7)
            
        Returns:
            dict: Activity summary with counts by type and success rate
        """
        from datetime import timedelta
        from sqlalchemy import func
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get activities in date range
        activities = cls.query.filter(
            cls.created_at >= start_date,
            cls.created_at <= end_date
        ).all()
        
        # Calculate statistics
        total_activities = len(activities)
        successful_activities = len([a for a in activities if a.success])
        failed_activities = total_activities - successful_activities
        
        # Count by activity type
        activity_types = {}
        for activity in activities:
            activity_type = activity.activity_type
            if activity_type not in activity_types:
                activity_types[activity_type] = {'total': 0, 'successful': 0, 'failed': 0}
            
            activity_types[activity_type]['total'] += 1
            if activity.success:
                activity_types[activity_type]['successful'] += 1
            else:
                activity_types[activity_type]['failed'] += 1
        
        return {
            'time_period_days': days,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_activities': total_activities,
            'successful_activities': successful_activities,
            'failed_activities': failed_activities,
            'success_rate': (successful_activities / total_activities * 100) if total_activities > 0 else 0,
            'activity_types': activity_types
        }
    
    @classmethod
    def get_activity_types(cls):
        """
        Get list of all distinct activity types in the database
        
        Returns:
            list: List of activity type strings
        """
        from sqlalchemy import distinct
        
        types = db.session.query(distinct(cls.activity_type)).all()
        return [t[0] for t in types if t[0]]
    
    @classmethod
    def log_activity(cls, activity_type, user_id=None, description=None, 
                    ip_address=None, user_agent=None, request_method=None,
                    request_path=None, status_code=None, metadata=None,
                    session_id=None, resource_type=None, resource_id=None,
                    success=True, error_message=None):
        """
        Create and save a new activity log entry
        
        Args:
            activity_type (str): Type of activity (e.g., 'user_login', 'user_logout')
            user_id (int, optional): ID of user performing the activity
            description (str, optional): Human-readable description
            ip_address (str, optional): IP address of request
            user_agent (str, optional): User agent string
            request_method (str, optional): HTTP method (GET, POST, etc.)
            request_path (str, optional): Request path
            status_code (int, optional): HTTP status code
            metadata (dict, optional): Additional metadata as JSON
            session_id (str, optional): Session identifier
            resource_type (str, optional): Type of resource affected
            resource_id (int, optional): ID of resource affected
            success (bool, optional): Whether activity was successful (default: True)
            error_message (str, optional): Error message if activity failed
            
        Returns:
            ActivityLog: The created activity log entry
        """
        activity = cls(
            activity_type=activity_type,
            user_id=user_id,
            activity_description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            status_code=status_code,
            activity_metadata=metadata or {},
            session_id=session_id,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            error_message=error_message
        )
        
        db.session.add(activity)
        db.session.commit()
        
        return activity
