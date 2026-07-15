import requests

url = "http://activist-birds.picoctf.net:51700"
login_data = {"username": "user@ses", "password": "2f4167548ca5a3bdafc23ef1513cd9fd"}

session = requests.Session()
response = session.post(f"{url}/api/login", json=login_data)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
print(f"Cookies: {session.cookies.get_dict()}")
