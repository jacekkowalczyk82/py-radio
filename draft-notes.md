

## Radio app in LXC container

```



lxc launch ubuntu:24.04 my-lxc-radio
lxc list 

lxc exec my-lxc-radio -- /bin/bash

apt update
apt install python3 -y

echo "print('Kod edytowany na hoscie, uruchomiony w kontenerze ')" > ~/git/py-radio/hello.py

lxc config device add my-lxc-radio folder-projektu disk source=$HOME/git/py-radio path=/app



lxc exec my-lxc-radio -- /bin/bash



cloud init yaml - setup-python.yaml

lxc launch ubuntu:24.04 my-lxc-radio-automat-1 --config=user.user-data="$(cat setup-python.yaml)"

lxc exec my-lxc-radio-automat-1  -- cloud-init status --wait

lxc exec my-lxc-radio-automat-1  -- systemctl status python-app.service

lxc exec my-lxc-radio-automat-1  -- cloud-init status --wait

nie dziala cos nie tak w tej komendzie ----lxc exec my-lxc-radio-automat-1  -- journalctl python-app.service


lxc exec my-lxc-radio-automat-1  -- tail -f /tmp/app.log

lxc stop my-lxc-radio-automat-1
lxc delete my-lxc-radio-automat-1


```
