#!/bin/sh
set -eu

if [ ! -f "$GOLDILOCKS_DB_PATH" ]; then
    mkdir -p "$(dirname "$GOLDILOCKS_DB_PATH")"
    cp /app/goldilocks.db "$GOLDILOCKS_DB_PATH"
fi

exec "$@"
