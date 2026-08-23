export type CustodyRole = 
  | 'shipper'
  | 'drayage_origin'
  | 'origin_terminal'
  | 'ocean_carrier'
  | 'rail_carrier'
  | 'destination_terminal'
  | 'drayage_destination'
  | 'consignee'
  | string;

export type HandoverStatus = 'clean' | 'exception_noted' | 'rejected' | 'unknown' | string;

export interface ModelConfigInfo {
  configured_model: string;
  provider: string;
  auth_configured: boolean;
  use_vertex: boolean;
  adk_compatible: boolean;
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  timestamp: string;
  model: ModelConfigInfo;
  environment: string;
}

export interface ApiError {
  type: string;
  message: string;
  details?: Record<string, any>;
}

// ==============================================================================
// OPENTELEMETRY OBSERVABILITY & EXECUTION TRACE
// ==============================================================================

export interface OperationalSpanEvent {
  span_id: string;
  trace_id: string;
  parent_span_id?: string;
  step_name: string;
  category: string;
  start_time_utc: string;
  end_time_utc: string;
  duration_ms: number;
  status: 'SUCCESS' | 'FAILED' | string;
  case_id?: string;
  attributes: Record<string, any>;
  error_message?: string;
}

export interface ExecutionTraceResponse {
  case_id?: string;
  total_steps_count: number;
  spans: OperationalSpanEvent[];
}

export interface ObservabilityStatusResponse {
  service_name: string;
  opentelemetry_version: string;
  gcp_trace_active: boolean;
  total_spans_in_memory: number;
}

// ==============================================================================
// ASYNCHRONOUS BACKGROUND JOBS & SIMULATION
// ==============================================================================

export interface AsyncSubmissionResponse {
  case_id: string;
  job_id: string;
  status: string;
  idempotency_key: string;
  is_duplicate: boolean;
  message: string;
  tracking_url: string;
}

export interface AsyncJobStatus {
  job_id: string;
  case_id: string;
  idempotency_key: string;
  status: string;
  progress_stage: string;
  progress_pct: number;
  created_at_utc: string;
  updated_at_utc: string;
  error_message?: string;
  retry_count: number;
}

// ==============================================================================
// CASE STATE & MANAGEMENT TYPES
// ==============================================================================

export type CaseStatus =
  | 'NEW'
  | 'INGESTING'
  | 'ANALYZING'
  | 'EXTRACTION_REVIEW'
  | 'ASSESSMENT_READY'
  | 'HUMAN_REVIEW'
  | 'APPROVED'
  | 'AWAITING_RESPONSE'
  | 'NEGOTIATION'
  | 'RESOLVED'
  | 'FAILED';

export interface ShipmentInfo {
  container_id?: string;
  commodity?: string;
  declared_value_usd?: number;
  claimed_loss_usd?: number;
  origin_facility?: string;
  destination_facility?: string;
  shipper_name?: string;
  carrier_name?: string;
  consignee_name?: string;
  bill_of_lading_number?: string;
}

export interface SourceDocumentRef {
  document_id: string;
  filename: string;
  mime_type: string;
  sha256_hash: string;
  file_size_bytes?: number;
  uploaded_at_utc?: string;
  document_type?: string;
}

export interface TelemetryRef {
  device_id?: string;
  total_readings_count?: number;
  breaches_detected_count?: number;
  earliest_reading_utc?: string;
  latest_reading_utc?: string;
  has_critical_shock?: boolean;
  has_temp_excursion?: boolean;
}

export interface HumanApprovalEvent {
  approval_id: string;
  adjuster_name: string;
  approved_at_utc?: string;
  allocated_liability_pct: number;
  notes?: string;
  audit_badge_token: string;
}

export interface SettlementState {
  target_recovery_usd: number;
  acceptable_settlement_floor_usd: number;
  recommended_posture: string;
  current_carrier_offer_usd?: number;
  settlement_status: string;
}

export interface NegotiationMessage {
  message_id: string;
  timestamp_utc?: string;
  sender_party: string;
  recipient_party: string;
  message_type?: string;
  message_text: string;
  proposed_amount_usd?: number;
  response_deadline_utc?: string;
}

export interface AuditEvent {
  event_id: string;
  event_type: string;
  description: string;
  actor: string;
  timestamp_utc: string;
  metadata?: Record<string, any>;
}

export interface CaseModel {
  case_id: string;
  status: CaseStatus;
  shipment_info: ShipmentInfo;
  source_document_refs: SourceDocumentRef[];
  telemetry_ref?: TelemetryRef;
  extracted_custody_events?: Record<string, any>;
  human_corrections?: Record<string, any>;
  normalized_timeline: Array<Record<string, any>>;
  assessment?: Record<string, any>;
  human_approvals: HumanApprovalEvent[];
  settlement_state?: SettlementState;
  negotiation_history: NegotiationMessage[];
  created_at_utc: string;
  updated_at_utc: string;
  closed_at_utc?: string;
  model_identifier: string;
  application_version: string;
  audit_events: AuditEvent[];
  version: number;
}

// ==============================================================================
// FORENSIC INVESTIGATION & CITATIONS
// ==============================================================================

export interface EvidenceCitation {
  citation_id: string;
  source_type: string;
  source_reference: string;
  verbatim_quote_or_datapoint: string;
  relevance_explanation: string;
}

export interface LegalFrameworkReference {
  framework_name: string;
  governing_law_citation: string;
  key_legal_principle: string;
  relevance_to_dispute?: string;
}

export interface EvidenceBackedAssessment {
  potentially_responsible_party: string;
  responsibility_confidence: number;
  evidence_supporting_assessment: string[];
  conflicting_evidence: string[];
  uncertainties: string[];
  applicable_legal_framework: LegalFrameworkReference[];
  recommended_recovery_action: string;
  human_review_required: boolean;
  legal_boundary_disclaimer?: string;
}

// ==============================================================================
// SETTLEMENT AGENT & NEGOTIATION
// ==============================================================================

export type CarrierObjectionType =
  | 'NOTICE_ALLEGEDLY_LATE'
  | 'DISPUTES_CUSTODY'
  | 'DISPUTES_SENSOR_RELIABILITY'
  | 'DAMAGE_BEFORE_PICKUP'
  | 'REQUESTS_SUPPORTING_DOCS'
  | 'PARTIAL_SETTLEMENT_OFFER'
  | 'GENERAL_DENIAL';

export type DraftApprovalStatus =
  | 'DRAFT'
  | 'SECURITY_REVIEW'
  | 'SECURITY_BLOCKED'
  | 'HUMAN_REVIEW'
  | 'APPROVE'
  | 'SECURITY_CHECK'
  | 'READY_TO_SEND';

export interface InboundCarrierMessage {
  message_id: string;
  case_id: string;
  sender_party: string;
  sender_email?: string;
  subject: string;
  body_text: string;
  offered_amount_usd?: number;
  identified_objection?: CarrierObjectionType;
  received_at_utc?: string;
}

export interface OutboundDraft {
  draft_id: string;
  case_id: string;
  in_response_to_message_id?: string;
  identified_carrier_objection: CarrierObjectionType;
  relevant_evidence_citations: EvidenceCitation[];
  draft_subject: string;
  draft_body_markdown: string;
  proposed_settlement_amount_usd?: number;
  security_report?: Record<string, any>;
  status: DraftApprovalStatus;
  human_reviewer?: string;
  adjuster_modifications_notes?: string;
  security_check_passed: boolean;
  created_at_utc?: string;
  reviewed_at_utc?: string;
  approved_at_utc?: string;
  next_recommended_action: string;
  requires_escalation: boolean;
  escalation_reason?: string;
}

export interface SimulationTurn {
  turn_index: number;
  inbound_carrier_message: InboundCarrierMessage;
  outbound_draft: OutboundDraft;
  status_at_turn_end: DraftApprovalStatus;
  notes: string;
}

export interface ThreeTurnNegotiationResult {
  simulation_id: string;
  case_id: string;
  starting_demand_usd: number;
  final_settlement_usd?: number;
  settlement_achieved: boolean;
  turns: SimulationTurn[];
  completed_at_utc: string;
}

// ==============================================================================
// SECURITY GATE & MODEL ARMOR TYPES
// ==============================================================================

export type SecurityVerdict = 'PASS' | 'REVIEW' | 'BLOCK';

export interface SecurityFinding {
  finding_id: string;
  category: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
  redacted_match: string;
  character_span?: [number, number];
  suggested_replacement?: string;
}

export interface SecurityScreeningReport {
  screening_id: string;
  case_id: string;
  draft_id: string;
  timestamp_utc: string;
  verdict: SecurityVerdict;
  engine_used: string;
  findings_count: number;
  findings: SecurityFinding[];
  original_text_preserved: string;
  suggested_sanitization: string;
  action_taken: string;
}

// ==============================================================================
// COMPATIBILITY TYPES FOR PROTO COMPONENTS
// ==============================================================================

export interface TelemetryPoint {
  timestamp: string;
  latitude: number;
  longitude: number;
  location_name?: string;
  temperature_c?: number;
  humidity_pct?: number;
  shock_g?: number;
  door_open?: boolean;
  power_connected?: boolean;
  battery_pct?: number;
}

export interface TelemetryThresholds {
  temp_min_c?: number;
  temp_max_c?: number;
  temp_excursion_duration_mins_tolerance?: number;
  shock_g_warning?: number;
  shock_g_critical?: number;
  authorized_geofences?: Array<{
    name: string;
    center?: [number, number];
    radius_km?: number;
  }>;
}

export interface AnomalyEvent {
  id: string;
  anomaly_type: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  severity: 'CRITICAL' | 'MAJOR' | 'MINOR' | string;
  peak_value: number;
  threshold_value: number;
  location_name: string;
  coordinates: [number, number];
  description: string;
  affected_samples_count: number;
}

export interface TelemetryDataset {
  device_id: string;
  device_model: string;
  container_id: string;
  points: TelemetryPoint[];
  sampling_interval_seconds: number;
}

export interface SealRecord {
  seal_number: string;
  seal_type?: string;
  intact: boolean;
  tampered: boolean;
  notes?: string;
}

export interface EIRRecord {
  id: string;
  document_type: string;
  issuing_facility: string;
  location_code?: string;
  timestamp: string;
  releasing_party: string;
  releasing_party_role: CustodyRole;
  receiving_party: string;
  receiving_party_role: CustodyRole;
  container_number: string;
  seal_records: SealRecord[];
  equipment_condition: HandoverStatus;
  damage_remarks?: string;
  handover_status: HandoverStatus;
  source_file_url?: string;
  sha256_hash?: string;
}

export interface CustodyHandover {
  handover_id: string;
  timestamp: string;
  releasing_party: string;
  releasing_role: CustodyRole;
  receiving_party: string;
  receiving_role: CustodyRole;
  location_name: string;
  facility_type: string;
  condition: HandoverStatus;
  eir_ref?: string;
  has_exceptions: boolean;
  notes?: string;
}

export interface CustodyChain {
  container_id: string;
  origin_shipper: string;
  destination_consignee: string;
  declared_commodity: string;
  cargo_value_usd: number;
  handovers: CustodyHandover[];
  current_custody_holder: string;
}

export interface FusedTimelineEvent {
  id?: string;
  event_id?: string;
  timestamp: string;
  event_type: string;
  title?: string;
  description: string;
  location_name: string;
  custody_holder?: string;
  custody_role?: CustodyRole;
  severity?: string;
  evidence_source?: string;
  evidence_reference?: string;
  is_liability_trigger?: boolean;
  is_breach_event?: boolean;
  coordinates?: [number, number];
}

export interface IncidentReconstruction {
  case_id: string;
  fused_timeline: FusedTimelineEvent[];
  culpable_custody_window?: {
    responsible_party: string;
    responsible_role: CustodyRole;
    start_time: string;
    end_time: string;
    triggering_anomaly_id: string;
    confidence_score: number;
  };
}

export interface ResponsibilityAssessment {
  case_id: string;
  liable_party: string;
  liable_role: CustodyRole;
  confidence_score: number;
  primary_rationale: string;
  corroborating_facts: string[];
  applicable_framework: string;
  counter_arguments_analyzed: Array<{
    argument: string;
    rebuttal: string;
    weight: 'STRONG' | 'MEDIUM' | 'WEAK' | string;
  }>;
  alternative_hypotheses: Array<{
    party: string;
    likelihood: number;
    reason_rejected: string;
  }>;
  recommended_recovery_action: string;
  settlement_range: {
    minimum_acceptable_usd: number;
    target_demand_usd: number;
    maximum_legal_exposure_usd: number;
  };
  uncertainties: string[];
  audit_badge_hash: string;
}

export interface ItemizedLossSchedule {
  item_description?: string;
  quantity?: number;
  unit_value_usd?: number;
  total_loss_usd?: number;
  salvage_recovered_usd?: number;
  net_claim_usd?: number;
  items?: any[];
  total_subrogation_claim_usd?: number;
}

export interface DemandLetter {
  demand_id?: string;
  letter_date?: string;
  claimant_name?: string;
  target_carrier_name?: string;
  target_carrier_address?: string;
  container_id?: string;
  loss_amount_usd?: number;
  governing_law_citation?: string;
  formal_notice_text?: string;
  exhibits_referenced?: string[];
  response_deadline_date?: string;
  body_markdown?: string;
  notice_type?: string;
  reference_claim_number?: string;
  date_issued?: string;
  addressed_to_carrier?: string;
  addressed_to_department?: string;
  subject_line?: string;
  exhibits_attached?: string[];
}

export interface SettlementStrategy {
  case_id?: string;
  claim_amount_usd?: number;
  itemized_loss?: ItemizedLossSchedule[] | any;
  recommended_posture?: string;
  concession_thresholds?: Array<{
    round: number;
    proposed_amount_usd: number;
    justification: string;
  }>;
  demand_letter?: DemandLetter;
  probability_of_full_recovery_pct?: number;
  recommended_negotiation_posture?: string;
  target_recovery_usd?: number;
  acceptable_settlement_floor_usd?: number;
  counter_defenses?: any[];
  recommended_next_steps?: any[];
}

export interface SubrogationPackage {
  package_id?: string;
  case_id: string;
  container_id: string;
  commodity: string;
  total_loss_claimed_usd: number;
  eir_records: EIRRecord[];
  telemetry: TelemetryDataset;
  anomalies: AnomalyEvent[];
  custody_chain: CustodyChain;
  reconstruction: IncidentReconstruction;
  assessment: ResponsibilityAssessment;
  settlement_strategy: SettlementStrategy;
  human_approval_required: boolean;
  approval_status: 'PENDING_REVIEW' | 'APPROVED' | 'MODIFIED_BY_ADJUSTER' | 'REJECTED' | string;
  loss_schedule?: any;
  demand_letter?: any;
  responsibility_assessment?: any;
  incident_reconstruction?: any;
  shipment_id?: string;
  category?: string;
}

export interface HumanApprovalResponse {
  case_id: string;
  approved_by_adjuster: string;
  approval_timestamp: string;
  status: 'APPROVED' | 'MODIFIED' | 'REJECTED' | string;
  adjuster_notes: string;
  modified_demand_usd?: number;
  cryptographic_signature: string;
}

export interface ScenarioSummary {
  id: string;
  title: string;
  container_id: string;
  commodity: string;
  claimed_amount?: number;
  responsible_party: string;
  breach_type?: string;
  description: string;
  category?: string;
  claimed_loss_usd?: number;
  carrier_dispute_parties?: string[];
}

export interface ScenarioDefinition {
  id: string;
  package: SubrogationPackage;
}
