#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

# Start supervisord to manage Redis and Daphne
exec /usr/bin/supervisord -n