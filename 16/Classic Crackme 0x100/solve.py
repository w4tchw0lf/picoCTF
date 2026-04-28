import angr
import claripy

print("[*] Iniciando ejecución simbólica con angr...")

project = angr.Project("./crackme100")
longitud = 50

# 50 variables simbólicas
chars = [claripy.BVS(f'c_{i}', 8) for i in range(longitud)]
input_str = claripy.Concat(*chars + [claripy.BVV(b'\n')])

# Inicializamos el estado
state = project.factory.full_init_state(
    stdin=input_str,
    add_options={angr.options.ZERO_FILL_UNCONSTRAINED_MEMORY, angr.options.ZERO_FILL_UNCONSTRAINED_REGISTERS}
)

# Restringimos a texto legible
for c in chars:
    state.solver.add(c >= 0x20)
    state.solver.add(c <= 0x7e)

simgr = project.factory.simgr(state)

print("[*] Ejecutando todos los caminos posibles hasta el final...")
# Usamos run() para que llegue hasta el final de la ejecución (deadended)
simgr.run()

encontrado = False

# Revisamos todos los caminos que llegaron al final
for path in simgr.deadended:
    salida_pantalla = path.posix.dumps(1)
    
    # Buscamos el camino que imprimió el texto inicial pero NO imprimió FAILED!
    if b"Enter the secret password:" in salida_pantalla and b"FAILED!" not in salida_pantalla:
        solution = path.solver.eval(input_str, cast_to=bytes)
        password = solution.decode('utf-8', errors='ignore').strip()
        print("\n[+] ¡BINGO! Camino exitoso encontrado.")
        print(f"[*] CONTRASEÑA: {password}")
        encontrado = True
        break

if not encontrado:
    print("\n[-] Vaya... Angr revisó todo pero no encontró la clave.")
