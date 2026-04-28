def decrypt(a, b, cipher):
    p = 97
    g = 31
    text_key = "trudeau"
    
    # 1. Reconstruir la llave secreta (shared_key)
    # Según la fórmula del código original: key = (g^a % p)^b % p  -> que es igual a g^(a*b) % p
    shared_key = pow(g, a * b, p)
    
    # 2. Deshacer la función 'encrypt' (División)
    semi_cipher = ""
    for num in cipher:
        # Dividimos para recuperar el valor original de la letra
        char_ascii = num // (shared_key * 311)
        semi_cipher += chr(char_ascii)
        
    # 3. Deshacer la función 'dynamic_xor_encrypt' (XOR inverso)
    reversed_plaintext = ""
    key_length = len(text_key)
    for i, char in enumerate(semi_cipher):
        key_char = text_key[i % key_length]
        # Al aplicar XOR con la misma llave, recuperamos la letra
        decrypted_char = chr(ord(char) ^ ord(key_char))
        reversed_plaintext += decrypted_char
        
    # 4. Deshacer el [::-1] (Volver a darle la vuelta a la cadena)
    plaintext = reversed_plaintext[::-1]
    
    return plaintext

# ==========================================
# INSTRUCCIONES:
# Reemplaza estos valores con lo que dice tu archivo 'flag_info'
# ==========================================
a = 94 # PON TU NUMERO 'a' AQUI
b = 29 # PON TU NUMERO 'b' AQUI
cipher = [260307, 491691, 491691, 2487378, 2516301, 0, 1966764, 1879995, 1995687, 1214766, 0, 2400609, 607383, 144615, 1966764, 0, 636306, 2487378, 28923, 1793226, 694152, 780921, 173538, 173538, 491691, 173538, 751998, 1475073, 925536, 1417227, 751998, 202461, 347076, 491691]

# Ejecutar y mostrar la flag
print("\n[+] Reversión completada. Tu flag es:")
print(decrypt(a, b, cipher))
