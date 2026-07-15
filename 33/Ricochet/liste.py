import time
import requests

SERVER_URL = "http://activist-birds.picoctf.net:61764"

print("[*] Escuchando el canal de radio pasivamente...")
print("[*] Asegúrate de haber pulsado 'Start' en la web.")

for i in range(30):
    msgs = requests.get(SERVER_URL + "/radio_rx").json()
    if msgs:
        print(f"[{i}] Mensajes detectados: {msgs}")
    else:
        print(f"[{i}] Canal vacío...")
    time.sleep(1)
