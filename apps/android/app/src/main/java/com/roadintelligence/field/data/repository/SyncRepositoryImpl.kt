package com.roadintelligence.field.data.repository

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import com.roadintelligence.field.data.local.dao.SyncQueueDao
import com.roadintelligence.field.domain.model.SyncQueueItem
import com.roadintelligence.field.domain.model.SyncStatus
import com.roadintelligence.field.domain.repository.SyncRepository
import com.roadintelligence.field.sync.InspectionSyncWorker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import java.util.UUID

class SyncRepositoryImpl(
    private val context: Context,
    private val syncQueueDao: SyncQueueDao
) : SyncRepository {

    override fun getSyncQueue(): Flow<List<SyncQueueItem>> {
        return syncQueueDao.getQueueItems().map { list ->
            list.map {
                SyncQueueItem(
                    id = it.id,
                    inspectionLocalId = it.inspectionLocalId,
                    operation = it.operation,
                    status = try { SyncStatus.valueOf(it.status) } catch (_: Exception) { SyncStatus.QUEUED },
                    attemptCount = it.attemptCount,
                    nextAttemptAt = it.nextAttemptAt,
                    lastError = it.lastError,
                    createdAt = it.createdAt,
                    updatedAt = it.updatedAt
                )
            }
        }
    }

    override suspend fun enqueueSync(inspectionLocalId: String): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val existing = syncQueueDao.getItemByInspectionId(inspectionLocalId)
            if (existing == null) {
                val item = com.roadintelligence.field.data.local.entity.SyncQueueEntity(
                    id = UUID.randomUUID().toString(),
                    inspectionLocalId = inspectionLocalId,
                    operation = "SYNC_INSPECTION",
                    status = SyncStatus.QUEUED.name,
                    attemptCount = 0,
                    nextAttemptAt = System.currentTimeMillis()
                )
                syncQueueDao.insertQueueItem(item)
            }
            triggerWorkManagerSync()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun triggerManualSync(): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            triggerWorkManagerSync()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun retryFailedItem(queueItemId: String): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            syncQueueDao.updateStatus(queueItemId, SyncStatus.QUEUED.name, null)
            triggerWorkManagerSync()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun clearCompleted(): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            syncQueueDao.clearCompleted()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private fun triggerWorkManagerSync() {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val syncRequest = OneTimeWorkRequestBuilder<InspectionSyncWorker>()
            .setConstraints(constraints)
            .build()

        WorkManager.getInstance(context).enqueueUniqueWork(
            InspectionSyncWorker.WORK_NAME,
            ExistingWorkPolicy.REPLACE,
            syncRequest
        )
    }
}
