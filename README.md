# queueCTL
QueueCTL is a lightweight, production-grade background job queue system built with Python, SQLite, and Flask. It supports enqueuing, concurrent workers, retries with exponential backoff, DLQ management, and persistent logging, offering full CLI and REST API control for reliable background processing.

## 1. Setup instructions
Tech Stack Used = ```Python3, Flask, Click and SQLite```

Follow the steps below to set up and run QueueCTL on your local system.


### 1.1 Clone the Repository

```bash
git clone [https://github.com/](https://github.com/)<your-username>/queuectl.git
cd queuectl
```

### 1.2 Activate  Create and Activate a Virtual Environment

 macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```
 windows
```bash
python -m venv venv
venv\Scripts\activate
```
## 1.3 Install Dependencies
```bash
pip install -r requirements.txt
```
## 1.4 Initialize the Queue System
```bash
python3 queuectl.py status
```
this automatically creates,
```bash
~/.queuectl/queue.db   → Persistent job database  
~/.queuectl/logs/      → Log directory for job outputs
```
## 1.5 Run the Flask API Server
```bash
python3 server.py
```
You should see:
```bash
 * Running on http://127.0.0.1:8080
```
## 1.6 Enqueue jobs

### Using CLI
```bash
python3 queuectl.py enqueue '{"id":"job1","command":"echo Hello QueueCTL"}'
```
### Using API
```bash
curl -X POST http://127.0.0.1:8080/enqueue \
  -H "Content-Type: application/json" \
  -d '{"id":"api_job1","command":"echo Hello from API"}'
```

## 1.7 Start workers
### Using CLI
```bash
python3 queuectl.py worker start --count 2
```
### Using API
```bash
curl -X POST http://127.0.0.1:8080/workers/start \
  -H "Content-Type: application/json" \
  -d '{"count":2}'
```
## 1.8 Check Queue Status & Metrics
### Using CLI
```bash
python3 queuectl.py status
```
### Using API
```bash
curl http://127.0.0.1:8080/status
curl http://127.0.0.1:8080/metrics
```
## 1.9 View Job Logs
Each executed job stores its output in persistent logs.
### Using CLI
```bash
cat ~/.queuectl/logs/job_<job_id>.txt
```
### Using API
```bash
curl http://127.0.0.1:8080/logs/<job_id>
```
## 1.10 Stop Workers Gracefully
Stop workers safely after they finish current jobs.
```bash
python3 queuectl.py worker stop
```

## 2.1 CLI DEMO FLOW

Status before adding jobs

<img width="603" height="63" alt="Screenshot 2025-11-11 at 1 05 50 PM" src="https://github.com/user-attachments/assets/125f9bd4-9037-4000-8263-bf08f66a43b8" />

### Step 1 — Enqueue Four Jobs
```bash
python3 queuectl.py enqueue '{"id":"job1","command":"echo Job 1 executed"}'
python3 queuectl.py enqueue '{"id":"job2","command":"sleep 2"}'
python3 queuectl.py enqueue '{"id":"job3","command":"not_a_real_command"}'
python3 queuectl.py enqueue '{"id":"job4","command":"echo Final Job done"}'
```
<img width="871" height="114" alt="Screenshot 2025-11-11 at 1 06 00 PM" src="https://github.com/user-attachments/assets/8284a6e5-083e-4e64-9fc4-f6676e080e22" />

### Step 2 — Start Workers
```bash
python3 queuectl.py worker start --count 2
```
<img width="767" height="310" alt="Screenshot 2025-11-11 at 1 06 30 PM" src="https://github.com/user-attachments/assets/3f77bccf-b780-4206-8503-a4223360d4a8" />

### Step 3 — Check Queue Status
```bash
python3 queuectl.py status
```
<img width="550" height="76" alt="Screenshot 2025-11-11 at 1 06 57 PM" src="https://github.com/user-attachments/assets/c9828001-ada6-4011-a7ac-046bbe92a43c" />

### Step 4 — View Dead Letter Queue
```bash
python3 queuectl.py dlq list
```
<img width="671" height="59" alt="Screenshot 2025-11-11 at 1 07 21 PM" src="https://github.com/user-attachments/assets/5dd04b6a-89fa-4656-9bfb-6203317087c3" />

### Step 5 — Retry the Failed Job
```bash
python3 queuectl.py dlq retry job3
```
<img width="1011" height="76" alt="Screenshot 2025-11-11 at 1 07 34 PM" src="https://github.com/user-attachments/assets/0fa1c6ca-5f18-4b45-8889-3de0e108802c" />

### Step 6 — Confirm Pending Jobs
```bash
python3 queuectl.py list --state pending
```
<img width="1011" height="76" alt="Screenshot 2025-11-11 at 1 07 34 PM" src="https://github.com/user-attachments/assets/6abc7ec6-47bc-4f56-9563-3c8b918e816a" />

### Step 7 — Retry Processing
```bash
python3 queuectl.py worker start --count 1
```
<img width="704" height="185" alt="Screenshot 2025-11-11 at 1 07 54 PM" src="https://github.com/user-attachments/assets/e49f47e6-b612-403d-a632-3fb6b97d0124" />

### Step 8 — View Job Logs
```bash
cat ~/.queuectl/logs/job_job1.txt
```
<img width="681" height="139" alt="Screenshot 2025-11-11 at 1 08 13 PM" src="https://github.com/user-attachments/assets/de0d3f72-4f3a-434b-ab83-c0767a7b66ee" />

## 2.2 API Demo Flow (Flask Layer)

### Start the flask server
```bash
python3 server.py
```
Server runs on: ```http://127.0.0.1:8080 ```
<img width="885" height="155" alt="Screenshot 2025-11-11 at 1 28 34 PM" src="https://github.com/user-attachments/assets/8f042759-1397-42c7-859d-aac4196fa961" />


### Step 1 - Enqueue Jobs via API
```bash
curl -X POST http://127.0.0.1:8080/enqueue \
  -H "Content-Type: application/json" \
  -d '{"id":"job1","command":"echo Job 1 via API"}'
```
<img width="817" height="436" alt="Screenshot 2025-11-11 at 1 34 38 PM" src="https://github.com/user-attachments/assets/db8722ed-8bc0-4fcc-bef9-17f185c94dab" />

### Step 2 - Start Workers via API
```bash
curl -X POST http://127.0.0.1:8080/workers/start \
  -H "Content-Type: application/json" \
  -d '{"count":2}'
```
<img width="729" height="100" alt="Screenshot 2025-11-11 at 1 34 57 PM" src="https://github.com/user-attachments/assets/e3bdd55f-dd6e-4ab5-ae8b-06dee3d319dc" />

### Step 3 - Check Status
```bash
curl http://127.0.0.1:8080/status
```
<img width="579" height="86" alt="Screenshot 2025-11-11 at 1 35 05 PM" src="https://github.com/user-attachments/assets/8346de91-6d9a-4edd-8054-038f2e4fe638" />

### Step 4 - View DLQ
```bash
curl http://127.0.0.1:8080/dlq
```
<img width="637" height="125" alt="Screenshot 2025-11-11 at 1 44 18 PM" src="https://github.com/user-attachments/assets/42c70921-dd9b-4c0b-93e9-ea87b0ca1bb1" />

### Step 5 - Retry DLQ Job
```bash
curl -X POST http://127.0.0.1:8080/dlq/retry/job3
```
<img width="740" height="74" alt="Screenshot 2025-11-11 at 1 44 31 PM" src="https://github.com/user-attachments/assets/7e99ef91-698e-4dc5-bd70-af985876d70b" />

### Step 6 - Fetch Job Logs
```bash
curl http://127.0.0.1:8080/logs/job1
```
<img width="1172" height="70" alt="Screenshot 2025-11-11 at 1 44 49 PM" src="https://github.com/user-attachments/assets/dc816bfc-c7d8-4f30-a755-7c08c6ec45ee" />

### Step 7 - View Metrics
```bash
curl http://127.0.0.1:8080/metrics
```
<img width="650" height="130" alt="Screenshot 2025-11-11 at 1 45 03 PM" src="https://github.com/user-attachments/assets/de3a4389-e56c-4642-88f6-c068c0c8e3e9" />


In Browser:

<img width="906" height="560" alt="Screenshot 2025-11-11 at 1 45 16 PM" src="https://github.com/user-attachments/assets/3b14fd68-85e8-40af-b750-587226b9b9ab" />

## 3. Architecture Overview
It consists of four major components — Job Queue, Worker Pool, CLI, and Flask API Layer — working together with persistent state management through SQLite.

### 3.1 Job Lifecycle

<img width="415" height="88" alt="Screenshot 2025-11-11 at 2 00 03 PM" src="https://github.com/user-attachments/assets/e7023f29-6ca2-41f9-805b-e6beb5c22d3c" />

### 3.2 Data Persistence (SQLite)
```bash
~/.queuectl/queue.db
```
<img width="505" height="192" alt="Screenshot 2025-11-11 at 2 01 55 PM" src="https://github.com/user-attachments/assets/591e0092-315b-4c1d-93e1-0cd3b3967d5c" />

Persistence Features:

	•	Survives restarts automatically
  
	•	SQLite ensures ACID transactions
  
	•	Workers use BEGIN IMMEDIATE locks to prevent duplicate claims
  
	•	Automatically reinitializes missing schema on startup

### 3.3 Worker Logic
Workers are isolated Python processes launched via multiprocessing.
Each worker:
	1.	Claims a single pending job atomically.
	2.	Executes its command via subprocess.run() with a 10s timeout.
	3.	Records success or failure based on exit code.
	4.	Retries failed jobs with exponential backoff (delay = base ^ attempts).
	5.	Moves permanently failed jobs to Dead Letter Queue (DLQ).
	6.	Writes execution logs to:

  ```bash
  ~/.queuectl/logs/job_<id>.txt
  ```
### 3.4 CLI Interface (Click)
The CLI (queuectl.py) provides complete control over the system:

<img width="705" height="341" alt="Screenshot 2025-11-11 at 2 04 02 PM" src="https://github.com/user-attachments/assets/50e52541-699f-43ba-9709-0ee9ea06123c" />

### 3.5 Flask REST API Layer
Provides web-based control and observability over the system.

<img width="738" height="370" alt="Screenshot 2025-11-11 at 2 04 41 PM" src="https://github.com/user-attachments/assets/e975983f-c1f5-4480-b65a-67e2b8f31f8e" />

Additional Features:
	•	/metrics returns real-time stats for monitoring.
	•	/logs/<id> exposes per-job execution logs.
	•	Ready for integration with dashboards or Prometheus.

### 3.6 High-Level Architecture Diagram

<img width="389" height="428" alt="Screenshot 2025-11-11 at 2 05 36 PM" src="https://github.com/user-attachments/assets/49add1ab-0594-4d23-baae-c7ce32ee4e83" />

This architecture provides:
	•	Reliability → Persistent + restart-safe queue
	•	Concurrency → Multi-process worker pool
	•	Resilience → Auto retry and DLQ handling
	•	Observability → Metrics, logging, and API access


## 4. Assumptions & Trade-offs
To keep QueueCTL lightweight, reliable, and testable within a local environment, several deliberate design decisions were made.

### 4.1 Core Assumptions
	1.	Local-first Persistence
  	•	SQLite is used as the job store.
	  •	It provides full ACID compliance and persistence across restarts without needing external dependencies like Redis or PostgreSQL.
	2.	Atomic Job Claiming
	  •	Workers claim jobs atomically using SQLite transactions (BEGIN IMMEDIATE) to prevent double-processing.
  	•	Assumes a single machine setup for concurrency, not distributed workers across servers.
	3.	Exponential Backoff Strategy
	  •	Retry delay is computed as base ^ attempts.
	  •	This design prevents retry storms and mimics production-grade retry policies (like AWS SQS).
	4.	Shell Command Execution
	  •	Jobs execute using subprocess.run() with shell=True.
	  •	Simple, language-agnostic execution pattern that works for any shell-compatible command.
	5.	Timeout Handling
	  •	Each job has a default timeout of 10 seconds to prevent blocking workers indefinitely.
	  •	Timeout failures are retried based on backoff configuration.
	6.	Persistent Logging
	  •	Logs are stored per job at ~/.queuectl/logs/.
	  •	Each log contains command, timestamp, stdout, stderr, and exit code — ensuring full traceability.

### 4.2 Trade-offs & Design Choices
  
<img width="971" height="366" alt="Screenshot 2025-11-11 at 2 11 12 PM" src="https://github.com/user-attachments/assets/2ea1170d-0169-4068-a2b7-c0fdcac902ef" />


## 5. Testing Instructions

### 5.1 Quick functional test
```bash
python3 queuectl.py enqueue '{"id":"job1","command":"echo Hello QueueCTL"}'
python3 queuectl.py worker start --count 1
python3 queuectl.py status
  ```
Expected Output:
```bash
[INFO] [job1] processing -> `echo Hello QueueCTL`
[INFO] [job1] completed ✔
```
```bash
state        | count
--------------+-------
completed    | 1
stop_flag    | 0
```

### 5.2  Retry and DLQ Test
Run a failing job:
```bash
python3 queuectl.py enqueue '{"id":"job_fail","command":"not_a_real_command"}'
python3 queuectl.py worker start --count 1
```
Expected Output:
```bash
[WARN] [job_fail] moved to DLQ (command not found)
```
Check DLQ:
```bash
python3 queuectl.py dlq list
```
Retry it:
```bash
python3 queuectl.py dlq retry job_fail
```

### 5.3 Persistence test

	1.	Enqueue 3 jobs.
	2.	Stop workers (Ctrl + C).
	3.	Restart queue:

```bash
python3 queuectl.py status
```

### 5.4 Logging Test
After processing jobs:
```bash
ls ~/.queuectl/logs/
cat ~/.queuectl/logs/job_job1.txt
```
Each job produces a log file containing:
```bash
Command executed
Exit Code
STDOUT
STDERR
Timestamp
```

### 5.5 API Endpoint Test
Run Flask server:
```bash
python3 server.py
```
Then verify endpoints:
```bash
curl http://127.0.0.1:8080/status
curl http://127.0.0.1:8080/metrics
curl http://127.0.0.1:8080/dlq
curl http://127.0.0.1:8080/logs/job1
```
Confirms API control, observability, and monitoring

### 5.6 Full System Demo Script
```bash
chmod +x demo_test.sh
./demo_test.sh
```
This automated script validates:
	•	Enqueueing and execution
	•	Retry and backoff
	•	DLQ transfer and retry
	•	Persistent job recovery
	•	Worker concurrency
	•	Log and metric generation

<img width="802" height="309" alt="Screenshot 2025-11-11 at 2 22 38 PM" src="https://github.com/user-attachments/assets/3eafece6-a800-480f-9525-03e54c60cd95" />









