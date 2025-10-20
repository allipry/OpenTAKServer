#!/usr/bin/env python3
"""
Database utility functions for MAGK-Admin
Provides secure database connections using environment variables
"""

import os
import psycopg2
import logging

logger = logging.getLogger(__name__)

def get_database_connection():
    """
    Get a database connection using environment variables
    Returns a psycopg2 connection object
    """
    try:
        conn = psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "ots-postgresql"),
            database=os.environ.get("POSTGRES_DB", "opentakserver"),
            user=os.environ.get("POSTGRES_USER", "ots"),
            password=os.environ.get("POSTGRES_PASSWORD"),
            port=int(os.environ.get("POSTGRES_PORT", "5432"))
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def get_database_config():
    """
    Get database configuration from environment variables
    Returns a dictionary with database configuration
    """
    return {
        'host': os.environ.get("POSTGRES_HOST", "ots-postgresql"),
        'database': os.environ.get("POSTGRES_DB", "opentakserver"),
        'user': os.environ.get("POSTGRES_USER", "ots"),
        'password': os.environ.get("POSTGRES_PASSWORD"),
        'port': int(os.environ.get("POSTGRES_PORT", "5432"))
    }

def get_database_uri():
    """
    Get database URI for SQLAlchemy
    Returns a database URI string
    """
    config = get_database_config()
    return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"