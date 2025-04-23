#!/bin/bash
# entrypoint.sh

# Cron‑Daemon starten
service cron start

# Supervisor im Vordergrund starten
exec /usr/bin/supervisord -n
