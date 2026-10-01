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
    @SerializedName("pagination") val pagination: PaginationMetaDto? = null,
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
    @SerializedName("expires_in") val expiresIn: Int,
    @SerializedName("user") val user: UserDto
)

data class UserDto(
    @SerializedName("id") val id: String,
    @SerializedName("email") val email: String,
    @SerializedName("full_name") val fullName: String,
    @SerializedName("role") val role: String?,
    @SerializedName("organizations") val organizations: List<OrgMembershipDto> = emptyList()
)

data class OrgMembershipDto(
    @SerializedName("organization_id") val organizationId: String,
    @SerializedName("organization_name") val organizationName: String,
    @SerializedName("role") val role: String
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
    @SerializedName("length_m") val lengthMeters: Double?,
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

// Media upload flow
data class UploadUrlRequestDto(
    @SerializedName("media_type") val mediaType: String,
    @SerializedName("filename") val filename: String,
    @SerializedName("mime_type") val mimeType: String,
    @SerializedName("file_size_bytes") val fileSizeBytes: Long
)

data class UploadUrlResponseDto(
    @SerializedName("media_id") val mediaId: String,
    @SerializedName("upload_url") val uploadUrl: String,
    @SerializedName("storage_path") val storagePath: String,
    @SerializedName("expires_in") val expiresIn: Int
)

data class MediaCompleteDto(
    @SerializedName("media_id") val mediaId: String,
    @SerializedName("checksum") val checksum: String? = null
)

data class SubmitInspectionResponseDto(
    @SerializedName("inspection_id") val inspectionId: String,
    @SerializedName("status") val status: String,
    @SerializedName("job_id") val jobId: String?
)
