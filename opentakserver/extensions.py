import colorlog
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from opentakserver.models.Base import Base
from flask_mailman import Mail
from flask_apscheduler import APScheduler

logger = colorlog.getLogger('OpenTAKServer')

mail = Mail()

apscheduler = APScheduler()

db = SQLAlchemy(model_class=Base)

socketio = SocketIO(
    async_mode='gevent',
    cors_allowed_origins='*',  # Allow all origins for Socket.IO
    logger=True,
    engineio_logger=True,  # Enable detailed error logging
    # Force WebSocket-only transport to avoid session routing issues
    # Polling transport can cause "Invalid session" errors with multiple workers
    # because session is created on one worker but POST requests hit different workers
    transports=['websocket'],
    allow_upgrades=False,  # No upgrade from polling needed since we only use websocket
    ping_timeout=60,
    ping_interval=25
)

migrate = Migrate()
