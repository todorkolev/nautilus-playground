#!/bin/bash
# Script to start JupyterLab server

# Check if JupyterLab is already running
if pgrep -f "jupyter-lab" > /dev/null; then
    echo "JupyterLab is already running."
    jupyter server list
    exit 0
fi

# Create log directory if it doesn't exist
mkdir -p /tmp/jupyter-logs

# Start JupyterLab with nohup to keep it running after the script exits
echo "Starting JupyterLab..."
nohup jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token='' --NotebookApp.password='' > /tmp/jupyter-logs/jupyterlab.log 2>&1 &

# Store the process ID
JUPYTER_PID=$!
echo "JupyterLab started with PID: $JUPYTER_PID"

# Wait a moment for the server to start
echo "Waiting for JupyterLab to start..."
sleep 5

# Check if the process is still running
if ! ps -p $JUPYTER_PID > /dev/null; then
    echo "Error: JupyterLab failed to start. Check logs at /tmp/jupyter-logs/jupyterlab.log"
    cat /tmp/jupyter-logs/jupyterlab.log
    exit 1
fi

# Display server information
echo "JupyterLab server started successfully with PID: $JUPYTER_PID"
jupyter server list || echo "Could not list servers, but process is running with PID: $JUPYTER_PID"

echo "You can access JupyterLab at: http://localhost:8888/lab"
echo "Logs are available at: /tmp/jupyter-logs/jupyterlab.log"

# Create a PID file for easier management
echo $JUPYTER_PID > /tmp/jupyter.pid
