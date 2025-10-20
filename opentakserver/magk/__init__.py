"""
MAGK Extension for OpenTAKServer
Auto-discovers and registers all MAGK blueprints without patching OTS code
"""

import os
import sys
import logging
from pathlib import Path
from flask import Blueprint

logger = logging.getLogger(__name__)

def discover_blueprints(app):
    """
    Auto-discover and register all MAGK blueprints
    """
    blueprints_registered = 0
    
    try:
        # Get blueprints directory
        magk_dir = Path(__file__).parent
        blueprints_dir = magk_dir / 'blueprints'
        
        if not blueprints_dir.exists():
            logger.warning(f"MAGK blueprints directory not found: {blueprints_dir}")
            return 0
        
        # Import each blueprint module
        for blueprint_file in blueprints_dir.glob('*.py'):
            if blueprint_file.name.startswith('_'):
                continue
            
            module_name = f'opentakserver.magk.blueprints.{blueprint_file.stem}'
            
            try:
                # Import the module
                module = __import__(module_name, fromlist=[''])
                
                # Find and register blueprints
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, Blueprint):
                        app.register_blueprint(attr)
                        logger.info(f"✅ Registered MAGK blueprint: {attr.name} at {attr.url_prefix}")
                        blueprints_registered += 1
                        
            except Exception as e:
                logger.error(f"❌ Failed to load MAGK blueprint {module_name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        return blueprints_registered
        
    except Exception as e:
        logger.error(f"❌ MAGK blueprint discovery failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def init_magk(app):
    """
    Initialize MAGK extension
    """
    logger.info("🚀 Initializing MAGK extension...")
    
    # Discover and register blueprints
    count = discover_blueprints(app)
    
    if count > 0:
        logger.info(f"✅ MAGK extension initialized: {count} blueprints registered")
    else:
        logger.warning("⚠️  No MAGK blueprints registered")
    
    return app
