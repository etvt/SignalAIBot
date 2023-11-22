#!/bin/bash

set -euo pipefail

SIGNALD_PID=
CMD_PID=
SLEEP_PID=
EXIT_REQUESTED=

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
    # Unregister the traps inside the cleanup to prevent recursive triggering
    trap - EXIT SIGINT SIGTERM
    echo "Exit requested. Cleaning up..."
    EXIT_REQUESTED=true

    echo "Stopping CMD..."
    stop_process "$CMD_PID"
    CMD_PID=

    echo "Sleeping for 1 second..."
    sleep 1

    echo "Stopping signald..."
    stop_process "$SIGNALD_PID"
    SIGNALD_PID=

    if [[ -n "$SLEEP_PID" ]]; then
      echo "Stopping sleep on error..."
      stop_process "$SLEEP_PID"
      SLEEP_PID=
    fi

    echo "Cleanup complete."
}

# Call cleanup when the script exits or receives a signal
trap cleanup EXIT SIGINT SIGTERM


# Start signald in the background
pushd / >/dev/null

if [ -z "${POSTGRES_URL:-}" ]; then  # no database is specified
  signald -d /persistent_data/signald  -s /signald/signald.sock &
else # db connection string is specified
  if [[ $POSTGRES_URL != "postgresql"* ]]; then
    # signald does not accept the 'postgres' URI scheme
    POSTGRES_URL=${POSTGRES_URL/postgres/postgresql}
  fi
  signald -d /persistent_data/signald --database="$POSTGRES_URL" -s /signald/signald.sock &
fi
SIGNALD_PID=$!
echo "Started signald with PID $SIGNALD_PID"

popd >/dev/null


echo "Waiting for signald socket to become available..."
timeout=60  # 60 seconds timeout
while [ $timeout -gt 0 ] && [ "$EXIT_REQUESTED" != true ]; do
    if [ -S /signald/signald.sock ]; then
        echo "signald socket is available."
        break
    fi

    # Check if signald is still running
    if ! kill -0 $SIGNALD_PID > /dev/null 2>&1; then
        echo "signald process has exited."
        break
    fi

    echo "Waiting for signald socket... $timeout seconds remaining"
    sleep 1
    ((timeout--))
done

if [ "$EXIT_REQUESTED" == true ]; then
    echo "Exit requested during wait. Exiting..."
    exit 1
fi

if [ ! -S /signald/signald.sock ] || ! kill -0 $SIGNALD_PID > /dev/null 2>&1; then
    echo "Timeout reached waiting for socket or signald process is not running. Exiting..."
    exit 1
fi


# Start the cmd in the background
"$@" &
CMD_PID=$!
echo "Started CMD (" "$@" ") with PID $CMD_PID"


# Wait for either process to exit. The trap will handle the cleanup.
if wait -n $SIGNALD_PID $CMD_PID; then
  EXIT_CODE=$?
  echo "Received exit code '$EXIT_CODE' from one process. Exiting..."
else
  EXIT_CODE=$?
  echo "Received ERROR code '$EXIT_CODE' from one process. Exiting..."

  if [ "$EXIT_REQUESTED" != true ] && [ -n "${SLEEP_ON_ERROR:-}" ]; then
    sleep "$SLEEP_ON_ERROR" &
    SLEEP_PID=$!
    echo "Started sleeping on error (sleep " "$SLEEP_ON_ERROR" ") with PID $SLEEP_PID..."

    wait -n $SLEEP_PID || true
    echo "Sleep finished."
    SLEEP_PID=
  fi
fi

# Exit with the code from the process that terminated first
exit $EXIT_CODE
