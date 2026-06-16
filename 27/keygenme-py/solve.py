import hashlib

# 1. El nombre de usuario que usa el programa
username = b"BENNETT"

# 2. Calculamos el hash SHA-256
hash_result = hashlib.sha256(username).hexdigest()

# 3. Las posiciones exactas que pide la función check_key()
# (Ojo: los índices en las listas de Python empiezan a contar desde 0)
p1 = hash_result[4]
p2 = hash_result[5]
p3 = hash_result[3]
p4 = hash_result[6]
p5 = hash_result[2]
p6 = hash_result[7]
p7 = hash_result[1]
p8 = hash_result[8]

# 4. Construimos la parte dinámica
dynamic_part = p1 + p2 + p3 + p4 + p5 + p6 + p7 + p8

# 5. Juntamos todo para revelar la bandera
flag = "picoCTF{1n_7h3_kk3y_of_" + dynamic_part + "}"

print("¡Aquí tienes tu bandera!")
print(flag)
