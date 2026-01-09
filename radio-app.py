import vlc
import time
import sys
import logging
import json
import os
from configparser import ConfigParser

DEFAULT_STATION_RMF_FM = "http://31.192.216.5/rmf_fm"
ANTY_RADIO = "http://redir.atmcdn.pl/sc/o2/Eurozet/live/antyradio.livx"
RADIO_WNET = "http://audio.radiownet.pl:8000/stream64"
RADIO_ZET = "http://redir.atmcdn.pl/sc/o2/Eurozet/live/audio.livx"
RADIO_PR24 = "http://stream3.polskieradio.pl:8080/"

CHECK_CONTROL_MESSAGE_INTERVAL_SECONDS = 60

# for testing only
CHECK_CONTROL_MESSAGE_INTERVAL_SECONDS_TESTING_ONLY = 10

# DEFAULT_STATION_1001 = "http://streaming.radio.pl/1001.pls"

# Konfiguracja logowania (będzie widoczne w journalctl)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# Konfiguracja logowania (będzie widoczne w journalctl)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RadioApp")

def get_aws_session(config):
    import boto3
    profile_name = config.get("radio.aws.profile")
    region_name = config.get("radio.aws.region")
    
    if profile_name:
        return boto3.Session(profile_name=profile_name, region_name=region_name)
    else:
        return boto3.Session(region_name=region_name)

def synthesize_announcement(text, config):
    logger.info(f"Synthesizing announcement for: '{text}'")
    if not text:
        logger.warning("Text is empty, skipping announcement.")
        return None
        
    try:
        session = get_aws_session(config)
        logger.debug(f"AWS Session created: region={session.region_name}, profile={session.profile_name}")
        
        polly = session.client("polly")
        logger.debug("Polly client created. calling synthesize_speech...")
        
        response = polly.synthesize_speech(
            Text=f"<speak><prosody volume='x-loud'>{text}</prosody></speak>",
            TextType="ssml",
            OutputFormat="mp3",
            VoiceId="Maja" # Polish voice
        )
        logger.debug("Polly response received.")
        
        output_path = "/tmp/announcement.mp3"
        with open(output_path, "wb") as f:
            f.write(response["AudioStream"].read())
            
        if os.path.exists(output_path):
            logger.info(f"Announcement saved to {output_path}, size: {os.path.getsize(output_path)} bytes")
            return output_path
        else:
            logger.error("File write appeared to fail - file not found after writing.")
            return None
            
    except Exception as e:
        logger.error(f"Polly error details: {type(e).__name__}: {e}", exc_info=True)
        return None

def control_radio(player, name, url, volume, action, config=None):
    # Parametry dla VLC:
    # --no-video: nie szukaj ekranu
    # -vvv: bardzo gadatliwe logi (przydatne do debugowania dźwięku)
    

    if action == 'play':
        
        logger.info(f"Playing {name} at {url}")

        # use txt to audio service or lib to say what radio will be started 
        
        if not instance:
            logger.error("NIE UDALO SIE zainicjalizowac libvlc! Sprawdz biblioteki systemowe.")
            return

        # Announcement
        if config and name:
            logger.info("Generating announcement...")
            
            # Set volume before playing announcement
            player.audio_set_volume(int(volume))
            
            mp3_path = synthesize_announcement(f"Radio: {name}", config)
            if mp3_path and os.path.exists(mp3_path):
                logger.info(f"Playing announcement: {mp3_path}")
                media_ann = instance.media_new(mp3_path)
                player.set_media(media_ann)
                player.play()
                
                # Wait for announcement to finish
                time.sleep(1) # Wait for state to change to playing
                wait_count = 0 
                while True:
                    state = player.get_state()
                    if state == vlc.State.Ended or state == vlc.State.Error:
                        break
                    time.sleep(0.1)
                    wait_count += 1
                    if wait_count > 100: # 10s timeout
                         logger.warning("Announcement timeout")
                         break
            else:
                 logger.warning("Announcement file not generated.")
        else:
            logger.warning("No config or name provided - Announcement skipped.")

        media = instance.media_new(url)
        player.set_media(media)
        player.audio_set_volume(int(volume))

        logger.info(f"Proba odtworzenia strumienia: {url}")
        
        if player.play() == -1:
            logger.error("Blad podczas proby odtworzenia strumienia.")
            return

        state = player.get_state()
        if state == vlc.State.Error:
            logger.error("VLC napotkalo blad podczas odtwarzania.")
            return
        elif state == vlc.State.Ended:
            logger.info("Strumien zakonczony. Restartuje...")
            player.play()

        # # Petla monitorujaca status
        # try:
        #     while True:
        #         state = player.get_state()
        #         if state == vlc.State.Error:
        #             logger.error("VLC napotkalo blad podczas odtwarzania.")
        #             break
        #         elif state == vlc.State.Ended:
        #             logger.info("Strumien zakonczony. Restartuje...")
        #             player.play()
                
        #         time.sleep(5)
        # except KeyboardInterrupt:
        #     logger.info("Zamykanie aplikacji...")
        #     player.stop()
    elif action == 'stop':
        logger.info("Stop playing...")
        player.stop()

def read_config(config_file_path):
    logger.debug(f"Reading config from {config_file_path}")
    config_parser = ConfigParser()
    logger.debug(config_parser.sections())
    # with open(config_file_path) as config_file:
    #     config_parser.read_file(config_file)
    config_parser.read(config_file_path)
    logger.debug(config_parser.sections())
    logger.debug(config_parser["default"])
    logger.debug(dict(config_parser["default"]))
    config = dict(config_parser["default"])

    
    if "aws" in config_parser.sections():
        logger.debug(dict(config_parser["aws"]))
        config.update(config_parser["aws"])
    
    logger.debug(config)
    return config

def get_radio_control_message_from_queue(config):
    logger.debug("Getting radio control message from queue")
    
    session = get_aws_session(config)
    sqs = session.resource('sqs')

    queue_name = config.get("radio.control.queue.name")
    logger.debug(f"Queue name: {queue_name}")

    # Get the queue. This returns an SQS.Queue instance
    queue = sqs.get_queue_by_name(QueueName=queue_name)

    # You can now access identifiers and attributes
    logger.debug(queue.url)
    # logger.debug("DelaySeconds", str(queue.attributes.get("DelaySeconds")))
    # # logger.debug("queue attributes", str(queue.attributes))

    # Process messages by printing out body and optional author name    
    message = None
    messages = queue.receive_messages()
    if len(messages) > 0:
        logger.debug(f"There should be some message on queue: {queue_name}")
        message = messages[0]
         # Print out the body 
        logger.debug(f"Received message on {queue_name}: {message.body}")
        body = message.body
        # Let the queue know that the message is processed
        message.delete()
        logger.debug(f"Message deleted from queue: {queue_name}")
        logger.debug(f"Message body: {body}")
        return body
        
    else:
        logger.debug("No messages in queue")
        return None  

if __name__ == "__main__":
    
    config_path = os.path.expanduser("~/.config/py-radio/config.ini")
    CONFIG = read_config(config_path)

    # VLC_args = ['--no-video', '-vvv'] # for debugging VLC player
    VLC_args = ['--no-video']
    logger.info("Inicjalizacja instancji VLC...")
    instance = vlc.Instance(*VLC_args)

    player = instance.media_player_new()

    # Przykladowy strumien (możesz zmienic na wlasny)
    RADIO_URL = DEFAULT_STATION_RMF_FM  
    control_radio(player, "Radio RMF FM", RADIO_URL,100,'play', CONFIG)

    # tor testing only 
    # pause for 1 minute
    time.sleep(CHECK_CONTROL_MESSAGE_INTERVAL_SECONDS)
    

    previous_control_message = None
    while True:
        message_string = get_radio_control_message_from_queue(CONFIG)
        if message_string:
            if message_string:
                logger.debug(f"Message string: {message_string}")
                control_message = json.loads(message_string)
                logger.debug(f"Control message: {control_message}")
                if previous_control_message != control_message:
                    control_radio(player, control_message['name'], control_message['station'], control_message['volume'], control_message['action'], CONFIG)
                    previous_control_message = control_message.copy()
        time.sleep(CHECK_CONTROL_MESSAGE_INTERVAL_SECONDS_TESTING_ONLY)