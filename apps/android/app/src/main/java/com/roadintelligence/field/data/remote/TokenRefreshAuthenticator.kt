package com.roadintelligence.field.data.remote

import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.roadintelligence.field.data.local.SecureSessionManager
import com.roadintelligence.field.data.remote.dto.ApiEnvelope
import com.roadintelligence.field.data.remote.dto.LoginResponseDataDto
import okhttp3.Authenticator
import okhttp3.HttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okhttp3.Route
import java.util.concurrent.TimeUnit

/**
 * On a 401 from the platform API, exchanges the stored refresh token for a new token pair
 * (POST /api/v1/auth/refresh) and retries the request once. Access tokens are short-lived,
 * so without this, queued offline inspections fail with "Unauthorized" an hour after login.
 *
 * The server rotates refresh tokens (each is single-use), so refreshes are serialised: a
 * request that failed with a token another thread already replaced just retries with the new one.
 */
class TokenRefreshAuthenticator(
    private val sessionManager: SecureSessionManager,
    private val apiBaseUrl: () -> HttpUrl?
) : Authenticator {

    // Bare client: no auth interceptor or authenticator, so a failed refresh cannot recurse.
    private val refreshClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()
    private val gson = Gson()

    override fun authenticate(route: Route?, response: Response): Request? {
        val request = response.request
        val base = apiBaseUrl() ?: return null
        if (!AuthInterceptor.isApiRequest(request.url, base)) return null
        if (request.url.encodedPath.contains("/auth/")) return null
        if (response.priorResponse != null) return null // already retried once

        val failedToken = request.header("Authorization")?.removePrefix("Bearer ")
        synchronized(lock) {
            val current = sessionManager.getAccessToken()
            if (current != null && current != failedToken) {
                return request.withToken(current)
            }
            val refreshToken = sessionManager.getRefreshToken() ?: return null
            val newAccess = refresh(base, refreshToken) ?: return null
            return request.withToken(newAccess)
        }
    }

    private fun refresh(base: HttpUrl, refreshToken: String): String? {
        val url = base.resolve("api/v1/auth/refresh") ?: return null
        val body = gson.toJson(mapOf("refresh_token" to refreshToken))
            .toRequestBody("application/json; charset=utf-8".toMediaType())
        return try {
            refreshClient.newCall(Request.Builder().url(url).post(body).build()).execute().use { res ->
                if (!res.isSuccessful) return null
                val type = object : TypeToken<ApiEnvelope<LoginResponseDataDto>>() {}.type
                val data = gson.fromJson<ApiEnvelope<LoginResponseDataDto>>(res.body?.charStream(), type)?.data
                    ?: return null
                sessionManager.updateTokens(data.accessToken, data.refreshToken)
                data.accessToken
            }
        } catch (e: Exception) {
            null
        }
    }

    private fun Request.withToken(token: String): Request =
        newBuilder().header("Authorization", "Bearer $token").build()

    private companion object {
        val lock = Any()
    }
}
