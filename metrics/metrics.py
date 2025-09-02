import os
import statsd
from tools.logging_config import setup_logging, format_log_message

# Set up component-specific logger
logger = setup_logging("METRICS")

# Singleton instance of StatsD client
_statsd_client = None

def get_metrics_client():
    """
    Get the singleton instance of the StatsD client.
    
    Returns:
        statsd.StatsClient: The StatsD client instance
    """
    global _statsd_client
    
    # Initialize the client if it doesn't exist
    if _statsd_client is None:
        # Get StatsD configuration from environment variables or use defaults
        statsd_host = os.environ.get('STATSD_HOST', 'localhost')
        statsd_port = int(os.environ.get('STATSD_PORT', 9125))
        
        # Initialize StatsD client
        _statsd_client = statsd.StatsClient(statsd_host, statsd_port, prefix='na_ponimanii')
        logger.info(format_log_message(
            "Initialized StatsD client",
            host=statsd_host,
            port=statsd_port
        ))
    
    return _statsd_client