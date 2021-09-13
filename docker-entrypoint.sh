#!/bin/bash

echo "Running collectstatic"
python manage.py collectstatic --noinput

echo "Starting server"
gunicorn marketplace.wsgi -c gunicorn.conf.py
