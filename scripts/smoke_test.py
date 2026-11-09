"""FraudGuard AI end-to-end smoke test (standard library only).

Run from the project root while the backend is running:
    python scripts/smoke_test.py   (use the project .venv python)

It builds requests from your live /openapi.json and real rows from
ai_engine/data/banks/<bank>/transactions.csv. Nothing is mocked.
"""
import csv, json, sys, uuid, urllib.request, urllib.error, urllib.parse
from pathlib import Path

BASE = "http://127.0.0.1:8082"
API = BASE + "/api/v1"
ROOT = Path(__file__).resolve().parent.parent
BANKS = ["alpha", "beta", "gamma"]
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + name + (f"  -> {detail}" if detail else ""))
    return ok


def call(method, url, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def schema_props(spec, name):
    s = spec["components"]["schemas"].get(name, {})
    return s.get("properties", {}), s.get("required", [])


def prop_types(p):
    if "type" in p:
        return {p["type"]}
    return {x.get("type") for x in p.get("anyOf", []) if x.get("type")}


def coerce(value, p):
    t = prop_types(p)
    if "boolean" in t:
        return str(value).strip().lower() in ("1", "true", "yes")
    if "integer" in t:
        return int(float(value))
    if "number" in t:
        return float(value)
    return value


def sample_rows(bank):
    path = ROOT / "ai_engine" / "data" / "banks" / bank / "transactions.csv"
    fraud = legit = None
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["is_fraud"] == "1" and fraud is None:
                fraud = row
            elif row["is_fraud"] == "0" and legit is None:
                legit = row
            if fraud and legit:
                break
    return fraud, legit


def build_tx(row, props, required):
    payload, missing = {}, []
    for k, p in props.items():
        if k in row:
            payload[k] = coerce(row[k], p)
    if "transaction_id" in payload:
        payload["transaction_id"] += "-SMOKE-" + uuid.uuid4().hex[:6]
    missing = [r for r in required if r not in payload]
    return payload, missing


def main():
    try:
        s, spec = call("GET", BASE + "/openapi.json")
    except Exception as e:
        print("Backend not reachable:", e); sys.exit(1)
    check("openapi reachable", s == 200)

    s, body = call("GET", API + "/health")
    check("GET /health", s == 200, str(body))
    s, body = call("GET", API + "/health/ready")
    check("GET /health/ready (database)", s == 200 and body.get("database") == "ok", str(body))

    # ---- auth ----
    reg_props, reg_req = schema_props(spec, "RegisterRequest")
    login_props, login_req = schema_props(spec, "LoginRequest")
    tag = uuid.uuid4().hex[:8]
    password = "SmokeTest#12345"
    fill = {"email": f"smoke_{tag}@example.com", "password": password,
            "full_name": "Smoke Tester", "name": "Smoke Tester",
            "username": f"smoke_{tag}"}
    reg = {k: fill[k] for k in reg_req if k in fill}
    unknown = [k for k in reg_req if k not in fill]
    if unknown:
        print("Register needs fields this script cannot fill:", unknown); sys.exit(1)
    s, body = call("POST", API + "/auth/register", reg)
    check("POST /auth/register", s in (200, 201), f"{s} {str(body)[:120]}")
    login = {k: fill[k] for k in login_props if k in fill}
    s, body = call("POST", API + "/auth/login", login)
    ok = check("POST /auth/login", s == 200 and isinstance(body, dict) and "access_token" in body, str(s))
    if not ok:
        print(body); sys.exit(1)
    token = body["access_token"]
    s, me = call("GET", API + "/auth/me", token=token)
    check("GET /auth/me", s == 200, str(me)[:100])
    s, _ = call("GET", API + "/alerts")
    check("alerts require auth (no token rejected)", s in (401, 403), str(s))
    s, _ = call("POST", API + "/predictions/alpha", {})
    check("predictions require auth", s in (401, 403), str(s))

    # ---- predictions ----
    tx_props, tx_req = schema_props(spec, "TransactionInput")
    pr_props, _ = schema_props(spec, "PredictionResponse")
    print("\nPredictionResponse fields:", list(pr_props))
    for bank in BANKS:
        fraud, legit = sample_rows(bank)
        for label, row in (("fraud-labelled", fraud), ("legit-labelled", legit)):
            if row is None:
                check(f"{bank} {label} sample row exists", False); continue
            payload, missing = build_tx(row, tx_props, tx_req)
            if missing:
                check(f"{bank} {label} payload complete", False, f"missing {missing}"); continue
            s, body = call("POST", API + f"/predictions/{bank}", payload, token)
            check(f"POST /predictions/{bank} ({label})", s in (200, 201), f"{s}")
            if s in (200, 201):
                print("      response:", json.dumps(body)[:400])
    s, body = call("POST", API + "/predictions/doesnotexist", build_tx(sample_rows("alpha")[1], tx_props, tx_req)[0], token)
    check("unknown bank rejected (4xx)", 400 <= s < 500, str(s))

    # ---- alerts ----
    s, alerts = call("GET", API + "/alerts", token=token)
    check("GET /alerts", s == 200, f"{s}")
    items = alerts if isinstance(alerts, list) else (alerts or {}).get("items", [])
    check("alerts exist after fraud-labelled predictions", len(items) > 0, f"{len(items)} alerts")
    s, filtered = call("GET", API + "/alerts?" + urllib.parse.urlencode({"status": "resolved"}), token=token)
    f_items = filtered if isinstance(filtered, list) else (filtered or {}).get("items", [])
    print(f"      status filter probe: unfiltered={len(items)} status=resolved -> {len(f_items)} "
          f"({'filter appears to be IGNORED' if len(f_items) == len(items) and items and any(i.get('status') != 'resolved' for i in items) else 'filter works or no mismatch'})")
    if not items:
        print("No alert to continue workflow with."); return summary()
    alert_id = items[0]["id"]

    s, body = call("GET", API + f"/alerts/{alert_id}", token=token)
    check("GET /alerts/{id}", s == 200)
    s, body = call("PATCH", API + f"/alerts/{alert_id}/status", {"status": "reviewing"}, token)
    check("PATCH alert status -> reviewing", s == 200 and body.get("status") == "reviewing", f"{s}")
    s, body = call("GET", API + f"/alerts/{alert_id}", token=token)
    check("alert status persisted", s == 200 and body.get("status") == "reviewing")

    # ---- case ----
    s, case = call("POST", API + "/cases", {"title": "Smoke test case", "priority": "high", "alert_ids": [alert_id]}, token)
    ok = check("POST /cases with alert_ids", s in (200, 201), f"{s} {str(case)[:150]}")
    if ok:
        cid = case["id"]
        s, got = call("GET", API + f"/cases/{cid}", token=token)
        linked = json.dumps(got).count(alert_id) > 0
        check("case shows linked alert", s == 200 and linked)
        s, upd = call("PATCH", API + f"/cases/{cid}", {"status": "investigating"}, token)
        check("PATCH case -> investigating", s == 200 and upd.get("status") == "investigating", str(s))
        s, lst = call("GET", API + "/cases", token=token)
        check("GET /cases lists new case", s == 200 and cid in json.dumps(lst))

    # ---- feedback ----
    s, fb = call("POST", API + "/feedback", {"alert_id": alert_id, "verdict": "confirmed_fraud", "notes": "smoke test"}, token)
    check("POST /feedback", s in (200, 201), f"{s} {str(fb)[:120]}")
    s, mine = call("GET", API + "/feedback/me", token=token)
    check("GET /feedback/me contains it", s == 200 and alert_id in json.dumps(mine))

    # ---- assistant ----
    chat_props, chat_req = schema_props(spec, "ChatRequest")
    chat = {k: "What does a high fraud probability mean?" for k in chat_req}
    s, body = call("POST", API + "/assistant/chat", chat, token)
    check("POST /assistant/chat", s == 200, f"{s}")
    if s == 200:
        print("      response:", json.dumps(body)[:400])
    summary()


def summary():
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()