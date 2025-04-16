#!/bin/bash
set -e

echo "🚀 Starting supervisord..."
exec supervisord -c /app/supervisord.conf
