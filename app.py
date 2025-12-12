import streamlit as st
import cv2
import numpy as np
from insightface.app import FaceAnalysis
from datetime import datetime
import hashlib
import json
import os
from web3 import Web3
from eth_account import Account

# -------------------------
# Streamlit Page Config
# -------------------------
st.set_page_config(page_title="FaceGuard", layout="centered")
st.title("🛡️ FaceGuard - Blockchain Attendance System")

# -------------------------
# Blockchain Configuration
# -------------------------
WEB3_PROVIDER_URI = "http://127.0.0.1:7545"   # Ganache RPC URL
PRIVATE_KEY = "0x1d77cbde1e28ba8aaaf6e9ff779f36822b9a39a7851654ca76efda7c89eb778d"
ACCOUNT_ADDRESS = "0xA31534EC2d144C309b08BB9a51A8b6CfDCb385ec"
CONTRACT_ADDRESS = "0xF00FbA609da21a13d3afb8682afe8A181bF3EA15"

# Load ABI
with open("AttendanceABI.json", "r") as f:
    ABI = json.load(f)

# Connect web3
web3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URI))
contract = web3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS), 
    abi=ABI
)

# -------------------------
# Auto-Load All Embeddings
# -------------------------
def load_known_embeddings():
    embeddings = {}
    folder = "student_data"

    for filename in os.listdir(folder):
        if filename.endswith(".json"):
            path = os.path.join(folder, filename)

            # Extract student name from filename
            student_name = filename.replace("_embedding.json", "")

            with open(path, 'r') as f:
                data = json.load(f)

            embeddings[student_name] = data

    return embeddings


# -------------------------
# Compare Face Embeddings
# -------------------------
def compare_embeddings(emb1, emb2):
    emb1 = np.array(emb1)
    emb2 = np.array(emb2)
    return np.dot(emb1, emb2) / (np.linalg.norm(emb1)*np.linalg.norm(emb2))


# -------------------------
# Match Face to Student
# -------------------------
def match_face(face_embedding, known_embeddings):
    for name, known_emb in known_embeddings.items():
        if compare_embeddings(face_embedding, known_emb) > 0.50:   # threshold
            return name
    return None


# -------------------------
# Save Attendance to Blockchain
# -------------------------
def save_to_blockchain(name, timestamp):
    hash_str = hashlib.sha256(f"{name}-{timestamp}".encode()).hexdigest()

    try:
        nonce = web3.eth.get_transaction_count(ACCOUNT_ADDRESS)

        txn = {
            'from': ACCOUNT_ADDRESS,
            'nonce': nonce,
            'gasPrice': web3.to_wei('10', 'gwei'),
            'chainId': 1337
        }

        txn['gas'] = contract.functions.logAttendance(
            name, timestamp, hash_str
        ).estimate_gas(txn)

        txn = contract.functions.logAttendance(
            name, timestamp, hash_str
        ).build_transaction(txn)

        signed_txn = Account.sign_transaction(txn, private_key=PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

        st.success(f"✅ Saved to blockchain!\nTx Hash: {tx_receipt.transactionHash.hex()}")

    except Exception as e:
        st.error(f"❌ Blockchain Error: {str(e)}")


# -------------------------
# Initialize Face Model
# -------------------------
@st.cache_resource
def init_model():
    app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))
    return app


app_model = init_model()
known_embeddings = load_known_embeddings()


# -------------------------
# Streamlit Session State
# -------------------------
if "run_webcam" not in st.session_state:
    st.session_state.run_webcam = False

if "logged_users" not in st.session_state:
    st.session_state.logged_users = set()

if "session_entries" not in st.session_state:
    st.session_state.session_entries = []


# -------------------------
# Buttons (Start/Stop Webcam)
# -------------------------
col1, col2 = st.columns(2)
with col1:
    if st.button("▶️ Start Webcam"):
        st.session_state.run_webcam = True
        st.session_state.logged_users = set()
        st.session_state.session_entries = []

with col2:
    if st.button("⏹️ Stop Webcam"):
        st.session_state.run_webcam = False


# -------------------------
# Webcam Processing
# -------------------------
stframe = st.empty()

if st.session_state.run_webcam:
    cap = cv2.VideoCapture(0)

    while st.session_state.run_webcam:
        ret, frame = cap.read()
        if not ret:
            break

        faces = app_model.get(frame)

        for face in faces:
            embedding = face.embedding.tolist()
            name = match_face(embedding, known_embeddings)

            if name and name not in st.session_state.logged_users:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # record locally in session_entries for dashboard and later MetaMask sending
                hash_str = hashlib.sha256(f"{name}-{timestamp}".encode()).hexdigest()
                entry = {"name": name, "timestamp": timestamp, "hash": hash_str, "tx": None}
                st.session_state.session_entries.append(entry)
                st.session_state.logged_users.add(name)
                label = f"{name} @ {timestamp}"
                color = (0, 255, 0)

            elif name:
                label = f"{name} (Already Logged)"
                color = (100, 255, 100)

            else:
                label = "Unknown"
                color = (0, 0, 255)

            x1, y1, x2, y2 = map(int, face.bbox)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        stframe.image(frame, channels="RGB")

    cap.release()
    stframe.empty()

    # Show session dashboard when webcam stops
    if st.session_state.session_entries:
        st.markdown("---")
        st.markdown("## Session Attendance Dashboard")
        # Show a simple table
        df_rows = [ {"Name": e["name"], "Timestamp": e["timestamp"], "Hash": e["hash"], "Tx": e.get("tx", "")} for e in st.session_state.session_entries ]
        st.table(df_rows)

        # Allow user to send per-entry via MetaMask
        st.markdown("---")
        st.markdown("### Send entries via MetaMask")

        abi_text = json.dumps(ABI)
        contract_address = CONTRACT_ADDRESS

        for i, entry in enumerate(st.session_state.session_entries):
            st.write(f"**{entry['name']}** — {entry['timestamp']} — {entry['hash']}")
            if entry.get('tx'):
                st.success(f"Already sent on chain — Tx: {entry['tx']}")
                continue

            # build JS content to call contract.logAttendance with Ethers.js and MetaMask
            js_html = f"""
            <div>
              <button id='send_{i}'>Send via MetaMask</button>
              <div id='status_{i}'></div>
            </div>
            <script src='https://cdn.jsdelivr.net/npm/ethers@5.7.2/dist/ethers.min.js'></script>
            <script>
            const abi = {abi_text};
            const contractAddress = '{contract_address}';
            const name = {json.dumps(entry['name'])};
            const timestamp = {json.dumps(entry['timestamp'])};
            const hash = {json.dumps(entry['hash'])};

            document.getElementById('send_{i}').onclick = async function() {{
                const statusEl = document.getElementById('status_{i}');
                if (!window.ethereum) {{
                    statusEl.innerText = 'MetaMask not found';
                    return;
                }}
                try {{
                    const provider = new ethers.providers.Web3Provider(window.ethereum);
                    await provider.send('eth_requestAccounts', []);
                    const signer = provider.getSigner();
                    const contract = new ethers.Contract(contractAddress, abi, signer);
                    statusEl.innerText = 'Sending...';
                    const tx = await contract.logAttendance(name, timestamp, hash);
                    statusEl.innerText = 'Tx sent: ' + tx.hash + ' (waiting for confirmation)';
                    const receipt = await tx.wait();
                    statusEl.innerText = 'Mined: ' + receipt.transactionHash;
                }} catch (err) {{
                    statusEl.innerText = 'Error: ' + err.message;
                }}
            }}
            </script>
            """

            st.components.v1.html(js_html, height=160)

            st.markdown("---")
            if st.button("Refresh On-Chain Records"):
                try:
                    total = contract.functions.totalRecords().call()
                    records = []
                    for idx in range(total):
                        n, t, h = contract.functions.getRecord(idx).call()
                        records.append({"index": idx, "name": n, "timestamp": t, "hash": h})
                    st.write("### On-chain Records")
                    st.table(records)
                except Exception as e:
                    st.error(f"Error reading on-chain records: {e}")
