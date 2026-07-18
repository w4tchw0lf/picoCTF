#!/usr/bin/env python3
import copy
import json
import os
import sys
import time
from pathlib import Path
import requests
import monocypher

ROBOT = 0x20
CTRL = 0x10
MITM_CTRL = 0x30
DUMMY_ROBOT = 0x40
CACHE_FILE = 'ricochet_hmac_cache.json'

S = requests.Session()
SERVER = None
PENDING = []

NEEDED_COMMANDS = [('east', 9), ('north', 15), ('west', 21), ('south', 27), ('east', 33)]
NEEDED_BLANKS = [10, 11]


def norm_url(x):
    x = str(x).strip().rstrip('/')
    if x.isdigit():
        return f'http://activist-birds.picoctf.net:{x}'
    return x


def short(m):
    m = copy.deepcopy(m)
    for k in ('encrypted', 'key', 'response'):
        if isinstance(m.get(k), str) and len(m[k]) > 18:
            m[k] = m[k][:10] + '...'
    return m


def rx(verbose=False):
    r = S.get(SERVER + '/radio_rx', timeout=10)
    r.raise_for_status()
    out = r.json()
    if verbose:
        for m in out:
            print('RX', short(m), flush=True)
    return out


def tx(msg, verbose=True):
    if verbose:
        print('TX', short(msg), flush=True)
    r = S.post(SERVER + '/radio_tx', json=msg, timeout=10)
    r.raise_for_status()


def start():
    S.get(SERVER + '/start', timeout=10).raise_for_status()


def stop():
    S.get(SERVER + '/stop', timeout=10).raise_for_status()


def state():
    r = S.get(SERVER + '/state', timeout=10)
    r.raise_for_status()
    return r.json()


def drain(n=5):
    PENDING.clear()
    for _ in range(n):
        try:
            rx(False)
        except Exception:
            pass
        time.sleep(0.12)
    PENDING.clear()


def reset_controller_addr():
    # Try all addresses the controller may have been moved to.
    for dst in [CTRL, MITM_CTRL, 0, 0x69, DUMMY_ROBOT, ROBOT, 0xff]:
        try:
            tx({'msg_type': 'set_addr', 'src': 1, 'dst': dst, 'new_addr': CTRL}, verbose=False)
        except Exception:
            pass
        time.sleep(0.04)
    drain(2)


def prepare_fresh_phase():
    # This script is designed for one phase per fresh instance. We still try a light cleanup.
    try:
        reset_controller_addr()
    except Exception:
        pass
    try:
        stop()
    except Exception:
        pass
    time.sleep(2)
    drain(6)
    try:
        st = state()
        print('[+] Estado antes de fase:', st, flush=True)
        if st.get('running'):
            print('[!] La instancia ya esta running=true. Si no llega validate, reinicia la instancia y repite esta fase.', flush=True)
    except Exception:
        pass


def wait(pred, desc, timeout=25, verbose=False):
    end = time.time() + timeout
    while time.time() < end:
        for i, m in enumerate(PENDING):
            if pred(m):
                out = PENDING.pop(i)
                if verbose:
                    print('RX*', short(out), flush=True)
                return out
        msgs = rx(verbose)
        if msgs:
            PENDING.extend(msgs)
            continue
        time.sleep(0.08)
    print('[!] Timeout esperando:', desc, flush=True)
    print('[!] Pendientes:', [short(x) for x in PENDING], flush=True)
    try:
        print('[!] Estado:', json.dumps(state(), indent=2), flush=True)
    except Exception:
        pass
    raise TimeoutError(desc)


def wait_type(t, src=None, dst=None, encrypted=False, timeout=25):
    def pred(m):
        if m.get('msg_type') != t:
            return False
        if src is not None and int(m.get('src', -1)) != src:
            return False
        if dst is not None and int(m.get('dst', -1)) != dst:
            return False
        if encrypted and 'encrypted' not in m:
            return False
        return True
    return wait(pred, f'{t} src={src} dst={dst}', timeout=timeout)


def compute_hmac(message, nonce, key):
    h = (message + str(nonce) + key.hex()).encode()
    for _ in range(32):
        h = monocypher.blake2b(h + key)
    return monocypher.blake2b(h)


def add_hmac(message, nonce, key):
    h = compute_hmac(message, nonce, key)
    return {'message': message, 'nonce': nonce, 'hmac': h.hex()}


def encrypt(message, key):
    k = monocypher.blake2b(key)[:32]
    nonce = os.urandom(24)
    tag, ct = monocypher.lock(k, nonce, message.encode())
    return ct.hex() + ';' + tag.hex() + ';' + nonce.hex()


def decrypt(message, key):
    k = monocypher.blake2b(key)[:32]
    ct, tag, nonce = message.split(';')
    return monocypher.unlock(k, bytes.fromhex(nonce), bytes.fromhex(tag), bytes.fromhex(ct))


def dec_json(pkt, key):
    return json.loads(decrypt(pkt['encrypted'], key).decode())


def mitm_session():
    prepare_fresh_phase()

    # Move the real controller from 0x10 to 0x30, so robot still talks to 0x10 and we can relay.
    tx({'msg_type': 'set_addr', 'src': ROBOT, 'dst': CTRL, 'new_addr': MITM_CTRL})
    time.sleep(0.35)
    drain(2)

    print('[+] Starting robot / waiting validate...', flush=True)
    start()
    time.sleep(0.2)

    v = wait_type('validate', src=ROBOT, dst=CTRL, timeout=30)
    tx({'msg_type': 'validate', 'src': ROBOT, 'dst': MITM_CTRL, 'challenge': v['challenge']})
    wait_type('ack_validate', src=MITM_CTRL, dst=ROBOT, timeout=25)

    my_priv = os.urandom(32)
    kx = wait_type('key_exchange', src=ROBOT, dst=CTRL, timeout=25)
    shared_robot = monocypher.key_exchange(my_priv, bytes.fromhex(kx['key']))
    my_pub = monocypher.compute_key_exchange_public_key(my_priv).hex()
    tx({'msg_type': 'ack_key_exchange', 'src': MITM_CTRL, 'dst': ROBOT, 'key': my_pub})

    first = wait_type('secure_data', src=ROBOT, dst=CTRL, encrypted=True, timeout=25)
    msg_robot = dec_json(first, shared_robot)

    # Separate key with real controller as a dummy robot.
    tx({'msg_type': 'key_exchange', 'src': DUMMY_ROBOT, 'dst': MITM_CTRL, 'key': my_pub})
    ack = wait_type('ack_key_exchange', src=MITM_CTRL, dst=DUMMY_ROBOT, timeout=25)
    shared_controller = monocypher.key_exchange(my_priv, bytes.fromhex(ack['key']))

    print('[+] MITM listo. Primer paquete:', msg_robot, flush=True)
    return msg_robot, shared_robot, shared_controller


def send_to_controller(pt_obj, typ, shared_controller):
    pkt = {
        'msg_type': typ,
        'src': DUMMY_ROBOT,
        'dst': MITM_CTRL,
        'encrypted': encrypt(json.dumps(pt_obj), shared_controller),
    }
    tx(pkt)
    expected = 'secure_data_ack' if typ == 'secure_data' else 'secure_data_response'
    resp = wait_type(expected, src=MITM_CTRL, dst=DUMMY_ROBOT, encrypted=True, timeout=25)
    return dec_json(resp, shared_controller)


def wait_next_robot(shared_robot):
    pkt = wait(lambda m: m.get('src') == ROBOT and m.get('dst') == CTRL and m.get('msg_type') in ('secure_data', 'secure_data_request') and 'encrypted' in m,
               'next encrypted robot packet', timeout=30)
    return pkt['msg_type'], dec_json(pkt, shared_robot)


def send_to_robot(pt_obj, typ, shared_robot, wait_next=True):
    pkt = {
        'msg_type': typ,
        'src': MITM_CTRL,
        'dst': ROBOT,
        'encrypted': encrypt(json.dumps(pt_obj), shared_robot),
    }
    tx(pkt)
    if not wait_next:
        return None, None
    return wait_next_robot(shared_robot)


def normal_round(msg_robot, shared_controller, shared_robot):
    ack = send_to_controller(msg_robot, 'secure_data', shared_controller)
    typ, msg_robot = send_to_robot(ack, 'secure_data_ack', shared_robot)
    if typ != 'secure_data_request':
        req = wait_type('secure_data_request', src=ROBOT, dst=CTRL, encrypted=True, timeout=25)
        msg_robot = dec_json(req, shared_robot)
    response = send_to_controller(msg_robot, 'secure_data_request', shared_controller)
    typ, next_robot = send_to_robot(response, 'secure_data_response', shared_robot)
    return next_robot, response


def normal_round_final(msg_robot, shared_controller, shared_robot):
    ack = send_to_controller(msg_robot, 'secure_data', shared_controller)
    typ, msg_robot = send_to_robot(ack, 'secure_data_ack', shared_robot)
    if typ != 'secure_data_request':
        req = wait_type('secure_data_request', src=ROBOT, dst=CTRL, encrypted=True, timeout=25)
        msg_robot = dec_json(req, shared_robot)
    response = send_to_controller(msg_robot, 'secure_data_request', shared_controller)
    send_to_robot(response, 'secure_data_response', shared_robot, wait_next=False)
    return response


def blank_round(msg_robot, shared_controller, shared_robot):
    response = send_to_controller(msg_robot, 'secure_data_request', shared_controller)
    typ, next_robot = send_to_robot(response, 'secure_data_response', shared_robot)
    return next_robot, response


def invalid_ack(shared_robot):
    # Any bad HMAC keeps robot nonce unchanged and pushes it into recv_secure_data.
    bad = add_hmac('', 99, shared_robot)
    tx({'msg_type': 'secure_data_ack', 'src': MITM_CTRL, 'dst': ROBOT, 'encrypted': encrypt(json.dumps(bad), shared_robot)})
    req = wait_type('secure_data_request', src=ROBOT, dst=CTRL, encrypted=True, timeout=30)
    return dec_json(req, shared_robot)


def load_cache():
    p = Path(CACHE_FILE)
    if not p.exists():
        return {'commands': {}, 'blanks': {}}
    return json.loads(p.read_text())


def save_cache(cache):
    Path(CACHE_FILE).write_text(json.dumps(cache, indent=2, sort_keys=True))
    print(f'[+] Guardado {CACHE_FILE}', flush=True)


def key_cmd(message, nonce):
    return f'{message}:{int(nonce)}'


def phase_cmd():
    cache = load_cache()
    cache.setdefault('commands', {})
    msg_robot, shared_robot, shared_controller = mitm_session()

    for i in range(20):
        # Last movement does not need a following robot packet; use final only on i==19.
        if i == 19:
            resp = normal_round_final(msg_robot, shared_controller, shared_robot)
            msg_robot = None
        else:
            msg_robot, resp = normal_round(msg_robot, shared_controller, shared_robot)
        k = key_cmd(resp['message'], resp['nonce'])
        cache['commands'][k] = resp
        print(f'[+] Movimiento {i+1:02d}: {resp}', flush=True)
        save_cache(cache)
        if all(key_cmd(m, n) in cache['commands'] for m, n in NEEDED_COMMANDS):
            print('[+] Ya estan todos los movimientos necesarios.', flush=True)
            return
    print('[+] Fin de captura de comandos. Reinicia instancia para la siguiente fase.', flush=True)


def phase_blank():
    cache = load_cache()
    cache.setdefault('blanks', {})
    msg_robot, shared_robot, shared_controller = mitm_session()

    msg_robot = invalid_ack(shared_robot)
    for i in range(14):
        msg_robot, resp = blank_round(msg_robot, shared_controller, shared_robot)
        cache['blanks'][str(int(resp['nonce']))] = resp
        print(f'[+] Blank {i:02d}: {resp}', flush=True)
        save_cache(cache)
        if all(str(n) in cache['blanks'] for n in NEEDED_BLANKS):
            print('[+] Ya estan los blanks necesarios.', flush=True)
            return
    print('[+] Fin de captura de blanks. Reinicia instancia para solve.', flush=True)


def controller_only(msg_robot, typ, shared_controller):
    resp = send_to_controller(msg_robot, typ, shared_controller)
    print('[+] Controller-only:', resp, flush=True)
    return resp


def chosen_response(resp_obj, shared_robot):
    print('[+] Chosen response:', resp_obj, flush=True)
    typ, msg_robot = send_to_robot(resp_obj, 'secure_data_response', shared_robot)
    print('[+] Robot next:', typ, msg_robot, flush=True)
    return msg_robot


def phase_solve():
    cache = load_cache()
    missing_cmd = [key_cmd(m, n) for m, n in NEEDED_COMMANDS if key_cmd(m, n) not in cache.get('commands', {})]
    missing_blank = [str(n) for n in NEEDED_BLANKS if str(n) not in cache.get('blanks', {})]
    if missing_cmd or missing_blank:
        print('[!] Faltan valores en cache.', flush=True)
        print('    comandos:', missing_cmd, flush=True)
        print('    blanks:', missing_blank, flush=True)
        print('    Ejecuta primero: cmd en una instancia fresca, luego blank en otra instancia fresca.', flush=True)
        sys.exit(2)

    forced = [cache['commands'][key_cmd(m, n)] for m, n in NEEDED_COMMANDS]
    blanks = [cache['blanks'][str(n)] for n in NEEDED_BLANKS]

    msg_robot, shared_robot, shared_controller = mitm_session()

    # First: east, south normally.
    for _ in range(2):
        msg_robot, resp = normal_round(msg_robot, shared_controller, shared_robot)
        print('[+] Normal:', resp, flush=True)

    msg_robot = invalid_ack(shared_robot)
    for _ in range(5):
        msg_robot, _ = blank_round(msg_robot, shared_controller, shared_robot)
    controller_only(msg_robot, 'secure_data_request', shared_controller)
    msg_robot = chosen_response(forced[0], shared_robot)

    controller_only(msg_robot, 'secure_data', shared_controller)
    msg_robot = invalid_ack(shared_robot)
    msg_robot = chosen_response(blanks[0], shared_robot)
    controller_only(msg_robot, 'secure_data_request', shared_controller)
    msg_robot = chosen_response(blanks[1], shared_robot)
    for _ in range(3):
        msg_robot, _ = blank_round(msg_robot, shared_controller, shared_robot)
    controller_only(msg_robot, 'secure_data_request', shared_controller)
    msg_robot = chosen_response(forced[1], shared_robot)

    msg_robot = invalid_ack(shared_robot)
    for _ in range(5):
        msg_robot, _ = blank_round(msg_robot, shared_controller, shared_robot)
    controller_only(msg_robot, 'secure_data_request', shared_controller)
    msg_robot = chosen_response(forced[2], shared_robot)

    msg_robot = invalid_ack(shared_robot)
    for _ in range(5):
        msg_robot, _ = blank_round(msg_robot, shared_controller, shared_robot)
    controller_only(msg_robot, 'secure_data_request', shared_controller)
    msg_robot = chosen_response(forced[3], shared_robot)

    msg_robot = invalid_ack(shared_robot)
    for _ in range(5):
        msg_robot, _ = blank_round(msg_robot, shared_controller, shared_robot)
    controller_only(msg_robot, 'secure_data_request', shared_controller)
    msg_robot = chosen_response(forced[4], shared_robot)

    for _ in range(6):
        msg_robot, resp = normal_round(msg_robot, shared_controller, shared_robot)
        print('[+] Final normal:', resp, flush=True)

    time.sleep(1)
    st = state()
    print('[+] Estado final:')
    print(json.dumps(st, indent=2), flush=True)
    if 'picoCTF{' in str(st.get('flag', '')):
        print('[+] FLAG:', st['flag'], flush=True)
    else:
        print('[!] No salio flag. Reinicia una instancia fresca y repite solo solve con la cache ya guardada.', flush=True)


def main():
    global SERVER
    if len(sys.argv) != 3 or sys.argv[1] not in ('cmd', 'blank', 'solve'):
        print(f'Usage: {sys.argv[0]} cmd|blank|solve <port_or_url>')
        print('Workflow:')
        print('  1) Fresh instance: python3 ricochet_three_phase.py cmd URL')
        print('  2) Restart instance: python3 ricochet_three_phase.py blank NEW_URL')
        print('  3) Restart instance: python3 ricochet_three_phase.py solve NEW_URL')
        sys.exit(1)
    mode = sys.argv[1]
    SERVER = norm_url(sys.argv[2])
    print('[+] URL:', SERVER, flush=True)
    print('[+] Mode:', mode, flush=True)
    if mode == 'cmd':
        phase_cmd()
    elif mode == 'blank':
        phase_blank()
    else:
        phase_solve()


if __name__ == '__main__':
    main()
