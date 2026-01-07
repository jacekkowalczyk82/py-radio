
import time
import requests
import vlc # pip install python-vlc
import socket

DEFAULT_STATION_RMF_FM = "http://31.192.216.5/rmf_fm"
DEFAULT_STATION_1001 = "http://streaming.radio.pl/1001.pls"


hostname = socket.gethostname()
print(f"Radio Python na kontenerze {hostname} wystartowała!")
# Prosta pętla, aby proces nie zginął (np. udajemy serwer)

instance = vlc.Instance('--run-as-root', '--no-video')
player = instance.media_player_new()
# player = vlc.MediaPlayer()
player.audio_set_volume(100)
player.set_mrl(DEFAULT_STATION_RMF_FM)
player.play()

while True:
    print (f"Radio is working ... {time.ctime()} \n")
    with open("/tmp/app.log", "a") as f:
        f.write(f"Radio is working... {time.ctime()}\n")
    time.sleep(10)
