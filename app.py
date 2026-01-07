
import time
import requests
import vlc # pip install python-vlc
import socket
      
hostname = socket.gethostname()
print(f"Radio Python na kontenerze {hostname} wystartowała!")
# Prosta pętla, aby proces nie zginął (np. udajemy serwer)
while True:
    print (f"Radio is working ... {time.ctime()} \n")
    with open("/tmp/app.log", "a") as f:
        f.write(f"Radio is working... {time.ctime()}\n")
    time.sleep(10)
