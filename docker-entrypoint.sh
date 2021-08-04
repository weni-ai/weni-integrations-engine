#!/bin/bash

echo "Running collectstatic"
python manage.py collectstatic

echo "Starting server"
gunicorn marketplace.wsgi -c gunicorn.conf.py --workers 4
