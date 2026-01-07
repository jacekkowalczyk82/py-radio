#!/usr/bin/env bash

CONTAINER_NAME="my-lxc-radio-automat-1"

OPTION=$1

if [ "$OPTION" == "init" ]; then

echo "Starting container in interactive mode"

lxc init ubuntu:24.04 $CONTAINER_NAME --config=user.user-data="$(cat app-config.yaml)"
lxc list 
lxc config device add $CONTAINER_NAME moj-kod disk source=$HOME/git/py-radio path=/mnt/app


# 1. Pass the PulseAudio socket
lxc config device add my-lxc-radio-automat-1 pulse-socket disk source=/run/user/1000/pulse/native path=/mnt/pulse-socket

# 2. Pass the Pulse Cookie (Authentication)
lxc config device add my-lxc-radio-automat-1 pulse-cookie disk source=$HOME/.config/pulse/cookie path=/mnt/pulse-cookie

# 3. Add GPU/Audio device access (Standard for sound)
lxc config device add my-lxc-radio-automat-1 snd unix-char path=/dev/snd

lxc list 

lxc config show  $CONTAINER_NAME

echo "Starting container"

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
elif [ "$OPTION" == "bash" ]; then
    lxc exec $CONTAINER_NAME  -- /bin/bash
    
elif [ "$OPTION" == "delete" ]; then
    lxc delete $CONTAINER_NAME
    lxc list 
fi 

