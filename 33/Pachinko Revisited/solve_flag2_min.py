import requests, json

HOST = "http://activist-birds.picoctf.net:50108"

# payload pequeño, no 10000 entradas
circuit = []

# circuito NAND válido para flag1
for i in range(4):
    circuit.append({"input1": 5+i, "input2": 5+i, "output": 1+i})

r = requests.post(
    HOST + "/check",
    headers={"Content-Type": "application/json"},
    data=json.dumps({"circuit": circuit}, separators=(",", ":"))
)

print(r.status_code)
print(r.text)
