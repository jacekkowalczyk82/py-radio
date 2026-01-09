# py-radio
simple online radio playyer python app


Setup required libs 

```
sudo apt update && sudo apt upgrade -y
sudo apt install lxd-installer -y
sudo lxd init

```

Creating and starting container

```
./deploy.sh init

```

Additional operations

```
./deploy.sh start
./deploy.sh stop
./deploy.sh status
./deploy.sh logs
./deploy.sh bash
./deploy.sh delete
```

# AWS SQS controlling messages

```
aws sqs send-message --queue-url https://sqs.us-east-2.amazonaws.com/347779256781/py-radio-control-queue --message-body "{'action':'play','station':'http://stream.polskieradio.pl/pr3'}"
```

