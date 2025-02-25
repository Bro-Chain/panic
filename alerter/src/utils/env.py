import os

"""
This module is here to reduce any ambiguity with environment variables and
types. We use `os.getenv()` to define a default value in the case that the
key is not present. This way, we can decide if each environment variable is
mandatory or not, and if not what the default value is. We can also use this
to typecast values.

This also ensures all mandatory values are present before running by
initialising the class 
"""

# Alerter configuration
UNIQUE_ALERTER_IDENTIFIER = os.environ['UNIQUE_ALERTER_IDENTIFIER']

# Mongo configuration
DB_IP = os.environ['DB_IP']
DB_PORT = os.environ['DB_PORT']
DB_USERNAME = os.environ['DB_USERNAME']
DB_PASSWORD = os.environ['DB_PASSWORD']

# Redis configuration
REDIS_IP = os.environ['REDIS_IP']
REDIS_PORT = int(os.environ['REDIS_PORT'])
REDIS_DB = int(os.environ['REDIS_DB'])

# RabbitMQ configuration
RABBIT_IP = os.environ['RABBIT_IP']
RABBIT_PORT = int(os.environ['RABBIT_PORT'])

# Substrate API IP
SUBSTRATE_API_IP = os.environ['SUBSTRATE_API_IP']
SUBSTRATE_API_PORT = int(os.environ['SUBSTRATE_API_PORT'])

# Logs configuration
LOGGING_LEVEL = os.environ['LOGGING_LEVEL']
DATA_STORE_LOG_FILE_TEMPLATE = os.environ['DATA_STORE_LOG_FILE_TEMPLATE']
MONITORS_LOG_FILE_TEMPLATE = os.environ['MONITORS_LOG_FILE_TEMPLATE']
TRANSFORMERS_LOG_FILE_TEMPLATE = os.environ['TRANSFORMERS_LOG_FILE_TEMPLATE']
MANAGERS_LOG_FILE_TEMPLATE = os.environ['MANAGERS_LOG_FILE_TEMPLATE']
ALERTERS_LOG_FILE_TEMPLATE = os.environ['ALERTERS_LOG_FILE_TEMPLATE']
ALERT_ROUTER_LOG_FILE = os.environ['ALERT_ROUTER_LOG_FILE']
CONFIG_MANAGER_LOG_FILE = os.environ['CONFIG_MANAGER_LOG_FILE']
CHANNEL_HANDLERS_LOG_FILE_TEMPLATE = \
    os.environ['CHANNEL_HANDLERS_LOG_FILE_TEMPLATE']
ALERTS_LOG_FILE = os.environ['ALERTS_LOG_FILE']
HEALTH_CHECKER_LOG_FILE_TEMPLATE = os.environ[
    'HEALTH_CHECKER_LOG_FILE_TEMPLATE']

# GitHub monitoring configuration
GITHUB_RELEASES_TEMPLATE = os.environ['GITHUB_RELEASES_TEMPLATE']

# DockerHub monitoring configuration
DOCKERHUB_TAGS_TEMPLATE = os.environ['DOCKERHUB_TAGS_TEMPLATE']

# Monitoring periods
SYSTEM_MONITOR_PERIOD_SECONDS = int(os.environ['SYSTEM_MONITOR_PERIOD_SECONDS'])
GITHUB_MONITOR_PERIOD_SECONDS = int(os.environ['GITHUB_MONITOR_PERIOD_SECONDS'])
DOCKERHUB_MONITOR_PERIOD_SECONDS = \
    int(os.environ['DOCKERHUB_MONITOR_PERIOD_SECONDS'])
NODE_MONITOR_PERIOD_SECONDS = int(os.environ['NODE_MONITOR_PERIOD_SECONDS'])
CHAINLINK_CONTRACTS_MONITOR_PERIOD_SECONDS = int(
    os.environ['CHAINLINK_CONTRACTS_MONITOR_PERIOD_SECONDS'])
NETWORK_MONITOR_PERIOD_SECONDS = int(
    os.environ['NETWORK_MONITOR_PERIOD_SECONDS'])
# These define how often a monitor runs an iteration of its monitoring loop

# Publishers limits
DATA_TRANSFORMER_PUBLISHING_QUEUE_SIZE = int(
    os.environ['DATA_TRANSFORMER_PUBLISHING_QUEUE_SIZE'])
ALERTER_PUBLISHING_QUEUE_SIZE = int(os.environ['ALERTER_PUBLISHING_QUEUE_SIZE'])
CHANNELS_MANAGER_PUBLISHING_QUEUE_SIZE = int(
    os.environ['CHANNELS_MANAGER_PUBLISHING_QUEUE_SIZE'])
ALERT_ROUTER_PUBLISHING_QUEUE_SIZE = int(
    os.environ['ALERT_ROUTER_PUBLISHING_QUEUE_SIZE'])
CONFIG_PUBLISHING_QUEUE_SIZE = int(
    os.environ['CONFIG_PUBLISHING_QUEUE_SIZE'])

# Console Output
ENABLE_CONSOLE_ALERTS: bool = \
    os.getenv('ENABLE_CONSOLE_ALERTS', False).lower() in (
        True, "true", "yes", "y")

# Log Alerts
ENABLE_LOG_ALERTS: bool = \
    os.getenv('ENABLE_LOG_ALERTS', False).lower() in (
        True, "true", "yes", "y")

# Twilio Preferences
TWIML = os.environ['TWIML']
TWIML_IS_URL = os.environ['TWIML_IS_URL'].lower() in ["true", "yes", "y"]