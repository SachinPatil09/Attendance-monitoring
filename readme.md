# 🛡️ FaceGuard – Tamper-Proof Facial Attendance System with Blockchain Logging

FaceGuard is a secure facial recognition-based attendance system powered by blockchain. It ensures attendance records are immutable, tamper-proof, and securely logged on a local Ethereum blockchain.

This project combines computer vision (InsightFace), real-time face recognition (OpenCV + Streamlit), and smart contract integration (Solidity + Web3.py + Ganache).

---

## 📌 Features

- 🎯 Real-time face recognition using InsightFace
- 📝 Record attendance with student name and timestamp
- 🔒 Save each record immutably to a blockchain (Ganache)
- 🧠 Store embeddings in `student_data/` for fast lookup
- 🧪 Test scripts to verify face detection and blockchain write/read

---

## 🗃️ Folder Structure

FaceGuard/

│
|
├── Register_Student.py # CLI to register new students
|
├── face_attendance.py # Local test to verify face recognition works
|
├── app.py # Main Streamlit web interface with blockchain
|
├── test_blockchain.py # Verifies that records are stored on-chain
|
├── AttendanceABI.json # ABI file from compiled smart contract
|
├── student_data/ # Stores embeddings for each registered student
|
├── Attendance.sol # Solidity smart contract (optional)
|
├── requirements.txt # Python dependencies
|
└── README.md


---

## ⚙️ Requirements

- Python 3.10
- Ganache(https://trufflesuite.com/ganache/)
- MetaMask (for optional public testnets)
- Streamlit
- InsightFace
- OpenCV
- Web3.py

---

## 🔧 Installation

### 1. Clone this repository

```bash
git clone https://github.com/qasim233/FaceGuard_Attendance_System_Using_Face_Recognition_on_Blockchain.git
cd FaceGuard_Attendance_System_Using_Face_Recognition_on_Blockchain
```

### 2. Create a virtual Environment

For windows:
```bash
python -m venv .venv

.venv/Scripts/activate
```

For Linux:
```bash
python -m venv .venv

source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

## 🧑‍🎓 Step 1: Register Student
Use Register_Student.py to generate a face embedding for a student. The image filename must match the student name.

```bash
python Register_Student.py
```
You will be prompted to enter name of student, and path of image. It will save the embedding in student_data/ folder.

## 🧪 Step 2: Test Face Detection Locally
To check if face recognition is working before using the blockchain:

```bash
python face_attendance.py
```

- Opens your webcam
- Displays “Welcome [Name]” if known
- Logs the result to the console with hash

## 🌐 Step 3: Launch the Streamlit Web App
Run the web interface that logs attendance to the blockchain:

```bash
streamlit run app.py
```
- Recognized faces are logged with name and timestamp
- A SHA-256 hash is generated
- A transaction is sent to the smart contract

**Note:** 🧠 Make sure you have embeddings inside student_data/ and have updated the known_faces dictionary in app.py.

## 🔗 Blockchain Setup (Ganache + MetaMask)
# ✅ Using Ganache (Local Blockchain)
Download & install Ganache:
https://trufflesuite.com/ganache/

- Run Ganache GUI
- Copy an account's address and private key
- Update ACCOUNT_ADDRESS and PRIVATE_KEY in app.py
- Deploy the **attendance.sol** contract in Remix IDE
After deploying:
-Copy the contract address into CONTRACT_ADDRESS in app.py
-Copy the ABI from Remix and save to AttendanceABI.json

## 🧪 Step 4: Test Blockchain Records
After using the Streamlit app, you can verify that records in **new terminal**, are saved:

```bash
python test_blockchain.py
```
This script:
- Reads total records from the smart contract
- Prints each student's name, timestamp, and hash

### 🔒 Security Notes
-NEVER expose your private key in a public repo
-For production: use MetaMask or hardware wallet
- Always restrict contract permissions and audit your code

## 👨‍💻 Author
Made with ❤️ by Muhammad Qasim
