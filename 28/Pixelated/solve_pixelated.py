from PIL import Image

# 1. Abrimos las dos imágenes en modo RGB
print("[*] Cargando imágenes escaneadas...")
img1 = Image.open("scrambled1.png").convert("RGB")
img2 = Image.open("scrambled2.png").convert("RGB")

# Aseguramos que ambas tengan las mismas dimensiones
width, height = img1.size

# 2. Creamos un nuevo lienzo en blanco para el resultado
flag_img = Image.new("RGB", (width, height))

# Cargamos los mapas de píxeles en memoria para ir rápido
pixels1 = img1.load()
pixels2 = img2.load()
pixels_flag = flag_img.load()

print("[*] Combinando capas de píxeles mediante adición modular...")

# 3. Recorremos cada píxel sumando sus componentes (R, G, B)
for x in range(width):
    for y in range(height):
        r1, g1, b1 = pixels1[x, y]
        r2, g2, b2 = pixels2[x, y]
        
        # Sumamos los valores aplicando módulo 256 para evitar desbordamientos
        r_new = (r1 + r2) % 256
        g_new = (g1 + g2) % 256
        b_new = (b1 + b2) % 256
        
        pixels_flag[x, y] = (r_new, g_new, b_new)

# 4. Guardamos la imagen resultante
flag_img.save("flag.png")
print("[+] ¡Éxito! La imagen combinada ha sido guardada como 'flag.png'.")
