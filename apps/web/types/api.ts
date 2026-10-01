export interface ResponseMeta {
  request_id?: string;
  timestamp: string;
}

export interface PaginationMeta extends ResponseMeta {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ResponseEnvelope<T> {
  success: boolean;
  data: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  meta: ResponseMeta;
}

export interface PaginatedResponseEnvelope<T> {
  success: boolean;
  data: T[];
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  meta: PaginationMeta;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  phone_number?: string;
  is_active: boolean;
  role: string;
  organization_id?: string;
  organization_name?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginResponseData {
  user: UserProfile;
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LocationData {
  latitude: number;
  longitude: number;
  accuracy_m?: number;
}

export interface Road {
  id: string;
  organization_id: string;
  name: string;
  road_code?: string;
  road_type?: string;
  administrative_area?: string;
  description?: string;
  is_active: boolean;
  segment_count?: number;
  created_at: string;
  updated_at: string;
}

export interface RoadSegment {
  id: string;
  road_id: string;
  road_name?: string;
  segment_number: number;
  start_chainage_meters?: number;
  end_chainage_meters?: number;
  length_meters?: number;
  surface_type?: string;
  lane_count?: number;
  current_pci?: number;
  created_at: string;
}

export interface InspectionMediaSummary {
  media_count: number;
  image_count: number;
  video_count: number;
}

export interface Inspection {
  id: string;
  organization_id: string;
  inspector_user_id: string;
  inspector_name?: string;
  road_id?: string;
  road_name?: string;
  road_segment_id?: string;
  segment_number?: number;
  status: "DRAFT" | "SUBMITTED" | "PROCESSING" | "COMPLETED" | "REJECTED";
  source: string;
  captured_at: string;
  submitted_at?: string;
  location?: LocationData;
  notes?: string;
  media_summary?: InspectionMediaSummary;
  created_at: string;
  updated_at: string;
}

export interface InspectionMedia {
  id: string;
  inspection_id: string;
  media_type: "IMAGE" | "VIDEO";
  storage_bucket: string;
  storage_path: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  upload_status: string;
  duration_seconds?: number;
  width_px?: number;
  height_px?: number;
  created_at: string;
}

export interface DamageType {
  id: string;
  code: string;
  name: string;
  description?: string;
  is_active: boolean;
}

export interface DamageRecord {
  id: string;
  organization_id: string;
  inspection_id: string;
  source_detection_id?: string;
  road_id?: string;
  road_name?: string;
  road_segment_id?: string;
  segment_number?: number;
  damage_type_id: string;
  damage_type_code: string;
  damage_type_name: string;
  source_type: "AI" | "MANUAL";
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  severity_score?: number;
  location?: LocationData;
  status: "DETECTED" | "PENDING_REVIEW" | "CONFIRMED" | "REJECTED" | "REPAIRED";
  confidence?: number;
  estimated_area_m2?: number;
  detected_at?: string;
  reviewed_at?: string;
  reviewed_by_user_id?: string;
  reviewed_by_name?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface DamageReview {
  id: string;
  damage_record_id: string;
  reviewer_user_id: string;
  reviewer_name?: string;
  review_status: string;
  original_severity?: string;
  reviewed_severity?: string;
  review_notes?: string;
  reviewed_at: string;
}

export interface MaintenanceJob {
  id: string;
  organization_id: string;
  road_id?: string;
  road_segment_id?: string;
  created_by_user_id: string;
  assigned_to_user_id?: string;
  assigned_to_organization_id?: string;
  title: string;
  description?: string;
  priority_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  priority_score?: number;
  status:
    | "OPEN"
    | "ASSIGNED"
    | "IN_PROGRESS"
    | "COMPLETED"
    | "VERIFICATION_PENDING"
    | "VERIFIED"
    | "REJECTED"
    | "CANCELLED";
  due_at?: string;
  started_at?: string;
  completed_at?: string;
  verified_at?: string;
  completion_notes?: string;
  latitude?: number;
  longitude?: number;
  damage_count?: number;
  created_at: string;
  updated_at: string;
}

export interface MaintenanceStatusHistory {
  id: string;
  organization_id: string;
  maintenance_job_id: string;
  previous_status?: string;
  new_status: string;
  changed_by_user_id: string;
  reason?: string;
  changed_at: string;
}

export interface MaintenanceDamageLink {
  maintenance_job_id: string;
  damage_record_id: string;
  relationship_type: string;
  created_at: string;
  severity?: string;
  status?: string;
  damage_type?: string;
}

export interface RepairEvidence {
  id: string;
  organization_id: string;
  maintenance_job_id: string;
  evidence_type: "BEFORE_REPAIR" | "DURING_REPAIR" | "AFTER_REPAIR" | "SIGN_OFF_DOCUMENT";
  storage_path: string;
  file_size_bytes?: number;
  content_type?: string;
  latitude?: number;
  longitude?: number;
  captured_at?: string;
  created_at: string;
}

export interface RepairVerification {
  id: string;
  organization_id: string;
  maintenance_job_id: string;
  verified_by_user_id?: string;
  verification_status: "PENDING" | "AI_EVALUATED" | "VERIFIED" | "REJECTED";
  ai_confidence?: number;
  comparison_metrics?: Record<string, any>;
  findings?: Record<string, any>;
  reviewer_notes?: string;
  verified_at?: string;
  created_at: string;
}
