package com.roadintelligence.field.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.roadintelligence.field.data.local.AppDatabase
import com.roadintelligence.field.data.local.SecureSessionManager
import com.roadintelligence.field.data.remote.NetworkClient
import com.roadintelligence.field.data.remote.dto.InspectionCreateDto
import com.roadintelligence.field.data.remote.dto.LocationDto
import com.roadintelligence.field.data.remote.dto.MediaCompleteDto
import com.roadintelligence.field.data.remote.dto.UploadUrlRequestDto
import com.roadintelligence.field.domain.model.SyncStatus
import com.roadintelligence.field.domain.model.UploadStatus
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

class InspectionSyncWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    companion object {
        const val WORK_NAME = "inspection_sync_work"
    }

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val database = AppDatabase.getInstance(applicationContext)
        val sessionManager = SecureSessionManager(applicationContext)
        val apiService = NetworkClient.getApiService(sessionManager)

        if (!sessionManager.isLoggedIn()) {
            return@withContext Result.failure()
        }

        val inspectionDao = database.inspectionDao()
        val mediaDao = database.inspectionMediaDao()
        val syncQueueDao = database.syncQueueDao()

        val pendingItems = syncQueueDao.getPendingQueueItems()
        if (pendingItems.isEmpty()) {
            return@withContext Result.success()
        }

        var anyFailed = false

        for (item in pendingItems) {
            val localInspection = inspectionDao.getInspectionByIdSync(item.inspectionLocalId)
            if (localInspection == null) {
                syncQueueDao.deleteItem(item.id)
                continue
            }

            try {
                // Update status to UPLOADING
                syncQueueDao.updateStatus(item.id, SyncStatus.UPLOADING.name, null)
                inspectionDao.updateSyncStatus(localInspection.localId, SyncStatus.UPLOADING.name, null)

                // 1. Create or retrieve server inspection
                var serverId = localInspection.serverId
                if (serverId.isNullOrEmpty()) {
                    val createPayload = InspectionCreateDto(
                        roadId = localInspection.roadId,
                        roadSegmentId = localInspection.segmentId,
                        clientId = localInspection.clientId,
                        location = if (localInspection.latitude != null && localInspection.longitude != null) {
                            LocationDto(
                                latitude = localInspection.latitude,
                                longitude = localInspection.longitude,
                                accuracyM = localInspection.accuracyMeters
                            )
                        } else null,
                        notes = localInspection.notes
                    )

                    val createResponse = apiService.createInspection(createPayload)
                    if (createResponse.isSuccessful && createResponse.body()?.data != null) {
                        val responseData = createResponse.body()!!.data!!
                        serverId = responseData.id
                        inspectionDao.markUploaded(localInspection.localId, serverId, responseData.status)
                    } else {
                        throw Exception("Failed to create inspection on server: ${createResponse.message()}")
                    }
                }

                // 2. Upload pending media files
                val mediaList = mediaDao.getMediaForInspection(localInspection.localId)
                for (media in mediaList) {
                    if (media.uploadStatus == UploadStatus.COMPLETED.name && !media.serverId.isNullOrEmpty()) {
                        continue
                    }

                    val file = File(media.localFilePath)
                    if (!file.exists() || file.length() == 0L) {
                        mediaDao.updateMediaStatus(media.localId, UploadStatus.FAILED.name, null, "File not found or empty")
                        continue
                    }

                    mediaDao.updateMediaStatus(media.localId, UploadStatus.UPLOADING.name, null, null)

                    // Request upload URL
                    val uploadUrlResponse = apiService.requestMediaUploadUrl(
                        inspectionId = serverId,
                        request = UploadUrlRequestDto(
                            mediaType = media.mediaType,
                            filename = file.name,
                            mimeType = media.mimeType,
                            fileSizeBytes = file.length()
                        )
                    )

                    if (!uploadUrlResponse.isSuccessful || uploadUrlResponse.body()?.data == null) {
                        throw Exception("Failed to get upload URL: ${uploadUrlResponse.message()}")
                    }

                    val uploadData = uploadUrlResponse.body()!!.data!!

                    // Upload binary to signed URL
                    val requestBody = file.asRequestBody(media.mimeType.toMediaTypeOrNull())
                    val binaryUploadResponse = apiService.uploadToSignedUrl(
                        uploadUrl = uploadData.uploadUrl,
                        contentType = media.mimeType,
                        fileBytes = requestBody
                    )

                    if (!binaryUploadResponse.isSuccessful) {
                        throw Exception("Binary upload failed: ${binaryUploadResponse.message()}")
                    }

                    // Complete media upload handshake
                    val completeResponse = apiService.completeMediaUpload(
                        inspectionId = serverId,
                        request = MediaCompleteDto(mediaId = uploadData.mediaId)
                    )

                    if (!completeResponse.isSuccessful) {
                        throw Exception("Media completion failed: ${completeResponse.message()}")
                    }

                    mediaDao.updateMediaStatus(media.localId, UploadStatus.COMPLETED.name, uploadData.mediaId, null)
                }

                // 3. Submit inspection for AI processing
                val submitResponse = apiService.submitInspection(serverId)
                val finalStatus = if (submitResponse.isSuccessful) {
                    submitResponse.body()?.data?.status ?: "SUBMITTED"
                } else {
                    "SUBMITTED"
                }

                // 4. Mark inspection and sync queue item completed
                inspectionDao.updateSyncStatus(localInspection.localId, SyncStatus.COMPLETED.name, null)
                inspectionDao.markUploaded(localInspection.localId, serverId, finalStatus)
                syncQueueDao.updateStatus(item.id, SyncStatus.COMPLETED.name, null)

            } catch (e: Exception) {
                anyFailed = true
                val errorMsg = e.message ?: "Sync error"
                syncQueueDao.updateStatus(item.id, SyncStatus.UPLOAD_FAILED.name, errorMsg)
                inspectionDao.updateSyncStatus(localInspection.localId, SyncStatus.UPLOAD_FAILED.name, errorMsg)
            }
        }

        if (anyFailed) {
            Result.retry()
        } else {
            Result.success()
        }
    }
}
