import { 
  HealthResponse, 
  CaseModel, 
  InboundCarrierMessage, 
  OutboundDraft, 
  ThreeTurnNegotiationResult,
  CarrierObjectionType,
  HumanApprovalEvent
} from '../types';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = ((import.meta.env.VITE_API_BASE_URL as string) || '')) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...options.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMsg = `HTTP ${response.status} Error`;
      try {
        const rawText = await response.text();
        try {
          const errorData = JSON.parse(rawText);
          errorMsg = errorData.detail || errorData.message || errorMsg;
        } catch {
          if (rawText && rawText.trim()) {
            errorMsg = rawText.length > 200 ? `${rawText.slice(0, 200)}...` : rawText;
          }
        }
      } catch {
        // stream already consumed or network fault
      }
      throw new Error(errorMsg);
    }

    return await response.json();
  }

  /** Checks backend system health and model configuration */
  async checkHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }

  // ============================================================================
  // CASE MANAGEMENT & DEMO CONTROLS
  // ============================================================================

  async listCases(): Promise<CaseModel[]> {
    return this.request<CaseModel[]>('/api/cases');
  }

  async getCase(caseId: string): Promise<CaseModel> {
    return this.request<CaseModel>(`/api/cases/${caseId}`);
  }

  async loadDemoCleanCase(): Promise<CaseModel> {
    return this.request<CaseModel>('/api/cases/demo/load-clean', { method: 'POST' });
  }

  async loadDemoFailureCase(): Promise<CaseModel> {
    return this.request<CaseModel>('/api/cases/demo/load-failure', { method: 'POST' });
  }

  async resetDemoState(): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>('/api/cases/demo/reset', { method: 'POST' });
  }

  async approveLiability(caseId: string, approval: HumanApprovalEvent, expectedVersion?: number): Promise<CaseModel> {
    return this.request<CaseModel>(`/api/cases/${caseId}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        approval,
        actor: approval.adjuster_name,
        expected_version: expectedVersion
      })
    });
  }

  async reanalyzeCase(caseId: string, corrections: Record<string, any>): Promise<CaseModel> {
    return this.request<CaseModel>(`/api/cases/${caseId}/reanalyze`, {
      method: 'POST',
      body: JSON.stringify(corrections)
    });
  }

  async transitionCaseStatus(caseId: string, newStatus: string, expectedVersion?: number): Promise<CaseModel> {
    return this.request<CaseModel>(`/api/cases/${caseId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({
        new_status: newStatus,
        expected_version: expectedVersion
      })
    });
  }

  // ============================================================================
  // INVESTIGATION SUBMISSION & FILE UPLOADS
  // ============================================================================

  async submitNewInvestigation(formData: FormData): Promise<CaseModel> {
    const url = `${this.baseUrl}/api/investigation/assess-multipart`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorMsg = `HTTP ${response.status} Error`;
      try {
        const rawText = await response.text();
        try {
          const errorData = JSON.parse(rawText);
          errorMsg = errorData.detail || errorData.message || errorMsg;
        } catch {
          if (rawText && rawText.trim()) {
            errorMsg = rawText.length > 200 ? `${rawText.slice(0, 200)}...` : rawText;
          }
        }
      } catch {
        // stream already consumed or network fault
      }
      throw new Error(errorMsg);
    }

    const data = await response.json();
    return data.case || data;
  }

  async submitAsyncInvestigation(payload: any, customCaseId?: string, eventId?: string): Promise<any> {
    const params = new URLSearchParams();
    if (customCaseId) params.append('custom_case_id', customCaseId);
    if (eventId) params.append('event_id', eventId);
    const qs = params.toString() ? `?${params.toString()}` : '';

    return this.request<any>(`/api/investigation/submit-async${qs}`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async createCase(payload: any): Promise<CaseModel> {
    return this.request<CaseModel>('/api/cases', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  // ============================================================================
  // SETTLEMENT AGENT & SIMULATION
  // ============================================================================

  async generateCarrierObjectionSample(
    caseId: string, 
    objectionType: CarrierObjectionType, 
    carrierName?: string
  ): Promise<InboundCarrierMessage> {
    return this.request<InboundCarrierMessage>('/api/settlement/carrier-objection-sample', {
      method: 'POST',
      body: JSON.stringify({
        case_id: caseId,
        objection_type: objectionType,
        carrier_name: carrierName || 'N/A'
      })
    });
  }

  async generateSettlementDraft(caseId: string, inboundMessage: InboundCarrierMessage): Promise<OutboundDraft> {
    return this.request<OutboundDraft>(`/api/settlement/${caseId}/draft`, {
      method: 'POST',
      body: JSON.stringify({
        inbound_message: inboundMessage,
        actor: 'SETTLEMENT_AGENT'
      })
    });
  }

  async applyDraftSanitization(draftId: string): Promise<OutboundDraft> {
    return this.request<OutboundDraft>(`/api/settlement/drafts/${draftId}/apply-sanitization`, {
      method: 'POST'
    });
  }

  async approveDraft(draftId: string, adjusterName: string, notes?: string): Promise<OutboundDraft> {
    return this.request<OutboundDraft>(`/api/settlement/drafts/${draftId}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        adjuster_name: adjusterName,
        notes: notes || 'Adjuster verified forensic citations and approved rebuttal.'
      })
    });
  }

  async runDraftSecurityCheck(draftId: string): Promise<OutboundDraft> {
    return this.request<OutboundDraft>(`/api/settlement/drafts/${draftId}/security-check`, {
      method: 'POST'
    });
  }

  async dispatchDraft(caseId: string, draftId: string, actor: string = 'ADJUSTER'): Promise<CaseModel> {
    return this.request<CaseModel>(`/api/settlement/${caseId}/drafts/${draftId}/dispatch`, {
      method: 'POST',
      body: JSON.stringify({ actor })
    });
  }

  async simulateThreeTurnNegotiation(caseId: string): Promise<ThreeTurnNegotiationResult> {
    return this.request<ThreeTurnNegotiationResult>(`/api/settlement/${caseId}/simulate-three-turn`, {
      method: 'POST'
    });
  }

  // ============================================================================
  // OPENTELEMETRY OBSERVABILITY & EXECUTION TRACE
  // ============================================================================

  async getCaseExecutionTrace(caseId: string): Promise<{ case_id: string; total_steps_count: number; spans: any[] }> {
    return this.request<{ case_id: string; total_steps_count: number; spans: any[] }>(`/api/observability/cases/${caseId}/trace`);
  }

  async getObservabilityStatus(): Promise<{ service_name: string; opentelemetry_version: string; gcp_trace_active: boolean; total_spans_in_memory: number }> {
    return this.request<{ service_name: string; opentelemetry_version: string; gcp_trace_active: boolean; total_spans_in_memory: number }>('/api/observability/status');
  }

  // ============================================================================
  // ASYNCHRONOUS BACKGROUND JOBS & TELEMETRY SIMULATOR
  // ============================================================================

  async simulateTelemetryEvent(eventType: string = 'SHOCK', containerId: string = '', eventId?: string): Promise<any> {
    const params = new URLSearchParams({ event_type: eventType, container_id: containerId });
    if (eventId) params.append('event_id', eventId);

    return this.request<any>(`/api/investigation/simulate-telemetry-event?${params.toString()}`, {
      method: 'POST'
    });
  }

  async retryCase(caseId: string, actor: string = 'ADJUSTER'): Promise<CaseModel> {
    return this.request<CaseModel>(`/api/cases/${caseId}/retry`, {
      method: 'POST',
      body: JSON.stringify({ actor })
    });
  }

  async getJobStatus(jobId: string): Promise<any> {
    return this.request<any>(`/api/investigation/jobs/${jobId}`);
  }
}

export const apiClient = new ApiClient();
