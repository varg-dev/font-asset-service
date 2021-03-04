#!/bin/sh
case $1 in
    'start') docker-compose \
        -f docker-compose.yml \
        -f docker-compose.production.yml \
        up -d --build service;;
    'stop') docker-compose \
        down;;
    *) echo 'unknown command';;
esac
