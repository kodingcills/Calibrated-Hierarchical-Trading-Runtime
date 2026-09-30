#!/usr/bin/env python3
"""V1 integrity chain check for the W3 basis artefacts.

Verifies that every raw-byte hash the producer recorded actually matches the bytes
on disk: HL API pages (raw + canonical sorted-key sha256) and every Binance archive
zip.  A missing/mismatched raw hash is a finding, not a formatting issue.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "M2" / "data" / "raw" / "basis"
ADM = json.loads((ROOT / "M2" / "data" / "derived_basis" / "admission.json").read_text())


def main() -> int:
    res: dict = {}
    res["request_summary"] = ADM.get("request_summary")

    # 1. HL API pages: raw + canonical sha256 recorded in admission.json
    hl_ok = hl_bad = hl_missing = 0
    bad = []
    for entry in ADM.get("hl_api_payloads", []):
        name = entry.get("name")
        p = RAW / name
        if not p.exists():
            hl_missing += 1
            bad.append({"name": name, "issue": "raw file absent"})
            continue
        blob = p.read_bytes()
        raw_h = hashlib.sha256(blob).hexdigest()
        canon_h = hashlib.sha256(
            json.dumps(json.loads(blob), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        ok_raw = raw_h == entry.get("sha256")
        ok_canon = canon_h == entry.get("canonical_sha256")
        if ok_raw and ok_canon:
            hl_ok += 1
        else:
            hl_bad += 1
            bad.append({"name": name, "raw_ok": ok_raw, "canon_ok": ok_canon})
    res["hl_pages"] = {"checked": len(ADM.get("hl_api_payloads", [])), "ok": hl_ok,
                       "mismatch": hl_bad, "missing_raw": hl_missing, "bad": bad[:10]}

    # 2. Binance zips: sha256 recorded in binance_file_validation + artifact_hashes
    rec = ADM.get("binance_file_validation", {})
    zips = 0
    zip_ok = 0
    zip_bad = []
    for kind in ("klines", "markPriceKlines"):
        for f in rec.get(kind, []):
            url = f.get("url", "")
            tag = f.get("tag")
            if not tag:
                continue
            p = RAW / f"{tag}.zip"
            if not p.exists():
                zip_bad.append({"tag": tag, "issue": "zip absent"})
                continue
            zips += 1
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            if h == f.get("sha256"):
                zip_ok += 1
            else:
                zip_bad.append({"tag": tag, "recorded": f.get("sha256"), "disk": h})
    for f in rec.get("repairs_applied", {}).get("klines", []) + rec.get("repairs_applied", {}).get("markPriceKlines", []):
        tag = f.get("tag")
        p = RAW / f"{tag}.zip" if tag else None
        if p and p.exists():
            zips += 1
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            if h == f.get("sha256"):
                zip_ok += 1
            else:
                zip_bad.append({"tag": tag, "recorded": f.get("sha256"), "disk": h})
    res["binance_zips"] = {"checked": zips, "ok": zip_ok, "mismatch_or_missing": zip_bad[:10],
                           "n_bad": len(zip_bad)}

    # 3. fundingRate zips (aux axis)
    fr = ADM.get("binance_funding_files", [])
    fr_ok = fr_bad = 0
    for f in fr:
        url = f.get("url", "")
        # cached name is '<kind>-<YYYY-MM>' e.g. fundingRate-2026-03
        tag = "fundingRate-" + url.rsplit("fundingRate-", 1)[-1].replace(".zip", "")
        p = RAW / f"{tag}.zip"
        if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == f.get("sha256"):
            fr_ok += 1
        else:
            fr_bad += 1
    res["funding_zips"] = {"checked": len(fr), "ok": fr_ok, "bad": fr_bad}

    # 4. crosscheck with prior probe CSV: recompute independently from the CSV
    probe = ROOT / ".research" / "m2_bridge_001" / "probes" / "probe_c_join_2026-06_2026-08.csv"
    res["prior_probe_csv_present"] = probe.exists()
    if probe.exists():
        import csv
        from datetime import datetime, timezone
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import v1_reverify_pairing as V
        klines, _, _ = V.load_binance("klines")
        marks, _, _ = V.load_binance("markPriceKlines")
        candles, _ = V.load_hl_candles()
        funding, _, _, _, _ = V.load_hl_funding()
        mism = 0
        rows = 0
        inside = 0
        for r in csv.DictReader(open(probe)):
            ts = int(datetime.strptime(r["utc_hour"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()) * 1000
            rows += 1
            if min(candles) <= ts <= max(candles) and ts in funding:
                inside += 1
                if (funding[ts]["fundingRate"] != r["hl_funding_rate"]
                        or funding[ts]["premium"] != r["hl_premium"]
                        or candles[ts]["c"] != r["hl_mid_1h_close"]
                        or klines[ts] != r["binance_kline_close"]
                        or marks[ts] != r["binance_mark_close"]):
                    mism += 1
        res["prior_probe_crosscheck"] = {"rows": rows, "inside_window": inside, "value_mismatches": mism}

    return res


if __name__ == "__main__":
    out = main()
    Path(__file__).resolve().parent.joinpath("v1_integrity_chain.json").write_text(
        json.dumps(out, indent=2, sort_keys=True))
    print(json.dumps(out, indent=2, sort_keys=True))