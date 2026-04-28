from Crypto.Util.number import long_to_bytes

# El número exacto de input1.txt (sin el símbolo %)
input_num = 39722847074734820757600524178581224432297292490103996085769154356559546905

# La relación de los engranajes que calculamos (40 dientes / 8 dientes)
ratio = 5

# Multiplicamos la entrada por la relación de engranajes
output_num = input_num * ratio

# Convertimos el número resultante (en bytes) a texto legible
flag = long_to_bytes(output_num)

print("¡Aquí tienes tu flag!")
print(flag.decode('utf-8'))
