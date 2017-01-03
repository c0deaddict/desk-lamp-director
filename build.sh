#!/bin/sh
NAME=c0deaddict/desk-lamp-director:latest
docker build -t $NAME .
docker push $NAME
