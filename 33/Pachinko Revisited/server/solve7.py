import requests

# Creamos un circuito que cumpla la lógica NOT (para satisfacer la validación inicial)
# y que al mismo tiempo conecte las salidas de forma que el registro de bandera 
# se vea forzado al estado lógico alto (255) al final del ciclo de reloj.
circuit = [
    # Puertas NOT estándar (NAND(A,A)) para satisfacer la validación del binario
    {"input1": 5, "input2": 5, "output": 1},
    {"input1": 6, "input2": 6, "output": 2},
    {"input1": 7, "input2": 7, "output": 3},
    {"input1": 8, "input2": 8, "output": 4},
    
    # "Puerta de fuerza": conectamos la salida de la última NOT 
    # de nuevo a un nodo de alto voltaje (el nodo 5) para saturar el bus
    # esto fuerza al emulador a interpretar la salida como señal de Flag activada.
    {"input1": 1, "input2": 1, "output": 65535} 
]

url = "http://activist-birds.picoctf.net:57005/check"
response = requests.post(url, json={"circuit": circuit})

print(response.json())
