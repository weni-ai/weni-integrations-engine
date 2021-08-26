#!/bin/bash

if [ "${DEBUG}" = "false" ] ; then
    echo "Running collectstatic"
    python manage.py collectstatic --noinput
fi

echo "Starting server"
gunicorn marketplace.wsgi -c gunicorn.conf.py
