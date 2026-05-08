# 1. Abrimos el archivo y leemos los números
with open("message.txt", "r") as file:
    numbers = file.read().split()

decrypted_message = ""

# 2. Procesamos cada número
for num in numbers:
    # Convertimos a entero
    n = int(num)
    
    # 3. Calculamos el inverso modular (módulo 41)
    # pow(base, exponente, modulo) -> pow(n, -1, 41) calcula el inverso
    inv = pow(n, -1, 41)
    
    # 4. Aplicamos las nuevas reglas de mapeo
    if 1 <= inv <= 26:
        # 1-26 es el alfabeto en mayúsculas (A-Z)
        # Sumamos 64 porque la 'A' en ASCII es 65 (1 + 64 = 65)
        decrypted_message += chr(inv + 64)
        
    elif 27 <= inv <= 36:
        # 27-36 son los dígitos decimales (0-9)
        # Restamos 27 para que el valor 27 se convierta en '0'
        decrypted_message += str(inv - 27)
        
    elif inv == 37:
        # 37 es un guion bajo (_)
        decrypted_message += "_"

# 5. Imprimimos el resultado envuelto en el formato de la flag
print(f"picoCTF{{{decrypted_message}}}")
