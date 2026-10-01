package com.roadintelligence.field.domain.model

data class UserSession(
    val userId: String,
    val email: String,
    val fullName: String,
    val role: String,
    val organizationId: String,
    val organizationName: String,
    val accessToken: String,
    val refreshToken: String
)

data class LocationData(
    val latitude: Double,
    val longitude: Double,
    val accuracyMeters: Float? = null,
    val timestamp: Long = System.currentTimeMillis()
)

data class Road(
    val id: String,
    val name: String,
    val roadCode: String? = null,
    val surfaceType: String = "ASPHALT",
    val segmentCount: Int = 0
)

data class RoadSegment(
    val id: String,
    val roadId: String,
    val segmentNumber: Int,
    val lengthMeters: Double? = null,
    val surfaceType: String? = null
)

data class Inspection(
    val localId: String,
    val serverId: String? = null,
    val clientId: String,
    val roadId: String?,
    val roadName: String?,
    val segmentId: String?,
    val segmentNumber: Int?,
    val inspectorId: String,
    val status: String = "DRAFT",
    val latitude: Double?,
    val longitude: Double?,
    val accuracyMeters: Float?,
    val capturedAt: Long = System.currentTimeMillis(),
    val notes: String? = null,
    val syncStatus: SyncStatus = SyncStatus.LOCAL_DRAFT,
    val lastSyncError: String? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val mediaList: List<InspectionMedia> = emptyList()
)

data class InspectionMedia(
    val localId: String,
    val serverId: String? = null,
    val inspectionLocalId: String,
    val localFilePath: String,
    val mediaType: String = "IMAGE",
    val mimeType: String = "image/jpeg",
    val fileSizeBytes: Long = 0L,
    val capturedAt: Long = System.currentTimeMillis(),
    val latitude: Double? = null,
    val longitude: Double? = null,
    val uploadStatus: UploadStatus = UploadStatus.PENDING,
    val uploadAttempts: Int = 0,
    val lastError: String? = null
)

data class SyncQueueItem(
    val id: String,
    val inspectionLocalId: String,
    val operation: String = "SYNC_INSPECTION",
    val status: SyncStatus = SyncStatus.QUEUED,
    val attemptCount: Int = 0,
    val nextAttemptAt: Long = 0L,
    val lastError: String? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
)

enum class SyncStatus {
    LOCAL_DRAFT,
    QUEUED,
    UPLOADING,
    UPLOADED,
    PROCESSING,
    COMPLETED,
    UPLOAD_FAILED
}

enum class UploadStatus {
    PENDING,
    UPLOADING,
    COMPLETED,
    FAILED
}
