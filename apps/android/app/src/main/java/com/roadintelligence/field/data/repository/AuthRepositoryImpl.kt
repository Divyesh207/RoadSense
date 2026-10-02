package com.roadintelligence.field.data.repository

import com.roadintelligence.field.data.local.SecureSessionManager
import com.google.gson.Gson
import com.roadintelligence.field.data.remote.ApiService
import com.roadintelligence.field.data.remote.dto.ApiEnvelope
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
                // Login returns tokens only; the profile and memberships come from /auth/me.
                val meResponse = apiService.getCurrentUser("Bearer ${data.accessToken}")
                val user = meResponse.body()?.data
                if (!meResponse.isSuccessful || user == null) {
                    return@withContext Result.failure(Exception("Failed to load user profile: HTTP ${meResponse.code()}"))
                }
                val org = user.organizations.firstOrNull { it.status == null || it.status == "ACTIVE" }
                    ?: return@withContext Result.failure(Exception("User has no active organization membership"))
                val session = UserSession(
                    userId = user.id,
                    email = user.email,
                    fullName = user.fullName,
                    role = org.roleCode,
                    organizationId = org.organizationId,
                    organizationName = org.organizationName,
                    accessToken = data.accessToken,
                    refreshToken = data.refreshToken
                )
                sessionManager.saveSession(session)
                Result.success(session)
            } else {
                // Non-2xx bodies arrive in errorBody(), e.g. 401 INVALID_CREDENTIALS.
                val apiError = response.errorBody()?.string()?.let { raw ->
                    runCatching { Gson().fromJson(raw, ApiEnvelope::class.java)?.error?.message }.getOrNull()
                }
                val errorMsg = apiError ?: response.body()?.error?.message ?: response.message().ifBlank { "Authentication failed" }
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
