#!/bin/bash

echo "Running collectstatic"
python manage.py collectstatic --noinput

echo "Running migrate"
python manage.py migrate

echo "Starting server"
gunicorn marketplace.wsgi -c gunicorn.conf.py
