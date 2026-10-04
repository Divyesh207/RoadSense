package com.roadintelligence.field.ui.components

import android.Manifest
import android.content.Context
import android.location.LocationManager
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.State
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.core.location.LocationManagerCompat
import com.roadintelligence.field.data.repository.InspectionRemoteRepository
import com.roadintelligence.field.data.repository.ServerReachability
import com.roadintelligence.field.ui.permissions.hasAnyPermission
import com.roadintelligence.field.ui.theme.ErrorRose
import com.roadintelligence.field.ui.theme.SuccessEmerald
import com.roadintelligence.field.ui.theme.TextSecondary
import com.roadintelligence.field.ui.theme.WarningAmber
import kotlinx.coroutines.delay

private fun Context.hasNetwork(): Boolean {
    val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager ?: return false
    val caps = cm.getNetworkCapabilities(cm.activeNetwork ?: return false) ?: return false
    return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) ||
        caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ||
        caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)
}

/** Whether the device currently has any network (not whether the platform server is reachable). */
@Composable
fun rememberDeviceOnline(): State<Boolean> {
    val context = LocalContext.current
    val online = remember { mutableStateOf(context.hasNetwork()) }
    DisposableEffect(context) {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
        val callback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) { online.value = true }
            override fun onLost(network: Network) { online.value = context.hasNetwork() }
        }
        try {
            cm?.registerDefaultNetworkCallback(callback)
        } catch (_: Exception) {
        }
        onDispose {
            try {
                cm?.unregisterNetworkCallback(callback)
            } catch (_: Exception) {
            }
        }
    }
    return online
}

/** Polls the server's public liveness endpoint while the screen is shown. */
@Composable
fun rememberServerReachability(remote: InspectionRemoteRepository, refreshKey: Any? = null): State<ServerReachability> {
    val state = remember { mutableStateOf(ServerReachability.UNKNOWN) }
    LaunchedEffect(remote, refreshKey) {
        while (true) {
            state.value = remote.checkServer()
            delay(20_000)
        }
    }
    return state
}

data class StatusChipInfo(val label: String, val color: Color)

fun serverChip(reachability: ServerReachability, deviceOnline: Boolean): StatusChipInfo = when {
    reachability == ServerReachability.REACHABLE -> StatusChipInfo("Server online", SuccessEmerald)
    reachability == ServerReachability.UNKNOWN -> StatusChipInfo("Checking server", TextSecondary)
    !deviceOnline -> StatusChipInfo("Offline", WarningAmber)
    else -> StatusChipInfo("Server unreachable", ErrorRose)
}

/** What the device can do about location right now; this is readiness, not a GPS fix. */
enum class GpsReadiness { READY, PERMISSION_NEEDED, LOCATION_OFF }

private val LOCATION_PERMISSIONS = arrayOf(
    Manifest.permission.ACCESS_FINE_LOCATION,
    Manifest.permission.ACCESS_COARSE_LOCATION
)

fun Context.gpsReadiness(): GpsReadiness {
    if (!hasAnyPermission(LOCATION_PERMISSIONS)) return GpsReadiness.PERMISSION_NEEDED
    val lm = getSystemService(Context.LOCATION_SERVICE) as? LocationManager ?: return GpsReadiness.LOCATION_OFF
    return if (LocationManagerCompat.isLocationEnabled(lm)) GpsReadiness.READY else GpsReadiness.LOCATION_OFF
}

@Composable
fun rememberGpsReadiness(refreshKey: Any? = null): State<GpsReadiness> {
    val context = LocalContext.current
    val state = remember { mutableStateOf(context.gpsReadiness()) }
    LaunchedEffect(refreshKey) {
        while (true) {
            state.value = context.gpsReadiness()
            delay(5_000)
        }
    }
    return state
}

fun gpsChip(readiness: GpsReadiness): StatusChipInfo = when (readiness) {
    GpsReadiness.READY -> StatusChipInfo("GPS ready", SuccessEmerald)
    GpsReadiness.PERMISSION_NEEDED -> StatusChipInfo("GPS permission needed", WarningAmber)
    GpsReadiness.LOCATION_OFF -> StatusChipInfo("Location is off", ErrorRose)
}

/** Colour for a reported GPS accuracy in metres. */
fun accuracyColor(accuracyMeters: Float?): Color = when {
    accuracyMeters == null -> TextSecondary
    accuracyMeters <= 10f -> SuccessEmerald
    accuracyMeters <= 25f -> WarningAmber
    else -> ErrorRose
}

fun accuracyLabel(accuracyMeters: Float?): String = when {
    accuracyMeters == null -> "not reported"
    accuracyMeters <= 10f -> "good"
    accuracyMeters <= 25f -> "fair"
    else -> "low"
}
