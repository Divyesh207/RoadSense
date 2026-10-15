package com.roadintelligence.field.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import android.location.Location
import android.os.Build
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.roadintelligence.field.domain.model.*
import com.roadintelligence.field.domain.repository.InspectionRepository
import com.roadintelligence.field.domain.repository.RoadRepository
import com.roadintelligence.field.domain.repository.SyncRepository
import com.roadintelligence.field.ui.components.*
import com.roadintelligence.field.ui.permissions.PermissionResult
import com.roadintelligence.field.ui.permissions.openAppSettings
import com.roadintelligence.field.ui.permissions.rememberPermissionRequest
import com.roadintelligence.field.ui.theme.*
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.UUID

private const val GPS_LOG_TAG = "RoadGPS"
private const val GPS_REQUEST_TIMEOUT_MS = 25_000L   // give up after this long without a new fix
private const val GPS_FRESH_MAX_AGE_MS = 10_000L     // a fix older than this is treated as cached
private const val GPS_STALE_WARNING_MIN = 5L         // warn on screen once the held fix is this old
private const val GPS_SAMPLE_INTERVAL_MS = 1_000L    // how often a new fix is requested while acquiring
private const val GPS_SETTLE_MS = 8_000L             // after the first fix, keep sampling this long for a better one
private const val GPS_GOOD_ACCURACY_M = 10f          // stop early once a fix is at least this accurate

/** The location request in progress, so it can be stopped when it is done or the screen closes. */
private class GpsSampling {
    var callback: LocationCallback? = null
    var jobs: List<Job> = emptyList()
}

/**
 * Inspection form data that must survive leaving the composition, e.g. while the
 * CameraX screen replaces this one. Owned by MainActivity; photos captured on the
 * camera screen are stored under [localId], so it must not change mid-inspection.
 */
class NewInspectionFormState {
    var localId by mutableStateOf(UUID.randomUUID().toString())
    var clientId by mutableStateOf(UUID.randomUUID().toString())
    var selectedRoad by mutableStateOf<Road?>(null)
    var selectedSegment by mutableStateOf<RoadSegment?>(null)
    var latitude by mutableStateOf<Double?>(null)
    var longitude by mutableStateOf<Double?>(null)
    var accuracyMeters by mutableStateOf<Float?>(null)
    /** Wall-clock time of the GPS fix held above (null when there is none). */
    var fixTimeMillis by mutableStateOf<Long?>(null)
    var fixIsMock by mutableStateOf(false)
    var gpsStatusMessage by mutableStateOf("Tap 'Acquire GPS' to capture coordinates")
    var notes by mutableStateOf("")
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NewInspectionScreen(
    form: NewInspectionFormState,
    inspectionRepository: InspectionRepository,
    roadRepository: RoadRepository,
    syncRepository: SyncRepository,
    onNavigateBack: () -> Unit,
    onNavigateToCamera: (String) -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val scrollState = rememberScrollState()

    // Inspection data lives in the hoisted form state (survives camera navigation)
    val localId = form.localId
    val clientId = form.clientId

    val roads by roadRepository.getCachedRoads().collectAsState(initial = emptyList())
    var selectedRoad by form::selectedRoad
    var roadDropdownExpanded by remember { mutableStateOf(false) }

    val segments by (if (selectedRoad != null) roadRepository.getCachedSegments(selectedRoad!!.id) else null)
        ?.collectAsState(initial = emptyList()) ?: remember { mutableStateOf(emptyList()) }
    var selectedSegment by form::selectedSegment
    var segmentDropdownExpanded by remember { mutableStateOf(false) }

    var latitude by form::latitude
    var longitude by form::longitude
    var accuracyMeters by form::accuracyMeters
    var fixTimeMillis by form::fixTimeMillis
    var fixIsMock by form::fixIsMock
    var isAcquiringGps by remember { mutableStateOf(false) }
    // Re-read the clock twice a minute so the age of the fix shown on screen stays current.
    var nowMillis by remember { mutableStateOf(System.currentTimeMillis()) }
    LaunchedEffect(Unit) {
        while (true) {
            nowMillis = System.currentTimeMillis()
            kotlinx.coroutines.delay(30_000)
        }
    }
    var gpsStatusMessage by form::gpsStatusMessage
    var locationPermanentlyDenied by remember { mutableStateOf(false) }

    var cameraPermissionMessage by remember { mutableStateOf<String?>(null) }
    var cameraPermanentlyDenied by remember { mutableStateOf(false) }

    var notes by form::notes
    var mediaList by remember { mutableStateOf<List<InspectionMedia>>(emptyList()) }
    var isSaving by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    // Load initial roads and media
    LaunchedEffect(Unit) {
        roadRepository.syncRoadsFromServer()
        mediaList = inspectionRepository.getMediaForInspection(localId)
    }

    val fusedLocationClient = remember { LocationServices.getFusedLocationProviderClient(context) }
    val gpsSampling = remember { GpsSampling() }
    fun stopGpsSampling() {
        gpsSampling.callback?.let { fusedLocationClient.removeLocationUpdates(it) }
        gpsSampling.callback = null
        gpsSampling.jobs.forEach { it.cancel() }
        gpsSampling.jobs = emptyList()
    }
    DisposableEffect(Unit) {
        onDispose { stopGpsSampling() }
    }

    // Acquire GPS function (only called once location permission is granted)
    fun acquireLocation() {
        val hasFine = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED
        val hasCoarse = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED
        if (!hasFine && !hasCoarse) {
            gpsStatusMessage = "Location permission is required to capture coordinates."
            return
        }
        isAcquiringGps = true
        gpsStatusMessage = "Acquiring a fresh GPS fix..."
        // Drop the previous fix first: an old position must never be shown or saved as the
        // result of this request, including when the request fails.
        latitude = null
        longitude = null
        accuracyMeters = null
        fixTimeMillis = null
        fixIsMock = false
        // Approximate-only grants (Android 12+) cannot use high-accuracy GPS.
        val priority = if (hasFine) Priority.PRIORITY_HIGH_ACCURACY else Priority.PRIORITY_BALANCED_POWER_ACCURACY
        // The first fix after the receiver starts is often the least accurate, so fixes are collected
        // for a short time and the most accurate one is kept. maxUpdateAge 0 = never answer from the
        // location cache; every fix is newly computed.
        val request = LocationRequest.Builder(priority, GPS_SAMPLE_INTERVAL_MS)
            .setMinUpdateIntervalMillis(GPS_SAMPLE_INTERVAL_MS / 2)
            .setMaxUpdateAgeMillis(0)
            .build()
        Log.i(GPS_LOG_TAG, "sampling fresh fixes: priority=${if (hasFine) "HIGH_ACCURACY" else "BALANCED (approximate permission)"} " +
            "maxUpdateAgeMs=0 timeoutMs=$GPS_REQUEST_TIMEOUT_MS settleMs=$GPS_SETTLE_MS inspection=$localId")
        stopGpsSampling()
        var best: Location? = null
        var done = false
        fun accuracyOf(loc: Location) = if (loc.hasAccuracy()) loc.accuracy else Float.MAX_VALUE
        fun finish() {
            if (done) return
            done = true
            stopGpsSampling()
            isAcquiringGps = false
            val kept = best
            if (kept == null) {
                Log.w(GPS_LOG_TAG, "no fix within ${GPS_REQUEST_TIMEOUT_MS / 1000}s (no cached location used)")
                gpsStatusMessage = "No GPS fix yet. Move to open sky, check that Location is on, and try again."
                return
            }
            Log.i(GPS_LOG_TAG, "kept fix: lat=${kept.latitude} lon=${kept.longitude} accuracy=±${kept.accuracy}m inspection=$localId")
            gpsStatusMessage = "GPS Acquired: ±%.1f m accuracy".format(kept.accuracy) +
                if (fixIsMock) " (MOCK location: a mock-location app is active)" else ""
        }
        val callback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                if (done) return
                for (loc in result.locations) {
                    val ageMs = (SystemClock.elapsedRealtimeNanos() - loc.elapsedRealtimeNanos) / 1_000_000
                    val fresh = ageMs <= GPS_FRESH_MAX_AGE_MS
                    val mock = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) loc.isMock else @Suppress("DEPRECATION") loc.isFromMockProvider
                    Log.i(GPS_LOG_TAG, "fix ${if (fresh) "FRESH" else "CACHED"}: lat=${loc.latitude} lon=${loc.longitude} " +
                        "accuracy=±${loc.accuracy}m provider=${loc.provider} fixTime=${java.time.Instant.ofEpochMilli(loc.time)} " +
                        "ageMs=$ageMs mock=$mock inspection=$localId")
                    // Should not happen with maxUpdateAge 0; if it does, refuse the old position.
                    if (!fresh) continue
                    val previous = best
                    if (previous != null && accuracyOf(loc) >= accuracyOf(previous)) continue
                    best = loc
                    latitude = loc.latitude
                    longitude = loc.longitude
                    accuracyMeters = if (loc.hasAccuracy()) loc.accuracy else null
                    fixTimeMillis = System.currentTimeMillis() - ageMs
                    fixIsMock = mock
                    gpsStatusMessage = "Improving accuracy: ±%.1f m so far. Hold still...".format(loc.accuracy)
                    if (previous == null) {
                        gpsSampling.jobs = gpsSampling.jobs + coroutineScope.launch {
                            delay(GPS_SETTLE_MS)
                            finish()
                        }
                    }
                }
                if (best?.let { accuracyOf(it) <= GPS_GOOD_ACCURACY_M } == true) finish()
            }
        }
        gpsSampling.callback = callback
        gpsSampling.jobs = listOf(coroutineScope.launch {
            delay(GPS_REQUEST_TIMEOUT_MS)
            finish()
        })
        try {
            fusedLocationClient.requestLocationUpdates(request, callback, Looper.getMainLooper())
                .addOnFailureListener { e ->
                    done = true
                    stopGpsSampling()
                    isAcquiringGps = false
                    Log.e(GPS_LOG_TAG, "requestLocationUpdates failed (no cached location used)", e)
                    gpsStatusMessage = "GPS Error: ${e.message}"
                }
        } catch (e: SecurityException) {
            // Permission revoked between the check and the call.
            done = true
            stopGpsSampling()
            isAcquiringGps = false
            gpsStatusMessage = "Location permission is required to capture coordinates."
        }
    }

    // Runtime permissions are requested contextually, when the user taps the feature.
    val requestLocationPermission = rememberPermissionRequest(LOCATION_PERMISSIONS, requireAll = false) { result ->
        locationPermanentlyDenied = result == PermissionResult.PERMANENTLY_DENIED
        when (result) {
            PermissionResult.GRANTED -> acquireLocation()
            PermissionResult.DENIED ->
                gpsStatusMessage = "Location permission denied. Tap 'Acquire' again to allow it."
            PermissionResult.PERMANENTLY_DENIED ->
                gpsStatusMessage = "Location permission is blocked. Enable it in App Settings."
        }
    }

    val requestCameraPermission = rememberPermissionRequest(arrayOf(Manifest.permission.CAMERA), requireAll = true) { result ->
        cameraPermanentlyDenied = result == PermissionResult.PERMANENTLY_DENIED
        when (result) {
            PermissionResult.GRANTED -> {
                cameraPermissionMessage = null
                onNavigateToCamera(localId)
            }
            PermissionResult.DENIED ->
                cameraPermissionMessage = "Camera permission is required to capture photo evidence. Tap Capture Photo Evidence again to allow it."
            PermissionResult.PERMANENTLY_DENIED ->
                cameraPermissionMessage = "Camera permission is blocked. Enable it in App Settings to capture photo evidence."
        }
    }

    // Same data and persistence as before; only the status passed in differs.
    fun buildInspection(status: SyncStatus) = Inspection(
        localId = localId,
        clientId = clientId,
        roadId = selectedRoad?.id,
        roadName = selectedRoad?.name,
        segmentId = selectedSegment?.id,
        segmentNumber = selectedSegment?.segmentNumber,
        inspectorId = "",
        latitude = latitude,
        longitude = longitude,
        accuracyMeters = accuracyMeters,
        notes = notes.ifBlank { null },
        syncStatus = status
    ).also {
        val ageS = fixTimeMillis?.let { t -> (System.currentTimeMillis() - t) / 1000 }
        Log.i(GPS_LOG_TAG, "saving inspection=$localId status=$status lat=$latitude lon=$longitude " +
            "accuracy=${accuracyMeters?.let { a -> "±${a}m" } ?: "none"} fixAgeS=${ageS ?: "no fix"} mock=$fixIsMock")
    }

    val road = selectedRoad
    val segment = selectedSegment
    val lat = latitude
    val lon = longitude
    val accuracy = accuracyMeters
    val hasGps = lat != null && lon != null
    val stepsDone = listOf(road != null, hasGps, mediaList.isNotEmpty(), notes.isNotBlank()).count { it }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .glassBackground()
    ) {
        CommonTopBar(
            title = "New Inspection",
            canNavigateBack = true,
            onNavigateBack = onNavigateBack
        )

        // Progress across the four parts of the form
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(GlassBar)
                .padding(horizontal = 16.dp, vertical = 10.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = "$stepsDone of 4 steps filled",
                    color = TextSecondary,
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.weight(1f)
                )
                Text("${stepsDone * 25}%", color = AccentBright, style = CodeSm)
            }
            Spacer(modifier = Modifier.height(6.dp))
            LinearProgressIndicator(
                progress = { stepsDone / 4f },
                color = Accent,
                trackColor = SurfaceLowest,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp))
            )
        }

        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(scrollState)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            if (errorMessage != null) {
                MessageCard(kind = MessageKind.ERROR, title = null, message = errorMessage ?: "")
            }

            // ---- Step 1: road and segment --------------------------------------------------
            StepCard(number = 1, title = "Select Road & Segment", done = road != null) {
                if (roads.isEmpty()) {
                    MessageCard(
                        kind = MessageKind.WARNING,
                        title = "No roads available",
                        message = "Roads are downloaded from the server. Connect and tap retry.",
                        actionLabel = "Retry",
                        onAction = { coroutineScope.launch { roadRepository.syncRoadsFromServer() } }
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                }

                ExposedDropdownMenuBox(
                    expanded = roadDropdownExpanded,
                    onExpandedChange = { roadDropdownExpanded = !roadDropdownExpanded }
                ) {
                    OutlinedTextField(
                        value = road?.let { r -> if (r.roadCode.isNullOrBlank()) r.name else "${r.name} (${r.roadCode})" }
                            ?: "Select a road...",
                        onValueChange = {},
                        readOnly = true,
                        singleLine = true,
                        label = { Text("Road") },
                        leadingIcon = { Icon(Icons.Default.Route, contentDescription = null) },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = roadDropdownExpanded) },
                        colors = fieldTextFieldColors(),
                        shape = MaterialTheme.shapes.medium,
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor()
                    )
                    ExposedDropdownMenu(
                        expanded = roadDropdownExpanded,
                        onDismissRequest = { roadDropdownExpanded = false },
                        modifier = Modifier.background(SurfaceCard)
                    ) {
                        roads.forEach { item ->
                            DropdownMenuItem(
                                text = {
                                    Column {
                                        Text(item.name, color = TextPrimary, style = MaterialTheme.typography.bodyMedium)
                                        if (!item.roadCode.isNullOrBlank()) {
                                            Text(item.roadCode, color = TextSecondary, style = CodeSm)
                                        }
                                    }
                                },
                                onClick = {
                                    selectedRoad = item
                                    selectedSegment = null
                                    roadDropdownExpanded = false
                                    coroutineScope.launch {
                                        roadRepository.syncSegmentsFromServer(item.id)
                                    }
                                }
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                ExposedDropdownMenuBox(
                    expanded = segmentDropdownExpanded,
                    onExpandedChange = { if (selectedRoad != null) segmentDropdownExpanded = !segmentDropdownExpanded }
                ) {
                    OutlinedTextField(
                        value = if (segment != null) "Segment #${segment.segmentNumber}" else "Select segment (optional)",
                        onValueChange = {},
                        readOnly = true,
                        singleLine = true,
                        enabled = road != null,
                        label = { Text("Segment") },
                        leadingIcon = { Icon(Icons.Default.Timeline, contentDescription = null) },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = segmentDropdownExpanded) },
                        colors = fieldTextFieldColors(),
                        shape = MaterialTheme.shapes.medium,
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor()
                    )
                    ExposedDropdownMenu(
                        expanded = segmentDropdownExpanded,
                        onDismissRequest = { segmentDropdownExpanded = false },
                        modifier = Modifier.background(SurfaceCard)
                    ) {
                        if (segments.isEmpty()) {
                            DropdownMenuItem(
                                text = { Text("No segments for this road", color = TextSecondary) },
                                onClick = { segmentDropdownExpanded = false }
                            )
                        }
                        segments.forEach { seg ->
                            DropdownMenuItem(
                                text = { Text("Segment #${seg.segmentNumber} (${seg.surfaceType ?: "ASPHALT"})", color = TextPrimary) },
                                onClick = {
                                    selectedSegment = seg
                                    segmentDropdownExpanded = false
                                }
                            )
                        }
                    }
                }
            }

            // ---- Step 2: GPS ---------------------------------------------------------------
            StepCard(
                number = 2,
                title = "Capture GPS",
                done = hasGps,
                trailing = {
                    when {
                        isAcquiringGps -> StatusPill("ACQUIRING", WarningAmber, Icons.Default.GpsNotFixed)
                        hasGps -> StatusPill(
                            label = if (accuracy != null) "FIX ±%.1f m".format(accuracy) else "FIX",
                            color = accuracyColor(accuracy),
                            icon = Icons.Default.GpsFixed
                        )
                        else -> StatusPill("NO FIX", TextSecondary, Icons.Default.GpsOff)
                    }
                }
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(SurfaceLowest, RoundedCornerShape(12.dp))
                        .border(1.dp, BorderDark, RoundedCornerShape(12.dp))
                        .padding(12.dp)
                ) {
                    Row(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.weight(1f)) {
                            FieldLabel("Latitude")
                            Text(
                                text = if (lat != null) "%.6f".format(lat) else "—",
                                color = if (hasGps) AccentBright else TextMuted,
                                style = CodeLg
                            )
                        }
                        Column(modifier = Modifier.weight(1f)) {
                            FieldLabel("Longitude")
                            Text(
                                text = if (lon != null) "%.6f".format(lon) else "—",
                                color = if (hasGps) AccentBright else TextMuted,
                                style = CodeLg
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(10.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        FieldLabel("Accuracy")
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = if (accuracy != null) "±%.1f m (%s)".format(accuracy, accuracyLabel(accuracy)) else "—",
                            color = accuracyColor(accuracy),
                            style = CodeMd
                        )
                    }
                    if (isAcquiringGps) {
                        Spacer(modifier = Modifier.height(10.dp))
                        LinearProgressIndicator(
                            color = WarningAmber,
                            trackColor = SurfaceCard,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(4.dp)
                                .clip(RoundedCornerShape(2.dp))
                        )
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = gpsStatusMessage,
                    color = when {
                        isAcquiringGps -> WarningAmber
                        hasGps -> accuracyColor(accuracy)
                        else -> TextSecondary
                    },
                    style = MaterialTheme.typography.bodySmall
                )

                val fixTime = fixTimeMillis
                if (hasGps && fixTime != null) {
                    val ageMin = ((nowMillis - fixTime) / 60_000).coerceAtLeast(0)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Fix taken at " + java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.US).format(java.util.Date(fixTime)) +
                            if (ageMin >= GPS_STALE_WARNING_MIN) " · $ageMin min ago. Re-acquire if you have moved." else "",
                        color = if (ageMin >= GPS_STALE_WARNING_MIN || fixIsMock) WarningAmber else TextMuted,
                        style = CodeSm
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))
                SecondaryButton(
                    text = if (isAcquiringGps) "Acquiring..." else if (hasGps) "Re-acquire GPS" else "Acquire GPS",
                    icon = Icons.Default.MyLocation,
                    onClick = { requestLocationPermission() },
                    enabled = !isAcquiringGps,
                    contentColor = AccentBright,
                    modifier = Modifier.fillMaxWidth()
                )

                if (locationPermanentlyDenied) {
                    Spacer(modifier = Modifier.height(6.dp))
                    TextButton(onClick = { context.openAppSettings() }) {
                        Icon(Icons.Default.Settings, contentDescription = null, tint = AccentBright, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Open App Settings", color = AccentBright, style = MaterialTheme.typography.labelLarge)
                    }
                }
            }

            // ---- Step 3: photos ------------------------------------------------------------
            StepCard(
                number = 3,
                title = "Capture Photos",
                done = mediaList.isNotEmpty(),
                trailing = {
                    Text(
                        text = if (mediaList.size == 1) "1 photo" else "${mediaList.size} photos",
                        color = if (mediaList.isEmpty()) TextSecondary else SuccessEmerald,
                        style = CodeSm
                    )
                }
            ) {
                SecondaryButton(
                    text = if (mediaList.isEmpty()) "Capture Photo Evidence" else "Capture More Photos",
                    icon = Icons.Default.PhotoCamera,
                    // Requests CAMERA if needed, then opens the CameraX capture screen
                    onClick = { requestCameraPermission() },
                    contentColor = AccentBright,
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(10.dp))
                if (mediaList.isEmpty()) {
                    Text(
                        "No photos captured yet. Frame the damage with some surrounding road visible.",
                        color = TextSecondary,
                        style = MaterialTheme.typography.bodySmall
                    )
                } else {
                    Row(
                        modifier = Modifier.horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        mediaList.forEach { media ->
                            Column(modifier = Modifier.width(112.dp)) {
                                LocalThumbnail(
                                    path = media.localFilePath,
                                    contentDescription = "Captured photo",
                                    modifier = Modifier
                                        .size(width = 112.dp, height = 84.dp)
                                        .clip(RoundedCornerShape(10.dp))
                                        .border(1.dp, BorderDark, RoundedCornerShape(10.dp))
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = java.io.File(media.localFilePath).name,
                                    color = TextOnSurface,
                                    style = CodeSm,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
                                )
                                Text(formatFileSize(media.fileSizeBytes), color = TextSecondary, style = CodeSm)
                            }
                        }
                    }
                }

                cameraPermissionMessage?.let { message ->
                    Spacer(modifier = Modifier.height(10.dp))
                    MessageCard(
                        kind = MessageKind.WARNING,
                        title = "Camera permission",
                        message = message,
                        actionLabel = if (cameraPermanentlyDenied) "Open App Settings" else null,
                        onAction = if (cameraPermanentlyDenied) ({ context.openAppSettings() }) else null
                    )
                }
            }

            // ---- Step 4: notes -------------------------------------------------------------
            StepCard(number = 4, title = "Inspection Details", done = notes.isNotBlank()) {
                OutlinedTextField(
                    value = notes,
                    onValueChange = { notes = it },
                    label = { Text("Inspector notes (optional)") },
                    placeholder = { Text("Field observations, weather, traffic notes...", color = TextMuted) },
                    minLines = 3,
                    maxLines = 6,
                    colors = fieldTextFieldColors(),
                    shape = MaterialTheme.shapes.medium,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text("${notes.length} characters", color = TextMuted, style = CodeSm)
            }

            // ---- Review --------------------------------------------------------------------
            FieldCard {
                SectionTitle("Review", icon = Icons.Default.FactCheck)
                Spacer(modifier = Modifier.height(10.dp))
                ReviewRow("Road", road?.name ?: "Not selected", road != null)
                ReviewRow("Segment", segment?.let { "Segment #${it.segmentNumber}" } ?: "Not selected (optional)", segment != null, optional = true)
                ReviewRow(
                    "GPS",
                    if (lat != null && lon != null) {
                        "%.6f, %.6f".format(lat, lon) + (accuracy?.let { "  ±%.1f m".format(it) } ?: "")
                    } else "Not captured",
                    hasGps
                )
                ReviewRow("Photos", if (mediaList.isEmpty()) "None captured" else "${mediaList.size} captured", mediaList.isNotEmpty())
                ReviewRow("Notes", if (notes.isBlank()) "None (optional)" else "${notes.length} characters", notes.isNotBlank(), optional = true)
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "After upload the inspection is submitted to the server. AI analysis is started from the operations console and its result appears in the inspection's detail screen.",
                    color = TextSecondary,
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }

        // Sticky actions
        Column(modifier = Modifier.background(GlassBar)) {
            HorizontalDivider(color = BorderDark)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 10.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                SecondaryButton(
                    text = "Save Draft",
                    enabled = !isSaving,
                    onClick = {
                        isSaving = true
                        coroutineScope.launch {
                            inspectionRepository.createLocalDraft(buildInspection(SyncStatus.LOCAL_DRAFT))
                            isSaving = false
                            onNavigateBack()
                        }
                    },
                    modifier = Modifier.weight(1f)
                )
                PrimaryButton(
                    text = "Queue & Sync",
                    icon = Icons.Default.CloudUpload,
                    loading = isSaving,
                    onClick = {
                        isSaving = true
                        coroutineScope.launch {
                            inspectionRepository.createLocalDraft(buildInspection(SyncStatus.QUEUED))
                            inspectionRepository.queueForUpload(localId)
                            syncRepository.triggerManualSync()
                            isSaving = false
                            onNavigateBack()
                        }
                    },
                    modifier = Modifier.weight(1.25f)
                )
            }
        }
    }
}

@Composable
private fun StepCard(
    number: Int,
    title: String,
    done: Boolean,
    trailing: @Composable (() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit
) {
    FieldCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(26.dp)
                    .clip(CircleShape)
                    .background(if (done) SuccessEmerald else SurfaceCard),
                contentAlignment = Alignment.Center
            ) {
                if (done) {
                    Icon(Icons.Default.Check, contentDescription = "Step filled", tint = OnSuccess, modifier = Modifier.size(16.dp))
                } else {
                    Text(number.toString(), color = TextSecondary, style = CodeSm, fontWeight = FontWeight.Bold)
                }
            }
            Spacer(modifier = Modifier.width(10.dp))
            Text(
                text = "STEP $number · ${title.uppercase()}",
                color = TextPrimary,
                style = MaterialTheme.typography.labelLarge,
                modifier = Modifier.weight(1f)
            )
            if (trailing != null) {
                Spacer(modifier = Modifier.width(8.dp))
                trailing()
            }
        }
        Spacer(modifier = Modifier.height(12.dp))
        content()
    }
}

@Composable
private fun ReviewRow(label: String, value: String, filled: Boolean, optional: Boolean = false) {
    val icon: ImageVector
    val tint: Color
    when {
        filled -> { icon = Icons.Default.CheckCircle; tint = SuccessEmerald }
        optional -> { icon = Icons.Default.RemoveCircleOutline; tint = TextMuted }
        else -> { icon = Icons.Default.WarningAmber; tint = WarningAmber }
    }
    Row(modifier = Modifier.padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(16.dp))
        Spacer(modifier = Modifier.width(8.dp))
        Text(label, color = TextSecondary, style = MaterialTheme.typography.bodySmall, modifier = Modifier.width(72.dp))
        Text(
            text = value,
            color = if (filled) TextPrimary else TextSecondary,
            style = if (label == "GPS") CodeSm else MaterialTheme.typography.bodySmall,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis
        )
    }
}

private val LOCATION_PERMISSIONS = arrayOf(
    Manifest.permission.ACCESS_FINE_LOCATION,
    Manifest.permission.ACCESS_COARSE_LOCATION
)
