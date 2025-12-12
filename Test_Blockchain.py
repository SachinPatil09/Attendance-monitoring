from web3 import Web3

# -------------------------------
# 1. Connect to Blockchain Node
# -------------------------------
# Ganache (Local)
WEB3_PROVIDER = "http://127.0.0.1:7545"

# If you want Sepolia (future use):
# WEB3_PROVIDER = "https://sepolia.infura.io/v3/YOUR_INFURA_KEY"

w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

if not w3.is_connected():
    print("❌ ERROR: Web3 not connected! Check Ganache/Infura.")
    exit()
else:
    print("✅ Web3 Connected Successfully.")

# -------------------------------
# 2. Contract Details
# -------------------------------
CONTRACT_ADDRESS = "A"

ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "_name", "type": "string"},
            {"internalType": "string", "name": "_timestamp", "type": "string"},
            {"internalType": "string", "name": "_hash", "type": "string"}
        ],
        "name": "logAttendance",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "index", "type": "uint256"}],
        "name": "getRecord",
        "outputs": [
            {"internalType": "string", "name": "", "type": "string"},
            {"internalType": "string", "name": "", "type": "string"},
            {"internalType": "string", "name": "", "type": "string"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "records",
        "outputs": [
            {"internalType": "string", "name": "name", "type": "string"},
            {"internalType": "string", "name": "timestamp", "type": "string"},
            {"internalType": "string", "name": "hash", "type": "string"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalRecords",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Convert address to checksum
CONTRACT_ADDRESS = Web3.to_checksum_address(CONTRACT_ADDRESS)

# -------------------------------
# 3. Load Contract
# -------------------------------
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

# -------------------------------
# 4. Read Attendance Records
# -------------------------------
try:
    total = contract.functions.totalRecords().call()
    print(f"\n📌 Total Attendance Records: {total}\n")

    if total == 0:
        print("No records found.")
        exit()

    for i in range(total):
        name, timestamp, hash_value = contract.functions.getRecord(i).call()

        print(f"----- RECORD {i} -----")
        print(f"👤 Name: {name}")
        print(f"⏰ Time: {timestamp}")
        print(f"🔐 Hash: {hash_value}\n")

except Exception as e:
    print("❌ Error reading from contract:", str(e))
