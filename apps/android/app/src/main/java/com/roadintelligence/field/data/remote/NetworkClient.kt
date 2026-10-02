package com.roadintelligence.field.data.remote

import com.roadintelligence.field.data.local.SecureSessionManager
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Adds the platform bearer token and organization header to API requests only.
 * Signed storage URLs (e.g. Supabase) live on other hosts and must never
 * receive platform credentials.
 */
class AuthInterceptor(
    private val sessionManager: SecureSessionManager,
    private val apiBaseUrl: () -> HttpUrl?
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        if (!isApiRequest(original.url, apiBaseUrl())) {
            return chain.proceed(original)
        }
        val builder = original.newBuilder()

        if (original.header("Authorization") == null) {
            sessionManager.getAccessToken()?.let { token ->
                builder.header("Authorization", "Bearer $token")
            }
        }

        sessionManager.getOrganizationId()?.let { orgId ->
            if (orgId.isNotEmpty()) {
                builder.header("X-Organization-ID", orgId)
            }
        }

        return chain.proceed(builder.build())
    }

    companion object {
        fun isApiRequest(url: HttpUrl, apiBase: HttpUrl?): Boolean =
            apiBase != null && url.scheme == apiBase.scheme && url.host == apiBase.host && url.port == apiBase.port
    }
}

object NetworkClient {

    // Default base URL is 10.0.2.2 (standard Android Emulator loopback to host)
    // or standard localhost / LAN IP
    var baseUrl: String = "http://10.0.2.2:8000/"

    private var apiServiceInstance: ApiService? = null

    fun getApiService(sessionManager: SecureSessionManager): ApiService {
        return apiServiceInstance ?: synchronized(this) {
            val loggingInterceptor = HttpLoggingInterceptor().apply {
                // Headers only: bodies include binary media and tokens.
                level = HttpLoggingInterceptor.Level.HEADERS
                redactHeader("Authorization")
            }

            val okHttpClient = OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .writeTimeout(60, TimeUnit.SECONDS)
                .addInterceptor(AuthInterceptor(sessionManager) { baseUrl.toHttpUrlOrNull() })
                .addInterceptor(loggingInterceptor)
                .build()

            val retrofit = Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()

            val service = retrofit.create(ApiService::class.java)
            apiServiceInstance = service
            service
        }
    }
}
