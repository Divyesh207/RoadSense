package com.roadintelligence.field.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.roadintelligence.field.data.local.entity.InspectionEntity
import com.roadintelligence.field.data.local.entity.InspectionMediaEntity
import com.roadintelligence.field.data.local.entity.RoadEntity
import com.roadintelligence.field.data.local.entity.RoadSegmentEntity
import com.roadintelligence.field.data.local.entity.SyncQueueEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface InspectionDao {
    @Query("SELECT * FROM inspections ORDER BY createdAt DESC")
    fun getAllInspections(): Flow<List<InspectionEntity>>

    @Query("SELECT * FROM inspections WHERE localId = :localId LIMIT 1")
    fun getInspectionById(localId: String): Flow<InspectionEntity?>

    @Query("SELECT * FROM inspections WHERE localId = :localId LIMIT 1")
    suspend fun getInspectionByIdSync(localId: String): InspectionEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertInspection(inspection: InspectionEntity)

    @Update
    suspend fun updateInspection(inspection: InspectionEntity)

    @Query("UPDATE inspections SET syncStatus = :status, lastSyncError = :error WHERE localId = :localId")
    suspend fun updateSyncStatus(localId: String, status: String, error: String? = null)

    @Query("UPDATE inspections SET serverId = :serverId, status = :status WHERE localId = :localId")
    suspend fun markUploaded(localId: String, serverId: String, status: String)

    @Query("DELETE FROM inspections WHERE localId = :localId")
    suspend fun deleteInspection(localId: String)
}

@Dao
interface InspectionMediaDao {
    @Query("SELECT * FROM inspection_media WHERE inspectionLocalId = :inspectionId")
    suspend fun getMediaForInspection(inspectionId: String): List<InspectionMediaEntity>

    @Query("SELECT * FROM inspection_media WHERE inspectionLocalId = :inspectionId")
    fun observeMediaForInspection(inspectionId: String): Flow<List<InspectionMediaEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMedia(media: InspectionMediaEntity)

    @Update
    suspend fun updateMedia(media: InspectionMediaEntity)

    @Query("UPDATE inspection_media SET uploadStatus = :status, serverId = :serverId, lastError = :error WHERE localId = :localId")
    suspend fun updateMediaStatus(localId: String, status: String, serverId: String? = null, error: String? = null)

    @Query("DELETE FROM inspection_media WHERE localId = :localId")
    suspend fun deleteMedia(localId: String)
}

@Dao
interface RoadDao {
    @Query("SELECT * FROM roads ORDER BY name ASC")
    fun getAllRoads(): Flow<List<RoadEntity>>

    @Query("SELECT * FROM roads WHERE organizationId = :orgId ORDER BY name ASC")
    fun getRoadsForOrganization(orgId: String): Flow<List<RoadEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRoads(roads: List<RoadEntity>)

    @Query("SELECT * FROM road_segments WHERE roadId = :roadId ORDER BY segmentNumber ASC")
    fun getSegmentsForRoad(roadId: String): Flow<List<RoadSegmentEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertSegments(segments: List<RoadSegmentEntity>)

    @Query("DELETE FROM roads")
    suspend fun clearRoads()

    @Query("DELETE FROM road_segments WHERE roadId = :roadId")
    suspend fun clearSegmentsForRoad(roadId: String)
}

@Dao
interface SyncQueueDao {
    @Query("SELECT * FROM sync_queue ORDER BY createdAt ASC")
    fun getQueueItems(): Flow<List<SyncQueueEntity>>

    // UPLOAD_FAILED items are included so WorkManager retries pick them up again.
    @Query("SELECT * FROM sync_queue WHERE status IN ('QUEUED', 'UPLOAD_FAILED') ORDER BY createdAt ASC")
    suspend fun getPendingQueueItems(): List<SyncQueueEntity>

    @Query("SELECT * FROM sync_queue WHERE id = :id LIMIT 1")
    suspend fun getItemById(id: String): SyncQueueEntity?

    @Query("SELECT * FROM sync_queue WHERE inspectionLocalId = :inspectionLocalId LIMIT 1")
    suspend fun getItemByInspectionId(inspectionLocalId: String): SyncQueueEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertQueueItem(item: SyncQueueEntity)

    @Update
    suspend fun updateQueueItem(item: SyncQueueEntity)

    @Query("UPDATE sync_queue SET status = :status, attemptCount = attemptCount + 1, lastError = :error, updatedAt = :updatedAt WHERE id = :id")
    suspend fun updateStatus(id: String, status: String, error: String?, updatedAt: Long = System.currentTimeMillis())

    @Query("DELETE FROM sync_queue WHERE status = 'COMPLETED'")
    suspend fun clearCompleted()

    @Query("DELETE FROM sync_queue WHERE id = :id")
    suspend fun deleteItem(id: String)

    @Query("DELETE FROM sync_queue WHERE inspectionLocalId = :inspectionLocalId")
    suspend fun deleteItemsForInspection(inspectionLocalId: String)
}
