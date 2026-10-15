package com.roadintelligence.field.data.repository

import com.roadintelligence.field.data.local.SecureSessionManager
import com.roadintelligence.field.data.local.dao.RoadDao
import com.roadintelligence.field.data.local.entity.RoadEntity
import com.roadintelligence.field.data.local.entity.RoadSegmentEntity
import com.roadintelligence.field.data.remote.ApiService
import com.roadintelligence.field.domain.model.Road
import com.roadintelligence.field.domain.model.RoadSegment
import com.roadintelligence.field.domain.repository.RoadRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext

class RoadRepositoryImpl(
    private val apiService: ApiService,
    private val roadDao: RoadDao,
    private val sessionManager: SecureSessionManager
) : RoadRepository {

    override fun getCachedRoads(): Flow<List<Road>> {
        val orgId = sessionManager.getOrganizationId().orEmpty()
        val flow = if (orgId.isNotEmpty()) roadDao.getRoadsForOrganization(orgId) else roadDao.getAllRoads()
        return flow.map { list ->
            list.map {
                Road(
                    id = it.id,
                    name = it.name,
                    roadCode = it.roadCode,
                    surfaceType = it.surfaceType
                )
            }
        }
    }

    override fun getCachedSegments(roadId: String): Flow<List<RoadSegment>> {
        return roadDao.getSegmentsForRoad(roadId).map { list ->
            list.map {
                RoadSegment(
                    id = it.id,
                    roadId = it.roadId,
                    segmentNumber = it.segmentNumber,
                    lengthMeters = it.lengthMeters,
                    surfaceType = it.surfaceType
                )
            }
        }
    }

    override suspend fun syncRoadsFromServer(): Result<List<Road>> = withContext(Dispatchers.IO) {
        try {
            val orgId = sessionManager.getOrganizationId() ?: ""
            val response = apiService.getRoads(pageSize = 100)
            if (response.isSuccessful && response.body()?.success == true) {
                val dtos = response.body()?.data ?: emptyList()
                val entities = dtos.map {
                    RoadEntity(
                        id = it.id,
                        organizationId = orgId,
                        name = it.name,
                        roadCode = it.roadCode,
                        surfaceType = it.surfaceType ?: "ASPHALT"
                    )
                }
                roadDao.insertRoads(entities)

                val domainRoads = entities.map {
                    Road(
                        id = it.id,
                        name = it.name,
                        roadCode = it.roadCode,
                        surfaceType = it.surfaceType
                    )
                }
                Result.success(domainRoads)
            } else {
                Result.failure(Exception("Failed to fetch roads: ${response.message()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun syncSegmentsFromServer(roadId: String): Result<List<RoadSegment>> = withContext(Dispatchers.IO) {
        try {
            val orgId = sessionManager.getOrganizationId() ?: ""
            val response = apiService.getRoadSegments(roadId)
            if (response.isSuccessful && response.body()?.success == true) {
                val dtos = response.body()?.data ?: emptyList()
                val entities = dtos.map {
                    RoadSegmentEntity(
                        id = it.id,
                        roadId = it.roadId,
                        organizationId = orgId,
                        segmentNumber = it.segmentNumber,
                        lengthMeters = it.lengthMeters,
                        surfaceType = it.surfaceType
                    )
                }
                roadDao.insertSegments(entities)

                val domainSegments = entities.map {
                    RoadSegment(
                        id = it.id,
                        roadId = it.roadId,
                        segmentNumber = it.segmentNumber,
                        lengthMeters = it.lengthMeters,
                        surfaceType = it.surfaceType
                    )
                }
                Result.success(domainSegments)
            } else {
                Result.failure(Exception("Failed to fetch segments: ${response.message()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
