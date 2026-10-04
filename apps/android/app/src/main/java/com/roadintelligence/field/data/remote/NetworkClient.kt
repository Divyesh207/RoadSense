package com.roadintelligence.field.data.remote

import com.roadintelligence.field.BuildConfig
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

    // Server root, set per build type in app/build.gradle.kts (roadintel.apiBaseUrl.*).
    // Every ApiService call, including the upload handshake, resolves against it.
    val baseUrl: String = BuildConfig.API_BASE_URL

    // Route of the platform's own (local) storage backend, relative to the server root.
    private const val LOCAL_STORAGE_ROUTE = "/api/v1/storage/local/"

    /**
     * The address to send a signed upload to. The server builds the URL from its own
     * PUBLIC_API_BASE_URL setting, which can name a host this device cannot reach (a LAN
     * address while the app talks to the API through `adb reverse`, for example). When the
     * URL points at the platform's own storage route, it is the API itself, so it is
     * re-addressed to [apiBase], the one address every other call uses. The signature covers
     * the method, bucket, path and expiry only, so it stays valid. URLs for external storage
     * (e.g. Supabase) are returned unchanged.
     */
    fun resolveUploadUrl(serverUrl: String, apiBase: String = baseUrl): String {
        val url = serverUrl.toHttpUrlOrNull() ?: return serverUrl
        val base = apiBase.toHttpUrlOrNull() ?: return serverUrl
        if (!url.encodedPath.startsWith(LOCAL_STORAGE_ROUTE)) return serverUrl
        return url.newBuilder().scheme(base.scheme).host(base.host).port(base.port).build().toString()
    }

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
                .authenticator(TokenRefreshAuthenticator(sessionManager) { baseUrl.toHttpUrlOrNull() })
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
