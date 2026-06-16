# solve.sage
import sys
from sage.all import *

if len(sys.argv) != 3:
    print("Uso: sage solve.sage <Modulus_n> <Clue_e>")
    sys.exit(1)

n = int(sys.argv[1])
e = int(sys.argv[2])

M = 2**18
R = Zmod(n)
PR = PolynomialRing(R, 'x')
x = PR.gen()

print("[*] Generando puntos A_i y B_j...")
two = R(2)
step_A = two^(e * M)
step_B = two^(-e)

A = [R(0)] * M
B = [R(0)] * M

curr_A = R(1)
curr_B = two
for i in range(M):
    A[i] = curr_A
    curr_A *= step_A
    B[i] = curr_B
    curr_B *= step_B

def build_tree(points):
    tree = [[x - pt for pt in points]]
    while len(tree[-1]) > 1:
        prev = tree[-1]
        curr = []
        for i in range(0, len(prev), 2):
            if i + 1 < len(prev):
                curr.append(prev[i] * prev[i+1])
            else:
                curr.append(prev[i])
        tree.append(curr)
    return tree

print("[*] Construyendo Árbol de Subproductos para A (Esto tomará 1-2 minutos)...")
tree_A = build_tree(A)

print("[*] Construyendo Árbol de Subproductos para B...")
tree_B = build_tree(B)

f = tree_B[-1][0]

print("[*] Ejecutando Evaluación Multipunto Rápida...")
evals = [f]
for level in reversed(tree_A[:-1]):
    new_evals = []
    for i in range(len(level)):
        new_evals.append(evals[i // 2] % level[i])
    evals = new_evals

print("[*] Comprobando colisiones (GCD)...")
for i, val in enumerate(evals):
    p_candidate = gcd(int(val.constant_coefficient()), n)
    if p_candidate > 1 and p_candidate < n:
        print(f"\n[+] ¡Colisión encontrada!")
        p = p_candidate
        q = n // p
        print(f"p = {p}")
        print(f"q = {q}")
        print(f"\n[==> COPIA ESTO Y ENVÍALO AL SERVIDOR <==]")
        print(p + q)
        sys.exit(0)
