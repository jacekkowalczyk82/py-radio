#!/usr/bin/env bash

CONTAINER_NAME="my-lxc-radio-automat-1"

OPTION=$1

if [ "$OPTION" == "init" ]; then

echo "Starting container in interactive mode"

lxc init ubuntu:24.04 $CONTAINER_NAME --config=user.user-data="$(cat app-config.yaml)"
lxc list 
lxc config device add $CONTAINER_NAME moj-kod disk source=$HOME/git/py-radio path=/mnt/app
lxc list 

lxc config show  $CONTAINER_NAME

lxc start $CONTAINER_NAME
lxc list 

lxc exec $CONTAINER_NAME  -- cloud-init status --wait


lxc exec $CONTAINER_NAME -- systemctl status python-radio-app.service


lxc exec $CONTAINER_NAME -- journalctl -u python-radio-app.service


echo "Checking logs"
echo "Press Ctrl+C to exit"
lxc exec $CONTAINER_NAME  -- tail -f /tmp/app.log

elif [ "$OPTION" == "start" ]; then
    lxc start $CONTAINER_NAME
    lxc list 


elif [ "$OPTION" == "stop" ]; then
    lxc stop $CONTAINER_NAME
    lxc list 

elif [ "$OPTION" == "status" ]; then
    lxc list 
    lxc info $CONTAINER_NAME
elif [ "$OPTION" == "logs" ]; then
    lxc exec $CONTAINER_NAME  -- tail -f /tmp/app.log

elif [ "$OPTION" == "delete" ]; then
    lxc delete $CONTAINER_NAME
    lxc list 
fi 

