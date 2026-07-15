import os
import json
import monocypher
import crypto
from radio_interface import *
from keys import keys # Assuming you have access to keys.py per your provided imports

def solve():
    # 1. Initialize communication
    print("Starting robot...")
    start_robot()
    
    # 2. Setup Diffie-Hellman keys
    priv_key = os.urandom(32)
    pub_key = monocypher.compute_key_exchange_public_key(priv_key)
    
    # 3. Perform Key Exchange with the Robot
    # We send our public key to the robot (dest 0x10 is the controller)
    print("Performing key exchange...")
    inject_radio_message({
        "msg_type": "key_exchange",
        "src": 0x41, # Our spoofed address
        "dst": 0x10,
        "key": pub_key.hex()
    })

    # 4. Derive shared secret 
    # (In a real scenario, you'd capture the robot's response to get their public key)
    # For this challenge, we simulate the handshake completion
    # robot_pub_key = ... (extract from receive_radio_messages)
    # shared_secret = monocypher.key_exchange(priv_key, robot_pub_key)
    
    # 5. Send Commands
    # Since we want to stop the demo loop and move to the flag,
    # we send the payload encrypted with the session key.
    target_commands = ["north", "north", "east", "east"] # Example path
    
    for cmd in target_commands:
        print(f"Sending command: {cmd}")
        # We must use the HSK (authenticity key) for the HMAC
        # and the DH shared secret for the encryption
        msg_with_hmac = json.dumps(crypto.add_hmac(cmd, 0, keys["shared_hmac_key"]))
        encrypted_payload = crypto.encrypt(msg_with_hmac, shared_secret)
        
        inject_radio_message({
            "msg_type": "secure_data",
            "src": 0x41,
            "dst": 0x10,
            "encrypted": encrypted_payload
        })

if __name__ == "__main__":
    solve()
