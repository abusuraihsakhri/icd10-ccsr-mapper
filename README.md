# ICD-10 to CCSR Mapper

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Standards:** CAP / CLSI / ISO

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)

---

## What It Does

Maps ICD-10 diagnosis codes to AHRQ CCSR v2023 categories for comorbidity grouping and HCUP analysis.

- **Single lookup**: Token overlap + substring scoring with a built-in demo dictionary
- **Batch CSV processing**: Process multiple ICD-10 codes from a CSV file
- **Multi-worker analysis**: Three specialized workers (QC, Safety, Protocol) evaluate tasks
- **FastAPI REST API**: OpenAPI 3.1 endpoints with Prometheus metrics

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Usage

### Single Lookup (stdlib mapper)
```bash
python cli.py single "I10 Hypertension"
python ccsr_mapper.py single "Hypertension"
```

### Batch CSV Processing
```bash
python cli.py batch -i sample.csv -o results.csv
python ccsr_mapper.py batch --input sample.csv --output results.csv
```

### Audit (multi-worker supervisor)
```bash
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2
python cli.py chat "Explain the analysis"
python cli.py verify-audit
```

### REST API Server
```bash
python cli.py serve --host 127.0.0.1 --port 8000
# Or with Docker:
docker-compose up
```

### API Endpoints
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `POST /api/audit` - Dispatch task for multi-worker evaluation
- `POST /api/chat` - Supervisory chat query
- `GET /api/audit/logs` - Retrieve HMAC audit trail

---

## Security Features

- **PHI Outbound Guard**: Blocks SSNs, MRNs, phone numbers, emails, and patient identifiers from audit logs
- **HMAC-SHA256 Audit Trail**: Cryptographically chained, tamper-evident logs
- **Path Traversal Protection**: CLI validates input/output paths to prevent directory traversal attacks
- **Input Validation**: Strict type checking and file extension validation for batch operations

---

## Configuration

Set the audit secret key (required for production):

```bash
export AUDIT_SECRET_KEY="your-secure-random-key"
```

Without this, the system uses an ephemeral random key (audit integrity not preserved across restarts).

---

## Testing

```bash
pytest -v
```

Run simulation benchmark:

```bash
python simulator.py 1000
```

---

## Project Structure

```
icd10-ccsr-mapper/
├── agents/              # Multi-worker analysis agents
│   ├── base.py          # PHI guard, HMAC audit trail, security
│   ├── supervisor.py    # Task orchestration
│   ├── workers.py       # QC, Safety, Protocol workers
│   ├── api.py           # FastAPI REST endpoints
│   └── models.py        # Pydantic schemas
├── tests/               # Pytest test suite
├── cli.py               # Main CLI entry point
├── ccsr_mapper.py       # Stdlib ICD-10/CCSR mapper
├── enrichment.py        # Analytics engines
├── simulator.py         # Load/stress testing
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container image
├── docker-compose.yml   # Service orchestration
└── web/                 # Operations console (HTML)
```
