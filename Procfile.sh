#!/bin/bash

python manage.py migrate

gunicorn babubi.wsgi:application --timeout 30 --log-file -