from pwn import remote, context
from Crypto.Util.number import long_to_bytes, isPrime
from sympy import factorint
from itertools import combinations
import math
import signal

# Quitar los logs molestos de pwntools
context.log_level = 'error'

# Excepción personalizada para nuestro temporizador
class TimeoutException(Exception):
    pass

# Manejador del temporizador
def timeout_handler(signum, frame):
    raise TimeoutException

# Asociar la señal de alarma de Linux a nuestro manejador
signal.signal(signal.SIGALRM, timeout_handler)

def attempt():
    print("[*] Abriendo nueva sesión en saturn.picoctf.net...")
    try:
        r = remote('saturn.picoctf.net', 49614)
    except Exception as e:
        print(f"[-] Error de conexión: {e}")
        return False

    # Leer variables
    r.recvuntil(b"anger = ")
    c = int(r.recvline().strip())
    r.recvuntil(b"envy = ")
    d = int(r.recvline().strip())
    e = 65537

    ed_minus_1 = e * d - 1

    for k in range(1, e):
        if ed_minus_1 % k == 0:
            phi = ed_minus_1 // k
            
            print(f"[*] Intentando factorizar... (Límite: 5 segundos)")
            
            # Arrancar el cronómetro de 5 segundos
            signal.alarm(5) 
            try:
                # Si esto tarda más de 5 segundos, saltará a la excepción
                factors = factorint(phi)
                signal.alarm(0) # Apagar el cronómetro si tuvo éxito
                
            except TimeoutException:
                print("[-] Factores demasiado grandes. Descartando y reintentando...")
                r.close()
                return False # Fracaso, forzará un nuevo intento
                
            # Si llegamos aquí, la factorización fue muy rápida
            primes = []
            for p_factor, exp in factors.items():
                primes.extend([p_factor] * exp)
                
            # Calcular combinaciones
            for i in range(1, len(primes)):
                for comb in set(combinations(primes, i)):
                    p_minus_1 = math.prod(comb)
                    p_candidate = p_minus_1 + 1
                    
                    if p_candidate.bit_length() == 128 and isPrime(p_candidate):
                        q_minus_1 = phi // p_minus_1
                        q_candidate = q_minus_1 + 1
                        
                        if q_candidate.bit_length() == 128 and isPrime(q_candidate):
                            n = p_candidate * q_candidate
                            m = pow(c, d, n)
                            plaintext = long_to_bytes(m)
                            
                            if len(plaintext) == 16 and plaintext.isalnum():
                                print(f"\n[+] ¡BINGO! Colisión matemática encontrada.")
                                print(f"[+] Texto: {plaintext.decode()}")
                                
                                # Enviar respuesta al servidor
                                r.recvuntil(b"> ")
                                r.sendline(plaintext)
                                
                                # Imprimir la bandera final
                                print("\n" + "="*40)
                                print(r.recvall().decode().strip())
                                print("="*40)
                                r.close()
                                return True # Éxito total
    r.close()
    return False

# Bucle infinito: seguirá intentándolo hasta que rompa la clave
while True:
    if attempt():
        break
    print("--------------------------------------------------")
