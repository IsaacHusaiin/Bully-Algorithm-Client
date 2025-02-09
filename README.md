# Bully Algorithm Client Implementation 

## Project Overview
This project implements the client-side of a group of nodes that participate in leader election using the **Bully Algorithm**. The nodes communicate with a central **Group Coordinator Daemon (GCD)** to initiate and carry out leader elections, allowing them to handle leader failures and ensure a stable, fault-tolerant system.

### Author
**Isaac Yushaiyin**

### Purpose
The purpose of `lab2.py` is to manage leader election among distributed nodes, where the highest-priority node is selected as the leader. This algorithm is particularly useful in distributed systems requiring dynamic leader selection, such as clustered servers or fault-tolerant applications.

## Project Details

- **Filename**: `lab2.py`
- **Date**: October 17, 2024
- **Programming Language**: Python
- **Algorithm**: Bully Algorithm for leader election

### Key Features
- **Leader Election**: Each node is capable of participating in a leader election process.
- **Node Communication**: Uses network sockets to communicate with the GCD and other nodes.
- **Fault Tolerance**: Automatically initiates a leader election when the current leader fails.

## File Structure
- `lab2.py`: The main client script that connects to the GCD and participates in the leader election process.
- Other files (if applicable): Describe any other files, such as helper scripts or configuration files.

## Requirements
- Python 3.x
- `socket` library for networking (typically included with Python)

## How to Run
1. Ensure the GCD server is running and accessible.
2. Start multiple instances of `lab2.py` to simulate nodes in the network.
3. The nodes will communicate with the GCD and with each other to elect a leader.

### Example Usage
```bash
python3 lab2.py --host <GCD_host> --port <GCD_port>
