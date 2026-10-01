package com.roadintelligence.field.data.remote

import com.roadintelligence.field.data.local.SecureSessionManager
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

class AuthInterceptor(private val sessionManager: SecureSessionManager) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val builder = original.newBuilder()

        sessionManager.getAccessToken()?.let { token ->
            builder.header("Authorization", "Bearer $token")
        }

        sessionManager.getOrganizationId()?.let { orgId ->
            if (orgId.isNotEmpty()) {
                builder.header("X-Organization-ID", orgId)
            }
        }

        return chain.proceed(builder.build())
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
                level = HttpLoggingInterceptor.Level.BODY
            }

            val okHttpClient = OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .writeTimeout(60, TimeUnit.SECONDS)
                .addInterceptor(AuthInterceptor(sessionManager))
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
