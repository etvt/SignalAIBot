#!/bin/bash

set -euo pipefail

SIGNALD_PID=
CMD_PID=

# Function to stop a process gracefully
stop_process() {
    local pid=$1
    if [[ -n "$pid" ]]; then
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping process with PID $pid..."
            # Use 'kill' command to send SIGTERM and ignore its exit status
            kill -SIGTERM "$pid" || true
            # Use 'wait' command and handle its potential failure
            echo "Waiting until $pid exits..."
            wait "$pid" || true
            echo "Process with PID $pid has stopped."
        else
            echo "Process with PID $pid is not running."
        fi
    fi
}

# Function to stop both processes gracefully
cleanup() {
    echo "Cleaning up before exit..."
    stop_process "$CMD_PID"
    CMD_PID=
    echo "Sleeping for 2 seconds..."
    sleep 2
    stop_process "$SIGNALD_PID"
    SIGNALD_PID=
    echo "Cleanup complete. Exiting..."
}

# Call cleanup when the script exits or receives a signal
trap cleanup EXIT SIGINT SIGTERM


# Start signald in the background
pushd / >/dev/null
signald -d /signald/data -s /signald/signald.sock &
SIGNALD_PID=$!
echo "Started signald with PID $SIGNALD_PID"
popd >/dev/null

echo "Waiting 5 seconds for signald to initialize..."
sleep 5

if ! ps -p $SIGNALD_PID > /dev/null 2>&1; then
  echo "signald is not running. Exiting..."
  exit 1
fi

# Start the cmd in the background
"$@" &
CMD_PID=$!
echo "Started CMD (" "$@" ") with PID $CMD_PID"


# Wait for either process to exit. The trap will handle the cleanup.
if wait -n $SIGNALD_PID $CMD_PID; then
  EXIT_CODE=$?
  echo "Received exit code '$EXIT_CODE' from one process. Terminating the container..."
else
  EXIT_CODE=$?
  echo "Received ERROR code '$EXIT_CODE' from one process. Terminating the container..."
fi

# Exit with the code from the process that terminated first
exit $EXIT_CODE
