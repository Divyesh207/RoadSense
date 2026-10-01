package com.roadintelligence.field.domain.repository

import com.roadintelligence.field.domain.model.Inspection
import com.roadintelligence.field.domain.model.InspectionMedia
import com.roadintelligence.field.domain.model.Road
import com.roadintelligence.field.domain.model.RoadSegment
import com.roadintelligence.field.domain.model.SyncQueueItem
import com.roadintelligence.field.domain.model.UserSession
import kotlinx.coroutines.flow.Flow

interface AuthRepository {
    suspend fun login(email: String, password: String): Result<UserSession>
    suspend fun logout(): Result<Unit>
    fun getCurrentSession(): UserSession?
    fun isSessionValid(): Boolean
}

interface RoadRepository {
    fun getCachedRoads(): Flow<List<Road>>
    fun getCachedSegments(roadId: String): Flow<List<RoadSegment>>
    suspend fun syncRoadsFromServer(): Result<List<Road>>
    suspend fun syncSegmentsFromServer(roadId: String): Result<List<RoadSegment>>
}

interface InspectionRepository {
    fun getAllInspections(): Flow<List<Inspection>>
    fun getInspectionById(localId: String): Flow<Inspection?>
    suspend fun createLocalDraft(inspection: Inspection): Result<String>
    suspend fun updateInspection(inspection: Inspection): Result<Unit>
    suspend fun addMediaToInspection(media: InspectionMedia): Result<Unit>
    suspend fun getMediaForInspection(localInspectionId: String): List<InspectionMedia>
    suspend fun queueForUpload(localId: String): Result<Unit>
    suspend fun deleteDraft(localId: String): Result<Unit>
}

interface SyncRepository {
    fun getSyncQueue(): Flow<List<SyncQueueItem>>
    suspend fun enqueueSync(inspectionLocalId: String): Result<Unit>
    suspend fun triggerManualSync(): Result<Unit>
    suspend fun retryFailedItem(queueItemId: String): Result<Unit>
    suspend fun clearCompleted(): Result<Unit>
}
