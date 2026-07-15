import json
import sys

def find_hidden_flags(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            find_hidden_flags(v)
    elif isinstance(obj, list):
        if len(obj) > 10 and all(isinstance(x, int) for x in obj):
            try:
                decoded = "".join(chr(x) if 32 <= x <= 126 else "" for x in obj)
                if "picoCTF" in decoded:
                    print(f"\n[+] ¡Flag encontrada en la web!: {decoded}")
            except:
                pass
        else:
            for item in obj:
                find_hidden_flags(item)

try:
    with open('web_cpu.json', 'r') as f:
        # Si es un .js en lugar de un json puro, puede que falle aquí.
        # En ese caso habría que buscar el texto plano.
        data = json.load(f) 
        find_hidden_flags(data)
except Exception as e:
    print(f"[!] Error leyendo web_cpu.json: {e}")
    print("[*] Truco alternativo: usa el comando 'strings web_cpu.json | grep picoCTF'")
