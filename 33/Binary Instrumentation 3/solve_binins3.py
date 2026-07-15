#!/usr/bin/env python3
import frida
import os
import time
import base64
import re
import sys

EXE = "bin-ins3.exe"
OUTFILE = "flag.txt"

JS = r"""
function getExport(moduleName, exportName) {
    try {
        return Process.getModuleByName(moduleName).getExportByName(exportName);
    } catch (e1) {
        try {
            return Process.getModuleByName(moduleName.toLowerCase()).getExportByName(exportName);
        } catch (e2) {
            try {
                return Module.getGlobalExportByName(exportName);
            } catch (e3) {
                console.log("[!] No pude resolver " + exportName + ": " + e3);
                return null;
            }
        }
    }
}

const CreateFileA = getExport("KERNEL32.DLL", "CreateFileA");
const CreateProcessA = getExport("KERNEL32.DLL", "CreateProcessA");

if (CreateFileA === null || CreateProcessA === null) {
    throw new Error("No se pudieron resolver CreateFileA/CreateProcessA");
}

console.log("[+] CreateFileA     = " + CreateFileA);
console.log("[+] CreateProcessA  = " + CreateProcessA);
console.log("[+] Process.pointerSize = " + Process.pointerSize);

let lastFileHandle = ptr(0);

Interceptor.attach(CreateFileA, {
    onEnter(args) {
        try {
            const oldPath = args[0].readCString();
            console.log("[CreateFileA] old path = " + oldPath);

            if (
                oldPath.indexOf("output_flag.txt") !== -1 ||
                oldPath.indexOf("C:\\\\random") !== -1 ||
                oldPath.indexOf("C:\\random") !== -1
            ) {
                const newPath = Memory.allocUtf8String("flag.txt");
                this.newPath = newPath;
                args[0] = newPath;
                console.log("[CreateFileA] patched path = flag.txt");
            }
        } catch (e) {
            console.log("[CreateFileA] read error: " + e);
        }
    },
    onLeave(retval) {
        console.log("[CreateFileA] handle = " + retval);

        const invalid64 = ptr("0xffffffffffffffff");
        const invalid32 = ptr("0xffffffff");

        if (!retval.isNull() && !retval.equals(invalid64) && !retval.equals(invalid32)) {
            lastFileHandle = retval;
            console.log("[+] saved file handle = " + lastFileHandle);
        }
    }
});

Interceptor.attach(CreateProcessA, {
    onEnter(args) {
        try {
            const app = args[0].isNull() ? "" : args[0].readCString();
            const cmd = args[1].isNull() ? "" : args[1].readCString();

            console.log("[CreateProcessA] app = " + app);
            console.log("[CreateProcessA] cmd = " + cmd);

            const startup = args[8];

            let dwFlagsOff;
            let hStdInputOff;
            let hStdOutputOff;
            let hStdErrorOff;

            if (Process.pointerSize === 8) {
                // STARTUPINFOA x64
                dwFlagsOff = 60;
                hStdInputOff = 80;
                hStdOutputOff = 88;
                hStdErrorOff = 96;
            } else {
                // STARTUPINFOA x86
                dwFlagsOff = 44;
                hStdInputOff = 56;
                hStdOutputOff = 60;
                hStdErrorOff = 64;
            }

            const dwFlagsPtr = startup.add(dwFlagsOff);
            const hStdOutputPtr = startup.add(hStdOutputOff);
            const hStdErrorPtr = startup.add(hStdErrorOff);

            const flags = dwFlagsPtr.readU32();
            const hOut = hStdOutputPtr.readPointer();
            const hErr = hStdErrorPtr.readPointer();

            console.log("[CreateProcessA] dwFlags    = 0x" + flags.toString(16));
            console.log("[CreateProcessA] hStdOutput = " + hOut);
            console.log("[CreateProcessA] hStdError  = " + hErr);

            // STARTF_USESTDHANDLES = 0x100
            dwFlagsPtr.writeU32(flags | 0x100);

            // El bug: el handle bueno está en stderr. Lo copiamos a stdout.
            if (!hErr.isNull()) {
                hStdOutputPtr.writePointer(hErr);
                console.log("[fix] hStdOutput = hStdError");
            } else if (!lastFileHandle.isNull()) {
                hStdOutputPtr.writePointer(lastFileHandle);
                hStdErrorPtr.writePointer(lastFileHandle);
                console.log("[fix] stdout/stderr = lastFileHandle");
            }

            // bInheritHandles = TRUE
            args[4] = ptr(1);
        } catch (e) {
            console.log("[CreateProcessA error] " + e);
        }
    },
    onLeave(retval) {
        console.log("[CreateProcessA] ret = " + retval);
    }
});
"""

def on_message(message, data):
    if message["type"] == "send":
        print("[*]", message["payload"])
    elif message["type"] == "error":
        print("[!] JS error:")
        print(message.get("stack", message))

def main():
    if not os.path.exists(EXE):
        print(f"[!] No encuentro {EXE}")
        print("[*] Pon example.py en la misma carpeta que bin-ins3.exe")
        sys.exit(1)

    if os.path.exists(OUTFILE):
        os.remove(OUTFILE)

    print(f"[+] Spawning {EXE} with Frida...")

    pid = frida.spawn([os.path.abspath(EXE)])
    session = frida.attach(pid)

    script = session.create_script(JS)
    script.on("message", on_message)
    script.load()

    frida.resume(pid)

    time.sleep(5)

    if not os.path.exists(OUTFILE):
        print("[!] No se creó flag.txt.")
        print("[*] Prueba ejecutar PowerShell como Administrador.")
        print("[*] También verifica que bin-ins3.exe esté en esta misma carpeta.")
        sys.exit(1)

    data = open(OUTFILE, "rb").read().decode(errors="ignore")

    print("\n[+] Contenido de flag.txt:")
    print(data)

    m = re.search(r"picoCTF\{[^}]+\}", data)
    if m:
        print("[+] FLAG:", m.group(0))
        return

    for token in re.findall(r"[A-Za-z0-9+/=]{20,}", data):
        try:
            decoded = base64.b64decode(token).decode(errors="ignore")
            if "picoCTF{" in decoded:
                print("[+] FLAG:", decoded.strip())
                return
        except Exception:
            pass

    print("[!] No encontré picoCTF{} automáticamente. Revisa flag.txt.")

if __name__ == "__main__":
    main()
