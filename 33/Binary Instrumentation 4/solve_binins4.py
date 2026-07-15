#!/usr/bin/env python3
import base64
import frida
import os
import re
import socket
import sys
import threading
import time

EXE = "bin-ins4.exe"
HOST = "127.0.0.1"
PORT = 9867

received_chunks = []
listener_done = threading.Event()

JS = r"""
function getExport(moduleNames, exportName) {
    for (const name of moduleNames) {
        try {
            const m = Process.getModuleByName(name);
            if (m.getExportByName) {
                return m.getExportByName(exportName);
            }
        } catch (e) {}
    }

    try {
        return Module.getGlobalExportByName(exportName);
    } catch (e) {}

    try {
        return Module.findGlobalExportByName(exportName);
    } catch (e) {}

    throw new Error("No pude resolver " + exportName);
}

const connectFn = getExport(["ws2_32.dll", "WS2_32.dll"], "connect");
const lstrcmpA = getExport(["kernel32.dll", "KERNEL32.DLL"], "lstrcmpA");

console.log("[+] connect  = " + connectFn);
console.log("[+] lstrcmpA = " + lstrcmpA);

Interceptor.attach(connectFn, {
    onEnter(args) {
        const sa = args[1];

        // sockaddr_in:
        // +0 family
        // +2 port, big endian
        // +4 IPv4 bytes
        const port = (sa.add(2).readU8() << 8) | sa.add(3).readU8();
        const ip = [
            sa.add(4).readU8(),
            sa.add(5).readU8(),
            sa.add(6).readU8(),
            sa.add(7).readU8()
        ].join(".");

        console.log("[connect] original -> " + ip + ":" + port);

        if (port === 9867) {
            // Redirigir a 127.0.0.1
            sa.add(4).writeU8(127);
            sa.add(5).writeU8(0);
            sa.add(6).writeU8(0);
            sa.add(7).writeU8(1);

            console.log("[+] connect redirigido a 127.0.0.1:9867");
        }
    }
});

Interceptor.attach(lstrcmpA, {
    onEnter(args) {
        try {
            const a = args[0].readCString();
            const b = args[1].readCString();
            console.log("[lstrcmpA] '" + a + "' vs '" + b + "'");
        } catch (e) {
            console.log("[lstrcmpA] no pude leer args: " + e);
        }
    },
    onLeave(retval) {
        // lstrcmpA devuelve 0 si las strings son iguales.
        retval.replace(0);
        console.log("[+] lstrcmpA forzado a 0");
    }
});
"""

def listener():
    print(f"[+] Listener en {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)

        conn, addr = s.accept()
        print(f"[+] Conexión recibida de {addr}")

        with conn:
            conn.settimeout(8)

            # Recibir prompt o datos iniciales
            try:
                data = conn.recv(4096)
                if data:
                    text = data.decode(errors="ignore")
                    print("[socket recv]", repr(text))
                    received_chunks.append(data)
            except socket.timeout:
                pass

            # Enviar cualquier key; lstrcmpA está parcheado a match.
            key = b"anything\n"
            print("[+] Enviando key falsa:", key)
            conn.sendall(key)

            # Recibir flag base64
            while True:
                try:
                    data = conn.recv(4096)
                    if not data:
                        break
                    text = data.decode(errors="ignore")
                    print("[socket recv]", repr(text))
                    received_chunks.append(data)
                except socket.timeout:
                    break

    listener_done.set()

def on_message(message, data):
    if message["type"] == "send":
        print("[*]", message["payload"])
    elif message["type"] == "error":
        print("[!] JS error:")
        print(message.get("stack", message))

def extract_flag(blob: bytes):
    text = blob.decode(errors="ignore")
    print("\n[+] Datos recibidos completos:")
    print(text)

    direct = re.search(r"picoCTF\{[^}]+\}", text)
    if direct:
        return direct.group(0)

    for token in re.findall(r"[A-Za-z0-9+/=]{20,}", text):
        try:
            decoded = base64.b64decode(token).decode(errors="ignore")
            print("[+] Base64 decodificado:", decoded.strip())
            m = re.search(r"picoCTF\{[^}]+\}", decoded)
            if m:
                return m.group(0)
        except Exception:
            pass

    return None

def main():
    if not os.path.exists(EXE):
        print(f"[!] No encuentro {EXE}")
        print("[*] Pon este script en la misma carpeta que bin-ins4.exe")
        sys.exit(1)

    t = threading.Thread(target=listener, daemon=True)
    t.start()

    time.sleep(0.5)

    print(f"[+] Spawning {EXE} con Frida...")
    pid = frida.spawn([os.path.abspath(EXE)])
    session = frida.attach(pid)

    script = session.create_script(JS)
    script.on("message", on_message)
    script.load()

    frida.resume(pid)

    listener_done.wait(timeout=15)

    blob = b"".join(received_chunks)
    if not blob:
        print("[!] No recibí nada en el socket.")
        print("[*] Ejecuta PowerShell como administrador si Frida no engancha bien.")
        sys.exit(1)

    flag = extract_flag(blob)

    if flag:
        print("\n[+] FLAG:", flag)
    else:
        print("\n[!] No encontré picoCTF{} automáticamente.")
        print("[*] Revisa el texto/base64 mostrado arriba.")

if __name__ == "__main__":
    main()
