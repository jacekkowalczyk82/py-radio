import logging
import json
import os
from abc import ABC, abstractmethod

# Configure logging
logger = logging.getLogger("Messaging")

class MessageConsumer(ABC):
    @abstractmethod
    def receive_messages(self):
        """
        Receive messages from the queue.
        Returns a list of message bodies (strings) or objects that behave like messages.
        """
        pass

    @abstractmethod
    def delete_message(self, message_handle):
        """
        Delete a processed message from the queue.
        """
        pass

class MessageProducer(ABC):
    @abstractmethod
    def send_message(self, action, name, station, volume):
        """
        Send a control message to the queue.
        """
        pass

class SQSConsumer(MessageConsumer):
    def __init__(self, config):
        import boto3
        self.config = config
        profile_name = config.get("radio.aws.profile")
        region_name = config.get("radio.aws.region")
        queue_name = config.get("radio.control.queue.name")
        
        if profile_name:
            self.session = boto3.Session(profile_name=profile_name, region_name=region_name)
        else:
            self.session = boto3.Session(region_name=region_name)
            
        self.sqs = self.session.resource('sqs')
        self.queue = self.sqs.get_queue_by_name(QueueName=queue_name)
        logger.info(f"SQS Consumer initialized for queue: {queue_name}")

    def receive_messages(self):
        return self.queue.receive_messages(MaxNumberOfMessages=1, WaitTimeSeconds=1)

    def delete_message(self, message):
        message.delete()
        logger.debug(f"SQS message deleted: {message.message_id}")

class SQSProducer(MessageProducer):
    def __init__(self, config):
        import boto3
        self.config = config
        profile_name = config.get("radio.aws.profile")
        region_name = config.get("radio.aws.region")
        self.queue_url = config.get("radio.control.sqs.url") # Prefer URL if available, else derive? 
        # Actually existing app used name lookup, let's stick to name lookup for consistency or URL if provided.
        # Web app had hardcoded URL. Let's try to be flexible.
        
        # If we are in the web app, we might check config for specific URL or lookup by name
        # For simplicity, let's duplicate the session logic
        if profile_name:
            self.session = boto3.Session(profile_name=profile_name, region_name=region_name)
        else:
            self.session = boto3.Session(region_name=region_name)
            
        self.sqs_client = self.session.client('sqs')
        
        # Cache Queue URL if possible, otherwise we need to look it up every time or config it
        # Existing web app hardcoded it. Let's try to find it by name if URL not explicitly in config.
        self.queue_name = config.get("radio.control.queue.name")
        self.queue_url = config.get("radio.control.queue.url")
        
        if not self.queue_url and self.queue_name:
             # Basic lookup
             try:
                 response = self.sqs_client.get_queue_url(QueueName=self.queue_name)
                 self.queue_url = response['QueueUrl']
             except Exception as e:
                 logger.error(f"Failed to resolve SQS Queue URL from name {self.queue_name}: {e}")

    def send_message(self, action, name, station, volume):
        if not self.queue_url:
            logger.error("Queue URL is not configured or resolved.")
            return False, "Queue URL missing"

        message_body = {
            "action": action,
            "name": name or "",
            "station": station or "",
            "volume": str(volume)
        }
        
        try:
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body)
            )
            return True, response.get('MessageId')
        except Exception as e:
            logger.error(f"SQS Send failed: {e}")
            return False, str(e)


class RabbitMQConsumer(MessageConsumer):
    def __init__(self, config):
        import pika
        self.config = config
        self.host = config.get("radio.rabbitmq.host", "localhost")
        self.port = int(config.get("radio.rabbitmq.port", 5672))
        self.queue_name = config.get("radio.control.queue.name", "py-radio-control-queue")
        self.user = config.get("radio.rabbitmq.user", "guest")
        self.password = config.get("radio.rabbitmq.password", "guest")
        
        self.credentials = pika.PlainCredentials(self.user, self.password)
        self.connection_params = pika.ConnectionParameters(
            host=self.host, port=self.port, credentials=self.credentials
        )
        self.connection = None
        self.channel = None
        
    def _connect(self):
        import pika
        if not self.connection or self.connection.is_closed:
            try:
                self.connection = pika.BlockingConnection(self.connection_params)
                self.channel = self.connection.channel()
                self.channel.queue_declare(queue=self.queue_name)
            except Exception as e:
                logger.error(f"RabbitMQ connection failed: {e}")
                
    def receive_messages(self):
        self._connect()
        if not self.channel:
            return []
            
        # Basic get (not basic_consume loop) to match existing polling architecture
        method_frame, header_frame, body = self.channel.basic_get(queue=self.queue_name, auto_ack=False)
        if method_frame:
            # Wrap in a simple object/dict to mimic SQS message object interface used in app
            # existing app uses message.body and message.delete()
            return [RabbitMQMessageWrapper(method_frame, body, self.channel)]
        else:
            return []

    def delete_message(self, message):
        # In RabbitMQ, we ack the message
        # The wrapper handles the ack call
        message.delete()


class RabbitMQMessageWrapper:
    def __init__(self, method_frame, body, channel):
        self.method_frame = method_frame
        self.body = body.decode('utf-8') # Decode bytes to string
        self.channel = channel
        
    def delete(self):
        self.channel.basic_ack(delivery_tag=self.method_frame.delivery_tag)


class RabbitMQProducer(MessageProducer):
    def __init__(self, config):
        import pika
        self.config = config
        self.host = config.get("radio.rabbitmq.host", "localhost")
        self.port = int(config.get("radio.rabbitmq.port", 5672))
        self.queue_name = config.get("radio.control.queue.name", "py-radio-control-queue")
        self.user = config.get("radio.rabbitmq.user", "guest")
        self.password = config.get("radio.rabbitmq.password", "guest")
        
        self.credentials = pika.PlainCredentials(self.user, self.password)
        self.connection_params = pika.ConnectionParameters(
            host=self.host, port=self.port, credentials=self.credentials
        )

    def send_message(self, action, name, station, volume):
        import pika
        try:
            connection = pika.BlockingConnection(self.connection_params)
            channel = connection.channel()
            channel.queue_declare(queue=self.queue_name)
            
            message_body = {
                "action": action,
                "name": name or "",
                "station": station or "",
                "volume": str(volume)
            }
            
            channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=json.dumps(message_body)
            )
            connection.close()
            return True, "sent"
        except Exception as e:
            logger.error(f"RabbitMQ Send failed: {e}")
            return False, str(e)


class MessagingFactory:
    @staticmethod
    def get_consumer(config):
        provider = config.get("radio.control.queue.provider", "aws")
        if provider == "rabbitmq":
            return RabbitMQConsumer(config)
        else:
            return SQSConsumer(config)

    @staticmethod
    def get_producer(config):
        provider = config.get("radio.control.queue.provider", "aws")
        if provider == "rabbitmq":
            return RabbitMQProducer(config)
        else:
            return SQSProducer(config)
