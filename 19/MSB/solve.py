from PIL import Image

# 1. Cargamos la imagen
img = Image.open('ninja-and-prince-genji-ukiyoe-utagawa-kunisada.flag.png')
pixels = list(img.getdata())

bits = ""

# 2. Extraemos el MSB (bit 7) de los colores Rojo, Verde y Azul de cada píxel
for p in pixels:
    bits += str((p[0] >> 7) & 1) # Rojo
    bits += str((p[1] >> 7) & 1) # Verde
    bits += str((p[2] >> 7) & 1) # Azul

# 3. Convertimos esa cadena gigante de unos y ceros a texto real (ASCII)
texto_extraido = ""
for i in range(0, len(bits), 8):
    byte = bits[i:i+8]
    if len(byte) == 8:
        texto_extraido += chr(int(byte, 2))

# 4. Buscamos y mostramos solo la flag
inicio = texto_extraido.find('picoCTF{')
if inicio != -1:
    fin = texto_extraido.find('}', inicio) + 1
    print("¡Bingo! La flag es:")
    print(texto_extraido[inicio:fin])
else:
    print("No se encontró la flag, verifica el nombre del archivo.")
