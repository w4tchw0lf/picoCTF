import hashlib

### FUNCIONES ORIGINALES ######################################################
def str_xor(secret, key):
    #extend key to secret length
    new_key = key
    i = 0
    while len(new_key) < len(secret):
        new_key = new_key + key[i]
        i = (i + 1) % len(key)        
    return "".join([chr(ord(secret_c) ^ ord(new_key_c)) for (secret_c,new_key_c) in zip(secret,new_key)])

flag_enc = open('level5.flag.txt.enc', 'rb').read()
correct_pw_hash = open('level5.hash.bin', 'rb').read()

def hash_pw(pw_str):
    pw_bytes = bytearray()
    pw_bytes.extend(pw_str.encode())
    m = hashlib.md5()
    m.update(pw_bytes)
    return m.digest()
###############################################################################

### NUESTRA FUNCIÓN PARA CRACKEAR EL DICCIONARIO ##############################
def crack_password():
    print("[*] Abriendo el diccionario...")
    
    # Hint 1: Abrimos el diccionario
    with open('dictionary.txt', 'r') as f:
        # Leemos el archivo línea por línea
        for line in f:
            # Hint 2: Eliminamos los espacios en blanco o saltos de línea con strip()
            password = line.strip()
            
            # Comprobamos si el hash de esta contraseña es igual al correcto
            if hash_pw(password) == correct_pw_hash:
                print(f"[+] ¡Contraseña encontrada!: {password}")
                
                # Desencriptamos la flag usando la contraseña encontrada
                decryption = str_xor(flag_enc.decode(), password)
                print(f"[+] Tu flag es: {decryption}")
                
                return # Salimos de la función porque ya terminamos
                
    print("[-] No se encontró la contraseña en el diccionario.")

# Ejecutamos el cracker
crack_password()
