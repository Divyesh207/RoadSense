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
import com.google.gson.JsonParser
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.asRequestBody
import retrofit2.Response
import java.io.File
import java.time.Instant

class InspectionSyncWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    private fun <T> formatError(response: Response<T>, defaultPrefix: String): String {
        return try {
            val errorJson = response.errorBody()?.string()
            if (!errorJson.isNullOrBlank()) {
                val jsonObject = JsonParser.parseString(errorJson).asJsonObject
                val errorObj = jsonObject.getAsJsonObject("error")
                val message = errorObj?.get("message")?.asString
                if (!message.isNullOrBlank()) {
                    return "$defaultPrefix: $message"
                }
            }
            val msg = response.message()
            if (!msg.isNullOrBlank()) "$defaultPrefix: $msg" else "$defaultPrefix: HTTP ${response.code()}"
        } catch (_: Exception) {
            val msg = response.message()
            if (!msg.isNullOrBlank()) "$defaultPrefix: $msg" else "$defaultPrefix: HTTP ${response.code()}"
        }
    }

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
        val seen = mutableSetOf<String>()

        for (item in pendingItems) {
            // Older app versions could queue the same inspection more than once; keep the first entry.
            if (!seen.add(item.inspectionLocalId)) {
                syncQueueDao.deleteItem(item.id)
                continue
            }
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
                        throw Exception(formatError(createResponse, "Failed to create inspection on server"))
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

                    // Request a signed upload URL
                    val uploadUrlResponse = apiService.requestMediaUploadUrl(
                        inspectionId = serverId,
                        request = UploadUrlRequestDto(
                            filename = file.name,
                            contentType = media.mimeType,
                            sizeBytes = file.length()
                        )
                    )

                    if (!uploadUrlResponse.isSuccessful || uploadUrlResponse.body()?.data == null) {
                        throw Exception(formatError(uploadUrlResponse, "Failed to get upload URL"))
                    }

                    val uploadData = uploadUrlResponse.body()!!.data!!

                    // Upload binary to the signed storage URL
                    val requestBody = file.asRequestBody(media.mimeType.toMediaTypeOrNull())
                    val binaryUploadResponse = apiService.uploadToSignedUrl(
                        uploadUrl = NetworkClient.resolveUploadUrl(uploadData.uploadUrl),
                        contentType = media.mimeType,
                        fileBytes = requestBody
                    )

                    if (!binaryUploadResponse.isSuccessful) {
                        throw Exception(formatError(binaryUploadResponse, "Binary upload failed"))
                    }

                    // Register the uploaded object as inspection media
                    val completeResponse = apiService.completeMediaUpload(
                        inspectionId = serverId,
                        request = MediaCompleteDto(
                            storagePath = uploadData.storagePath,
                            storageBucket = uploadData.storageBucket,
                            mediaType = media.mediaType,
                            mimeType = media.mimeType,
                            sizeBytes = file.length(),
                            originalFilename = file.name,
                            capturedAt = Instant.ofEpochMilli(media.capturedAt).toString(),
                            location = if (media.latitude != null && media.longitude != null) {
                                LocationDto(latitude = media.latitude, longitude = media.longitude)
                            } else null
                        )
                    )

                    val mediaServerId = completeResponse.body()?.data?.id
                    if (!completeResponse.isSuccessful || mediaServerId == null) {
                        throw Exception(formatError(completeResponse, "Media completion failed"))
                    }

                    mediaDao.updateMediaStatus(media.localId, UploadStatus.COMPLETED.name, mediaServerId, null)
                }

                // 3. Submit inspection (DRAFT/UPLOADING -> SUBMITTED). 409 means a
                // previous attempt already submitted it, which is fine on retry.
                val submitResponse = apiService.submitInspection(serverId)
                val finalStatus = when {
                    submitResponse.isSuccessful -> submitResponse.body()?.data?.status ?: "SUBMITTED"
                    submitResponse.code() == 409 -> localInspection.status.takeIf { it != "DRAFT" } ?: "SUBMITTED"
                    else -> throw Exception(formatError(submitResponse, "Submit failed"))
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
