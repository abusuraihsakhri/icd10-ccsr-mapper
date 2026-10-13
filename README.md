# ICD-10-CM to CCSR Mapper

Exact lookup of ICD-10-CM diagnosis codes in a user-supplied **AHRQ Clinical Classifications Software Refined (CCSR)** diagnosis mapping release. The application preserves all category assignments and the inpatient and outpatient default CCSR values when present.

**Mapping data is not bundled.** Download the diagnosis-tool ZIP from [AHRQ HCUP](https://hcup-us.ahrq.gov/toolssoftware/ccsr/dxccsr.jsp) and extract its `DXCCSR_vYYYY-R.csv` file. Select a release appropriate for the coding period. Do not use an ICD-10-PCS procedure crosswalk.

## Browser application

Open `web/index.html` in a modern browser, select the extracted AHRQ CSV, and enter one or more ICD-10-CM diagnosis codes. The app performs exact matching, displays all associated CCSR categories and defaults, and exports the complete result set to CSV.

All browser mapping data stays on the user's device. No API requests, accounts, or external script dependencies are required for processing. Unknown or invalid codes are identified, not guessed. Large result sets show a preview of the first 200 rows; the downloadable CSV contains the full batch (up to 5,000 submitted codes).

## Python command line

Requires Python 3.10 or later. The mapping engine itself uses only the standard library.

```bash
python ccsr_mapper.py single E11.9 --mapping /path/to/DXCCSR_vYYYY-R.csv
python ccsr_mapper.py batch --mapping /path/to/DXCCSR_vYYYY-R.csv \
  --input diagnoses.csv --output mapped.csv --column code
```

Example input `diagnoses.csv`:

```csv
code
E11.9
I10
Z99.99
```

Batch output appends `ccsr_found`, semicolon-separated `ccsr_categories`, `ccsr_inpatient_default`, `ccsr_outpatient_default`, and `ccsr_error`. Original input columns are retained. For datasets with multiple diagnoses per encounter, map each diagnosis separately; choose inpatient/outpatient defaults according to the AHRQ methodology rather than assuming that the first category is the default.

## Optional API and existing audit utilities

Install dependencies and launch the development API:

```bash
python -m pip install -r requirements.txt
export AUDIT_SECRET_KEY="replace-with-a-strong-random-secret"
export CCSR_MAPPING_CSV="/absolute/path/to/DXCCSR_vYYYY-R.csv"
python cli.py serve
```

`GET /api/ccsr/E11.9` serves exact mapping from the configured file; without `CCSR_MAPPING_CSV`, it returns HTTP 503. `GET /health` returns API health. Existing `cli.py audit`, `cli.py batch`, `cli.py chat`, `POST /api/audit`, and audit-log endpoints remain as **separate, generic demonstration utilities**, not CCSR coding/clinical scoring functions. The mock chat response is not a clinical interpretation. These endpoints do not implement user authentication; do not expose the development server or audit logs to untrusted networks.

The container configuration uses `requirements.txt`, runs under a non-root user, and binds Docker Compose's published port to localhost. To use CCSR lookup in Docker, mount the mapping file into the container and set `CCSR_MAPPING_CSV` to its *container* path.

## Validation and security

```bash
python -m pytest -q
python -m compileall -q ccsr_mapper.py cli.py agents tests
```

GitHub Actions runs Python tests on 3.10–3.12 and checks browser-script syntax. The application does not infer assignments without the official mapping file. Exported CSV values are protected against spreadsheet-formula interpretation.

The legacy audit subsystem maintains an HMAC-SHA256 chained log **in memory** and can detect modifications to signed entries. Its identifier-pattern guard is heuristic, not validated de-identification or HIPAA compliance. Neither the in-memory log nor the local browser supports regulated patient-data storage. Use de-identified research input only.

## Technology and compatibility

Python standard library for the mapper; FastAPI, Pydantic and Uvicorn for the optional server; HTML, CSS and vanilla JavaScript for the local browser. Requires a modern browser with File API, Blob, and JavaScript enabled (current Chromium, Firefox, Safari). The browser version does not require Pyodide or a Python server. This project is licensed under [MIT](LICENSE).

**Data source:** AHRQ, [Clinical Classifications Software Refined for ICD-10-CM Diagnoses](https://hcup-us.ahrq.gov/toolssoftware/ccsr/dxccsr.jsp). The available release and exact mappings may change; verify applicability to the study period.
