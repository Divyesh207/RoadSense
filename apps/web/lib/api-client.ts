import {
  DamageRecord,
  DamageReview,
  DamageType,
  Inspection,
  LoginResponseData,
  MaintenanceDamageLink,
  MaintenanceJob,
  MaintenanceStatusHistory,
  PaginatedResponseEnvelope,
  RecurrenceRecord,
  RepairEvidence,
  RepairVerification,
  ResponseEnvelope,
  Road,
  RoadSegment,
  SegmentHistoricalTimelineResponse,
  UserProfile,
} from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiClient {
  private getHeaders(customHeaders: Record<string, string> = {}): HeadersInit {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...customHeaders,
    };

    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const orgId = localStorage.getItem("organization_id");
      if (orgId) {
        headers["X-Organization-ID"] = orgId;
      }
    }

    return headers;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = this.getHeaders(options.headers as Record<string, string>);

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401 && typeof window !== "undefined") {
      // Clear token if expired
      localStorage.removeItem("access_token");
    }

    const data = await response.json();

    if (!response.ok) {
      const errorMsg = data?.error?.message || data?.detail?.message || "An unexpected API error occurred";
      const error = new Error(errorMsg) as any;
      error.code = data?.error?.code || data?.detail?.code || "API_ERROR";
      error.status = response.status;
      throw error;
    }

    return data;
  }

  // Authentication
  auth = {
    login: async (email: string, password: string): Promise<ResponseEnvelope<LoginResponseData>> => {
      const res = await this.request<ResponseEnvelope<LoginResponseData>>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      if (res.data?.access_token && typeof window !== "undefined") {
        localStorage.setItem("access_token", res.data.access_token);
        if (res.data.user?.organization_id) {
          localStorage.setItem("organization_id", res.data.user.organization_id);
        }
      }
      return res;
    },
    me: async (): Promise<ResponseEnvelope<UserProfile>> => {
      return this.request<ResponseEnvelope<UserProfile>>("/auth/me");
    },
    logout: async (): Promise<void> => {
      if (typeof window !== "undefined") {
        localStorage.removeItem("access_token");
        localStorage.removeItem("organization_id");
      }
    },
  };

  // Roads
  roads = {
    list: async (params: Record<string, any> = {}): Promise<PaginatedResponseEnvelope<Road>> => {
      const q = new URLSearchParams(params).toString();
      return this.request<PaginatedResponseEnvelope<Road>>(`/roads${q ? `?${q}` : ""}`);
    },
    get: async (roadId: string): Promise<ResponseEnvelope<Road>> => {
      return this.request<ResponseEnvelope<Road>>(`/roads/${roadId}`);
    },
    getSegments: async (roadId: string): Promise<ResponseEnvelope<RoadSegment[]>> => {
      return this.request<ResponseEnvelope<RoadSegment[]>>(`/roads/${roadId}/segments`);
    },
  };

  // Inspections
  inspections = {
    list: async (params: Record<string, any> = {}): Promise<PaginatedResponseEnvelope<Inspection>> => {
      const q = new URLSearchParams(params).toString();
      return this.request<PaginatedResponseEnvelope<Inspection>>(`/inspections${q ? `?${q}` : ""}`);
    },
    get: async (inspectionId: string): Promise<ResponseEnvelope<Inspection>> => {
      return this.request<ResponseEnvelope<Inspection>>(`/inspections/${inspectionId}`);
    },
    getDetections: async (inspectionId: string): Promise<ResponseEnvelope<any[]>> => {
      return this.request<ResponseEnvelope<any[]>>(`/inspections/${inspectionId}/detections`);
    },
    submit: async (inspectionId: string): Promise<ResponseEnvelope<Inspection>> => {
      return this.request<ResponseEnvelope<Inspection>>(`/inspections/${inspectionId}/submit`, {
        method: "POST",
      });
    },
    process: async (inspectionId: string): Promise<ResponseEnvelope<any>> => {
      return this.request<ResponseEnvelope<any>>(`/inspections/${inspectionId}/process`, {
        method: "POST",
      });
    },
  };

  // Damage Intelligence
  damages = {
    types: async (): Promise<ResponseEnvelope<DamageType[]>> => {
      return this.request<ResponseEnvelope<DamageType[]>>("/damage-types");
    },
    list: async (params: Record<string, any> = {}): Promise<PaginatedResponseEnvelope<DamageRecord>> => {
      const q = new URLSearchParams(params).toString();
      return this.request<PaginatedResponseEnvelope<DamageRecord>>(`/damages${q ? `?${q}` : ""}`);
    },
    get: async (damageId: string): Promise<ResponseEnvelope<DamageRecord>> => {
      return this.request<ResponseEnvelope<DamageRecord>>(`/damages/${damageId}`);
    },
    review: async (
      damageId: string,
      payload: { decision: "CONFIRMED" | "REJECTED"; severity?: string; damage_type_id?: string; notes?: string }
    ): Promise<ResponseEnvelope<DamageRecord>> => {
      return this.request<ResponseEnvelope<DamageRecord>>(`/damages/${damageId}/review`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    getReviews: async (damageId: string): Promise<ResponseEnvelope<DamageReview[]>> => {
      return this.request<ResponseEnvelope<DamageReview[]>>(`/damages/${damageId}/reviews`);
    },
  };

  // Maintenance Management
  maintenance = {
    list: async (params: Record<string, any> = {}): Promise<PaginatedResponseEnvelope<MaintenanceJob>> => {
      const q = new URLSearchParams(params).toString();
      return this.request<PaginatedResponseEnvelope<MaintenanceJob>>(`/maintenance-jobs${q ? `?${q}` : ""}`);
    },
    get: async (jobId: string): Promise<ResponseEnvelope<MaintenanceJob>> => {
      return this.request<ResponseEnvelope<MaintenanceJob>>(`/maintenance-jobs/${jobId}`);
    },
    create: async (payload: {
      title: string;
      description?: string;
      priority?: string;
      due_at?: string;
      road_id?: string;
      road_segment_id?: string;
      damage_record_ids?: string[];
    }): Promise<ResponseEnvelope<MaintenanceJob>> => {
      return this.request<ResponseEnvelope<MaintenanceJob>>("/maintenance-jobs", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    update: async (jobId: string, payload: Partial<MaintenanceJob>): Promise<ResponseEnvelope<MaintenanceJob>> => {
      return this.request<ResponseEnvelope<MaintenanceJob>>(`/maintenance-jobs/${jobId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    assign: async (jobId: string, payload: { assigned_to?: string; assigned_to_organization_id?: string }): Promise<ResponseEnvelope<MaintenanceJob>> => {
      return this.request<ResponseEnvelope<MaintenanceJob>>(`/maintenance-jobs/${jobId}/assign`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    transitionStatus: async (jobId: string, payload: { status: string; notes?: string }): Promise<ResponseEnvelope<MaintenanceJob>> => {
      return this.request<ResponseEnvelope<MaintenanceJob>>(`/maintenance-jobs/${jobId}/status`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    getHistory: async (jobId: string): Promise<ResponseEnvelope<MaintenanceStatusHistory[]>> => {
      return this.request<ResponseEnvelope<MaintenanceStatusHistory[]>>(`/maintenance-jobs/${jobId}/history`);
    },
    getDamages: async (jobId: string): Promise<ResponseEnvelope<MaintenanceDamageLink[]>> => {
      return this.request<ResponseEnvelope<MaintenanceDamageLink[]>>(`/maintenance-jobs/${jobId}/damages`);
    },
    linkDamage: async (jobId: string, damageRecordId: string, relationshipType = "PRIMARY"): Promise<ResponseEnvelope<MaintenanceDamageLink>> => {
      return this.request<ResponseEnvelope<MaintenanceDamageLink>>(`/maintenance-jobs/${jobId}/damages`, {
        method: "POST",
        body: JSON.stringify({ damage_record_id: damageRecordId, relationship_type: relationshipType }),
      });
    },
    unlinkDamage: async (jobId: string, damageRecordId: string): Promise<ResponseEnvelope<{ success: boolean }>> => {
      return this.request<ResponseEnvelope<{ success: boolean }>>(`/maintenance-jobs/${jobId}/damages/${damageRecordId}`, {
        method: "DELETE",
      });
    },
  };

  // Repair Evidence & Verification (Phase 12)
  repair = {
    getUploadUrl: async (
      jobId: string,
      payload: { filename: string; content_type: string; size_bytes?: number }
    ): Promise<ResponseEnvelope<{ upload_url: string; storage_path: string; expires_in_seconds: number }>> => {
      return this.request<ResponseEnvelope<{ upload_url: string; storage_path: string; expires_in_seconds: number }>>(
        `/maintenance-jobs/${jobId}/repair-evidence/upload-url`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      );
    },
    completeEvidence: async (
      jobId: string,
      payload: {
        storage_path: string;
        evidence_type: string;
        latitude?: number;
        longitude?: number;
        captured_at?: string;
        notes?: string;
      }
    ): Promise<ResponseEnvelope<RepairEvidence>> => {
      return this.request<ResponseEnvelope<RepairEvidence>>(
        `/maintenance-jobs/${jobId}/repair-evidence/complete`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      );
    },
    listEvidence: async (jobId: string): Promise<ResponseEnvelope<RepairEvidence[]>> => {
      return this.request<ResponseEnvelope<RepairEvidence[]>>(`/maintenance-jobs/${jobId}/repair-evidence`);
    },
    evaluateAI: async (
      jobId: string,
      evidenceIds?: string[]
    ): Promise<ResponseEnvelope<RepairVerification>> => {
      return this.request<ResponseEnvelope<RepairVerification>>(
        `/maintenance-jobs/${jobId}/ai-evaluate`,
        {
          method: "POST",
          body: JSON.stringify(evidenceIds ? { evidence_ids: evidenceIds } : {}),
        }
      );
    },
    submitVerification: async (
      jobId: string,
      payload: { decision: "VERIFIED" | "REJECTED"; notes?: string }
    ): Promise<ResponseEnvelope<RepairVerification>> => {
      return this.request<ResponseEnvelope<RepairVerification>>(`/maintenance-jobs/${jobId}/verify`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    listVerifications: async (jobId: string): Promise<ResponseEnvelope<RepairVerification[]>> => {
      return this.request<ResponseEnvelope<RepairVerification[]>>(`/maintenance-jobs/${jobId}/verifications`);
    },
  };

  // Recurrence & Historical Intelligence (Phase 13)
  recurrence = {
    list: async (params: Record<string, any> = {}): Promise<PaginatedResponseEnvelope<RecurrenceRecord>> => {
      const q = new URLSearchParams(params).toString();
      return this.request<PaginatedResponseEnvelope<RecurrenceRecord>>(`/recurrence${q ? `?${q}` : ""}`);
    },
    get: async (recurrenceId: string): Promise<ResponseEnvelope<RecurrenceRecord>> => {
      return this.request<ResponseEnvelope<RecurrenceRecord>>(`/recurrence/${recurrenceId}`);
    },
    evaluate: async (payload: {
      new_damage_id?: string;
      road_segment_id?: string;
      max_distance_meters?: number;
    }): Promise<ResponseEnvelope<RecurrenceRecord[]>> => {
      return this.request<ResponseEnvelope<RecurrenceRecord[]>>("/recurrence/evaluate", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    review: async (
      recurrenceId: string,
      payload: { status: "CONFIRMED" | "DISMISSED" | "FALSE_POSITIVE"; notes?: string }
    ): Promise<ResponseEnvelope<RecurrenceRecord>> => {
      return this.request<ResponseEnvelope<RecurrenceRecord>>(`/recurrence/${recurrenceId}/review`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    getSegmentTimeline: async (segmentId: string): Promise<ResponseEnvelope<SegmentHistoricalTimelineResponse>> => {
      return this.request<ResponseEnvelope<SegmentHistoricalTimelineResponse>>(`/recurrence/segments/${segmentId}/timeline`);
    },
  };
}

export const api = new ApiClient();
