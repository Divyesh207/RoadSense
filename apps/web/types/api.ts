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

export interface OrganizationMembershipInfo {
  organization_id: string;
  organization_name: string;
  organization_code: string;
  role_id: string;
  role_code: string;
  status: string;
  permissions: string[];
}

// GET /auth/me
export interface CurrentUserData {
  id: string;
  email: string;
  full_name: string;
  phone?: string | null;
  is_active: boolean;
  organizations: OrganizationMembershipInfo[];
}

// CurrentUserData plus the active membership resolved on the client.
export interface UserProfile extends CurrentUserData {
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

// POST /auth/login (tokens only; the profile comes from /auth/me)
export interface LoginResponseData {
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
  geometry?: GeoJSONLineGeometry | null;
  traffic_volume_class?: string | null;
  traffic_aadt?: number | null;
  traffic_data_source?: string | null;
  is_active: boolean;
  segment_count?: number;
  created_at: string;
  updated_at: string;
}

// POST /roads (RoadCreateRequest). Only fields the API accepts.
export interface RoadCreatePayload {
  name: string;
  road_code?: string;
  road_type?: string;
  administrative_area?: string;
  description?: string;
  traffic_volume_class?: "LOW" | "MEDIUM" | "HIGH" | "VERY_HIGH";
  traffic_aadt?: number;
  traffic_data_source?: string;
}

// POST /roads/{road_id}/segments (RoadSegmentCreateRequest). Chainage is in kilometres.
export interface RoadSegmentCreatePayload {
  segment_number: number;
  name?: string;
  start_chainage?: number;
  end_chainage?: number;
  length_meters?: number;
  geometry?: GeoJSONLineGeometry;
}

export interface RoadSegment {
  id: string;
  road_id: string;
  road_name?: string;
  segment_number: number;
  name?: string | null;
  start_chainage?: number | null;
  end_chainage?: number | null;
  geometry?: GeoJSONLineGeometry | null;
  is_active?: boolean;
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
  // Backend lifecycle: DRAFT -> UPLOADING -> SUBMITTED -> PROCESSING -> ANALYZED | PROCESSING_FAILED
  status:
    | "DRAFT"
    | "UPLOADING"
    | "SUBMITTED"
    | "PROCESSING"
    | "ANALYZED"
    | "PROCESSING_FAILED"
    | "COMPLETED"
    | "REJECTED";
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
  /** Short-lived signed view URL; only present when requested with includeUrls. */
  download_url?: string | null;
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

// GET /inspections/{id}/detections (bbox coordinates are normalized 0..1)
export interface InspectionDetection {
  id: string;
  inspection_id: string;
  media_id: string;
  damage_type: string;
  damage_type_id: string;
  // Heuristic fallback scores are not probabilities; see score_type / detection_method.
  confidence: number;
  score_type?: "MODEL_CONFIDENCE" | "HEURISTIC_SCORE" | null;
  detection_method?: "TRAINED_MODEL" | "HEURISTIC_FALLBACK" | "UNKNOWN";
  model_name?: string | null;
  model_version?: string | null;
  bbox: { x_min: number; y_min: number; x_max: number; y_max: number };
  pixel_width?: number | null;
  pixel_height?: number | null;
  frame_number?: number | null;
  frame_timestamp_ms?: number | null;
  location?: LocationData | null;
  severity: string;
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
  detection_method?: "TRAINED_MODEL" | "HEURISTIC_FALLBACK" | "MANUAL" | "UNKNOWN" | null;
  score_type?: "MODEL_CONFIDENCE" | "HEURISTIC_SCORE" | null;
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
  priority_factors?: PriorityFactors | null;
  created_at: string;
  updated_at: string;
}

export interface PriorityFactors {
  mode?: "AUTO" | "MANUAL" | "MANUAL_LEVEL";
  method?: string;
  version?: string;
  inputs?: Record<string, any>;
  components?: Record<string, number>;
  level_floor_from_severity?: string;
  calculated_at?: string;
}

export interface HealthSummary {
  health_score: number | null;
  health_status: string;
  calculation_version: string;
  calculated_at: string;
}

export interface MaintenanceJobContext {
  road: { id: string; name: string; road_code?: string; traffic_volume_class?: string | null } | null;
  segment: { id: string; name?: string; segment_number: number } | null;
  damages: {
    id: string;
    relationship_type: string;
    damage_type: string | null;
    severity: string;
    status: string;
    source_type: string;
    confidence: number | null;
    observation_count: number;
    inspection_id: string | null;
    source_detection_id: string | null;
    road_id: string | null;
    road_segment_id: string | null;
    location: { latitude: number; longitude: number } | null;
    detected_at: string | null;
  }[];
  segment_health: HealthSummary | null;
  road_health: HealthSummary | null;
  assigned_user: { id: string; full_name: string; email: string } | null;
  assigned_organization: { id: string; name: string } | null;
  allowed_transitions: string[];
}

export interface MaintenanceAssignees {
  users: { id: string; full_name: string; email: string; role: string }[];
  contractor_organizations: { id: string; name: string; code: string }[];
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
  storage_bucket?: string;
  storage_path: string;
  media_type?: "IMAGE" | "VIDEO";
  mime_type?: string;
  uploaded_by_user_id?: string;
  file_size_bytes?: number;
  content_type?: string;
  notes?: string;
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
  // AUTOMATED_CHECK: evidence presence + GPS location only (no image analysis).
  // AI_EVALUATED appears only on records created before that relabelling.
  // AUTOMATED_IMAGE_ANALYSIS rows move QUEUED -> PROCESSING -> COMPLETED | FAILED;
  // HUMAN_REVIEW rows are REVIEWED.
  verification_status:
    | "PENDING"
    | "AUTOMATED_CHECK"
    | "AI_EVALUATED"
    | "VERIFIED"
    | "REJECTED"
    | "QUEUED"
    | "PROCESSING"
    | "COMPLETED"
    | "FAILED"
    | "REVIEWED";
  verification_type?:
    | "AUTOMATED_IMAGE_ANALYSIS"
    | "HUMAN_REVIEW"
    | "HUMAN_SIGNOFF"
    | "AUTOMATED_EVIDENCE_CHECK"
    | null;
  result?: "SUCCESSFUL" | "SUBSTANDARD" | "UNRESOLVED" | null;
  ai_confidence?: number;
  comparison_metrics?: Record<string, any>;
  findings?: Record<string, any>;
  reviewer_notes?: string;
  verified_at?: string;
  before_evidence_id?: string | null;
  before_media_id?: string | null;
  after_evidence_id?: string | null;
  processing_job_id?: string | null;
  model_name?: string | null;
  model_version?: string | null;
  algorithm_version?: string | null;
  reviewed_verification_id?: string | null;
  previous_result?: string | null;
  review_decision?: "CONFIRMED" | "REJECTED" | "UNRESOLVED" | null;
  error_code?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface RecurrenceRecord {
  id: string;
  organization_id: string;
  historical_damage_id: string;
  new_damage_id: string;
  related_maintenance_job_id?: string;
  related_repair_verification_id?: string;
  road_segment_id?: string;
  spatial_distance_meters?: number;
  temporal_distance_days?: number;
  similarity_score?: number;
  recurrence_score?: number;
  detection_method_version?: string;
  status: "POTENTIAL" | "CONFIRMED" | "DISMISSED" | "FALSE_POSITIVE";
  evaluated_at: string;
  reviewed_by_user_id?: string;
  reviewed_at?: string;
  review_notes?: string;
  created_at: string;
  updated_at: string;
  historical_damage?: {
    id: string;
    damage_type: string;
    severity: string;
    status: string;
    latitude?: number;
    longitude?: number;
    detected_at?: string;
  };
  new_damage?: {
    id: string;
    damage_type: string;
    severity: string;
    status: string;
    latitude?: number;
    longitude?: number;
    detected_at?: string;
  };
  road_name?: string;
  segment_name?: string;
}

export interface SegmentTimelineEvent {
  event_type: "DAMAGE_DETECTED" | "MAINTENANCE_CREATED" | "MAINTENANCE_COMPLETED" | "REPAIR_VERIFIED" | "RECURRENCE_DETECTED";
  timestamp: string;
  entity_id: string;
  title: string;
  description?: string;
  severity?: string;
  status?: string;
  metadata?: Record<string, any>;
}

export interface SegmentHistoricalTimelineResponse {
  road_segment_id: string;
  road_name?: string;
  segment_number?: number;
  total_events: number;
  events: SegmentTimelineEvent[];
}

export interface DashboardSummaryData {
  total_roads: number;
  total_segments: number;
  active_inspections: number;
  open_damages: number;
  high_severity_damages: number;
  critical_damages: number;
  maintenance_open: number;
  maintenance_in_progress: number;
  verification_pending: number;
  verified_repairs: number;
  recurrence_count: number;
  average_road_health?: number | null;
  pending_review_damages?: number;
  maintenance_by_status?: Record<string, number>;
  escalated_recurrences?: number;
  roads_with_health?: number;
  road_health_status_counts?: Record<string, number>;
  repair_verification_results?: Record<string, number>;
}

export interface HealthPoint {
  id: string;
  road_segment_id: string | null;
  health_score: number | null;
  health_status: string;
  calculation_version: string;
  calculated_at: string;
  score_deductions: Record<string, number>;
  recurrence_count?: number | null;
  total_damages?: number | null;
  traffic?: { traffic_volume_class: string | null; traffic_known: boolean; traffic_multiplier: number } | null;
}

export interface TimelineEvent {
  type: "INSPECTION" | "DAMAGE" | "DAMAGE_REVIEW" | "HEALTH" | "PRIORITY" | "MAINTENANCE" | "REPAIR_EVIDENCE" | "VERIFICATION" | "RECURRENCE";
  at: string;
  title: string;
  entity_id: string;
  data: Record<string, any>;
}

export interface RoadIntelligence {
  road: {
    id: string;
    name: string;
    road_code?: string | null;
    road_type?: string | null;
    traffic_volume_class?: string | null;
    traffic_aadt?: number | null;
    traffic_data_source?: string | null;
  };
  segments: { id: string; segment_number: number; name?: string | null; length_meters?: number | null; latest_health?: HealthPoint | null }[];
  road_health_history: HealthPoint[];
  segment_health_history: Record<string, HealthPoint[]>;
  summary: {
    active_damages: number;
    pending_review_damages: number;
    repaired_damages: number;
    active_by_severity: Record<string, number>;
    maintenance_by_status: Record<string, number>;
    active_recurrences: number;
    inspections: number;
  };
  timeline: TimelineEvent[];
}

export interface RecurrenceOverviewItem {
  id: string;
  status: string;
  escalation_level: string | null;
  escalation_reasons: { code: string; level: string; detail: string }[];
  historical_damage_id: string;
  new_damage_id: string;
  damage_type: string | null;
  new_severity: string | null;
  location: { latitude: number; longitude: number } | null;
  road_id: string | null;
  road_name: string | null;
  segment_number: number | null;
  distance_meters: number | null;
  days_since_repair: number | null;
  recurrence_number_at_location: number | null;
  previous_repair_job_id: string | null;
  previous_repair_job_title: string | null;
  previous_verification_result: string | null;
  previous_verification_source: string | null;
  detection_method_version: string | null;
  evaluated_at: string;
}

export interface VerificationOverviewItem {
  verification_id: string;
  maintenance_job_id: string;
  job_title: string | null;
  job_status: string | null;
  status: string;
  automated_result: string | null;
  reason_code: string | null;
  before_detection_count: number | null;
  after_detection_count: number | null;
  residual_detection_count: number | null;
  model_name: string | null;
  model_version: string | null;
  algorithm_version: string | null;
  analysed_at: string | null;
  requested_at: string;
  review_decision: string | null;
  final_result: string | null;
  reviewed_at: string | null;
  reviewer_user_id: string | null;
  reviewer_notes: string | null;
}

export interface PriorityOverviewItem {
  rank: number;
  job_id: string;
  title: string;
  status: string;
  priority_level: string;
  priority_score: number | null;
  mode: string | null;
  version: string | null;
  components: Record<string, number> | null;
  inputs: Record<string, any> | null;
  calculated_at: string | null;
  road_id: string | null;
  road_name: string | null;
  segment_number: number | null;
  linked_damage_count: number;
  max_severity: string | null;
  segment_health: HealthPoint | null;
  active_recurrences: number;
  escalation_level: string | null;
  deterioration_estimate: {
    predicted_risk: number | null;
    risk_band: string | null;
    horizon_days: number;
    method: string;
    generated_at: string;
  } | null;
  created_at: string;
}

export interface DeteriorationEstimate {
  id: string;
  road_segment_id: string;
  model_name: string;
  model_version: string;
  prediction_horizon_days: number;
  predicted_risk: number | null;
  predicted_value: number | null;
  confidence: number | null;
  features: Record<string, any>;
  generated_at: string;
  status: string;
  estimation_method?: string | null;
  disclaimer?: string;
}

export interface ContractorHistoryItem {
  assignee_type: "USER" | "CONTRACTOR";
  assignee_id: string;
  name: string | null;
  assigned_jobs: number;
  completed_jobs: number;
  verified_jobs: number;
  rejected_jobs: number;
  open_jobs: number;
  verification_outcomes: Record<string, number>;
  recurrences_after_repair: number;
  jobs: { id: string; title: string; status: string; completed_at: string | null }[];
}

export interface DamageTrendPoint {
  date: string;
  count: number;
  severity_breakdown?: Record<string, number>;
}

export interface DamageTrendsData {
  series: DamageTrendPoint[];
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  total_damages: number;
}

export interface CriticalSegmentSummary {
  segment_id: string;
  road_id: string;
  road_name: string;
  segment_number: number;
  current_health_score?: number | null;
  classification: string;
  open_damages_count: number;
}

export interface RoadHealthAnalyticsData {
  average_health?: number | null;
  health_distribution: Record<string, number>;
  critical_segments: CriticalSegmentSummary[];
  total_segments_evaluated: number;
  segments_insufficient_data?: number;
}

export interface MaintenanceAnalyticsData {
  open_jobs: number;
  in_progress_jobs: number;
  completed_jobs: number;
  verified_repairs: number;
  rejected_repairs: number;
  verification_rate: number;
  avg_completion_time_days?: number | null;
  recurrence_after_repair_count: number;
}

export interface InspectionAnalyticsData {
  total_inspections: number;
  by_status: Record<string, number>;
  total_media_captured: number;
  ai_processed_count: number;
}

export interface GeneratedReport {
  id: string;
  organization_id: string;
  requested_by_user_id: string;
  report_type: string;
  status: string;
  parameters: Record<string, any>;
  storage_path?: string | null;
  generated_at?: string | null;
  expires_at?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface ReportDownloadUrlResponse {
  report_id: string;
  download_url: string;
  expires_in_seconds: number;
}

export interface AuditLogItem {
  id: string;
  organization_id?: string | null;
  actor_user_id?: string | null;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  request_id?: string | null;
  before_data?: Record<string, any> | null;
  after_data?: Record<string, any> | null;
  metadata?: Record<string, any> | null;
  ip_address?: string | null;
  user_agent?: string | null;
  created_at: string;
}

// GIS Map (GET /map/damages, /map/roads, /map/segments)
export interface GeoJSONLineGeometry {
  type: "LineString" | "MultiLineString";
  coordinates: number[][] | number[][][];
}

export interface MapDamageFeature {
  id: string;
  damage_type: string;
  severity: string;
  status: string;
  confidence?: number | null;
  detection_method?: string | null;
  score_type?: string | null;
  latitude: number;
  longitude: number;
  road_id?: string | null;
  road_name?: string | null;
  road_segment_id?: string | null;
  segment_number?: number | null;
  segment_name?: string | null;
  detected_at?: string | null;
  observation_count?: number;
  maintenance_status?: string | null;
  active_recurrences?: number;
  escalation_level?: string | null;
  segment_health_score?: number | null;
  segment_health_status?: string | null;
}

export interface MapRoadFeature {
  id: string;
  name: string;
  road_code?: string | null;
  road_type?: string | null;
  geometry: GeoJSONLineGeometry;
  length_km?: number | null;
  is_active: boolean;
  segment_count: number;
  damage_count: number;
  critical_damage_count: number;
  health_score?: number | null;
  health_status?: string | null;
}

export interface MapSegmentFeature {
  id: string;
  road_id: string;
  road_name?: string | null;
  segment_number: number;
  name?: string | null;
  start_chainage?: number | null;
  end_chainage?: number | null;
  length_meters?: number | null;
  geometry: GeoJSONLineGeometry;
  damage_count: number;
  critical_damage_count: number;
  health_score?: number | null;
  health_status?: string | null;
  priority_score?: number | null;
}
