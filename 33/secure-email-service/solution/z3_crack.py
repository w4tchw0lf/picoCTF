from z3 import *
from random import Random
from itertools import count
from time import time
import logging

logging.basicConfig(format='STT> %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
SYMBOLIC_COUNTER = count()


class Untwister:
    def __init__(self):
        name = next(SYMBOLIC_COUNTER)
        self.MT = [BitVec(f'MT_{i}_{name}', 32) for i in range(624)]
        self.index = 0
        self.solver = Solver()

    def symbolic_untamper(self, solver, y):
        name = next(SYMBOLIC_COUNTER)
        y1 = BitVec(f'y1_{name}', 32)
        y2 = BitVec(f'y2_{name}', 32)
        y3 = BitVec(f'y3_{name}', 32)
        y4 = BitVec(f'y4_{name}', 32)
        solver.add(y2 == y1 ^ LShR(y1, 11))
        solver.add(y3 == y2 ^ ((y2 << 7) & 0x9D2C5680))
        solver.add(y4 == y3 ^ ((y3 << 15) & 0xEFC60000))
        solver.add(y == y4 ^ LShR(y4, 18))
        return y1

    def symbolic_twist(self, MT, n=624, upper_mask=0x80000000, lower_mask=0x7FFFFFFF, a=0x9908B0DF, m=397):
        MT = [i for i in MT]
        for i in range(n):
            x = (MT[i] & upper_mask) + (MT[(i + 1) % n] & lower_mask)
            xA = LShR(x, 1)
            xB = If(x & 1 == 0, xA, xA ^ a)
            MT[i] = MT[(i + m) % n] ^ xB
        return MT

    def get_symbolic(self, guess):
        assert isinstance(guess, str), 'guess must be a bit string'
        assert all(c in '01?' for c in guess), 'guess must contain only 0, 1, ?'
        assert len(guess) <= 32, 'one 32-bit number at a time'
        name = next(SYMBOLIC_COUNTER)
        symbolic_guess = BitVec(f'symbolic_guess_{name}', 32)
        guess = guess.zfill(32)[::-1]
        for i, bit in enumerate(guess):
            if bit != '?':
                self.solver.add(Extract(i, i, symbolic_guess) == int(bit))
        return symbolic_guess

    def submit(self, guess):
        if self.index >= 624:
            name = next(SYMBOLIC_COUNTER)
            next_mt = self.symbolic_twist(self.MT)
            self.MT = [BitVec(f'MT_{i}_{name}', 32) for i in range(624)]
            for i in range(624):
                self.solver.add(self.MT[i] == next_mt[i])
            self.index = 0
        symbolic_guess = self.get_symbolic(guess)
        symbolic_guess = self.symbolic_untamper(self.solver, symbolic_guess)
        self.solver.add(self.MT[self.index] == symbolic_guess)
        self.index += 1

    def get_random(self):
        logger.info('Solving...')
        start = time()
        if self.solver.check() != sat:
            raise RuntimeError('solver failed')
        model = self.solver.model()
        logger.info(f'Solved! in {time() - start:.3f}s')
        state = [model[x].as_long() for x in self.MT]
        r = Random()
        r.setstate((3, tuple(state + [self.index]), None))
        return r
