#!/usr/bin/env python3
"""
Direct Database Teams Module
Provides direct database access for team information
"""

import logging
from opentakserver.database_utils import get_database_connection

logger = logging.getLogger(__name__)

def get_teams_from_db():
    """
    Get teams directly from the database
    Returns a list of team dictionaries
    """
    try:
        # Connect to database
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Get all active teams
        cursor.execute("""
            SELECT id, name, description, team_type, max_members, color
            FROM teams 
            WHERE is_active = true 
            ORDER BY name
        """)
        
        teams = []
        for row in cursor.fetchall():
            teams.append({
                "id": row[0],
                "name": row[1],
                "description": row[2] or f"{row[1]} tactical team",
                "type": row[3] or "standard",
                "maxMembers": row[4],
                "color": row[5]
            })
        
        cursor.close()
        conn.close()
        
        logger.info(f"Retrieved {len(teams)} teams from database")
        return teams
        
    except Exception as e:
        logger.error(f"Error getting teams from database: {e}")
        # Return fallback teams if database fails
        return [
            {
                "id": 1,
                "name": "Blue Team",
                "description": "Default blue team for tactical operations",
                "type": "standard",
                "maxMembers": None,
                "color": "#0066cc"
            },
            {
                "id": 2,
                "name": "Red Team", 
                "description": "Default red team for opposing force",
                "type": "standard",
                "maxMembers": None,
                "color": "#cc0000"
            },
            {
                "id": 3,
                "name": "Green Team",
                "description": "Default green team for support operations", 
                "type": "standard",
                "maxMembers": None,
                "color": "#00cc00"
            },
            {
                "id": 4,
                "name": "Admin Team",
                "description": "Administrative team with elevated privileges",
                "type": "admin", 
                "maxMembers": None,
                "color": "#666666"
            }
        ]

def get_events_from_db():
    """
    Get events directly from the database
    Returns a list of event dictionaries
    """
    try:
        # Connect to database
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Get all active events
        cursor.execute("""
            SELECT id, name, description, event_type, is_active, start_date, end_date
            FROM events 
            WHERE is_active = true 
            ORDER BY name
        """)
        
        events = []
        for row in cursor.fetchall():
            events.append({
                "id": row[0],
                "name": row[1],
                "description": row[2] or f"{row[1]} tactical operation",
                "type": row[3] or "operational",
                "active": row[4],
                "start_date": row[5].isoformat() if row[5] else None,
                "end_date": row[6].isoformat() if row[6] else None
            })
        
        cursor.close()
        conn.close()
        
        logger.info(f"Retrieved {len(events)} events from database")
        return events
        
    except Exception as e:
        logger.error(f"Error getting events from database: {e}")
        # Return fallback events if database fails
        return [
            {
                "id": 1,
                "name": "Default Operation",
                "description": "Default tactical operation context",
                "type": "operational",
                "active": True
            },
            {
                "id": 2,
                "name": "SOKOL",
                "description": "Operation SOKOL tactical exercise",
                "type": "exercise", 
                "active": True
            },
            {
                "id": 3,
                "name": "Training Exercise 2025",
                "description": "Annual training exercise",
                "type": "training",
                "active": True
            },
            {
                "id": 4,
                "name": "Field Operations - January",
                "description": "Monthly field operations",
                "type": "operational",
                "active": True
            },
            {
                "id": 5,
                "name": "Emergency Response Drill",
                "description": "Emergency response training",
                "type": "drill",
                "active": True
            }
        ]