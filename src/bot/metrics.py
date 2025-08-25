"""
Prometheus metrics for the Telegram bot.
"""
import time
from prometheus_client import Counter, Histogram, start_http_server

# Define metrics
COMMAND_COUNTER = Counter(
    'na_ponimanii_bot_commands_total', 
    'Total number of commands received by the bot',
    ['command']
)

MESSAGE_COUNTER = Counter(
    'na_ponimanii_bot_messages_total', 
    'Total number of messages received by the bot'
)

REQUEST_LATENCY = Histogram(
    'na_ponimanii_bot_request_latency_seconds', 
    'Latency of requests to the server API',
    ['endpoint']
)

TOPIC_COUNTER = Counter(
    'na_ponimanii_bot_topics_total', 
    'Total number of topics added',
    ['source']  # 'user' or 'related'
)

EXPLANATION_COUNTER = Counter(
    'na_ponimanii_bot_explanations_total', 
    'Total number of explanations generated'
)

def start_metrics_server(port=8001):
    """Start the Prometheus metrics server on the specified port."""
    start_http_server(port)
    return port

class LatencyTimer:
    """Context manager for measuring request latency."""
    
    def __init__(self, endpoint):
        self.endpoint = endpoint
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        latency = time.time() - self.start_time
        REQUEST_LATENCY.labels(endpoint=self.endpoint).observe(latency)