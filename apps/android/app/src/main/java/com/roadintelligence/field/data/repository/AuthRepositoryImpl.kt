package com.roadintelligence.field.data.repository

import com.roadintelligence.field.data.local.SecureSessionManager
import com.roadintelligence.field.data.remote.ApiService
import com.roadintelligence.field.data.remote.dto.LoginRequestDto
import com.roadintelligence.field.domain.model.UserSession
import com.roadintelligence.field.domain.repository.AuthRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class AuthRepositoryImpl(
    private val apiService: ApiService,
    private val sessionManager: SecureSessionManager
) : AuthRepository {

    override suspend fun login(email: String, password: String): Result<UserSession> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.login(LoginRequestDto(email, password))
            if (response.isSuccessful && response.body()?.success == true) {
                val data = response.body()?.data ?: return@withContext Result.failure(Exception("Empty login response"))
                val org = data.user.organizations.firstOrNull()
                val session = UserSession(
                    userId = data.user.id,
                    email = data.user.email,
                    fullName = data.user.fullName,
                    role = org?.role ?: data.user.role ?: "FIELD_INSPECTOR",
                    organizationId = org?.organizationId ?: "",
                    organizationName = org?.organizationName ?: "Default Org",
                    accessToken = data.accessToken,
                    refreshToken = data.refreshToken
                )
                sessionManager.saveSession(session)
                Result.success(session)
            } else {
                val errorMsg = response.body()?.error?.message ?: response.message() ?: "Authentication failed"
                Result.failure(Exception(errorMsg))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun logout(): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            sessionManager.clearSession()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override fun getCurrentSession(): UserSession? {
        return sessionManager.getSession()
    }

    override fun isSessionValid(): Boolean {
        return sessionManager.isLoggedIn()
    }
}
