from scapy.all import rdpcap, UDP

# Carga el archivo de captura (asegúrate de que el nombre sea el correcto)
paquetes = rdpcap('capture.pcap')
flag = ""

for paquete in paquetes:
    # Filtramos los paquetes UDP cuyo puerto destino sea el 22
    if UDP in paquete and paquete[UDP].dport == 22:
        # Restamos 5000 al puerto de origen para obtener el ASCII
        valor_ascii = paquete[UDP].sport - 5000
        # Convertimos el valor numérico a su carácter correspondiente
        flag += chr(valor_ascii)

print(f"La bandera es: {flag}")
