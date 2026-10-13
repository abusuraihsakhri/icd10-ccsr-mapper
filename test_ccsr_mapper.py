"""Regression tests for exact CSV-backed ICD-10-CM -> CCSR matching.

Category codes here are synthetic fixtures, not asserted clinical assignments.
"""
import csv
import json

import pytest

from ccsr_mapper import CCSRMapper, main, process_csv, safe_csv_cell
from agents.base import AuditTrail


@pytest.fixture
def mapping_csv(tmp_path):
    path = tmp_path / "DXCCSR_test.csv"
    path.write_text(
        "ICD-10-CM CODE,ICD-10-CM CODE DESCRIPTION,CCSR CATEGORY 1,"
        "CCSR CATEGORY 1 DESCRIPTION,CCSR CATEGORY 2,CCSR CATEGORY 2 DESCRIPTION,"
        "INPATIENT DEFAULT CCSR,OUTPATIENT DEFAULT CCSR\n"
        "A00.0,\"Example, comma\",TST001,First,TST002,Second,TST001,TST002\n"
        "B20,Example 2,TST003,Third,,,TST003,TST003\n",
        encoding="utf-8-sig"
    )
    return path


def test_exact_match_multiple_categories_and_defaults(mapping_csv):
    mapper = CCSRMapper.from_csv(mapping_csv)
    result = mapper.lookup(" a00.0 ")
    assert result["code"] == "A000"
    assert [x["code"] for x in result["categories"]] == ["TST001", "TST002"]
    assert result["description"] == "Example, comma"
    assert result["inpatient_default"] == "TST001"
    assert result["outpatient_default"] == "TST002"
    assert mapper.lookup("A00")["found"] is False
    assert mapper.lookup("creatinine")["found"] is False
    assert mapper.lookup("Z99.99")["found"] is False


def test_batch_and_csv_injection(mapping_csv, tmp_path):
    inp = tmp_path / "input.csv"
    out = tmp_path / "output.csv"
    inp.write_text('code,note\nA00.0,=HYPERLINK("bad")\nB20,normal\nNOPE,invalid\n')
    # The first note line is deliberately not a valid CSV quoting sequence for
    # a quoted expression, but remains a valid two-field CSV record.
    mapper = CCSRMapper.from_csv(mapping_csv)
    rows = process_csv(inp, out, mapper)
    assert len(rows) == 3
    assert rows[0]["ccsr_categories"] == "TST001;TST002"
    assert rows[1]["ccsr_found"] == "true"
    assert rows[2]["ccsr_found"] == "false"
    with out.open(newline="") as handle:
        saved = list(csv.DictReader(handle))
    assert saved[0]["note"].startswith("'=")
    assert saved[0]["ccsr_outpatient_default"] == "TST002"
    assert safe_csv_cell(" @cmd") == "' @cmd"


def test_refuse_overwrite_and_bad_mapping(mapping_csv, tmp_path):
    mapper = CCSRMapper.from_csv(mapping_csv)
    path = tmp_path / "in.csv"
    path.write_text("code\nB20\n")
    with pytest.raises(ValueError, match="differ"):
        process_csv(path, path, mapper)
    bad = tmp_path / "bad.csv"
    bad.write_text("code,category\nB20,X\n")
    with pytest.raises(ValueError, match="lacks"):
        CCSRMapper.from_csv(bad)
    duplicate = tmp_path / "duplicate.csv"
    duplicate.write_text("ICD-10-CM CODE,CCSR CATEGORY 1\nB20,X\nb20,Y\n")
    with pytest.raises(ValueError, match="Duplicate"):
        CCSRMapper.from_csv(duplicate)


def test_cli(mapping_csv, tmp_path, capsys):
    assert main(["single", "B20", "--mapping", str(mapping_csv)]) == 0
    assert json.loads(capsys.readouterr().out)["found"] is True
    assert main(["single", "B20", "--mapping", str(tmp_path / "missing.csv")]) == 2


def test_audit_signature_tampering_detection():
    trail = AuditTrail(secret_key="fixture-secret-not-production")
    trail.log("tester", "test", "event", {"status": "OK"})
    assert trail.verify_integrity()
    external = trail.get_trail()
    external[0]["actor"] = "attacker"
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "attacker"
    assert not trail.verify_integrity()
