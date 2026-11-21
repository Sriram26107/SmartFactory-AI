# SmartFactory AI

**AI-Powered Smart Manufacturing & Industrial Intelligence Platform**

A local-first, source-aware industrial analytics application with **12 integrated dashboard modules**. It has two explicit data modes:

- **Simulation:** reproducible generated manufacturing datasets plus optional continuously generated sensor readings.
- **Connected:** real MQTT telemetry and authorized CSV exports from MES, ERP, quality, energy and PLM systems. Missing data is shown as **Disconnected**, never silently replaced by simulated records.

## Features

1. Overview — unified source health, production KPIs, machine trends
2. MES & production — orders, priority scheduling, production summaries
3. Maintenance — current temperature/vibration conditions and service records
4. Quality & digital thread — inspection records, serial → work order → BOM → requirements
5. Supply chain — inventory reorder recommendations and delivery priorities
6. Energy & microgrid — energy totals and renewable shares from imported energy readings
7. Digital twin — manually configured what-if production simulator
8. Engineering & PLM — BOM and requirements records
9. AI assistant — rule-based answers from the selected data mode and local document retrieval
10. ML & CV Lab — synthetic ML experiment, user-trained image feature classifier, integer optimization, energy forecast
11. IoT & Database — CSV data connector, source health and persistent event log
12. Live monitoring — auto-refreshing temperature/vibration charts, live-source Connected mode and stale-data indication

**Scope:** This is a working local integration and analytics application, not an enterprise MES/PLM replacement or validated industrial control system. It does not issue PLC commands. No OPC UA/Modbus adapter, live camera stream, production LLM, or site-validated failure predictor is included. A real factory needs authorization, industrial network design, secure credentials, field mapping and equipment-specific validation.

## Run on Windows (normal CMD)

Unzip the project and open CMD in the folder that **contains `app.py`**:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

Open `http://localhost:8501`.

### Simulation mode

In another CMD window in the same project folder:

```bat
.venv\Scripts\activate
python -m smartfactory.live.simulator --interval 2
```

Select **Simulation** in the sidebar. The live tab displays simulated readings. Press Ctrl+C to stop the simulator.

### Connected mode — actual MQTT device/gateway

1. Obtain authorization from the factory and its automation/network team. Use **read-only** integration and a properly secured local broker (e.g. Mosquitto). Do not expose an anonymous broker to the Internet or a production network.
2. Configure a machine/gateway to publish JSON on topic `factory/machines/M-001/telemetry`:

```json
{"machine_id":"M-001","temperature_c":65.2,"vibration_mm_s":2.1,"pressure_bar":5.8,"energy_kw":8.4}
```

3. Start the receiver in another CMD window:

```bat
.venv\Scripts\activate
python -m smartfactory.live.receiver --host 127.0.0.1 --port 1883
```

If your broker uses authentication and TLS, configure `MQTT_USERNAME` and `MQTT_PASSWORD` environment variables and use `--username YOUR_USER --tls --port 8883 --ca-file path\to\ca.crt`. Use the broker host/IP address reachable from your computer, not necessarily 127.0.0.1. Never put passwords in Git.

4. Switch the dashboard sidebar to **Connected**. It uses only readings received through MQTT. A reading older than 60 seconds is marked **Stale**. The simulator's direct-to-SQLite messages are excluded from Connected mode.

### Connected mode — MES / ERP / quality / energy / PLM records

The IoT & Database tab includes a CSV import form for each dataset. Required headers are displayed in the app; example CSV files are provided in `examples/`. Import replaces the selected dataset atomically. All tabs share the imported data. Missing sources remain disconnected. **CSV import is a batch connector**, not continuous ERP/PLM synchronization. For continuous enterprise integration, implement approved APIs or read-only database connectors and feed the same validated data layer.

**Energy note:** MQTT `energy_kw` represents power, not accumulated energy. The Energy tab uses `consumption_kwh` imported from meter/EMS records. The app does not incorrectly convert instantaneous power to energy.

## Architecture

```text
Sensors / gateway -> MQTT broker -> read-only receiver -> telemetry SQLite
MES / ERP / PLM / quality / energy CSV -> validation -> integrated SQLite
                                      |                  |
                                      +-- source-aware data layer
                                                    |
                                           12 Streamlit modules
```

## Tests

```bat
python -m pytest -q
```

## Data safety and limitations

- Synthetic ML model metrics do not establish real-world failure prediction accuracy. In Connected mode, synthetic-model predictions are deliberately disabled.
- Condition thresholds are illustrative and must be approved and validated for each machine.
- Image defect classification requires user-provided labeled images and evaluation on a separate test set.
- Digital twin is a scenario calculator, not a physics-calibrated machine twin.
- No production equipment should be controlled from this application.
- MQTT receiver supports optional TLS and authentication. Configure network segmentation, least privilege and monitoring before real factory use.
- Database files, uploaded records and credentials should not be committed to Git.

## GitHub

```bat
git init
git add .
git commit -m "Build SmartFactory AI integrated manufacturing intelligence platform"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/SmartFactory-AI.git
git push -u origin main
```

## Integrated operational workflows (new)

The 12 modules now share a persistent **operations workflow** database (`smartfactory_workflows.db`):

- Every MQTT reading is validated and saved; abnormal temperature or vibration opens an incident and a linked maintenance task.
- Repeated abnormal readings update the same open incident instead of generating duplicate work orders. Severity may escalate from Watch to High.
- A normal reading does **not** automatically close an incident. A technician must supply a resolution note in the Maintenance tab.
- Overview and IoT & Database display the open-incident count and machines requiring review. These are **potential** production impacts, not measured downtime.
- MES & production accepts manually observed production events (planned minutes, actual running minutes, ideal cycle seconds, total units, good units), validates their consistency, stores them persistently, and computes Availability × Performance × Quality (OEE). Missing data is shown as unavailable.
- The direct SQLite simulator also exercises the incident workflow, allowing an end-to-end test without a broker. In Connected mode, only MQTT-tagged telemetry is treated as real machine readings.

**Important:** The default simulator normally produces healthy values. To verify an alert locally without hardware, run the following from the project root (in normal CMD):

```bat
python -c "from smartfactory.workflows import process_telemetry; print(process_telemetry({'machine_id':'M-001','temperature_c':91,'vibration_mm_s':8},source='simulator'))"
```

Then refresh Overview and Maintenance. Resolve the incident with a technician note in the Maintenance tab. For real MQTT, the receiver calls the same workflow automatically. The temperature/vibration thresholds are examples and must be configured and validated for each machine before use.

### OEE example

Record a production event with planned=60 minutes, runtime=50 minutes, ideal cycle=30 seconds, total=80 units, good=76 units. The dashboard calculates availability=83.33%, performance=80%, quality=95%, and OEE=63.33%. These are measurements **entered by the operator**, not automatically inferred from machine telemetry.

### What still needs actual factory integration

The software implements data ingestion, source-aware views, persistence, alerts, technician resolution, measured OEE, basic ML/CV experiments, and planning tools. It **does not** contain equipment-specific OPC UA/Modbus adapters, automatic PLC cycle counting, live camera drivers, validated failure prediction on actual equipment, proprietary MES/ERP/PLM APIs, industrial-grade cybersecurity, or a physics-calibrated digital twin. Those require equipment specifications, access to the relevant systems, real datasets, and site validation. No control commands are issued.


## Additional industrial data connectors

The application now includes optional **read-only OPC UA and Modbus TCP polling adapters** and an **authenticated local HTTP ingestion API**. Connected mode accepts telemetry from `mqtt`, `api`, `opcua`, and `modbus` sources. All adapters use the same telemetry database and maintenance incident workflow.

### Local HTTP API for factory gateway integration

From normal Windows CMD, set a long secret (replace the example with a unique random value) and start the API:

```bat
set SMARTFACTORY_API_TOKEN=REPLACE_WITH_A_LONG_RANDOM_SECRET_32_CHARS
python -m smartfactory.connectors.api --host 127.0.0.1 --port 8765
```

In another CMD window, send a test reading:

```bat
curl -X POST http://127.0.0.1:8765/api/v1/telemetry -H "Authorization: Bearer REPLACE_WITH_A_LONG_RANDOM_SECRET_32_CHARS" -H "Content-Type: application/json" -d "{\"machine_id\":\"M-001\",\"temperature_c\":88,\"vibration_mm_s\":7.2}"
```

For actual MES/ERP exports, upload validated CSV to `POST /api/v1/datasets/orders` (or any dataset named in `smartfactory/integration.py`) with `Content-Type: text/csv` and the same bearer token. The API is bound to localhost by default. **Do not expose this HTTP endpoint to an untrusted network**; use an authenticated TLS reverse proxy and network restrictions for remote integration.

### OPC UA (optional)

```bat
python -m pip install asyncua
python -m smartfactory.connectors.opcua --endpoint opc.tcp://127.0.0.1:4840 --machine-id M-001 --temp-node "ns=2;s=Machine.Temperature" --vibration-node "ns=2;s=Machine.Vibration"
```

The endpoint and node IDs above are **examples**. Obtain actual values and read-only access credentials from the factory's automation engineer. Configure OPC UA certificates and authentication appropriate to the site before connecting to equipment.

### Modbus TCP (optional)

```bat
python -m pip install pymodbus
python -m smartfactory.connectors.modbus --host 127.0.0.1 --machine-id M-001 --temp-register 100 --vibration-register 101 --temp-scale 0.1 --vibration-scale 0.01
```

Register addresses and scaling above are **examples**, not valid for arbitrary machines. The adapter reads holding registers only. Never poll a live machine without authorization and the manufacturer's register map. Modbus TCP has no built-in encryption; isolate it on an approved industrial network.

### Scope and validation

All software integrations can be tested locally. Real machine, camera, PLM, ERP and MES connectivity requires access to the specific equipment or enterprise system. ML and digital-twin results remain unvalidated until trained/calibrated against representative factory data. No software-only package can substitute for site acceptance testing or industrial safety review.
