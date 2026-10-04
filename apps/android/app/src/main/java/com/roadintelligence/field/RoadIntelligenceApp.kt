package com.roadintelligence.field

import android.app.Application
import com.roadintelligence.field.data.local.AppDatabase
import com.roadintelligence.field.data.local.SecureSessionManager
import com.roadintelligence.field.data.remote.NetworkClient
import com.roadintelligence.field.data.repository.AuthRepositoryImpl
import com.roadintelligence.field.data.repository.InspectionRemoteRepository
import com.roadintelligence.field.data.repository.InspectionRepositoryImpl
import com.roadintelligence.field.data.repository.RoadRepositoryImpl
import com.roadintelligence.field.data.repository.SyncRepositoryImpl
import com.roadintelligence.field.domain.repository.AuthRepository
import com.roadintelligence.field.domain.repository.InspectionRepository
import com.roadintelligence.field.domain.repository.RoadRepository
import com.roadintelligence.field.domain.repository.SyncRepository

class RoadIntelligenceApp : Application() {

    lateinit var database: AppDatabase private set
    lateinit var sessionManager: SecureSessionManager private set
    lateinit var authRepository: AuthRepository private set
    lateinit var roadRepository: RoadRepository private set
    lateinit var inspectionRepository: InspectionRepository private set
    lateinit var syncRepository: SyncRepository private set
    lateinit var inspectionRemote: InspectionRemoteRepository private set

    override fun onCreate() {
        super.onCreate()
        instance = this

        database = AppDatabase.getInstance(this)
        sessionManager = SecureSessionManager(this)

        val apiService = NetworkClient.getApiService(sessionManager)

        authRepository = AuthRepositoryImpl(apiService, sessionManager)
        roadRepository = RoadRepositoryImpl(apiService, database.roadDao(), sessionManager)
        inspectionRepository = InspectionRepositoryImpl(
            database.inspectionDao(),
            database.inspectionMediaDao(),
            database.syncQueueDao(),
            sessionManager
        )
        syncRepository = SyncRepositoryImpl(this, database.syncQueueDao())
        inspectionRemote = InspectionRemoteRepository(apiService)
    }

    companion object {
        lateinit var instance: RoadIntelligenceApp
            private set
    }
}
