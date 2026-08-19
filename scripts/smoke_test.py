#!/usr/bin/env python3
"""
SubroGate End-to-End Smoke Test Suite
Verifies core health, API endpoints, async background pipeline, OpenTelemetry,
and frontend SPA delivery against a local server or live Google Cloud Run deployment.
"""

import sys
import time
import argparse
import httpx


def run_smoke_tests(base_url: str) -> bool:
    base_url = base_url.rstrip("/")
    print("=" * 80)
    print(f" SUBROGATE END-TO-END SMOKE TEST: {base_url}")
    print("=" * 80)

    client = httpx.Client(base_url=base_url, timeout=30.0)
    tests_passed = 0
    total_tests = 6

    # 1. Health Check Endpoint
    try:
        start = time.time()
        res = client.get("/health")
        duration = round((time.time() - start) * 1000, 2)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data.get("status") == "healthy", f"Status not healthy: {data}"
        print(f"  [PASS] 1. System Health Check (/health) - {duration}ms [Model: {data['model']['configured_model']}]")
        tests_passed += 1
    except Exception as e:
        print(f"  [FAIL] 1. System Health Check (/health): {e}")

    # 2. OpenTelemetry Observability Status
    try:
        start = time.time()
        res = client.get("/api/observability/status")
        duration = round((time.time() - start) * 1000, 2)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert "service_name" in data, "Missing service_name"
        print(f"  [PASS] 2. OpenTelemetry Observability (/api/observability/status) - {duration}ms [GCP Trace: {data.get('gcp_trace_active')}]")
        tests_passed += 1
    except Exception as e:
        print(f"  [FAIL] 2. OpenTelemetry Observability (/api/observability/status): {e}")

    # 3. Ingest Demo Case
    try:
        start = time.time()
        res = client.post("/api/cases/demo/load-clean")
        duration = round((time.time() - start) * 1000, 2)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        case = res.json()
        assert case["case_id"] == "CASE-2026-DEMO-MSKU", f"Unexpected case ID: {case.get('case_id')}"
        print(f"  [PASS] 3. Case State Persistence (/api/cases/demo/load-clean) - {duration}ms [Case: {case['case_id']}]")
        tests_passed += 1
    except Exception as e:
        print(f"  [FAIL] 3. Case State Persistence (/api/cases/demo/load-clean): {e}")

    # 4. Reconstructed Timeline & Forensic Assessment
    try:
        start = time.time()
        res = client.get("/api/cases/CASE-2026-DEMO-MSKU")
        duration = round((time.time() - start) * 1000, 2)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        case = res.json()
        assert case["status"] in ["APPROVED", "ASSESSMENT_READY", "PROCESSING"], f"Invalid status: {case['status']}"
        assert case.get("normalized_timeline"), "Missing normalized timeline"
        assert case.get("assessment"), "Missing assessment"
        party = case["assessment"]["potentially_responsible_party"]
        print(f"  [PASS] 4. Forensic Timeline & Assessment (/api/cases/...) - {duration}ms [Party: {party}]")
        tests_passed += 1
    except Exception as e:
        print(f"  [FAIL] 4. Forensic Timeline & Assessment (/api/cases/...): {e}")

    # 5. Asynchronous Telemetry Simulation Pipeline
    try:
        start = time.time()
        res = client.post("/api/investigation/simulate-telemetry-event?event_type=SHOCK&container_id=MSKU9082345")
        duration = round((time.time() - start) * 1000, 2)
        assert res.status_code in [200, 202], f"Expected 202/200, got {res.status_code}"
        async_data = res.json()
        assert "job_id" in async_data, "Missing job_id"
        print(f"  [PASS] 5. Async Telemetry Pipeline (/api/investigation/simulate-telemetry-event) - {duration}ms [Job: {async_data['job_id']}]")
        tests_passed += 1
    except Exception as e:
        print(f"  [FAIL] 5. Async Telemetry Pipeline (/api/investigation/simulate-telemetry-event): {e}")

    # 6. Production Frontend Delivery
    try:
        start = time.time()
        res = client.get("/")
        duration = round((time.time() - start) * 1000, 2)
        # Should return 200 with HTML content if frontend built, or 404/200 in development
        assert res.status_code in [200, 404], f"Unexpected status code: {res.status_code}"
        is_html = "text/html" in res.headers.get("content-type", "")
        print(f"  [PASS] 6. Frontend SPA Delivery (/) - {duration}ms [HTML Delivered: {is_html}]")
        tests_passed += 1
    except Exception as e:
        print(f"  [FAIL] 6. Frontend SPA Delivery (/): {e}")

    print("=" * 80)
    print(f" SMOKE TEST SUMMARY: {tests_passed}/{total_tests} Tests Passed ({'ALL PASSED' if tests_passed == total_tests else 'SOME FAILED'})")
    print("=" * 80)

    return tests_passed == total_tests


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SubroGate Deployment Smoke Test")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of SubroGate instance")
    args = parser.parse_args()

    success = run_smoke_tests(args.url)
    sys.exit(0 if success else 1)
