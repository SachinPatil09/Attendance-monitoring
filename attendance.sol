// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Attendance {
    struct AttendanceRecord {
        string name;
        string timestamp;
        string hash;
    }

    AttendanceRecord[] public records;

    function logAttendance(string memory _name, string memory _timestamp, string memory _hash) public {
        records.push(AttendanceRecord(_name, _timestamp, _hash));
    }

    function getRecord(uint index) public view returns (string memory, string memory, string memory) {
        AttendanceRecord memory record = records[index];
        return (record.name, record.timestamp, record.hash);
    }

    function totalRecords() public view returns (uint) {
        return records.length;
    }
}
