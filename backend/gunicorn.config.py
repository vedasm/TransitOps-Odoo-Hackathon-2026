import os
import multiprocessing

# 1. Bind to port 8000 to match the EXPOSE layer in your Dockerfile
bind = "0.0.0.0:8000"
backlog = 2048

# 2. Worker Configuration
# Uses the standard production formula: (2 x CPU Cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Explicitly use the Uvicorn worker class for running your ASGI FastAPI app
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 30
keepalive = 2

# 3. Logging Configuration
# Redirects stdout/stderr directly to container output for docker logs visibility
loglevel = os.getenv("LOG_LEVEL", "info")
accesslog = "-"  
errorlog = "-"