#!/usr/bin/env bash

CONTAINER_NAME="my-lxc-web-radio"
CONFIG_FILE="web-config.yaml"

# Get absolute path to the project root (parent directory of web_control)
PROJECT_ROOT=$(dirname $(pwd))
# If running from project root, adjust
if [[ $(basename $(pwd)) != "web_control" ]]; then
    PROJECT_ROOT=$(pwd)
    CONFIG_FILE="web_control/web-config.yaml"
    cd web_control
fi

OPTION=$1

function init {
    echo "Building, configuring and starting WEB container for the first time"
    
    # Init container with config
    lxc init ubuntu:24.04 $CONTAINER_NAME --config=user.user-data="$(cat web-config.yaml)"
    
    lxc config set $CONTAINER_NAME boot.autostart true
    
    # Mount Source Code (Web Control)
    lxc config device add $CONTAINER_NAME source-code disk source=$PROJECT_ROOT/web_control path=/mnt/web_control
    
    # Mount AWS Secrets (Host secrets -> Container secrets)
    lxc config device add $CONTAINER_NAME aws_secrets disk source=$PROJECT_ROOT/secrets/.aws path=/home/radio/.aws
    
    # Mount App Config (Optional, if shared config needed)
    lxc config device add $CONTAINER_NAME app_config disk source=$PROJECT_ROOT/.config path=/home/radio/.config

    # Network Proxy - Expose port 5000
    # Listens on all host interfaces (0.0.0.0) port 5000 and forwards to container port 5000
    lxc config device add $CONTAINER_NAME myport5000 proxy listen=tcp:0.0.0.0:5000 connect=tcp:127.0.0.1:5000

    echo "Starting container..."
    lxc start $CONTAINER_NAME
    
    echo "Waiting for cloud-init..."
    lxc exec $CONTAINER_NAME -- cloud-init status --wait
    
    echo "Checking service status..."
    lxc exec $CONTAINER_NAME -- systemctl status python-web-control.service
}

if [ "$OPTION" == "init" ]; then
    init
elif [ "$OPTION" == "start" ]; then
    lxc start $CONTAINER_NAME
elif [ "$OPTION" == "stop" ]; then
    lxc stop $CONTAINER_NAME
elif [ "$OPTION" == "status" ]; then
    lxc list $CONTAINER_NAME
    lxc info $CONTAINER_NAME
elif [ "$OPTION" == "logs" ]; then
    lxc exec $CONTAINER_NAME -- journalctl -u python-web-control.service -f
elif [ "$OPTION" == "bash" ]; then
    lxc exec $CONTAINER_NAME -- /bin/bash
elif [ "$OPTION" == "delete" ]; then
    lxc delete $CONTAINER_NAME --force
elif [ "$OPTION" == "restart" ]; then
    lxc restart $CONTAINER_NAME
    lxc exec $CONTAINER_NAME -- systemctl restart python-web-control.service
else
    echo "Usage: $0 {init|start|stop|restart|status|logs|bash|delete}"
fi
