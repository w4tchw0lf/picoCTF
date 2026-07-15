import multiprocessing as mp

p = 7514777789

X = []
Y = []

for line in open("encoded.txt", "r").read().strip().split("\n"):
    x, y = line.split()
    X.append(int(x))
    Y.append(int(y))

K = GF(p)
R = PolynomialRing(K, "x")

def compZ(Xs):
    x = R.gen()
    Z = K(1)
    for xk in Xs:
        Z *= (x - xk)
    return Z

def comp(Xs, Ys, Xother):
    Z = compZ(Xother)
    Ys = [y / Z(x) for x, y in zip(Xs, Ys)]
    return Ys, Z

def solve(Xs, Ys):
    n = len(Ys)
    print("Solving for", n, "points...")

    if n <= 10:
        return R.lagrange_polynomial(list(zip(Xs, Ys)))

    nhalf = n // 2

    X1 = Xs[:nhalf]
    Y1 = Ys[:nhalf]
    X2 = Xs[nhalf:]
    Y2 = Ys[nhalf:]

    if nhalf > 10000:
        with mp.Pool(2) as pool:
            result1 = pool.apply_async(comp, (X1, Y1, X2))
            result2 = pool.apply_async(comp, (X2, Y2, X1))
            Y1, Z2 = result1.get()
            Y2, Z1 = result2.get()
    else:
        Y1, Z2 = comp(X1, Y1, X2)
        Y2, Z1 = comp(X2, Y2, X1)

    f1 = solve(X1, Y1)
    f2 = solve(X2, Y2)

    return f1 * Z2 + f2 * Z1

Y = [K(y) for y in Y]

f = solve(X, Y)

coeffs = f.coefficients(sparse=False)[:-1]
open("output.bmp", "wb").write(bytearray([int(c) for c in coeffs]))

print("[+] Wrote output.bmp")
