import argparse
import cv2
import os
import json
import hashlib
from datetime import datetime
import numpy as np
from pathlib import Path
import textwrap
from insightface.app import FaceAnalysis

# optional web3 imports — only required when user requests to send to blockchain
try:
    from web3 import Web3
    from eth_account import Account
except Exception:
    Web3 = None
    Account = None

# --------------------------------------
# 1. Initialize InsightFace model
# --------------------------------------
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

# --------------------------------------
# 2. Load all embeddings automatically
# --------------------------------------
STUDENT_FOLDER = "student_data"

def load_all_embeddings():
    embeddings = {}

    if not os.path.exists(STUDENT_FOLDER):
        print(f"❌ Folder not found: {STUDENT_FOLDER}")
        return embeddings

    for file in os.listdir(STUDENT_FOLDER):
        if file.endswith("_embedding.json"):
            name = file.replace("_embedding.json", "")
            path = os.path.join(STUDENT_FOLDER, file)

            try:
                with open(path, "r") as f:
                    embeddings[name] = json.load(f)
                print(f"✅ Loaded embedding → {name}")
            except Exception as e:
                print(f"⚠ Could not load {file}: {e}")

    return embeddings


# -----------------------------
# Configuration & Defaults
# Replace placeholders below or set the environment variables externally.
# Windows (cmd.exe):
#   set WEB3_PROVIDER_URI=http://127.0.0.1:7545
#   set CONTRACT_ADDRESS=0x<YOUR_CONTRACT_ADDRESS>
#   set ACCOUNT_ADDRESS=0x<YOUR_ACCOUNT>
#   set PRIVATE_KEY=0x<SOMEKEY>
# (recommended: set environment variables instead of hardcoding values here)
# -----------------------------

# You can edit the placeholder values below (not recommended for private keys in source control):
DEFAULT_WEB3_PROVIDER_URI = os.getenv('WEB3_PROVIDER_URI', 'http://127.0.0.1:7545')
DEFAULT_CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS', '0xF00FbA609da21a13d3afb8682afe8A181bF3EA15')
DEFAULT_ACCOUNT_ADDRESS = os.getenv('ACCOUNT_ADDRESS', '0xA31534EC2d144C309b08BB9a51A8b6CfDCb385ec')
DEFAULT_PRIVATE_KEY = os.getenv('PRIVATE_KEY', '0x1d77cbde1e28ba8aaaf6e9ff779f36822b9a39a7851654ca76efda7c89eb778d')



# --------------------------------------
# 3. Compare embeddings (cosine similarity)
# --------------------------------------
def compare_embeddings(e1, e2):
    e1, e2 = np.array(e1), np.array(e2)
    return np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2))


# --------------------------------------
# 4. Match detected face with known users
# --------------------------------------
def match_face(face_embedding, known_embeddings, threshold=0.55):
    best_name = None
    best_score = 0

    for name, emb in known_embeddings.items():
        score = compare_embeddings(face_embedding, emb)
        if score > threshold and score > best_score:
            best_score = score
            best_name = name

    return best_name


# --------------------------------------
# 5. Save attendance (blockchain placeholder)
# --------------------------------------
def save_to_blockchain(name, timestamp, web3=None, contract=None, account_address=None, private_key=None):
    hash_str = hashlib.sha256(f"{name}-{timestamp}".encode()).hexdigest()

    print("\n📌 Sending to blockchain...")
    print(f"👤 Name: {name}")
    print(f"⏰ Time: {timestamp}")
    print(f"🔐 Hash: {hash_str}\n")
    # If web3 is provided, attempt to send a real transaction
    if web3 and contract and private_key and account_address:
        try:
            nonce = web3.eth.get_transaction_count(account_address)

            txn = {
                'from': account_address,
                'nonce': nonce,
                'gasPrice': web3.to_wei('10', 'gwei'),
                'chainId': web3.eth.chain_id,
            }

            txn['gas'] = contract.functions.logAttendance(name, timestamp, hash_str).estimate_gas(txn)

            txn = contract.functions.logAttendance(name, timestamp, hash_str).build_transaction(txn)

            signed_txn = Account.sign_transaction(txn, private_key=private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

            print(f"✅ Sent to chain. Tx: {tx_receipt.transactionHash.hex()}")
            return True, tx_receipt.transactionHash.hex()
        except Exception as e:
            print(f"❌ Error sending transaction: {e}")
            return False, None

    # Not sending — fallback to printing only
    return False, None


# --------------------------------------
# 6. Webcam Attendance Capture
# --------------------------------------
def capture_and_log(send_to_chain=False, web3=None, contract=None, account_address=None, private_key=None):
    cap = cv2.VideoCapture(0)
    known_embeddings = load_all_embeddings()
    logged_today = set()

    print("\n🎥 Webcam started. Press Q to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Camera error.")
            break

        faces = app.get(frame)

        for face in faces:
            emb = face.embedding.tolist()
            name = match_face(emb, known_embeddings)

            x1, y1, x2, y2 = map(int, face.bbox)

            if name:
                # Log only once per run
                if name not in logged_today:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    if send_to_chain:
                        success, tx_hash = save_to_blockchain(name, timestamp, web3=web3, contract=contract, account_address=account_address, private_key=private_key)
                        if success:
                            logged_today.add(name)
                        else:
                            # still add to logged_today to avoid reattempt spamming if needed — change behavior if you prefer
                            logged_today.add(name)
                    else:
                        # Dry - just print
                        save_to_blockchain(name, timestamp)
                        logged_today.add(name)

                text = f"{name}"
                color = (0, 255, 0)

            else:
                text = "Unknown"
                color = (0, 0, 255)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, text, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        cv2.imshow("FaceGuard - Attendance System", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\n🛑 Webcam stopped.")


# --------------------------------------
# MAIN
# --------------------------------------
def init_web3_and_contract(rpc_url, contract_address, abi_path, private_key, account_address):
    if Web3 is None or Account is None:
        raise ImportError("web3/eth-account are required to send to blockchain. Install with `pip install web3 eth-account`")

    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise ConnectionError(f"Could not connect to RPC at {rpc_url}")

    with open(abi_path, 'r') as f:
        abi = json.load(f)

    contract = web3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
    return web3, contract


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Webcam face attendance. By default prints events without sending to blockchain.")
    parser.add_argument("--send", action='store_true', help="Attempt to send detected attendance events to the configured blockchain contract")
    parser.add_argument("--rpc", default=DEFAULT_WEB3_PROVIDER_URI, help="Web3 RPC URL")
    parser.add_argument("--contract", default=DEFAULT_CONTRACT_ADDRESS, help="Contract address")
    parser.add_argument("--abi", default=os.getenv('ATTENDANCE_ABI_PATH', 'AttendanceABI.json'), help="ABI path")
    parser.add_argument("--account", default=DEFAULT_ACCOUNT_ADDRESS, help="Account address used to send transactions")
    parser.add_argument("--private-key", default=DEFAULT_PRIVATE_KEY, help="(Optional) Private key for account. Recommended to use env var instead of passing on command line")

    args = parser.parse_args()

    web3_client = None
    contract_client = None
    if args.send:
        try:
            web3_client, contract_client = init_web3_and_contract(args.rpc, args.contract, args.abi, args.private_key, args.account)
        except Exception as e:
            print(f"❌ Could not initialize web3/contract: {e}")
            print("Note: Running in dry mode (will not send transactions)")
            args.send = False
    # Print selected configuration (mask private key)
    if args.send:
        masked_key = (args.private_key[:6] + '...' + args.private_key[-4:]) if args.private_key else '*** EMPTY - will fail to sign transactions'
        print(f"Using RPC: {args.rpc}")
        print(f"Using Contract: {args.contract}")
        print(f"Using Account: {args.account}")
        print(f"Using Private Key: {masked_key}")

    capture_and_log(send_to_chain=args.send, web3=web3_client, contract=contract_client, account_address=args.account, private_key=args.private_key)
