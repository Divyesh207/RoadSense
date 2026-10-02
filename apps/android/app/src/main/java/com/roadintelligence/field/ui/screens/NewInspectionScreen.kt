package com.roadintelligence.field.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import android.location.Location
import android.util.Log
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.roadintelligence.field.domain.model.*
import com.roadintelligence.field.domain.repository.InspectionRepository
import com.roadintelligence.field.domain.repository.RoadRepository
import com.roadintelligence.field.domain.repository.SyncRepository
import com.roadintelligence.field.ui.components.CommonTopBar
import com.roadintelligence.field.ui.permissions.PermissionResult
import com.roadintelligence.field.ui.permissions.openAppSettings
import com.roadintelligence.field.ui.permissions.rememberPermissionRequest
import com.roadintelligence.field.ui.theme.*
import kotlinx.coroutines.launch
import java.util.UUID

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NewInspectionScreen(
    inspectionRepository: InspectionRepository,
    roadRepository: RoadRepository,
    syncRepository: SyncRepository,
    onNavigateBack: () -> Unit,
    onNavigateToCamera: (String) -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val scrollState = rememberScrollState()

    // Local inspection state
    val localId = remember { UUID.randomUUID().toString() }
    val clientId = remember { UUID.randomUUID().toString() }

    val roads by roadRepository.getCachedRoads().collectAsState(initial = emptyList())
    var selectedRoad by remember { mutableStateOf<Road?>(null) }
    var roadDropdownExpanded by remember { mutableStateOf(false) }

    val segments by (if (selectedRoad != null) roadRepository.getCachedSegments(selectedRoad!!.id) else null)
        ?.collectAsState(initial = emptyList()) ?: remember { mutableStateOf(emptyList()) }
    var selectedSegment by remember { mutableStateOf<RoadSegment?>(null) }
    var segmentDropdownExpanded by remember { mutableStateOf(false) }

    var latitude by remember { mutableStateOf<Double?>(null) }
    var longitude by remember { mutableStateOf<Double?>(null) }
    var accuracyMeters by remember { mutableStateOf<Float?>(null) }
    var isAcquiringGps by remember { mutableStateOf(false) }
    var gpsStatusMessage by remember { mutableStateOf("Tap 'Acquire GPS' to capture coordinates") }
    var locationPermanentlyDenied by remember { mutableStateOf(false) }

    var cameraPermissionMessage by remember { mutableStateOf<String?>(null) }
    var cameraPermanentlyDenied by remember { mutableStateOf(false) }

    var notes by remember { mutableStateOf("") }
    var mediaList by remember { mutableStateOf<List<InspectionMedia>>(emptyList()) }
    var isSaving by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    // Load initial roads and media
    LaunchedEffect(Unit) {
        roadRepository.syncRoadsFromServer()
        mediaList = inspectionRepository.getMediaForInspection(localId)
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
        gpsStatusMessage = "Acquiring GPS fix from satellites..."
        // Approximate-only grants (Android 12+) cannot use high-accuracy GPS.
        val priority = if (hasFine) Priority.PRIORITY_HIGH_ACCURACY else Priority.PRIORITY_BALANCED_POWER_ACCURACY
        val fusedLocationClient = LocationServices.getFusedLocationProviderClient(context)
        try {
            fusedLocationClient.getCurrentLocation(priority, null)
                .addOnSuccessListener { loc: Location? ->
                    isAcquiringGps = false
                    if (loc != null) {
                        latitude = loc.latitude
                        longitude = loc.longitude
                        accuracyMeters = loc.accuracy
                        gpsStatusMessage = "GPS Acquired: ±%.1f m accuracy".format(loc.accuracy)
                    } else {
                        gpsStatusMessage = "Could not obtain GPS fix. Ensure location is enabled."
                    }
                }
                .addOnFailureListener { e ->
                    isAcquiringGps = false
                    Log.e("NewInspection", "getCurrentLocation failed", e)
                    gpsStatusMessage = "GPS Error: ${e.message}"
                }
        } catch (e: SecurityException) {
            // Permission revoked between the check and the call.
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
                cameraPermissionMessage = "Camera permission is required to capture photo evidence. Tap the card again to allow it."
            PermissionResult.PERMANENTLY_DENIED ->
                cameraPermissionMessage = "Camera permission is blocked. Enable it in App Settings to capture photo evidence."
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
    ) {
        CommonTopBar(
            title = "New Road Inspection",
            canNavigateBack = true,
            onNavigateBack = onNavigateBack
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(16.dp)
        ) {
            if (errorMessage != null) {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = ErrorRose.copy(alpha = 0.15f),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        text = errorMessage ?: "",
                        color = ErrorRose,
                        fontSize = 13.sp,
                        modifier = Modifier.padding(12.dp)
                    )
                }
                Spacer(modifier = Modifier.height(16.dp))
            }

            // 1. Road Selection
            Text("1. Select Road & Segment", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 15.sp)
            Spacer(modifier = Modifier.height(8.dp))

            ExposedDropdownMenuBox(
                expanded = roadDropdownExpanded,
                onExpandedChange = { roadDropdownExpanded = !roadDropdownExpanded }
            ) {
                OutlinedTextField(
                    value = selectedRoad?.name ?: "Select a road...",
                    onValueChange = {},
                    readOnly = true,
                    label = { Text("Road") },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = roadDropdownExpanded) },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = PrimaryCyan,
                        unfocusedBorderColor = BorderDark,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary
                    ),
                    modifier = Modifier
                        .fillMaxWidth()
                        .menuAnchor()
                )
                ExposedDropdownMenu(
                    expanded = roadDropdownExpanded,
                    onDismissRequest = { roadDropdownExpanded = false },
                    modifier = Modifier.background(SurfaceDark)
                ) {
                    roads.forEach { road ->
                        DropdownMenuItem(
                            text = { Text(road.name, color = TextPrimary) },
                            onClick = {
                                selectedRoad = road
                                selectedSegment = null
                                roadDropdownExpanded = false
                                coroutineScope.launch {
                                    roadRepository.syncSegmentsFromServer(road.id)
                                }
                            }
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Segment Dropdown
            ExposedDropdownMenuBox(
                expanded = segmentDropdownExpanded,
                onExpandedChange = { if (selectedRoad != null) segmentDropdownExpanded = !segmentDropdownExpanded }
            ) {
                OutlinedTextField(
                    value = if (selectedSegment != null) "Segment #${selectedSegment!!.segmentNumber}" else "Select road segment (optional)...",
                    onValueChange = {},
                    readOnly = true,
                    enabled = selectedRoad != null,
                    label = { Text("Segment") },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = segmentDropdownExpanded) },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = PrimaryCyan,
                        unfocusedBorderColor = BorderDark,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary
                    ),
                    modifier = Modifier
                        .fillMaxWidth()
                        .menuAnchor()
                )
                ExposedDropdownMenu(
                    expanded = segmentDropdownExpanded,
                    onDismissRequest = { segmentDropdownExpanded = false },
                    modifier = Modifier.background(SurfaceDark)
                ) {
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

            Spacer(modifier = Modifier.height(24.dp))

            // 2. GPS Location
            Text("2. GPS Coordinates", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 15.sp)
            Spacer(modifier = Modifier.height(8.dp))

            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = SurfaceDark,
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            if (latitude != null && longitude != null) {
                                Text(
                                    text = "%.6f, %.6f".format(latitude, longitude),
                                    fontSize = 16.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = PrimaryCyan
                                )
                                Text(
                                    text = gpsStatusMessage,
                                    fontSize = 12.sp,
                                    color = if ((accuracyMeters ?: 100f) < 15f) SuccessEmerald else WarningAmber
                                )
                            } else {
                                Text("No GPS Fixed", fontSize = 15.sp, color = TextSecondary)
                                Text(gpsStatusMessage, fontSize = 12.sp, color = TextMuted)
                            }
                        }

                        Button(
                            onClick = { requestLocationPermission() },
                            enabled = !isAcquiringGps,
                            colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            if (isAcquiringGps) {
                                CircularProgressIndicator(color = Color.Black, modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                            } else {
                                Icon(Icons.Default.MyLocation, contentDescription = null, tint = Color.Black, modifier = Modifier.size(18.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Acquire", color = Color.Black, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                            }
                        }
                    }

                    if (locationPermanentlyDenied) {
                        TextButton(onClick = { context.openAppSettings() }) {
                            Text("Open App Settings", color = PrimaryCyan, fontSize = 13.sp)
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // 3. Camera Evidence
            Text("3. Visual Evidence (CameraX)", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 15.sp)
            Spacer(modifier = Modifier.height(8.dp))

            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable {
                        // Requests CAMERA if needed, then opens the CameraX capture screen
                        requestCameraPermission()
                    },
                color = SurfaceDark,
                shape = RoundedCornerShape(12.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, BorderDark)
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(44.dp)
                            .background(PrimaryCyan.copy(alpha = 0.15f), shape = RoundedCornerShape(8.dp)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(Icons.Default.CameraAlt, contentDescription = null, tint = PrimaryCyan)
                    }
                    Spacer(modifier = Modifier.width(14.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Capture Photo Evidence", color = TextPrimary, fontWeight = FontWeight.SemiBold)
                        Text(
                            text = if (mediaList.isEmpty()) "No photos captured yet" else "${mediaList.size} photo(s) captured",
                            color = if (mediaList.isEmpty()) TextMuted else SuccessEmerald,
                            fontSize = 12.sp
                        )
                    }
                    Icon(Icons.Default.ChevronRight, contentDescription = null, tint = TextMuted)
                }
            }

            cameraPermissionMessage?.let { message ->
                Spacer(modifier = Modifier.height(8.dp))
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = WarningAmber.copy(alpha = 0.12f),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(message, color = WarningAmber, fontSize = 13.sp)
                        if (cameraPermanentlyDenied) {
                            TextButton(onClick = { context.openAppSettings() }) {
                                Text("Open App Settings", color = PrimaryCyan, fontSize = 13.sp)
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // 4. Notes
            Text("4. Inspector Notes", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 15.sp)
            Spacer(modifier = Modifier.height(8.dp))

            OutlinedTextField(
                value = notes,
                onValueChange = { notes = it },
                label = { Text("Field observations, weather, traffic notes...") },
                minLines = 3,
                maxLines = 5,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = PrimaryCyan,
                    unfocusedBorderColor = BorderDark,
                    focusedTextColor = TextPrimary,
                    unfocusedTextColor = TextPrimary
                ),
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(28.dp))

            // Actions
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Save Draft Button
                OutlinedButton(
                    onClick = {
                        isSaving = true
                        coroutineScope.launch {
                            val draft = Inspection(
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
                                syncStatus = SyncStatus.LOCAL_DRAFT
                            )
                            inspectionRepository.createLocalDraft(draft)
                            isSaving = false
                            onNavigateBack()
                        }
                    },
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = TextPrimary),
                    modifier = Modifier
                        .weight(1f)
                        .height(48.dp)
                ) {
                    Text("Save Draft")
                }

                // Queue Sync Button
                Button(
                    onClick = {
                        isSaving = true
                        coroutineScope.launch {
                            val draft = Inspection(
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
                                syncStatus = SyncStatus.QUEUED
                            )
                            inspectionRepository.createLocalDraft(draft)
                            inspectionRepository.queueForUpload(localId)
                            syncRepository.triggerManualSync()
                            isSaving = false
                            onNavigateBack()
                        }
                    },
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan),
                    modifier = Modifier
                        .weight(1f)
                        .height(48.dp)
                ) {
                    Icon(Icons.Default.CloudUpload, contentDescription = null, tint = Color.Black, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Queue & Sync", color = Color.Black, fontWeight = FontWeight.Bold)
                }
            }

            Spacer(modifier = Modifier.height(24.dp))
        }
    }
}

private val LOCATION_PERMISSIONS = arrayOf(
    Manifest.permission.ACCESS_FINE_LOCATION,
    Manifest.permission.ACCESS_COARSE_LOCATION
)
