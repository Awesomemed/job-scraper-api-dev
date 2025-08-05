"""
Gunicorn configuration file for handling long-running requests
"""

# Worker configuration
workers = 4
worker_class = 'sync'
worker_connections = 1000

# Timeout configuration
timeout = 1800  # 30 minutes timeout (increased from default 30 seconds)
keepalive = 5
graceful_timeout = 300  # 5 minutes for graceful shutdown

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Server socket
bind = '0.0.0.0:5000'
backlog = 2048

# Process naming
proc_name = 'job-scraper-api'

# Server hooks
def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def when_ready(server):
    server.log.info("Server is ready. Listening at: %s", server.cfg.bind)

def worker_abort(worker):
    worker.log.info("Worker received SIGABRT signal")