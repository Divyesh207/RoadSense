package com.roadintelligence.field.data.repository

import com.roadintelligence.field.data.remote.ApiService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.ConcurrentHashMap

/** Media metadata as recorded by the server (the API exposes no download URL for inspection media). */
data class ServerMedia(
    val id: String,
    val originalFilename: String?,
    val mimeType: String?,
    val fileSizeBytes: Long?,
    val uploadStatus: String,
    val createdAt: String?
)

/** One AI detection exactly as returned by GET /inspections/{id}/detections. */
data class ServerDetection(
    val id: String,
    val mediaId: String?,
    val damageType: String,
    val score: Double?,
    val scoreType: String?,
    val detectionMethod: String?,
    val modelName: String?,
    val modelVersion: String?,
    val severity: String?,
    val xMin: Float?,
    val yMin: Float?,
    val xMax: Float?,
    val yMax: Float?
) {
    /** True for the OpenCV rule-based fallback: its score is not a model probability. */
    val isHeuristic: Boolean
        get() = detectionMethod == "HEURISTIC_FALLBACK" || scoreType == "HEURISTIC_SCORE"
}

/** Server-side state of an uploaded inspection. */
data class ServerInspectionState(
    val status: String,
    val inspectorName: String?,
    val submittedAt: String?,
    val media: List<ServerMedia>,
    val detections: List<ServerDetection>
)

enum class ServerReachability { UNKNOWN, REACHABLE, UNREACHABLE }

/**
 * Read-only access to what the server knows about inspections this device uploaded.
 * Uses existing endpoints only; nothing here writes to the server or to Room.
 */
class InspectionRemoteRepository(private val apiService: ApiService) {

    private val cache = ConcurrentHashMap<String, ServerInspectionState>()

    fun cached(serverId: String): ServerInspectionState? = cache[serverId]

    suspend fun fetchState(serverId: String): Result<ServerInspectionState> = withContext(Dispatchers.IO) {
        try {
            val detail = apiService.getInspectionDetail(serverId)
            val inspection = detail.body()?.data
            if (!detail.isSuccessful || inspection == null) {
                return@withContext Result.failure(Exception(httpMessage(detail.code())))
            }
            val mediaResponse = apiService.getInspectionMedia(serverId)
            if (!mediaResponse.isSuccessful) {
                return@withContext Result.failure(Exception(httpMessage(mediaResponse.code())))
            }
            val detectionsResponse = apiService.getInspectionDetections(serverId)
            if (!detectionsResponse.isSuccessful) {
                return@withContext Result.failure(Exception(httpMessage(detectionsResponse.code())))
            }
            val state = ServerInspectionState(
                status = inspection.status,
                inspectorName = inspection.inspectorName,
                submittedAt = inspection.submittedAt,
                media = (mediaResponse.body()?.data ?: emptyList()).map {
                    ServerMedia(
                        id = it.id,
                        originalFilename = it.originalFilename,
                        mimeType = it.mimeType,
                        fileSizeBytes = it.fileSizeBytes,
                        uploadStatus = it.uploadStatus,
                        createdAt = it.createdAt
                    )
                },
                detections = (detectionsResponse.body()?.data ?: emptyList()).map {
                    ServerDetection(
                        id = it.id,
                        mediaId = it.mediaId,
                        damageType = it.damageType ?: "UNKNOWN",
                        score = it.confidence,
                        scoreType = it.scoreType,
                        detectionMethod = it.detectionMethod,
                        modelName = it.modelName,
                        modelVersion = it.modelVersion,
                        severity = it.severity,
                        xMin = it.bbox?.xMin,
                        yMin = it.bbox?.yMin,
                        xMax = it.bbox?.xMax,
                        yMax = it.bbox?.yMax
                    )
                }
            )
            cache[serverId] = state
            Result.success(state)
        } catch (e: Exception) {
            Result.failure(Exception(e.message ?: "Could not reach the server."))
        }
    }

    suspend fun checkServer(): ServerReachability = withContext(Dispatchers.IO) {
        try {
            if (apiService.healthLive().isSuccessful) ServerReachability.REACHABLE else ServerReachability.UNREACHABLE
        } catch (e: Exception) {
            ServerReachability.UNREACHABLE
        }
    }

    private fun httpMessage(code: Int): String = when (code) {
        401 -> "Session expired. Sign in again."
        403 -> "You do not have permission to view this inspection on the server."
        404 -> "The server no longer has this inspection."
        else -> "Server returned HTTP $code."
    }
}
