package com.roadintelligence.field.data.repository

import com.roadintelligence.field.data.local.SecureSessionManager
import com.roadintelligence.field.data.local.dao.InspectionDao
import com.roadintelligence.field.data.local.dao.InspectionMediaDao
import com.roadintelligence.field.data.local.dao.SyncQueueDao
import com.roadintelligence.field.data.local.entity.InspectionEntity
import com.roadintelligence.field.data.local.entity.InspectionMediaEntity
import com.roadintelligence.field.data.local.entity.SyncQueueEntity
import com.roadintelligence.field.domain.model.Inspection
import com.roadintelligence.field.domain.model.InspectionMedia
import com.roadintelligence.field.domain.model.SyncStatus
import com.roadintelligence.field.domain.model.UploadStatus
import com.roadintelligence.field.domain.repository.InspectionRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import java.util.UUID

class InspectionRepositoryImpl(
    private val inspectionDao: InspectionDao,
    private val mediaDao: InspectionMediaDao,
    private val syncQueueDao: SyncQueueDao,
    private val sessionManager: SecureSessionManager
) : InspectionRepository {

    override fun getAllInspections(): Flow<List<Inspection>> {
        return inspectionDao.getAllInspections().map { list ->
            list.map { entity ->
                mapToDomain(entity)
            }
        }
    }

    override fun getInspectionById(localId: String): Flow<Inspection?> {
        return inspectionDao.getInspectionById(localId).map { entity ->
            entity?.let {
                val mediaEntities = mediaDao.getMediaForInspection(it.localId)
                mapToDomain(it, mediaEntities)
            }
        }
    }

    override suspend fun createLocalDraft(inspection: Inspection): Result<String> = withContext(Dispatchers.IO) {
        try {
            val orgId = sessionManager.getOrganizationId() ?: ""
            val entity = InspectionEntity(
                localId = inspection.localId,
                serverId = inspection.serverId,
                clientId = inspection.clientId,
                organizationId = orgId,
                roadId = inspection.roadId,
                roadName = inspection.roadName,
                segmentId = inspection.segmentId,
                segmentNumber = inspection.segmentNumber,
                inspectorId = inspection.inspectorId,
                status = inspection.status,
                latitude = inspection.latitude,
                longitude = inspection.longitude,
                accuracyMeters = inspection.accuracyMeters,
                capturedAt = inspection.capturedAt,
                notes = inspection.notes,
                syncStatus = SyncStatus.LOCAL_DRAFT.name,
                lastSyncError = null,
                createdAt = inspection.createdAt
            )
            inspectionDao.insertInspection(entity)
            Result.success(inspection.localId)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun updateInspection(inspection: Inspection): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val orgId = sessionManager.getOrganizationId() ?: ""
            val entity = InspectionEntity(
                localId = inspection.localId,
                serverId = inspection.serverId,
                clientId = inspection.clientId,
                organizationId = orgId,
                roadId = inspection.roadId,
                roadName = inspection.roadName,
                segmentId = inspection.segmentId,
                segmentNumber = inspection.segmentNumber,
                inspectorId = inspection.inspectorId,
                status = inspection.status,
                latitude = inspection.latitude,
                longitude = inspection.longitude,
                accuracyMeters = inspection.accuracyMeters,
                capturedAt = inspection.capturedAt,
                notes = inspection.notes,
                syncStatus = inspection.syncStatus.name,
                lastSyncError = inspection.lastSyncError,
                createdAt = inspection.createdAt
            )
            inspectionDao.updateInspection(entity)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun addMediaToInspection(media: InspectionMedia): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val entity = InspectionMediaEntity(
                localId = media.localId,
                serverId = media.serverId,
                inspectionLocalId = media.inspectionLocalId,
                localFilePath = media.localFilePath,
                mediaType = media.mediaType,
                mimeType = media.mimeType,
                fileSizeBytes = media.fileSizeBytes,
                capturedAt = media.capturedAt,
                latitude = media.latitude,
                longitude = media.longitude,
                uploadStatus = media.uploadStatus.name,
                uploadAttempts = media.uploadAttempts,
                lastError = media.lastError
            )
            mediaDao.insertMedia(entity)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun getMediaForInspection(localInspectionId: String): List<InspectionMedia> = withContext(Dispatchers.IO) {
        val list = mediaDao.getMediaForInspection(localInspectionId)
        list.map { mapMediaToDomain(it) }
    }

    override suspend fun queueForUpload(localId: String): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            inspectionDao.updateSyncStatus(localId, SyncStatus.QUEUED.name, null)
            // One queue entry per inspection: a retry resets the existing entry instead of adding
            // another, so the worker never uploads the same inspection several times in one run.
            val now = System.currentTimeMillis()
            val existing = syncQueueDao.getItemByInspectionId(localId)
            val queueItem = existing?.copy(
                status = SyncStatus.QUEUED.name,
                attemptCount = 0,
                nextAttemptAt = now,
                lastError = null,
                updatedAt = now
            ) ?: SyncQueueEntity(
                id = UUID.randomUUID().toString(),
                inspectionLocalId = localId,
                operation = "SYNC_INSPECTION",
                status = SyncStatus.QUEUED.name,
                attemptCount = 0,
                nextAttemptAt = now
            )
            syncQueueDao.insertQueueItem(queueItem)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun deleteDraft(localId: String): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            inspectionDao.deleteInspection(localId)
            mediaDao.deleteMedia(localId)
            syncQueueDao.deleteItemsForInspection(localId)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private fun mapToDomain(
        entity: InspectionEntity,
        mediaEntities: List<InspectionMediaEntity> = emptyList()
    ): Inspection {
        return Inspection(
            localId = entity.localId,
            serverId = entity.serverId,
            clientId = entity.clientId,
            roadId = entity.roadId,
            roadName = entity.roadName,
            segmentId = entity.segmentId,
            segmentNumber = entity.segmentNumber,
            inspectorId = entity.inspectorId,
            status = entity.status,
            latitude = entity.latitude,
            longitude = entity.longitude,
            accuracyMeters = entity.accuracyMeters,
            capturedAt = entity.capturedAt,
            notes = entity.notes,
            syncStatus = try { SyncStatus.valueOf(entity.syncStatus) } catch (_: Exception) { SyncStatus.LOCAL_DRAFT },
            lastSyncError = entity.lastSyncError,
            createdAt = entity.createdAt,
            mediaList = mediaEntities.map { mapMediaToDomain(it) }
        )
    }

    private fun mapMediaToDomain(entity: InspectionMediaEntity): InspectionMedia {
        return InspectionMedia(
            localId = entity.localId,
            serverId = entity.serverId,
            inspectionLocalId = entity.inspectionLocalId,
            localFilePath = entity.localFilePath,
            mediaType = entity.mediaType,
            mimeType = entity.mimeType,
            fileSizeBytes = entity.fileSizeBytes,
            capturedAt = entity.capturedAt,
            latitude = entity.latitude,
            longitude = entity.longitude,
            uploadStatus = try { UploadStatus.valueOf(entity.uploadStatus) } catch (_: Exception) { UploadStatus.PENDING },
            uploadAttempts = entity.uploadAttempts,
            lastError = entity.lastError
        )
    }
}
