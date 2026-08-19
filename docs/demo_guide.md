# SubroGate Hackathon Demonstration Guide (12-Step Canonical Walkthrough)

This guide walks through the complete, 12-step canonical demonstration scenario of **SubroGate**: an evidence-backed autonomous subrogation recovery console built on Google Vertex AI (Gemini 2.5 Flash), Google Model Armor, and Google Cloud Run.

---

## The Dispute Scenario: High-Value Pharmaceutical Shipment

- **Commodity**: Frozen Pharmaceutical Vaccines ($100,000 declared value, $75,000 loss claim)
- **Container**: `MSKU9082345` (40ft High-Cube Reefer)
- **Shipper / Subrogating Insurer**: Pacific Pharma Global Inc. (via SubroGate)
- **Interchange Facility**: APM Terminals Pier 400 (Los Angeles, CA)
- **Motor Carrier**: Apex Drayage Logistics LLC
- **Incident**: Cold chain compressor failure and 4.2G shock impact during highway drayage

---

## 12-Step Live Demonstration Flow

### Step 1: Cargo Incident Overview
- Navigate to the SubroGate Dashboard (`http://localhost:5173` or live Cloud Run URL).
- Click **"Load Demo Case"** in the top action toolbar.
- The system loads case **`CASE-2026-DEMO-MSKU`** with ISO 6346 Modulo-11 verified checksum.

### Step 2: Ingest Messy Evidence (EIR + Sensor Stream)
- View the **Evidence Locker** section showing:
  - Scanned Gate Receipt (`APM_Pier400_GateReceipt_MSKU9082345.pdf`)
  - Continuous IoT Data Logger (`SENS-LOG-8891`) with 120 recorded telemetry points

### Step 3: Multi-Modal Document Extraction
- The Document Intelligence Agent parses the messy PDF gate receipt:
  - Identifies equipment condition: `CLEAN / INTACT`
  - Extracts seal number: `ML-US9082345`
  - Verifies ISO container check digit: `Valid (Modulo-11 ✓)`

### Step 4: Deterministic UTC Normalization
- The normalizer detects local interchange timestamp `2026-08-15 07:30:00 PDT` and standardizes it to `2026-08-15T14:30:00Z` (UTC).

### Step 5: Earliest Recorded Breach Identification
- Sensor telemetry shows cold-chain temp rising from `-18.0°C` to `+12.4°C` and a critical shock reading of `4.25G` at **17:15:00 UTC**.
- The Earliest Recorded Breach is mathematically fixed at `2026-08-15T17:15:00Z`.

### Step 6: Custody Correlation ($T_{\text{breach}} > T_{\text{handover}}$)
- The Deterministic Timeline Fusion Engine compares the timestamps:
  $$T_{\text{breach}} (\text{17:15 UTC}) > T_{\text{interchange}} (\text{14:30 UTC})$$
- The breach occurred **2 hours and 45 minutes AFTER** Apex Drayage Logistics LLC accepted the clean container at APM Terminals.

### Step 7: Evidence-Backed Responsibility Assessment
- The Investigator Agent generates the forensic assessment:
  - **Potentially Responsible Party**: `Apex Drayage Logistics LLC`
  - **Confidence**: `94% (High Confidence)`
  - **Statutory Citations**: Carmack Amendment (*49 U.S.C. § 14706*) and Uniform Intermodal Interchange Agreement (*UIIA Section E.2*)
  - **Strict Legal Boundary Notice**: Plainly displays *"Evidence-backed responsibility assessment"* rather than a legal ruling.

### Step 8: Human Claims Adjuster Approval Gate
- Scroll to the **Human Adjuster Checkpoint**.
- Enter adjuster notes (*"Verified clean gate receipt and sensor telemetry shock excursion"*).
- Click **"Authorize & Lock Liability Assessment"**.
- State locks into `APPROVED` and generates a cryptographically verifiable approval token.

### Step 9: Inbound Carrier Dispute Injection
- Scroll down to the **Settlement & Carrier Negotiation** console.
- In the **Simulate Inbound Carrier Defense** panel, select:
  - **"Pre-Existing Damage Defense"** (*"Carrier says damage occurred prior to gate pickup"*)
- Click **"Inject Carrier Objection"**.

### Step 10: Grounded Rebuttal Formulation
- The Settlement Agent activates (restricted to `APPROVED` cases).
- Reads the carrier objection and cross-references documented evidence:
  - Cites the signed APM Terminals EIR stating `CLEAN / INTACT` at gate-out.
  - Cites the 17:15 UTC telemetry spike proving damage occurred in carrier custody.
  - Proposes a $75,000 subrogation demand.

### Step 11: Google Model Armor Security Gate
- The security gateway automatically screens the outbound draft:
  - Scans for PII, private pricing margins, internal secrets, and prompt injections.
  - Verdict: `PASS (0 Violations Detected)`.
  - (Demonstrate failure: Insert a simulated API key to see the `BLOCK / SANITIZE` gate in action).

### Step 12: Final Recovery Package & Multi-Turn Negotiation
- Click **"Execute 3-Turn Negotiation"** to demonstrate automated multi-round settlement:
  - **Turn 1**: Carrier offers $45,000 (disputing sensor precision).
  - **Turn 2**: SubroGate presents calibration certificate & NIST traceability &rarr; Carrier counter-offers $68,500.
  - **Turn 3**: Case settles at **$71,250** (95% recovery).
- Case status transitions to `RESOLVED` with complete immutable audit trail.

---

## 1-Click Reset & Fallback
- To reset the demo at any time, click **"Reset"** in the top toolbar.
- To demonstrate failure recovery, click **"Simulate Failure"** followed by **"Retry Investigation"**.
- To stream simulated real-time IoT events into the async pipeline, click **"Simulate IoT Stream"**.
