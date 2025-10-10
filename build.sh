#!/usr/bin/env bash

# Install extra dev utils
curl https://getcroc.schollz.com | bash -s -- -p /storage

# Django build commands 
python manage.py makemigrations core eval
python manage.py collectstatic --noinput 
# Depending on provider this one might be auto-called on build 
# python manage.py migrate
