# alternatywa dla rabbitMQ

Jeśli priorytetem jest **minimalne obciążenie systemu** przy tak niskim natężeniu ruchu (1 wiadomość na minutę), RabbitMQ – choć stabilny – jest rozwiązaniem nieco „nadmiarowym”. Działa on na maszynie wirtualnej Erlanga, która sama w sobie rezerwuje sporo pamięci RAM na start.

Oto trzech brokerów, którzy przy małym użyciu zużywają ułamek zasobów RabbitMQ:

---

## 1. Mosquitto (Protokół MQTT) – Najlżejszy wybór

Jeśli Twoje wiadomości to proste powiadomienia lub dane czujników, Mosquitto jest bezkonkurencyjny. Jest napisany w C i zaprojektowany z myślą o urządzeniach o bardzo ograniczonej mocy (jak Raspberry Pi Zero).

* **RAM:** ok. **3-10 MB** (vs 150-250 MB w RabbitMQ).
* **CPU:** Praktycznie niewykrywalne przy 1 wiadomości/min.
* **Instalacja na Debianie:**
```bash
sudo apt update && sudo apt install mosquitto mosquitto-clients -y

```


* **Dla kogo:** Jeśli potrzebujesz prostego mechanizmu „publikuj/subskrybuj” i nie potrzebujesz skomplikowanego trasowania wiadomości.

## 2. Redis (Pub/Sub lub Listy) – Jeśli już go masz

Jeśli na serwerze i tak używasz bazy Redis do keszowania, nie instaluj niczego innego. Redis posiada wbudowane mechanizmy kolejek.

* **RAM:** Jeśli Redis już działa, obsługa kolejek nie doda niemal żadnego narzutu. Sam proces zajmuje ok. **5-10 MB** przy pustej bazie.
* **Instalacja na Debianie:**
```bash
sudo apt update && sudo apt install redis-server -y

```


* **Dla kogo:** Jeśli zależy Ci na szybkości i masz już Redis w stosie technologicznym. Pamiętaj tylko, że standardowy Pub/Sub w Redisie jest typu „fire-and-forget” (jeśli odbiorca jest offline, wiadomość przepadnie).

## 3. NATS – Nowoczesny i ultra-wydajny

NATS to broker napisany w Go. Jest niesamowicie prosty w obsłudze (często to po prostu jeden plik binarny) i znacznie lżejszy od RabbitMQ pod względem zużycia pamięci przy małej skali.

* **RAM:** ok. **15-30 MB**.
* **CPU:** Ekstremalnie niskie.
* **Instalacja:** Najlepiej pobrać gotowy plik binarny lub skorzystać z oficjalnego repozytorium (nie zawsze jest w standardowym `apt`).
* **Dla kogo:** Jeśli szukasz czegoś pomiędzy prostotą Mosquitto a możliwościami RabbitMQ.

---

### Porównanie zużycia RAM (Stan bezczynności)

| Broker | Język | Typowe zużycie RAM |
| --- | --- | --- |
| **Mosquitto** | C | ~5 MB |
| **Redis** | C | ~10 MB |
| **NATS** | Go | ~20 MB |
| **RabbitMQ** | Erlang | **~200 MB** |

---

**Moja rekomendacja:**
Jeśli nie potrzebujesz zaawansowanych funkcji RabbitMQ (takich jak skomplikowane potwierdzenia odbioru, kolejki priorytetowe czy routing typu Topic/Fanout w standardzie AMQP), wybierz **Mosquitto**. To "waga piórkowa", która na Debianie instaluje się w 5 sekund i po prostu działa, nie obciążając procesora ani pamięci.

Czy chciałbyś, abym pokazał Ci, jak przetestować wysyłanie wiadomości w **Mosquitto** za pomocą terminala?

## MQTT Mosquitto

To doskonały wybór. Do obsługi Mosquitto w Pythonie najczęściej używa się biblioteki `paho-mqtt`. Jest lekka, stabilna i bardzo prosta w implementacji.

### 1. Przygotowanie środowiska

Najpierw zainstaluj brokera (jeśli jeszcze tego nie zrobiłeś) oraz bibliotekę dla Pythona:

```bash
# Instalacja brokera na Debianie
sudo apt update && sudo apt install mosquitto mosquitto-clients -y

# Instalacja biblioteki paho-mqtt
pip install paho-mqtt

```

---

### 2. Skrypt wysyłający (Publisher) – `send.py`

Ten skrypt połączy się z brokerem, wyśle jedną wiadomość na temat (topic) `test/kolejka` i zakończy działanie.

```python
import paho.mqtt.client as mqtt
import time

# Konfiguracja
BROKER = "localhost"
TOPIC = "test/kolejka"

client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

try:
    client.connect(BROKER, 1883, 60)
    message = f"Wiadomość wysłana o: {time.strftime('%H:%M:%S')}"
    
    # Publikacja wiadomości
    client.publish(TOPIC, message)
    print(f" [x] Wysłano: '{message}'")
    
    client.disconnect()
except Exception as e:
    print(f"Błąd: {e}")

```

---

### 3. Skrypt odbierający (Subscriber) – `receive.py`

Ten skrypt będzie działał w pętli, oczekując na każdą nową wiadomość pojawiającą się w temacie.

```python
import paho.mqtt.client as mqtt

# Konfiguracja
BROKER = "localhost"
TOPIC = "test/kolejka"

# Funkcja wywoływana przy odebraniu wiadomości
def on_message(client, userdata, msg):
    print(f" [v] Odebrano: '{msg.payload.decode()}' z tematu: {msg.topic}")

# Konfiguracja klienta
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message

print(f" [*] Czekam na wiadomości w {TOPIC}. Naciśnij Ctrl+C, aby wyjść.")

try:
    client.connect(BROKER, 1883, 60)
    client.subscribe(TOPIC)
    
    # Pętla nasłuchująca (blokująca)
    client.loop_forever()
except KeyboardInterrupt:
    print("\nZatrzymano odbieranie.")
except Exception as e:
    print(f"Błąd: {e}")

```

---

### Jak to przetestować?

1. Uruchom odbiorcę w jednym oknie terminala:
```bash
python3 receive.py

```


2. W drugim oknie terminala uruchom nadawcę:
```bash
python3 send.py

```



### Kilka wskazówek:

* **QoS (Quality of Service):** Przy `client.publish(TOPIC, message, qos=1)` masz pewność, że wiadomość zostanie dostarczona przynajmniej raz, nawet przy gorszym połączeniu.
* **Persistent Connections:** Mosquitto domyślnie nie przechowuje wiadomości, które przyszły, gdy odbiorca był offline (chyba że skonfigurujesz tzw. *Clean Session* na `False`).
* **Bezpieczeństwo:** Domyślnie Mosquitto na nowych wersjach Debiana pozwala na połączenia tylko z `localhost`. Jeśli będziesz chciał się łączyć z innego komputera, musisz edytować `/etc/mosquitto/mosquitto.conf` i dodać `allow_anonymous true` (lub ustawić hasła) oraz `listener 1883`.

Czy chciałbyś, abym wyjaśnił, jak zabezpieczyć ten serwer hasłem?
