package com.roadintelligence.field.data.remote.dto

import com.google.gson.annotations.SerializedName

// Common Envelopes
data class ApiEnvelope<T>(
    @SerializedName("success") val success: Boolean,
    @SerializedName("data") val data: T?,
    @SerializedName("error") val error: ApiErrorDto? = null
)

data class PaginatedEnvelope<T>(
    @SerializedName("success") val success: Boolean,
    @SerializedName("data") val data: List<T>?,
    @SerializedName("meta") val meta: PaginationMetaDto? = null,
    @SerializedName("error") val error: ApiErrorDto? = null
)

data class PaginationMetaDto(
    @SerializedName("page") val page: Int,
    @SerializedName("page_size") val pageSize: Int,
    @SerializedName("total_count") val totalCount: Int,
    @SerializedName("total_pages") val totalPages: Int
)

data class ApiErrorDto(
    @SerializedName("code") val code: String?,
    @SerializedName("message") val message: String?,
    @SerializedName("details") val details: Any? = null
)

// Auth
data class LoginRequestDto(
    @SerializedName("email") val email: String,
    @SerializedName("password") val password: String
)

data class LoginResponseDataDto(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String,
    @SerializedName("token_type") val tokenType: String,
    @SerializedName("expires_in") val expiresIn: Int
)

// GET /api/v1/auth/me (login returns tokens only)
data class CurrentUserDto(
    @SerializedName("id") val id: String,
    @SerializedName("email") val email: String,
    @SerializedName("full_name") val fullName: String,
    @SerializedName("is_active") val isActive: Boolean = true,
    @SerializedName("organizations") val organizations: List<OrgMembershipDto> = emptyList()
)

data class OrgMembershipDto(
    @SerializedName("organization_id") val organizationId: String,
    @SerializedName("organization_name") val organizationName: String,
    @SerializedName("role_code") val roleCode: String,
    @SerializedName("status") val status: String? = null
)

// Roads & Segments
data class RoadDto(
    @SerializedName("id") val id: String,
    @SerializedName("name") val name: String,
    @SerializedName("road_code") val roadCode: String?,
    @SerializedName("surface_type") val surfaceType: String?,
    @SerializedName("segment_count") val segmentCount: Int? = 0
)

data class RoadSegmentDto(
    @SerializedName("id") val id: String,
    @SerializedName("road_id") val roadId: String,
    @SerializedName("segment_number") val segmentNumber: Int,
    @SerializedName("length_meters") val lengthMeters: Double?,
    @SerializedName("surface_type") val surfaceType: String?
)

// Inspections
data class LocationDto(
    @SerializedName("latitude") val latitude: Double,
    @SerializedName("longitude") val longitude: Double,
    @SerializedName("accuracy_m") val accuracyM: Float? = null
)

data class InspectionCreateDto(
    @SerializedName("road_id") val roadId: String?,
    @SerializedName("road_segment_id") val roadSegmentId: String?,
    @SerializedName("client_id") val clientId: String,
    @SerializedName("location") val location: LocationDto?,
    @SerializedName("notes") val notes: String?,
    @SerializedName("captured_at") val capturedAt: String? = null
)

data class InspectionResponseDto(
    @SerializedName("id") val id: String,
    @SerializedName("status") val status: String,
    @SerializedName("road_id") val roadId: String?,
    @SerializedName("road_name") val roadName: String?,
    @SerializedName("road_segment_id") val roadSegmentId: String?,
    @SerializedName("segment_number") val segmentNumber: Int?,
    @SerializedName("inspector_name") val inspectorName: String?,
    @SerializedName("client_inspection_id") val clientInspectionId: String?,
    @SerializedName("notes") val notes: String?,
    @SerializedName("created_at") val createdAt: String?
)

// Media upload flow (POST /inspections/{id}/media/upload-url -> PUT upload_url -> POST /media/complete)
data class UploadUrlRequestDto(
    @SerializedName("filename") val filename: String,
    @SerializedName("content_type") val contentType: String,
    @SerializedName("size_bytes") val sizeBytes: Long,
    @SerializedName("checksum") val checksum: String? = null
)

data class UploadUrlResponseDto(
    @SerializedName("upload_url") val uploadUrl: String,
    @SerializedName("storage_path") val storagePath: String,
    @SerializedName("storage_bucket") val storageBucket: String,
    @SerializedName("expires_in") val expiresIn: Int,
    @SerializedName("upload_method") val uploadMethod: String = "PUT",
    @SerializedName("upload_headers") val uploadHeaders: Map<String, String>? = null
)

data class MediaCompleteDto(
    @SerializedName("storage_path") val storagePath: String,
    @SerializedName("storage_bucket") val storageBucket: String,
    @SerializedName("media_type") val mediaType: String,
    @SerializedName("mime_type") val mimeType: String,
    @SerializedName("size_bytes") val sizeBytes: Long,
    @SerializedName("original_filename") val originalFilename: String? = null,
    @SerializedName("checksum") val checksum: String? = null,
    @SerializedName("captured_at") val capturedAt: String? = null,
    @SerializedName("location") val location: LocationDto? = null
)

data class InspectionMediaDto(
    @SerializedName("id") val id: String,
    @SerializedName("inspection_id") val inspectionId: String,
    @SerializedName("storage_path") val storagePath: String,
    @SerializedName("upload_status") val uploadStatus: String
)
