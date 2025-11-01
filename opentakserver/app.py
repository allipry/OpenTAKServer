from gevent import monkey
monkey.patch_all()

import random
import sys
import traceback
import logging

from flask_migrate import Migrate, upgrade
from opentakserver.PasswordValidator import PasswordValidator

import platform
import requests
from sqlalchemy import insert
import sqlite3
from opentakserver.models.Icon import Icon
from opentakserver.plugins.Plugin import Plugin
from opentakserver.plugins.PluginManager import PluginManager
from opentakserver.sql_jobstore import SQLJobStore

import yaml
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from opentakserver.EmailValidator import EmailValidator

from logging.handlers import TimedRotatingFileHandler
import os

import colorlog
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timezone
import sqlalchemy

import flask_wtf

import pika
from flask import Flask, jsonify
from flask_cors import CORS

from flask_security import Security, SQLAlchemyUserDatastore, hash_password, uia_username_mapper, uia_email_mapper
from flask_security.models import fsqla_v3 as fsqla
from flask_security.signals import user_registered, user_authenticated

import opentakserver
from opentakserver.extensions import logger, db, socketio, mail, apscheduler
from opentakserver.defaultconfig import DefaultConfig
from opentakserver.models.WebAuthn import WebAuthn

from opentakserver.controllers.meshtastic_controller import MeshtasticController
from opentakserver.certificate_authority import CertificateAuthority

try:
    from opentakserver.mumble.mumble_ice_app import MumbleIceDaemon
except ModuleNotFoundError:
    print("Mumble auth not supported on this platform")


def init_extensions(app):
    db.init_app(app)
    Migrate(app, db)

    logger.info(f"OpenTAKServer {opentakserver.__version__}")
    logger.info("Loading the database...")
    with app.app_context():
        upgrade(directory=os.path.join(os.path.dirname(os.path.realpath(opentakserver.__file__)), 'migrations'))
        # Flask-Migrate does weird things to the logger
        logger.disabled = False
        logger.parent.handlers.pop()
        if app.config.get("DEBUG"):
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    # Handle config options that can't be serialized to yaml
    app.config.update({"SCHEDULER_JOBSTORES": {'default': SQLJobStore(url=app.config.get("SQLALCHEMY_DATABASE_URI"))}})
    identity_attributes = [{"username": {"mapper": uia_username_mapper, "case_insensitive": True}}]

    # Don't allow registration unless email is enabled
    if app.config.get("OTS_ENABLE_EMAIL"):
        identity_attributes.append({"email": {"mapper": uia_email_mapper, "case_insensitive": True}})
        app.config.update({
            "SECURITY_REGISTERABLE": True,
            "SECURITY_CONFIRMABLE": True,
            "SECURITY_RECOVERABLE": True,
            "SECURITY_TWO_FACTOR_ENABLED_METHODS": ["authenticator", "email"]
        })
    else:
        app.config.update({
            "SECURITY_REGISTERABLE": False,
            "SECURITY_CONFIRMABLE": False,
            "SECURITY_RECOVERABLE": False,
            "SECURITY_TWO_FACTOR_ENABLED_METHODS": ["authenticator"]
        })
    app.config.update({"SECURITY_USER_IDENTITY_ATTRIBUTES": identity_attributes})

    ca = CertificateAuthority(logger, app)
    ca.create_ca()

    cors = CORS(app, resources={r"/api/*": {"origins": "*"}, r"/Marti/*": {"origins": "*"}, r"/*": {"origins": "*"}},
                supports_credentials=True)
    flask_wtf.CSRFProtect(app)

    socketio_logger = False
    if app.config.get("DEBUG"):
        socketio_logger = logger
    socketio.init_app(app, logger=socketio_logger, ping_timeout=1, message_queue=f"amqp://{app.config.get('OTS_RABBITMQ_USERNAME')}:{app.config.get('OTS_RABBITMQ_PASSWORD')}@{app.config.get('OTS_RABBITMQ_SERVER_ADDRESS')}/{app.config.get('OTS_RABBITMQ_VHOST')}")

    # Debug RabbitMQ configuration
    print(f"DEBUG: RabbitMQ Host: {app.config.get('OTS_RABBITMQ_SERVER_ADDRESS')}")
    print(f"DEBUG: RabbitMQ Port: {app.config.get('OTS_RABBITMQ_PORT', 5672)}")
    print(f"DEBUG: RabbitMQ VHost: {app.config.get('OTS_RABBITMQ_VHOST', '/')}")
    print(f"DEBUG: RabbitMQ Username: {app.config.get('OTS_RABBITMQ_USERNAME', 'guest')}")
    print(f"DEBUG: RabbitMQ Password: {'***' if app.config.get('OTS_RABBITMQ_PASSWORD') else 'None'}")
    
    # RabbitMQ connection with retry logic
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            print(f"INFO: Attempting RabbitMQ connection (attempt {attempt + 1}/{max_retries})")
            
            connection_params = pika.ConnectionParameters(
                host=app.config.get("OTS_RABBITMQ_SERVER_ADDRESS", "localhost"),
                port=int(app.config.get("OTS_RABBITMQ_PORT", 5672)),
                virtual_host=app.config.get("OTS_RABBITMQ_VHOST", "/"),
                credentials=pika.PlainCredentials(
                    app.config.get("OTS_RABBITMQ_USERNAME", "guest"),
                    app.config.get("OTS_RABBITMQ_PASSWORD", "guest")
                ),
                connection_attempts=3,
                retry_delay=1,
                socket_timeout=10,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            rabbit_connection = pika.BlockingConnection(connection_params)
            channel = rabbit_connection.channel()
            
            # Test the connection by declaring exchanges
            channel.exchange_declare('cot', durable=True, exchange_type='fanout')
            print("SUCCESS: RabbitMQ connection established and tested!")
            break
            
        except pika.exceptions.AMQPConnectionError as e:
            print(f"WARNING: RabbitMQ connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"INFO: Retrying in {retry_delay} seconds...")
                import time
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"ERROR: Failed to connect to RabbitMQ after {max_retries} attempts")
                print(f"ERROR: Connection details - Host: {app.config.get('OTS_RABBITMQ_SERVER_ADDRESS', 'localhost')}, Port: {app.config.get('OTS_RABBITMQ_PORT', 5672)}, VHost: {app.config.get('OTS_RABBITMQ_VHOST', '/')}, User: {app.config.get('OTS_RABBITMQ_USERNAME', 'guest')}")
                raise
        except Exception as e:
            print(f"ERROR: Unexpected RabbitMQ connection error: {e}")
            if attempt == max_retries - 1:
                raise
    channel.exchange_declare('dms', durable=True, exchange_type='direct')
    channel.exchange_declare('chatrooms', durable=True, exchange_type='direct')
    channel.queue_declare(queue='cot_controller')
    channel.exchange_declare(exchange='cot_controller', exchange_type='fanout')
    channel.exchange_declare("missions", durable=True, exchange_type='topic')  # For Data Sync mission feeds

    if not apscheduler.running:
        apscheduler.init_app(app)
        apscheduler.start(paused=False)

    try:
        fsqla.FsModels.set_db_info(db)
    except sqlalchemy.exc.InvalidRequestError:
        pass

    from opentakserver.models.user import User
    from opentakserver.models.role import Role

    user_datastore = SQLAlchemyUserDatastore(db, User, Role, WebAuthn)
    app.security = Security(app, user_datastore, mail_util_cls=EmailValidator, password_util_cls=PasswordValidator)

    mail.init_app(app)


def setup_logging(app):
    level = logging.INFO
    if app.config.get("DEBUG"):
        level = logging.DEBUG
    logger.setLevel(level)

    if sys.stdout.isatty():
        color_log_handler = colorlog.StreamHandler()
        color_log_formatter = colorlog.ColoredFormatter(
            '%(log_color)s[%(asctime)s] - OpenTAKServer[%(process)d] - %(module)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
        color_log_handler.setFormatter(color_log_formatter)
        logger.addHandler(color_log_handler)
        logger.info("Added color logger")

    os.makedirs(os.path.join(app.config.get("OTS_DATA_FOLDER"), "logs"), exist_ok=True)
    fh = TimedRotatingFileHandler(os.path.join(app.config.get("OTS_DATA_FOLDER"), 'logs', 'opentakserver.log'),
                                  when=app.config.get("OTS_LOG_ROTATE_WHEN"), interval=app.config.get("OTS_LOG_ROTATE_INTERVAL"),
                                  backupCount=app.config.get("OTS_BACKUP_COUNT"))
    fh.setFormatter(logging.Formatter("[%(asctime)s] - OpenTAKServer[%(process)d] - %(module)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s"))
    logger.addHandler(fh)


def create_app():
    app = Flask(__name__)
    app.config.from_object(DefaultConfig)
    
    setup_logging(app)

    # Load config.yml if it exists
    if os.path.exists(os.path.join(app.config.get("OTS_DATA_FOLDER"), "config.yml")):
        app.config.from_file(os.path.join(app.config.get("OTS_DATA_FOLDER"), "config.yml"), load=yaml.safe_load)
        print("DEBUG: Loaded config.yml file")
    else:
        # First run, created config.yml based on default settings
        logger.info("Creating config.yml")
        with open(os.path.join(app.config.get("OTS_DATA_FOLDER"), "config.yml"), "w") as config:
            conf = {}
            for option in DefaultConfig.__dict__:
                # Fix the sqlite DB path on Windows
                if option == "SQLALCHEMY_DATABASE_URI" and platform.system() == "Windows" and DefaultConfig.__dict__[option].startswith("sqlite"):
                    conf[option] = DefaultConfig.__dict__[option].replace("////", "///").replace("\\", "/")
                elif option.isupper():
                    conf[option] = DefaultConfig.__dict__[option]
            config.write(yaml.safe_dump(conf))

    # Load environment variables into Flask config AFTER config.yml
    # This ensures environment variables override both default config and config.yml
    env_vars_loaded = 0
    for key, value in os.environ.items():
        if key.startswith('OTS_') or key in ['POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'DATABASE_URL', 'SQLALCHEMY_DATABASE_URI']:
            app.config[key] = value
            env_vars_loaded += 1
    
    # Ensure DATABASE_URL is used as SQLALCHEMY_DATABASE_URI if available
    if os.environ.get('DATABASE_URL') and not os.environ.get('SQLALCHEMY_DATABASE_URI'):
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
        env_vars_loaded += 1
        print(f"INFO: Using DATABASE_URL as SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    elif os.environ.get('SQLALCHEMY_DATABASE_URI'):
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')
        print(f"INFO: Using SQLALCHEMY_DATABASE_URI from environment: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    print(f"INFO: Loaded {env_vars_loaded} environment variables into Flask config")
    
    # Validate critical configuration values
    critical_configs = {
        'OTS_RABBITMQ_SERVER_ADDRESS': app.config.get('OTS_RABBITMQ_SERVER_ADDRESS'),
        'OTS_RABBITMQ_USERNAME': app.config.get('OTS_RABBITMQ_USERNAME'),
        'OTS_RABBITMQ_PASSWORD': app.config.get('OTS_RABBITMQ_PASSWORD'),
        'OTS_RABBITMQ_VHOST': app.config.get('OTS_RABBITMQ_VHOST'),
        'OTS_RABBITMQ_PORT': app.config.get('OTS_RABBITMQ_PORT')
    }
    
    missing_configs = [key for key, value in critical_configs.items() if not value]
    if missing_configs:
        print(f"ERROR: Missing critical configuration: {missing_configs}")
        print("INFO: Using default values for missing configuration")
    
    # Debug: Print RabbitMQ configuration after all config loading
    print(f"INFO: RabbitMQ Configuration:")
    print(f"  Server: {app.config.get('OTS_RABBITMQ_SERVER_ADDRESS', 'localhost')}")
    print(f"  Username: {app.config.get('OTS_RABBITMQ_USERNAME', 'guest')}")
    print(f"  VHost: {app.config.get('OTS_RABBITMQ_VHOST', '/')}")
    print(f"  Port: {app.config.get('OTS_RABBITMQ_PORT', 5672)}")
    print(f"  Password: {'***' if app.config.get('OTS_RABBITMQ_PASSWORD') else 'None'}")

    # Try to set the MediaMTX token
    if app.config.get("OTS_MEDIAMTX_ENABLE"):
        try:
            new_conf = None
            with open(os.path.join(app.config.get("OTS_DATA_FOLDER"), "mediamtx", "mediamtx.yml"), "r") as mediamtx_config:
                conf = mediamtx_config.read()
                if "MTX_TOKEN" in conf:
                    new_conf = conf.replace("MTX_TOKEN", app.config.get("OTS_MEDIAMTX_TOKEN"))
            if new_conf:
                with open(os.path.join(app.config.get("OTS_DATA_FOLDER"), "mediamtx", "mediamtx.yml"), "w") as mediamtx_config:
                    mediamtx_config.write(new_conf)
        except BaseException as e:
            logger.error("Failed to set MediaMTX token: {}".format(e))
    else:
        logger.info("MediaMTX disabled")

    init_extensions(app)

    from opentakserver.blueprints.marti_api import marti_blueprint
    app.register_blueprint(marti_blueprint)

    # Note: Marti Authentication and Registration APIs now loaded via MAGK extension below
    
    # Register custom API endpoints (team management, etc.) BEFORE deprecation
    try:
        import sys
        sys.path.insert(0, '/app')
        from api.team_api import team_bp
        app.register_blueprint(team_bp)
        logger.info("✅ Registered team management API")
    except Exception as e:
        logger.warning(f"⚠️  Could not register team API: {e}")
    
    # Register API deprecation notices for non-Marti endpoints
    from opentakserver.api_deprecation_notice import deprecation_bp
    app.register_blueprint(deprecation_bp)

    from opentakserver.blueprints.ots_api import ots_api
    app.register_blueprint(ots_api)

    from opentakserver.blueprints.ots_socketio import ots_socketio_blueprint
    app.register_blueprint(ots_socketio_blueprint)

    from opentakserver.blueprints.cli import ots
    app.cli.add_command(ots, name="ots")

    from opentakserver.blueprints.scheduled_jobs import scheduler_blueprint
    app.register_blueprint(scheduler_blueprint)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)

    # Apply custom integrations
    # MAGK Extension Integration (volume-based, no patching)
    try:
        if os.environ.get('MAGK_ENABLED', 'true').lower() == 'true':
            from opentakserver.magk import init_magk
            app = init_magk(app)
            logger.info("✅ MAGK extension initialized successfully")
    except ImportError as e:
        logger.warning(f"⚠️  MAGK extension not found: {e}")
    except Exception as e:
        logger.error(f"❌ MAGK extension failed to load: {e}")
        import traceback
        logger.error(traceback.format_exc())

    return app


app = create_app()


@app.route("/")
def home():
    return jsonify([])


@app.after_request
def after_request_func(response):
    response.direct_passthrough = False
    return response


@user_registered.connect_via(app)
def user_registered_sighandler(app, user, confirmation_token, **kwargs):
    default_role = app.security.datastore.find_or_create_role(
        name="user", permissions={"user-read", "user-write"}
    )
    app.security.datastore.add_role_to_user(user, default_role)
    
    # Log user registration activity
    try:
        from opentakserver.magk.models.activity_log import ActivityLog
        from flask import request
        
        ActivityLog.log_activity(
            activity_type='user_registered',
            description=f'New user registered: {user.username}',
            user_id=user.id,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None,
            request_method='POST',
            request_path='/register',
            status_code=201,
            metadata={
                'email': user.email,
                'confirmation_required': confirmation_token is not None
            },
            resource_type='user',
            resource_id=user.id,
            success=True
        )
        logger.info(f"Activity logged: User registration for {user.username}")
    except Exception as e:
        logger.error(f"Failed to log user registration activity: {e}")


@user_authenticated.connect_via(app)
def user_authenticated_sighandler(app, user, **kwargs):
    """
    Signal handler for user authentication (login)
    Logs successful login attempts to activity_log table
    """
    try:
        from opentakserver.magk.models.activity_log import ActivityLog
        from flask import request
        
        ActivityLog.log_activity(
            activity_type='user_login',
            description=f'User logged in: {user.username}',
            user_id=user.id,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None,
            request_method=request.method if request else None,
            request_path=request.path if request else None,
            status_code=200,
            metadata={
                'email': user.email,
                'login_count': user.login_count if hasattr(user, 'login_count') else None
            },
            resource_type='user',
            resource_id=user.id,
            success=True
        )
        logger.info(f"Activity logged: User login for {user.username}")
    except Exception as e:
        logger.error(f"Failed to log user login activity: {e}")


def main():
    with app.app_context():
        # Download the icon sets if they aren't already in the DB
        icons = db.session.query(Icon).count()
        if icons == 0:
            logger.info("Downloading icons...")
            try:
                r = requests.get("https://github.com/brian7704/OpenTAKServer-Installer/raw/master/iconsets.sqlite", stream=True)
                with open(os.path.join(app.config.get("OTS_DATA_FOLDER"), "icons.sqlite"), "wb") as f:
                    f.write(r.content)

                def dict_factory(cursor, row):
                    d = {}
                    for idx, col in enumerate(cursor.description):
                        d[col[0]] = row[idx]
                    return d

                con = sqlite3.connect(os.path.join(app.config.get("OTS_DATA_FOLDER"), "icons.sqlite"))
                con.row_factory = dict_factory
                cur = con.cursor()
                rows = cur.execute("SELECT * FROM icons")
                for row in rows:
                    db.session.execute(insert(Icon).values(**row))
                db.session.commit()
            except BaseException as e:
                logger.error("Failed to download icons: {}".format(e))

        if app.config.get("DEBUG"):
            logger.debug("Starting in debug mode")
        else:
            logger.info("Starting in production mode")

        app.security.datastore.find_or_create_role(
            name="user", permissions={"user-read", "user-write"}
        )

        app.security.datastore.find_or_create_role(
            name="administrator", permissions={"administrator"}
        )

        if not app.security.datastore.find_user(username="administrator"):
            logger.info("Creating administrator account. The password is 'password'")
            app.security.datastore.create_user(username="administrator",
                                               password=hash_password("password"), roles=["administrator"])
        db.session.commit()

    if app.config.get("OTS_ENABLE_MESHTASTIC"):
        mestastic_thread = MeshtasticController(app.app_context())
        app.mestastic_thread = mestastic_thread
    else:
        app.meshtastic_thread = None

    if app.config.get("OTS_ENABLE_MUMBLE_AUTHENTICATION"):
        try:
            logger.info("Starting Mumble authentication handler")
            mumble_daemon = MumbleIceDaemon(app, logger)
            mumble_daemon.daemon = True
            mumble_daemon.start()
        except BaseException as e:
            logger.error("Failed to enable Mumble authentication: {}".format(e))
            logger.error(traceback.format_exc())
    else:
        logger.info("Mumble authentication handler disabled")

    if app.config.get("OTS_ENABLE_PLUGINS"):
        try:
            app.plugin_manager = PluginManager(Plugin.group, app)
            app.plugin_manager.load_plugins()
            app.plugin_manager.activate(app)
        except BaseException as e:
            logger.error(f"Failed to load plugins: {e}")
            logger.debug(traceback.format_exc())

    app.start_time = datetime.now(timezone.utc)

    try:
        socketio.run(app, host=app.config.get("OTS_LISTENER_ADDRESS"), port=app.config.get("OTS_LISTENER_PORT"),
                     debug=app.config.get("DEBUG"), log_output=app.config.get("DEBUG"), use_reloader=False)
    except KeyboardInterrupt:
        logger.warning("Caught CTRL+C, exiting...")
        if app.config.get("OTS_ENABLE_PLUGINS"):
            app.plugin_manager.stop_plugins()


if __name__ == '__main__':
    main()
