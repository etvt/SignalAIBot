#!/usr/bin/env bash

set -euo pipefail

cleanup() {
  # Unregister the traps inside the cleanup to prevent recursive triggering
  trap - EXIT SIGINT SIGTERM
  echo "Exit requested. Cleaning up in run-as-signald-entrypoint..."

  if [[ -n "$NESTED_PID" ]]; then
    if kill -0 "$NESTED_PID" 2>/dev/null; then
      echo "Stopping nested entrypoint with PID $NESTED_PID..."
      kill -SIGTERM "$NESTED_PID" || true
      echo "Waiting until nested entrypoint with PID $NESTED_PID exits..."
      wait "$NESTED_PID" || true
      echo "Nested entrypoint with PID $NESTED_PID has stopped."
    else
      echo "Nested entrypoint with PID $NESTED_PID is not running."
    fi
  fi

  if [[ -n "$original_owner" ]]; then
    echo "Restoring owner and group on /persistent_data to $original_owner"
    chown -R "$original_owner" /persistent_data
  fi

  echo "Cleanup complete."
}

if [[ "$(id -u)" == "0" ]]; then  # started as root
  # Change mounted permissions to signald user
  original_owner=$(stat -c "%u:%g" /persistent_data)
  echo "Chowning volume /persistent_data to signald:signald, original owner: $original_owner"
  chown -R signald:signald /persistent_data

  # Call cleanup when the script exits or receives a signal
  trap cleanup EXIT SIGINT SIGTERM

  echo "Continuing as user 'signald'"
  setpriv --reuid=1337 --regid=1337 --init-groups /usr/bin/entrypoint.sh "$@" &
  NESTED_PID=$!
  echo "Started nested entrypoint with PID $NESTED_PID, waiting for it to finish..."
  wait $NESTED_PID || true

  echo "Nested entrypoint exited. Exiting..."
elif [[ "$(id -u)" == "1337" ]]; then  # started as signald
  echo "Not chowning /persistent_data directory, you must configure permissions manually before running the container"
  exec /usr/bin/entrypoint.sh "$*"
else
  echo "Error: you must start the container either as root or signald. Exiting..." >&2
  exit 1
fi
