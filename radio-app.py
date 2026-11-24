import vlc
import time
import sys
import logging
import json
import os
import random
import subprocess
import threading
from configparser import ConfigParser
from urllib.parse import urlparse
from messaging import MessagingFactory

DEFAULT_STATION_RMF_FM = "http://31.192.216.5/rmf_fm"
ANTY_RADIO = "http://redir.atmcdn.pl/sc/o2/Eurozet/live/antyradio.livx"
RADIO_WNET = "http://audio.radiownet.pl:8000/stream64"
RADIO_ZET = "http://redir.atmcdn.pl/sc/o2/Eurozet/live/audio.livx"
RADIO_PR24 = "http://stream3.polskieradio.pl:8080/"

CHECK_CONTROL_MESSAGE_INTERVAL_SECONDS = 10

CHECK_CONTROL_MESSAGE_INTERVAL_SECONDS_MQ = 2

# for testing only
CHECK_CONTROL_MESSAGE_INTERVAL_SECONDS_TESTING_ONLY = 10

# in RMF_ONLY_MODE start only DEFAULT RMF FM station
RMF_ONLY_MODE = False
ENABLE_ANNOUNCEMENTS = False # requires polly and aws credentials and config 

# DEFAULT_STATION_1001 = "http://streaming.radio.pl/1001.pls"

# Konfiguracja logowania (będzie widoczne w journalctl)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# Konfiguracja logowania (będzie widoczne w journalctl)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RadioApp")

playlist_stop_event = threading.Event()
playlist_thread = None
LOCAL_PLAYLIST_FILES = {
    "local-IMPREZKA.txt",
    "local-10-milions.txt",
    "Eric-Clapton-Live-at-the-Royal-Albert-Hall.txt",
}

def download_youtube_playlist(playlist_url, temp_dir):
    os.makedirs(temp_dir, exist_ok=True)

    filename_process = subprocess.run(
        ["yt-dlp", "-f", "ba", "--get-filename", "--restrict-filenames", playlist_url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if filename_process.returncode != 0:
        logger.error("Failed to read playlist filenames: %s", filename_process.stderr.strip())
        return []

    filenames = [line.strip() for line in filename_process.stdout.splitlines() if line.strip()]
    missing = [name for name in filenames if not os.path.exists(os.path.join(temp_dir, name))]

    if missing:
        logger.info("Downloading %d missing playlist files", len(missing))
        download_process = subprocess.run(
            ["yt-dlp", "-f", "ba", "--restrict-filenames", "-P", temp_dir, playlist_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if download_process.returncode != 0:
            logger.error("Playlist download failed: %s", download_process.stderr.strip())

    files = []
    for name in filenames:
        path = os.path.join(temp_dir, name)
        if os.path.isfile(path):
            files.append(path)
            continue

        base_name, _ = os.path.splitext(name)
        matches = [
            os.path.join(temp_dir, candidate)
            for candidate in os.listdir(temp_dir)
            if candidate == name or candidate.startswith(base_name + ".")
        ]
        files.extend(sorted(path for path in matches if os.path.isfile(path)))

    logger.debug("Downloaded playlist files: %s", files)
    return list(dict.fromkeys(files))

def play_playlist(player, name, playlist_url, volume, config):
    global playlist_thread, playlist_stop_event

    playlist_stop_event.set()
    player.stop()
    playlist_stop_event = threading.Event()
    stop_event = playlist_stop_event

    def worker():
        temp_dir = os.path.expanduser(
            os.path.join("~", config.get("playtube.home.temp", "private/music/youtube-dl-temp"))
        )
        logger.info("Preparing playlist %s in %s", name, temp_dir)
        files = download_youtube_playlist(playlist_url, temp_dir)

        if config.get("play.order", "RANDOM").upper() == "RANDOM":
            random.shuffle(files)

        logger.info("Playing %d files from playlist %s", len(files), name)
        player.audio_set_volume(int(volume))

        for file_name in files:
            if stop_event.is_set():
                break
            logger.info("Playing playlist file %s", file_name)
            media = instance.media_new(file_name)
            player.set_media(media)
            if player.play() == -1:
                logger.error("VLC failed to play %s", file_name)
                continue

            while not stop_event.is_set():
                state = player.get_state()
                if state == vlc.State.Ended:
                    break
                if state == vlc.State.Error:
                    logger.error("VLC playback error for %s", file_name)
                    break
                time.sleep(0.1)

        if not stop_event.is_set():
            logger.info("Finished playlist %s", name)

    playlist_thread = threading.Thread(target=worker, daemon=True, name="youtube-playlist")
    playlist_thread.start()

def read_local_playlist(playlist_filename):
    if not isinstance(playlist_filename, str) or playlist_filename not in LOCAL_PLAYLIST_FILES:
        logger.error("Unsupported local playlist: %s", playlist_filename)
        return []

    playlist_path = os.path.join(os.path.expanduser("~/Music"), playlist_filename)
    try:
        with open(playlist_path, encoding="utf-8") as playlist_file:
            entries = [line.partition("#")[0].strip() for line in playlist_file]
    except OSError:
        logger.exception("Could not read local playlist %s", playlist_path)
        return []

    audio_files = []
    for entry in entries:
        if not entry or urlparse(entry).scheme:
            continue
        audio_path = entry if os.path.isabs(entry) else os.path.join(os.path.dirname(playlist_path), entry)
        if os.path.isfile(audio_path):
            audio_files.append(audio_path)
        else:
            logger.warning("Local playlist audio file not found: %s", audio_path)

    return list(dict.fromkeys(audio_files))

def play_local_playlist(player, name, playlist_filename, volume, config):
    global playlist_thread, playlist_stop_event

    files = read_local_playlist(playlist_filename)
    if not files:
        logger.error("No local audio files found for playlist %s", playlist_filename)
        return

    playlist_stop_event.set()
    player.stop()
    playlist_stop_event = threading.Event()
    stop_event = playlist_stop_event

    def worker():
        if config.get("play.order", "RANDOM").upper() == "RANDOM":
            random.shuffle(files)

        logger.info("Playing %d local files from playlist %s", len(files), name)
        player.audio_set_volume(int(volume))

        for file_name in files:
            if stop_event.is_set():
                break
            logger.info("Playing local playlist file %s", file_name)
            media = instance.media_new(file_name)
            player.set_media(media)
            if player.play() == -1:
                logger.error("VLC failed to play %s", file_name)
                continue

            while not stop_event.is_set():
                state = player.get_state()
                if state == vlc.State.Ended:
                    break
                if state == vlc.State.Error:
                    logger.error("VLC playback error for %s", file_name)
                    break
                time.sleep(0.1)

        if not stop_event.is_set():
            logger.info("Finished local playlist %s", name)

    playlist_thread = threading.Thread(target=worker, daemon=True, name="local-playlist")
    playlist_thread.start()

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
        playlist_stop_event.set()
        player.stop()

        logger.info(f"Playing {name} at {url}")

        # use txt to audio service or lib to say what radio will be started 
        
        if not instance:
            logger.error("NIE UDALO SIE zainicjalizowac libvlc! Sprawdz biblioteki systemowe.")
            return

        # Announcement
        if config and name and ENABLE_ANNOUNCEMENTS:
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
            logger.warning("No config or name provided or RMF_ONLY_MODE - Announcement skipped.")

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

    elif action == 'stop':
        logger.info("Stop playing...")
        playlist_stop_event.set()
        player.stop()
    elif action == 'play_playlist':
        if not url:
            logger.error("Playlist URL is required.")
            return
        play_playlist(player, name or "YouTube playlist", url, volume, config)
    elif action == 'play_local_playlist':
        if not url:
            logger.error("Local playlist filename is required.")
            return
        play_local_playlist(player, name or url, url, volume, config)

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
    
    if "rabbitmq" in config_parser.sections():
         config.update(config_parser["rabbitmq"])

    if "mqtt" in config_parser.sections():
        config.update(config_parser["mqtt"])

    return config



if __name__ == "__main__":
    config_path = os.path.expanduser("~/.config/py-radio/config.ini")
    # reading sys args

    if len(sys.argv) > 1:
        options = sys.argv[1]
        if options == "--rmf" :
            RMF_ONLY_MODE = True
            
    else:
        RMF_ONLY_MODE = False
    
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
    logger.debug("Ready for receiving messages.")
    
    if not RMF_ONLY_MODE: 
        previous_control_message = None
        
        consumer = MessagingFactory.get_consumer(CONFIG)
        
        while True:
            # logger.debug("debug...")
            messages = consumer.receive_messages()
            if messages:
                for message in messages:
                    logger.debug(f"Received message: {message.body}")
                    message_string = message.body
                    
                    try:
                        control_message = json.loads(message_string)
                        logger.debug(f"Control message: {control_message}")
                        
                        if previous_control_message != control_message:
                            control_radio(player, control_message.get('name'), control_message.get('station'), control_message.get('volume'), control_message.get('action'), CONFIG)
                            previous_control_message = control_message.copy()
                            
                        # Delete/Ack message after successful processing
                        message.delete()
                        logger.debug("Message processed and deleted/acked.")
                        
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        
            time.sleep(CHECK_CONTROL_MESSAGE_INTERVAL_SECONDS_MQ)