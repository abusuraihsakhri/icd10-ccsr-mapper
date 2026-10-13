#!/usr/bin/env python3
"""Deterministic ICD-10-CM diagnosis to AHRQ CCSR lookup from a supplied mapping CSV.

No category assignments are inferred. The caller must supply the official AHRQ
DXCCSR_vYYYY-R.csv for the data's coding period.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

CODE_PATTERN = re.compile(r"^[A-TV-Z][0-9][A-Z0-9]{1,5}$", re.ASCII)
CATEGORY_PATTERN = re.compile(r"^CCSR CATEGORY ([0-9]+)$")


def normalize_code(value):
    """Normalize an ICD-10-CM code without guessing missing characters."""
    return re.sub(r"[.\s]", "", str(value or "")).upper()


def normalize_header(value):
    return re.sub(r"\s+", " ", re.sub(r"[_\-]+", " ", str(value or "").strip().upper()))


class CCSRMapper:
    """Exact-match lookup, retaining all CCSR assignments and both defaults."""

    def __init__(self, records):
        self.records = records

    @classmethod
    def from_csv(cls, path):
        records = {}
        with open(path, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError("Mapping CSV has no header")
            header = {normalize_header(name): name for name in reader.fieldnames if name}
            code_field = next((header[k] for k in ("ICD 10 CM CODE", "ICD10CM CODE", "ICD 10 CM", "ICD 10 CODE")
                               if k in header), None)
            if not code_field:
                raise ValueError("Mapping file lacks an ICD-10-CM CODE column; supply an AHRQ DXCCSR CSV")
            category_fields = sorted(
                ((int(match.group(1)), original) for key, original in header.items()
                 if (match := CATEGORY_PATTERN.fullmatch(key))),
                key=lambda entry: entry[0]
            )
            if not category_fields:
                raise ValueError("Mapping file lacks CCSR CATEGORY 1/2/... columns")
            def field(name):
                return header.get(name)
            description_field = field("ICD 10 CM CODE DESCRIPTION")
            inpatient_field = field("INPATIENT DEFAULT CCSR")
            outpatient_field = field("OUTPATIENT DEFAULT CCSR")
            for line, row in enumerate(reader, start=2):
                raw = (row.get(code_field) or "").strip()
                if not raw:
                    continue
                code = normalize_code(raw)
                if not CODE_PATTERN.fullmatch(code):
                    raise ValueError(f"Invalid ICD-10-CM code at mapping line {line}: {raw!r}")
                categories = []
                for index, category_field in category_fields:
                    category = (row.get(category_field) or "").strip().upper()
                    if category:
                        description_column = field(f"CCSR CATEGORY {index} DESCRIPTION")
                        categories.append({
                            "code": category,
                            "description": (row.get(description_column) or "").strip() if description_column else ""
                        })
                if not categories:
                    raise ValueError(f"No CCSR category at mapping line {line} for {code}")
                if code in records:
                    raise ValueError(f"Duplicate ICD-10-CM code in mapping: {code}")
                records[code] = {
                    "code": code,
                    "description": (row.get(description_field) or "").strip() if description_field else "",
                    "categories": categories,
                    "inpatient_default": (row.get(inpatient_field) or "").strip().upper() if inpatient_field else "",
                    "outpatient_default": (row.get(outpatient_field) or "").strip().upper() if outpatient_field else ""
                }
        if not records:
            raise ValueError("Mapping CSV contains no ICD-10-CM mappings")
        return cls(records)

    def lookup(self, query):
        code = normalize_code(query)
        if not CODE_PATTERN.fullmatch(code):
            return {"query": query, "code": code, "found": False, "error": "Invalid ICD-10-CM diagnosis code"}
        record = self.records.get(code)
        if record is None:
            return {"query": query, "code": code, "found": False, "error": "Code not found in selected mapping release"}
        return {"query": query, "found": True, **record}


def lookup(query, mapper):
    return mapper.lookup(query)


def safe_csv_cell(value):
    """Prevent spreadsheet formula interpretation in exported CSV."""
    value = str(value if value is not None else "")
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def process_csv(inp, out, mapper, column=None):
    if Path(inp).resolve() == Path(out).resolve():
        raise ValueError("Input and output CSV paths must differ")
    with open(inp, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        if not fields:
            raise ValueError("Input CSV has no header")
        if len(fields) != len(set(fields)):
            raise ValueError("Input CSV contains duplicate columns")
        candidates = ("icd10", "icd10cm", "icd_10_cm", "icd10_code", "diagnosis_code", "code", "query")
        if column:
            if column not in fields:
                raise ValueError(f"Column {column!r} does not exist")
            code_field = column
        else:
            code_field = next((c for candidate in candidates for c in fields
                               if normalize_header(c).replace(" ", "") == normalize_header(candidate).replace(" ", "")), None)
            if code_field is None:
                raise ValueError("Specify --column for the ICD-10-CM code column")
        outputs = ["ccsr_found", "ccsr_categories", "ccsr_inpatient_default",
                   "ccsr_outpatient_default", "ccsr_error"]
        if any(field in fields for field in outputs):
            raise ValueError("Input CSV already contains one of the output column names")
        results = []
        for row in reader:
            if None in row:
                raise ValueError("Input CSV row has more cells than its header")
            result = mapper.lookup(row.get(code_field, ""))
            merged = dict(row)
            merged.update({
                "ccsr_found": str(result["found"]).lower(),
                "ccsr_categories": ";".join(cat["code"] for cat in result.get("categories", [])),
                "ccsr_inpatient_default": result.get("inpatient_default", ""),
                "ccsr_outpatient_default": result.get("outpatient_default", ""),
                "ccsr_error": result.get("error", "")
            })
            results.append(merged)
    with open(out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields + outputs)
        writer.writeheader()
        for row in results:
            writer.writerow({key: safe_csv_cell(value) for key, value in row.items()})
    return results


def build_parser():
    parser = argparse.ArgumentParser(description="Exact ICD-10-CM to AHRQ CCSR lookup")
    subs = parser.add_subparsers(dest="command", required=True)
    single = subs.add_parser("single", help="Look up one ICD-10-CM code")
    single.add_argument("code")
    single.add_argument("--mapping", required=True, help="Official AHRQ DXCCSR mapping CSV")
    batch = subs.add_parser("batch", help="Append CCSR categories to a CSV")
    batch.add_argument("--mapping", required=True)
    batch.add_argument("--input", required=True)
    batch.add_argument("--output", required=True)
    batch.add_argument("--column", help="ICD-10-CM code column in input CSV")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        mapper = CCSRMapper.from_csv(args.mapping)
        if args.command == "single":
            print(json.dumps(mapper.lookup(args.code), indent=2))
        else:
            results = process_csv(args.input, args.output, mapper, args.column)
            print(f"Processed {len(results)} rows -> {args.output}")
        return 0
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
