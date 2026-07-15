import json

def find_hidden_flags(obj):
    # Recorremos el JSON recursivamente
    if isinstance(obj, dict):
        for k, v in obj.items():
            find_hidden_flags(v)
    elif isinstance(obj, list):
        # Si encontramos una conexión (un array de números), intentamos decodificarla
        if all(isinstance(x, int) for x in obj):
            # Traduce valores ASCII a texto, omitiendo números que no sean texto imprimible
            decoded_string = "".join(chr(x) if 32 <= x <= 126 else "" for x in obj)
            if "picoCTF" in decoded_string:
                print(f"[*] ¡Conexión de instancia decodificada con éxito!: {decoded_string}")
        else:
            for item in obj:
                find_hidden_flags(item)

print("[*] Analizando arquitectura de hardware en cpu.json...")
try:
    with open('verilog/cpu.json', 'r') as f:
        data = json.load(f)
    find_hidden_flags(data)
except FileNotFoundError:
    print("[!] No se encontró verilog/cpu.json. Asegúrate de estar en el directorio raíz y haber extraído server.tar completo.")
