# 1. Abrimos el archivo y leemos los números
with open("message.txt", "r") as file:
    # Leemos todo el texto y lo separamos por espacios en una lista
    numbers = file.read().split()

decrypted_message = ""

# 2. Procesamos cada número
for num in numbers:
    # Convertimos el texto a entero y aplicamos el módulo 37
    mod_value = int(num) % 37
    
    # 3. Aplicamos las reglas del mapeo
    if 0 <= mod_value <= 25:
        # 0-25 es el alfabeto en mayúsculas (A-Z)
        # En la tabla ASCII, la 'A' es el número 65. 
        # Sumamos 65 al valor para obtener la letra correcta.
        decrypted_message += chr(mod_value + 65)
        
    elif 26 <= mod_value <= 35:
        # 26-35 son los dígitos decimales (0-9)
        # Restamos 26 para que el valor quede entre 0 y 9.
        decrypted_message += str(mod_value - 26)
        
    elif mod_value == 36:
        # 36 es un guion bajo (_)
        decrypted_message += "_"

# 4. Imprimimos el resultado envuelto en el formato de la flag
print(f"picoCTF{{{decrypted_message}}}")
