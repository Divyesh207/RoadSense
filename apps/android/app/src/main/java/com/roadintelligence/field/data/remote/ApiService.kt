package com.roadintelligence.field.data.remote

import com.roadintelligence.field.data.remote.dto.*
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    // Auth
    @POST("api/v1/auth/login")
    suspend fun login(
        @Body request: LoginRequestDto
    ): Response<ApiEnvelope<LoginResponseDataDto>>

    // Roads & Segments
    @GET("api/v1/roads")
    suspend fun getRoads(
        @Query("page_size") pageSize: Int = 100
    ): Response<PaginatedEnvelope<RoadDto>>

    @GET("api/v1/roads/{road_id}/segments")
    suspend fun getRoadSegments(
        @Path("road_id") roadId: String
    ): Response<ApiEnvelope<List<RoadSegmentDto>>>

    // Inspections
    @POST("api/v1/inspections")
    suspend fun createInspection(
        @Body request: InspectionCreateDto
    ): Response<ApiEnvelope<InspectionResponseDto>>

    @GET("api/v1/inspections")
    suspend fun getInspections(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 50
    ): Response<PaginatedEnvelope<InspectionResponseDto>>

    @GET("api/v1/inspections/{id}")
    suspend fun getInspectionDetail(
        @Path("id") inspectionId: String
    ): Response<ApiEnvelope<InspectionResponseDto>>

    // Media Upload Handshake
    @POST("api/v1/inspections/{id}/upload-url")
    suspend fun requestMediaUploadUrl(
        @Path("id") inspectionId: String,
        @Body request: UploadUrlRequestDto
    ): Response<ApiEnvelope<UploadUrlResponseDto>>

    @POST("api/v1/inspections/{id}/media")
    suspend fun completeMediaUpload(
        @Path("id") inspectionId: String,
        @Body request: MediaCompleteDto
    ): Response<ApiEnvelope<Map<String, Any>>>

    // Direct Binary/Signed URL Upload
    @PUT
    suspend fun uploadToSignedUrl(
        @Url uploadUrl: String,
        @Header("Content-Type") contentType: String,
        @Body fileBytes: RequestBody
    ): Response<Unit>

    // Submit for AI Processing
    @POST("api/v1/inspections/{id}/submit")
    suspend fun submitInspection(
        @Path("id") inspectionId: String
    ): Response<ApiEnvelope<SubmitInspectionResponseDto>>
}
