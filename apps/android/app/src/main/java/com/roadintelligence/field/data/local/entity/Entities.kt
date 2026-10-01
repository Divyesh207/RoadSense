package com.roadintelligence.field.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "inspections")
data class InspectionEntity(
    @PrimaryKey
    val localId: String,
    val serverId: String? = null,
    val clientId: String,
    val organizationId: String,
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
    val syncStatus: String = "LOCAL_DRAFT",
    val lastSyncError: String? = null,
    val createdAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "inspection_media")
data class InspectionMediaEntity(
    @PrimaryKey
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
    val uploadStatus: String = "PENDING",
    val uploadAttempts: Int = 0,
    val lastError: String? = null
)

@Entity(tableName = "roads")
data class RoadEntity(
    @PrimaryKey
    val id: String,
    val organizationId: String,
    val name: String,
    val roadCode: String?,
    val surfaceType: String = "ASPHALT",
    val cachedAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "road_segments")
data class RoadSegmentEntity(
    @PrimaryKey
    val id: String,
    val roadId: String,
    val organizationId: String,
    val segmentNumber: Int,
    val lengthMeters: Double?,
    val surfaceType: String?,
    val cachedAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "sync_queue")
data class SyncQueueEntity(
    @PrimaryKey
    val id: String,
    val inspectionLocalId: String,
    val operation: String = "SYNC_INSPECTION",
    val status: String = "QUEUED",
    val attemptCount: Int = 0,
    val nextAttemptAt: Long = 0L,
    val lastError: String? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
)
