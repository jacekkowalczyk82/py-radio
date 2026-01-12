#!/usr/bin/env bash

CONTAINER_NAME="my-lxc-rabbitmq"
CONFIG_FILE="rabbitmq-cloud-init.yaml"

OPTION=$1

function init {
    echo "Creating RabbitMQ container..."
    
    # Init container with config
    lxc init ubuntu:24.04 $CONTAINER_NAME --config=user.user-data="$(cat $CONFIG_FILE)"
    
    # Auto-start
    lxc config set $CONTAINER_NAME boot.autostart true
    
    # Proxy RabbitMQ Main Port (5672)
    lxc config device add $CONTAINER_NAME port5672 proxy listen=tcp:0.0.0.0:5672 connect=tcp:127.0.0.1:5672
    
    # Proxy Management UI (15672)
    lxc config device add $CONTAINER_NAME port15672 proxy listen=tcp:0.0.0.0:15672 connect=tcp:127.0.0.1:15672
    
    echo "Starting container..."
    lxc start $CONTAINER_NAME
    
    echo "Waiting for cloud-init to complete (installing rabbitmq)..."
    lxc exec $CONTAINER_NAME -- cloud-init status --wait
    
    echo "Checking RabbitMQ status..."
    lxc exec $CONTAINER_NAME -- systemctl status rabbitmq-server
    
    echo "Done! RabbitMQ Management should be at http://localhost:15672"
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
    lxc exec $CONTAINER_NAME -- journalctl -u rabbitmq-server -f
elif [ "$OPTION" == "bash" ]; then
    lxc exec $CONTAINER_NAME -- /bin/bash
elif [ "$OPTION" == "delete" ]; then
    lxc delete $CONTAINER_NAME --force
elif [ "$OPTION" == "restart" ]; then
    lxc restart $CONTAINER_NAME
else
    echo "Usage: $0 {init|start|stop|restart|status|logs|bash|delete}"
fi
