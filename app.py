
# import time
# import requests
# import vlc # pip install python-vlc
# import socket

# DEFAULT_STATION_RMF_FM = "http://31.192.216.5/rmf_fm"
# DEFAULT_STATION_1001 = "http://streaming.radio.pl/1001.pls"


# hostname = socket.gethostname()
# print(f"Radio Python na kontenerze {hostname} wystartowała!")
# # Prosta pętla, aby proces nie zginął (np. udajemy serwer)

# instance = vlc.Instance('--no-video', '--aout=alsa')
# player = instance.media_player_new()
# # player = vlc.MediaPlayer()
# player.audio_set_volume(100)
# player.set_mrl(DEFAULT_STATION_RMF_FM)
# player.play()

# while True:
#     print (f"Radio is working ... {time.ctime()} \n")
#     with open("/tmp/app.log", "a") as f:
#         f.write(f"Radio is working... {time.ctime()}\n")
#     time.sleep(10)

import vlc
import time
import sys
import logging

DEFAULT_STATION_RMF_FM = "http://31.192.216.5/rmf_fm"
POLSKIE_RADIO_PR3 = "http://stream.polskieradio.pl/pr3"
DEFAULT_STATION_1001 = "http://streaming.radio.pl/1001.pls"

# Konfiguracja logowania (będzie widoczne w journalctl)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RadioApp")

def start_radio(url):
    # Parametry dla VLC:
    # --no-video: nie szukaj ekranu
    # --aout=alsa: wymuś wyjście dźwięku przez ALSA
    # -vvv: bardzo gadatliwe logi (przydatne do debugowania dźwięku)
    args = ['--no-video', '-vvv']
    # instance = vlc.Instance('--no-video', '--aout=alsa', '--alsa-audio-device=default')
    
    logger.info("Inicjalizacja instancji VLC...")
    instance = vlc.Instance(*args)
    
    if not instance:
        logger.error("NIE UDALO SIE zainicjalizowac libvlc! Sprawdz biblioteki systemowe.")
        return

    player = instance.media_player_new()
    media = instance.media_new(url)
    player.set_media(media)

    logger.info(f"Proba odtworzenia strumienia: {url}")
    
    if player.play() == -1:
        logger.error("Blad podczas proby odtworzenia strumienia.")
        return

    # Petla monitorujaca status
    try:
        while True:
            state = player.get_state()
            if state == vlc.State.Error:
                logger.error("VLC napotkalo blad podczas odtwarzania.")
                break
            elif state == vlc.State.Ended:
                logger.info("Strumien zakonczony. Restartuje...")
                player.play()
            
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Zamykanie aplikacji...")
        player.stop()

if __name__ == "__main__":
    # Przykladowy strumien (możesz zmienic na wlasny)
    RADIO_URL = DEFAULT_STATION_RMF_FM  
    start_radio(RADIO_URL)