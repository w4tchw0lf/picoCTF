import tarfile
import json

def find_hidden_flags(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            find_hidden_flags(v)
    elif isinstance(obj, list):
        # Buscamos arrays de enteros que sean lo suficientemente largos
        if len(obj) > 10 and all(isinstance(x, int) for x in obj):
            try:
                decoded = "".join(chr(x) if 32 <= x <= 126 else "" for x in obj)
                if "picoCTF" in decoded:
                    print(f"\n[+] ¡BINGO! Conexión de instancia decodificada: {decoded}")
            except:
                pass
        else:
            for item in obj:
                find_hidden_flags(item)

print("[*] Abriendo server.tar de forma segura...")
try:
    with tarfile.open('server.tar', 'r') as tar:
        for member in tar.getmembers():
            # Filtramos archivos que terminen en .json y que NO sean metadatos de macOS (._)
            if member.isfile() and member.name.endswith('.json') and '/._' not in member.name and not member.name.startswith('._'):
                print(f"[*] Inspeccionando: {member.name}")
                f = tar.extractfile(member)
                try:
                    # Leemos y decodificamos explícitamente en UTF-8
                    content = f.read().decode('utf-8')
                    data = json.loads(content)
                    find_hidden_flags(data)
                except Exception as e:
                    print(f"[-] Omitiendo {member.name} (no es un JSON válido o está corrupto)")
                    continue
    print("[*] Escaneo finalizado.")
except FileNotFoundError:
    print("[!] Error: No se encuentra server.tar.")
