import time
# print('Aplikacja uruchomiona z filesystemu hosta!')
# while True:
#    print('Serwer pracuje...')
#    time.sleep(10)


import time
import socket
      
hostname = socket.gethostname()
print(f"Aplikacja Python na kontenerze {hostname} wystartowała!")
# Prosta pętla, aby proces nie zginął (np. udajemy serwer)
while True:
    print (f"I am working ... {time.ctime()} \n")
    with open("/tmp/app.log", "a") as f:
        f.write(f"I am working... {time.ctime()}\n")
    time.sleep(10)
