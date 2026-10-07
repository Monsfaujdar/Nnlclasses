#!/bin/sh
set -u

python3 bot.py &
BOT_PID=$!

gunicorn app:app --bind 0.0.0.0:${PORT:-8080} &
WEB_PID=$!

cleanup() {
    kill -TERM "$BOT_PID" "$WEB_PID" 2>/dev/null || true
    wait "$BOT_PID" 2>/dev/null || true
    wait "$WEB_PID" 2>/dev/null || true
}

trap cleanup TERM INT

while kill -0 "$BOT_PID" 2>/dev/null && kill -0 "$WEB_PID" 2>/dev/null; do
    sleep 2
done

echo "A service process exited; stopping the container."
cleanup
exit 1
