#!/usr/bin/env bash

CONTAINER_NAME="my-lxc-radio"

OPTION=$1

function init {

echo "Building, configuring and starting container for the first time"

lxc init ubuntu:24.04 $CONTAINER_NAME --config=user.user-data="$(cat app-config.yaml)"
lxc list 

lxc config set $CONTAINER_NAME boot.autostart true
lxc config device add $CONTAINER_NAME shared-code-from-host disk source=$HOME/git/py-radio path=/mnt/app

lxc config device add $CONTAINER_NAME aws_config-from-host disk source=$HOME/git/py-radio/secrets/.aws path=/home/radio/.aws
lxc config device add $CONTAINER_NAME app-config-from-host disk source=$HOME/git/py-radio/.config  path=/home/radio/.config
# 1. Pass the PulseAudio socket
lxc config device add $CONTAINER_NAME pulse-socket disk source=/run/user/1000/pulse/native path=/mnt/pulse-socket

# 2. Pass the Pulse Cookie (Authentication)
lxc config device add $CONTAINER_NAME pulse-cookie disk source=$HOME/.config/pulse/cookie path=/mnt/pulse-cookie

# 3. Add GPU/Audio device access (Standard for sound)
# lxc config device add my-lxc-radio-automat-1 my-sound unix-char path=/dev/snd/controlC0
# Lub najbardziej uniwersalna metoda dla dźwięku:
# lxc config device add my-lxc-radio-automat-1 audio proxy listen=tcp:0.0.0.0:4713 connect=tcp:127.0.0.1:4713


# ALSA 
# lxc config device add my-lxc-radio-automat-1 alsa-control unix-char path=/dev/snd/controlC0
# lxc config device add my-lxc-radio-automat-1 alsa-pcm unix-char path=/dev/snd/pcmC0D0p

lxc list 

lxc config show  $CONTAINER_NAME

echo "Starting container"

lxc start $CONTAINER_NAME
lxc list 

lxc exec $CONTAINER_NAME  -- cloud-init status --wait


lxc exec $CONTAINER_NAME -- systemctl status python-radio-app.service

echo "Checking logs"
echo "Press Ctrl+C to exit"

lxc exec $CONTAINER_NAME -- journalctl -u python-radio-app.service -f 

}

if [ "$OPTION" == "init" ]; then
    init
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
    lxc exec $CONTAINER_NAME -- journalctl -u python-radio-app.service -f 
    
elif [ "$OPTION" == "bash" ]; then
    lxc exec $CONTAINER_NAME  -- /bin/bash

elif [ "$OPTION" == "delete" ]; then
    lxc delete $CONTAINER_NAME
    lxc list 
elif [ "$OPTION" == "reset" ]; then
    lxc stop $CONTAINER_NAME
    lxc list
    lxc delete $CONTAINER_NAME
    lxc list
    init
elif [ "$OPTION" == "restart" ]; then
    lxc stop $CONTAINER_NAME
    lxc list
    lxc start $CONTAINER_NAME
    lxc list
    
fi 

