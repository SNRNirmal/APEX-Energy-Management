# Deployment & Developer Setup Guide

This guide details the steps to set up, build, test, and run the APEX EMS and SCADA platform in developer and production environments.

---

## 1. Prerequisites

### Windows System
Ensure the following packages are installed:
* **Node.js**: v18.0.0 or higher (verify with `node --version`).
* **Python**: v3.10 or higher (verify with `py --version`).
* **pip**: Python package manager (verify with `py -m pip --version`).

---

## 2. Backend Installation & Run

1. Open a terminal (PowerShell or Command Prompt) and navigate to the project directory:
   ```bash
   cd e:/scada/backend
   ```

2. Install Python dependencies:
   ```bash
   py -m pip install -r requirements.txt
   ```
   *Note: If PostgreSQL, InfluxDB, or MongoDB bindings fail due to lack of local servers, standard warnings can be safely ignored. The project utilizes a local SQLite/JSON adapter that manages databases automatically out-of-the-box.*

3. Start the FastAPI server:
   ```bash
   py main.py
   ```
   The backend starts on:
   * **REST APIs**: `http://localhost:8000/api`
   * **WebSockets**: `ws://localhost:8000/ws`
   * **Swagger API Docs**: `http://localhost:8000/docs`

---

## 3. Frontend Installation & Run

1. Open a separate terminal window and navigate to the frontend directory:
   ```bash
   cd e:/scada/frontend
   ```

2. Install npm packages:
   ```bash
   npm install
   ```

3. Run the React application in developer mode:
   ```bash
   npm run dev
   ```
   Open your browser to:
   * **Local Server URL**: `http://localhost:5173/`

4. Compile production package (Optional):
   To build static production files, run:
   ```bash
   npm run build
   ```
   The production bundle is created in `frontend/dist/` and can be served using static hosts (Nginx, Apache, etc.).

---

## 4. Production Database Configuration

In production, change the storage layer from local SQLite to real PostgreSQL, InfluxDB, and MongoDB databases by setting standard environment variables:

```bash
# Relational DB Config (EMS configurations & scheduler settings)
export POSTGRES_URI="postgresql://username:password@localhost:5432/apex_ems"

# Document Store Config (Sensor telemetry logs & alerts historian)
export MONGO_URI="mongodb://username:password@localhost:27017/apex_logs"

# Time-Series DB Config (SCADA tag historian)
export INFLUXDB_URI="http://localhost:8086"
export INFLUXDB_TOKEN="your-influx-authentication-token"
export INFLUXDB_ORG="your-org"
export INFLUXDB_BUCKET="scada-telemetry"
```

Once environment variables are detected by the backend, the `database.py` adapter automatically redirects writes from SQLite to respective production databases.

---

## 5. Verification & Tests

To execute unit tests verifying the physical models, state machines, and protocol mappings:

1. Navigate to the backend directory:
   ```bash
   cd e:/scada/backend
   ```

2. Run tests using Python's standard unittest runner:
   ```bash
   py -m unittest test_backend.py
   ```
   Verify that all test cases pass successfully.
