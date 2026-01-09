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
aws sqs send-message --queue-url https://sqs.us-east-2.amazonaws.com/347779256781/py-radio-control-queue --message-body "{\"action\":\"stop\", \"name\":\"\", \"station\":\"\", \"volume\":\"0\"}"


# RMF FM
aws sqs send-message --queue-url https://sqs.us-east-2.amazonaws.com/347779256781/py-radio-control-queue --message-body "{\"action\":\"play\",\"name\":\"Radio RMF FM\",\"station\":\"http://31.192.216.5/rmf_fm\",\"volume\":\"100\"}"



# PR24
aws sqs send-message --queue-url https://sqs.us-east-2.amazonaws.com/347779256781/py-radio-control-queue --message-body "{\"action\":\"play\",\"name\":\"Polskie Radio 24\",\"station\":\"http://stream3.polskieradio.pl:8080/\",\"volume\":\"100\"}"

# WNET 
aws sqs send-message --queue-url https://sqs.us-east-2.amazonaws.com/347779256781/py-radio-control-queue --message-body "{\"action\":\"play\",\"name\":\"WNET\",\"station\":\"http://audio.radiownet.pl:8000/stream64\",\"volume\":\"100\"}"

# ANTY Radio
aws sqs send-message --queue-url https://sqs.us-east-2.amazonaws.com/347779256781/py-radio-control-queue --message-body "{\"action\":\"play\",\"name\":\"\!Anty\! Radio\",\"station\":\"http://redir.atmcdn.pl/sc/o2/Eurozet/live/antyradio.livx\",\"volume\":\"100\"}"


# ZET
aws sqs send-message --queue-url https://sqs.us-east-2.amazonaws.com/347779256781/py-radio-control-queue --message-body "{\"action\":\"play\",\"name\":\"ZET\",\"station\":\"http://redir.atmcdn.pl/sc/o2/Eurozet/live/audio.livx\",\"volume\":\"100\"}"
```

