"""
Get_Attendance_By_Time.py

Reads attendance records from the deployed Attendance contract and filters by time range.

Usage:
  python Get_Attendance_By_Time.py --start "2025-12-01 20:19:00" --end "2025-12-01 20:20:00" --rpc http://127.0.0.1:7545 --contract 0x5fE759fb539A504Db4deA32DEC8324E73c1FE9D7

Optional: --save results to a CSV/JSON file
"""

import argparse
import csv
import json
from datetime import datetime
import re
from pathlib import Path
from web3 import Web3
from web3.exceptions import BadFunctionCallOutput

# Default contract/ABI/settings from the repo (adjust if you deploy a different address)
DEFAULT_RPC = "http://127.0.0.1:7545"
DEFAULT_CONTRACT_ADDRESS = "0xF00FbA609da21a13d3afb8682afe8A181bF3EA15"
DEFAULT_ABI_PATH = "AttendanceABI.json"

# timestamp format used by the app
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def load_abi(path: str):
    with open(path, "r") as f:
        return json.load(f)


def parse_time(txt: str) -> datetime:
    # Accept date-only or date+time
    try:
        return datetime.strptime(txt, DATETIME_FORMAT)
    except ValueError:
        try:
            # try date only
            return datetime.strptime(txt, "%Y-%m-%d")
        except ValueError:
            raise


def collect_records(w3: Web3, contract, start_dt: datetime, end_dt: datetime, debug: bool = False, include_invalid: bool = False, block_time_map: dict = None):
    """Collect valid records between start_dt and end_dt.

    Returns a tuple: (valid_records_list, invalid_records_list)
    """
    records = []
    invalid_records = []
    total = contract.functions.totalRecords().call()

    for i in range(total):
        try:
            raw = contract.functions.getRecord(i).call()
        except Exception as e:
            print(f"⚠ Error fetching record {i}: {e}")
            continue

        if debug:
            print(f"DEBUG: raw record {i}: {repr(raw)} (types: {[type(x) for x in raw]})")

        try:
            name, timestamp_str, hash_value = raw
        except Exception as e:
            print(f"⚠ Unexpected record shape for {i}: {repr(raw)} -> {e}")
            if include_invalid:
                # include it as invalid if requested
                invalid_records.append({"index": i, "name": None, "timestamp": None, "hash": None, "raw": raw})
            continue

        # Parse the timestamp string. If unable to parse, try regex fallback.
        rec_dt = None
        try:
            rec_dt = datetime.strptime(timestamp_str, DATETIME_FORMAT)
        except Exception:
            m = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", str(timestamp_str))
            if m:
                try:
                    rec_dt = datetime.strptime(m.group(0), DATETIME_FORMAT)
                except Exception:
                    rec_dt = None

        # If block_time_map is provided and contains an entry for this index, use it as authoritative
        if block_time_map and i in block_time_map:
            rec_dt = block_time_map[i]

        if rec_dt is None:
            print(f"⚠ Skipping record {i} (timestamp parse error): {repr(timestamp_str)}")
            if debug:
                print(f"DEBUG: full record {i}: name={repr(name)}, ts={repr(timestamp_str)}, hash={repr(hash_value)}")
            if include_invalid:
                invalid_records.append({
                    "index": i,
                    "name": name,
                    "timestamp": timestamp_str,
                    "hash": hash_value,
                })
            continue

        if start_dt <= rec_dt <= end_dt:
            records.append({
                "index": i,
                "name": name,
                "timestamp": timestamp_str,
                "hash": hash_value,
            })

    return records, invalid_records


def save_to_csv(records, path: str):
    keys = ["index", "name", "timestamp", "hash"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in records:
            writer.writerow(r)


def save_to_json(records, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Query attendance records by time range")

    parser.add_argument("--start", help=f"Start datetime; format: '{DATETIME_FORMAT}' or 'YYYY-MM-DD'")
    parser.add_argument("--end", help=f"End datetime; format: '{DATETIME_FORMAT}' or 'YYYY-MM-DD' (default: now)")
    parser.add_argument("--date", help="Date-only filter in YYYY-MM-DD format (mutually exclusive with --start)")
    
    parser.add_argument("--rpc", default=DEFAULT_RPC, help="Web3 RPC URL (default: Ganache HTTP)")
    parser.add_argument("--contract", default=DEFAULT_CONTRACT_ADDRESS, help="Contract address (default value from repo)")
    parser.add_argument("--abi", default=DEFAULT_ABI_PATH, help="Path to ABI JSON file")

    parser.add_argument("--save", help="Save results to file (CSV or JSON by extension) e.g., out.csv or out.json")
    parser.add_argument("--debug", action="store_true", help="Print raw values from the contract for debugging")
    parser.add_argument("--include-invalid", action="store_true", help="Include records with invalid/unparseable timestamp in the output (printed separately)")
    parser.add_argument("--use-block-times", action="store_true", help="Use block timestamps for logAttendance transactions (fallback or authoritative time)")
    parser.add_argument("--from-block", type=int, default=0, help="Start block to scan for logAttendance transactions (when using --use-block-times)")
    parser.add_argument("--to-block", default="latest", help="End block to scan (int or 'latest'); used with --use-block-times")

    args = parser.parse_args()

    # If --date is provided, compute start and end for that whole day
    if args.date:
        if args.start or args.end:
            parser.error("--date cannot be used with --start or --end; pick one approach")

        # parse_date returns midnight start and end at 23:59:59
        try:
            day_dt = datetime.strptime(args.date, "%Y-%m-%d")
        except Exception as e:
            parser.error(f"Invalid --date format: use YYYY-MM-DD. Error: {e}")

        start_dt = datetime(year=day_dt.year, month=day_dt.month, day=day_dt.day, hour=0, minute=0, second=0)
        end_dt = datetime(year=day_dt.year, month=day_dt.month, day=day_dt.day, hour=23, minute=59, second=59)
    else:
        if not args.start:
            parser.error("--start is required unless --date is provided")

        start_dt = parse_time(args.start)
        end_dt = parse_time(args.end) if args.end else datetime.now()

    if end_dt < start_dt:
        parser.error("--end cannot be earlier than --start")

    # Connect web3
    w3 = Web3(Web3.HTTPProvider(args.rpc))
    if not w3.is_connected():
        print("❌ Web3 not connected. Check your RPC URL (Ganache).")
        return

    # Load ABI and contract
    try:
        abi = load_abi(args.abi)
    except Exception as e:
        print(f"❌ Could not load ABI from {args.abi}: {e}")
        return

    checksum_address = Web3.to_checksum_address(args.contract)
    contract = w3.eth.contract(address=checksum_address, abi=abi)

    # Diagnostic checks to help debug contract issues
    try:
        chain_id = w3.eth.chain_id
        print(f"Connected to chain id: {chain_id}")
    except Exception:
        print("⚠ Could not query chain id — check your RPC provider.")

    try:
        code = w3.eth.get_code(checksum_address)
        if not code or code in (b"", b"0x"):
            print(f"❌ No contract code found at {checksum_address}. Is the contract deployed to this chain?")
            return
    except Exception as e:
        print(f"⚠ Could not get code for contract address {checksum_address}: {e}")
        # proceed — the subsequent call will likely fail but we still attempt it for clearer error

    # Print total records (diagnostic)
    try:
        total_onchain = contract.functions.totalRecords().call()
        print(f"On-chain totalRecords: {total_onchain}")
    except Exception as e:
        print(f"⚠ Could not read totalRecords(): {e}")

    # If the user asked to use block timestamps, build a mapping of tx order to block datetime
    block_time_map = None
    if args.use_block_times:
        # Build mapping of record index -> block datetime using logAttendance transactions chronological order
        try:
            from_block = args.from_block
            to_block = args.to_block
            if to_block == "latest":
                to_block = w3.eth.block_number

            print(f"Scanning blocks {from_block}..{to_block} for logAttendance transactions (this may take a while)...")
            block_time_map = {}
            current_index = 0
            for b in range(from_block, int(to_block) + 1):
                block = w3.eth.get_block(b, full_transactions=True)
                for tx in block.transactions:
                    # Some transactions may have 'to' as None or not be to the contract
                    if not tx.to:
                        continue
                    if Web3.to_checksum_address(tx.to) != checksum_address:
                        continue
                    # Try to decode the function input using ABI
                    try:
                        fn, args_decoded = contract.decode_function_input(tx.input)
                    except Exception:
                        continue
                    if fn.fn_name == 'logAttendance':
                        block_time_map[current_index] = datetime.fromtimestamp(block.timestamp)
                        current_index += 1
            print(f"Found {len(block_time_map)} logAttendance transactions.")
        except Exception as e:
            print(f"⚠ Could not build block time mapping: {e}")
            block_time_map = None

    # Collect records in range
    try:
        results, invalid_records = collect_records(w3, contract, start_dt, end_dt, debug=args.debug, include_invalid=args.include_invalid, block_time_map=block_time_map)
    except BadFunctionCallOutput as e:
        print("❌ Could not call contract function — BadFunctionCallOutput (ABI mismatch or contract not deployed).")
        print("👉 Check: correct contract address, correct ABI JSON, and that Ganache is running on the provided RPC URL.")
        print(f"Error details: {e}")
        return
    except Exception as e:
        print(f"❌ Unexpected error while collecting records: {e}")
        return

    if not results:
        print("No attendance records found for the given time range.")
        if invalid_records:
            if args.include_invalid:
                print(f"Note: {len(invalid_records)} record(s) were skipped due to invalid timestamps; they are listed below.")
            else:
                print(f"Note: {len(invalid_records)} record(s) exist with invalid timestamps. Use --include-invalid to print them.")
    else:
        # Print results
        print(f"\n📌 Attendance records between {start_dt} and {end_dt}:\n")
        for r in results:
            print(f"--- Record {r['index']} ---")
            print(f"👤 Name: {r['name']}")
            print(f"⏰ Time: {r['timestamp']}")
            if block_time_map and r['index'] in block_time_map:
                print(f"⏱ Block Time: {block_time_map[r['index']].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🔐 Hash: {r['hash']}\n")

    # If there were invalid records and user asked to include them, print them now
    if args.include_invalid and invalid_records:
        print(f"\n⚠ Records with invalid timestamps (could not be parsed):\n")
        for r in invalid_records:
            print(f"--- Record {r.get('index')} ---")
            print(f"👤 Name: {r.get('name')}")
            print(f"⏰ Time: {r.get('timestamp')}")
            print(f"🔐 Hash: {r.get('hash')}")
            if 'raw' in r:
                print(f"RAW: {r['raw']}")
            print()

    # Save if asked
    if args.save:
        save_path = Path(args.save)
        ext = save_path.suffix.lower()
        try:
            if ext == ".csv":
                save_to_csv(results, str(save_path))
                print(f"Saved results to CSV: {save_path}")
            elif ext == ".json":
                save_to_json(results, str(save_path))
                print(f"Saved results to JSON: {save_path}")
            else:
                print("Unknown extension for --save. Use .csv or .json. Skipping save.")
        except Exception as e:
            print(f"Error saving results: {e}")


if __name__ == "__main__":
    main()
