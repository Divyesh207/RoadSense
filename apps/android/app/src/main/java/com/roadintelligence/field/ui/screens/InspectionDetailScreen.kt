package com.roadintelligence.field.ui.screens

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.roadintelligence.field.data.repository.InspectionRemoteRepository
import com.roadintelligence.field.data.repository.ServerDetection
import com.roadintelligence.field.data.repository.ServerInspectionState
import com.roadintelligence.field.domain.model.Inspection
import com.roadintelligence.field.domain.model.InspectionMedia
import com.roadintelligence.field.domain.model.SyncStatus
import com.roadintelligence.field.domain.model.UploadStatus
import com.roadintelligence.field.domain.repository.AuthRepository
import com.roadintelligence.field.domain.repository.InspectionRepository
import com.roadintelligence.field.domain.repository.SyncRepository
import com.roadintelligence.field.ui.components.*
import com.roadintelligence.field.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.io.File

/** What the server check says about one photo stored on this device. */
enum class ServerConfirmation { CONFIRMED, NOT_LISTED, NOT_UPLOADED, UNAVAILABLE }

@Composable
fun InspectionDetailScreen(
    localId: String,
    authRepository: AuthRepository,
    inspectionRepository: InspectionRepository,
    inspectionRemote: InspectionRemoteRepository,
    syncRepository: SyncRepository,
    onNavigateBack: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    val inspection by inspectionRepository.getInspectionById(localId).collectAsState(initial = null)

    // Server-side state (status, media list, detections); only exists once the upload has started.
    val serverId = inspection?.serverId?.takeIf { it.isNotEmpty() }
    var serverState by remember { mutableStateOf<ServerInspectionState?>(null) }
    var serverError by remember { mutableStateOf<String?>(null) }
    var serverLoading by remember { mutableStateOf(false) }
    var refreshTick by remember { mutableStateOf(0) }

    LaunchedEffect(serverId, refreshTick, inspection?.syncStatus) {
        if (serverId == null) return@LaunchedEffect
        serverState = serverState ?: inspectionRemote.cached(serverId)
        while (true) {
            serverLoading = true
            inspectionRemote.fetchState(serverId).fold(
                onSuccess = { serverState = it; serverError = null },
                onFailure = { serverError = it.message }
            )
            serverLoading = false
            // Keep checking while the server is still working on this inspection.
            val status = serverState?.status?.uppercase()
            if (status != "SUBMITTED" && status != "PROCESSING" && status != "UPLOADING") break
            delay(10_000)
        }
    }

    var viewerIndex by remember { mutableStateOf<Int?>(null) }
    var confirmDelete by remember { mutableStateOf(false) }

    BackHandler {
        if (viewerIndex != null) viewerIndex = null else onNavigateBack()
    }

    Box(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .glassBackground()
        ) {
            CommonTopBar(
                title = "Inspection Detail",
                canNavigateBack = true,
                onNavigateBack = onNavigateBack,
                actions = {
                    if (serverId != null) {
                        IconButton(onClick = { refreshTick++ }, enabled = !serverLoading) {
                            if (serverLoading) {
                                CircularProgressIndicator(color = Accent, modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
                            } else {
                                Icon(Icons.Default.Refresh, contentDescription = "Refresh server status", tint = AccentBright)
                            }
                        }
                    }
                }
            )

            val insp = inspection
            if (insp == null) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = Accent)
                }
            } else {
                val media = insp.mediaList
                val state = serverState
                val detections = state?.detections ?: emptyList()

                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    item { HeaderCard(insp, state, authRepository) }

                    if (insp.lastSyncError != null) {
                        item {
                            MessageCard(
                                kind = MessageKind.ERROR,
                                title = "Upload failed",
                                message = insp.lastSyncError + "\n\nThe inspection and its photos are still saved on this device.",
                                actionLabel = if (insp.syncStatus == SyncStatus.UPLOAD_FAILED) "Retry Upload" else null,
                                onAction = if (insp.syncStatus == SyncStatus.UPLOAD_FAILED) ({
                                    coroutineScope.launch {
                                        inspectionRepository.queueForUpload(insp.localId)
                                        syncRepository.triggerManualSync()
                                    }
                                }) else null
                            )
                        }
                    }

                    item { PipelineCard(insp, state) }

                    if (serverId != null) {
                        item {
                            AiResultsCard(
                                state = state,
                                loading = serverLoading,
                                error = serverError,
                                media = media,
                                onRetry = { refreshTick++ },
                                onOpenPhoto = { index -> viewerIndex = index }
                            )
                        }
                    }

                    item { GpsCard(insp) }

                    item {
                        FieldCard {
                            SectionTitle("Inspector Notes", icon = Icons.Default.Notes)
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(
                                text = insp.notes?.takeIf { it.isNotBlank() } ?: "No notes were recorded for this inspection.",
                                color = if (insp.notes.isNullOrBlank()) TextSecondary else TextOnSurface,
                                style = MaterialTheme.typography.bodyMedium
                            )
                        }
                    }

                    item {
                        PhotosCard(
                            media = media,
                            serverState = state,
                            serverChecked = serverId != null && state != null,
                            onOpen = { index -> viewerIndex = index }
                        )
                    }

                    // Actions (queue / retry / delete)
                    if (insp.syncStatus == SyncStatus.LOCAL_DRAFT || insp.syncStatus == SyncStatus.UPLOAD_FAILED) {
                        item {
                            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                PrimaryButton(
                                    text = if (insp.syncStatus == SyncStatus.UPLOAD_FAILED) "Retry Upload" else "Queue for Upload",
                                    icon = Icons.Default.Sync,
                                    onClick = {
                                        coroutineScope.launch {
                                            inspectionRepository.queueForUpload(insp.localId)
                                            syncRepository.triggerManualSync()
                                        }
                                    },
                                    modifier = Modifier.fillMaxWidth()
                                )
                                if (insp.syncStatus == SyncStatus.LOCAL_DRAFT || insp.syncStatus == SyncStatus.UPLOAD_FAILED) {
                                    SecondaryButton(
                                        text = if (insp.syncStatus == SyncStatus.UPLOAD_FAILED) "Delete Failed Inspection" else "Delete Draft",
                                        icon = Icons.Default.DeleteOutline,
                                        contentColor = ErrorRose,
                                        onClick = { confirmDelete = true },
                                        modifier = Modifier.fillMaxWidth()
                                    )
                                }
                            }
                        }
                    }

                    item { Spacer(modifier = Modifier.height(8.dp)) }
                }

                if (confirmDelete) {
                    AlertDialog(
                        onDismissRequest = { confirmDelete = false },
                        containerColor = SurfaceCard,
                        title = { Text("Delete this draft?", color = TextPrimary) },
                        text = { Text("The draft is removed from this device. It was never uploaded.", color = TextSecondary) },
                        confirmButton = {
                            TextButton(onClick = {
                                confirmDelete = false
                                coroutineScope.launch {
                                    inspectionRepository.deleteDraft(insp.localId)
                                    onNavigateBack()
                                }
                            }) { Text("Delete", color = ErrorRose) }
                        },
                        dismissButton = {
                            TextButton(onClick = { confirmDelete = false }) { Text("Cancel", color = TextOnSurface) }
                        }
                    )
                }
            }
        }

        // Full-screen photo viewer, drawn over the whole screen including the top bar.
        val current = inspection
        val index = viewerIndex
        if (current != null && index != null && index in current.mediaList.indices) {
            PhotoViewer(
                media = current.mediaList,
                startIndex = index,
                serverState = serverState,
                onClose = { viewerIndex = null }
            )
        }
    }
}

// ---------------------------------------------------------------------------------------------

@Composable
private fun HeaderCard(insp: Inspection, state: ServerInspectionState?, authRepository: AuthRepository) {
    // The inspector is the signed-in user of this device; the server's name is used once known.
    val inspector = state?.inspectorName?.takeIf { it.isNotBlank() }
        ?: authRepository.getCurrentSession()?.let { it.fullName.ifBlank { it.email } }

    FieldCard {
        Row(verticalAlignment = Alignment.Top) {
            Column(modifier = Modifier.weight(1f)) {
                FieldLabel("Inspection", color = AccentBright)
                Text(insp.displayId(), color = TextPrimary, style = CodeLg, fontWeight = FontWeight.Bold)
            }
            StatusBadge(status = insp.syncStatus)
        }
        if (!insp.serverId.isNullOrEmpty()) {
            Text(insp.serverId, color = TextMuted, style = CodeSm, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }

        Spacer(modifier = Modifier.height(12.dp))
        Text(
            text = insp.roadName ?: "Unassigned road",
            color = TextPrimary,
            style = MaterialTheme.typography.titleLarge
        )
        Spacer(modifier = Modifier.height(4.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.Timeline, contentDescription = null, tint = NeutralSoft, modifier = Modifier.size(14.dp))
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = insp.segmentNumber?.let { "Segment #$it" } ?: "No segment selected",
                color = if (insp.segmentNumber != null) NeutralSoft else TextSecondary,
                style = MaterialTheme.typography.bodyMedium
            )
        }

        Spacer(modifier = Modifier.height(12.dp))
        HorizontalDivider(color = BorderDark)
        Spacer(modifier = Modifier.height(12.dp))

        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            ValueTile("Captured", formatDateTime(insp.capturedAt), modifier = Modifier.weight(1f))
            ValueTile("Inspector", inspector ?: "—", modifier = Modifier.weight(1f), mono = false)
        }
    }
}

private enum class StepState { DONE, ACTIVE, WAITING, FAILED }

@Composable
private fun PipelineCard(insp: Inspection, state: ServerInspectionState?) {
    val uploaded = insp.mediaList.count { it.uploadStatus == UploadStatus.COMPLETED }
    val total = insp.mediaList.size
    val sync = insp.syncStatus
    val serverStatus = state?.status

    val uploadStep = when (sync) {
        SyncStatus.COMPLETED, SyncStatus.UPLOADED, SyncStatus.PROCESSING -> StepState.DONE
        SyncStatus.UPLOADING -> StepState.ACTIVE
        SyncStatus.UPLOAD_FAILED -> StepState.FAILED
        else -> StepState.WAITING
    }
    val submitStep = if (sync == SyncStatus.COMPLETED) StepState.DONE else StepState.WAITING
    val aiStep = when {
        sync != SyncStatus.COMPLETED -> StepState.WAITING
        isAnalysisFinished(serverStatus) -> StepState.DONE
        isAnalysisFailed(serverStatus) -> StepState.FAILED
        serverStatus?.uppercase() == "PROCESSING" -> StepState.ACTIVE
        else -> StepState.WAITING
    }

    FieldCard {
        SectionTitle("Processing Status", icon = Icons.Default.AccountTree)
        Spacer(modifier = Modifier.height(14.dp))
        Row(modifier = Modifier.fillMaxWidth()) {
            PipelineStep("Saved", "on device", StepState.DONE, Modifier.weight(1f))
            PipelineStep(
                "Upload",
                when (uploadStep) {
                    StepState.DONE -> "done"
                    StepState.ACTIVE -> "$uploaded of $total"
                    StepState.FAILED -> "failed"
                    StepState.WAITING -> if (sync == SyncStatus.QUEUED) "queued" else "not queued"
                },
                uploadStep, Modifier.weight(1f)
            )
            PipelineStep("Submitted", if (submitStep == StepState.DONE) "to server" else "waiting", submitStep, Modifier.weight(1f))
            PipelineStep(
                "AI analysis",
                when (aiStep) {
                    StepState.DONE -> "completed"
                    StepState.ACTIVE -> "running"
                    StepState.FAILED -> "failed"
                    StepState.WAITING -> "waiting"
                },
                aiStep, Modifier.weight(1f)
            )
        }

        if (sync == SyncStatus.UPLOADING && total > 0) {
            Spacer(modifier = Modifier.height(12.dp))
            LinearProgressIndicator(
                progress = { uploaded / total.toFloat() },
                color = Accent,
                trackColor = SurfaceLowest,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp))
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text("$uploaded of $total photos uploaded", color = TextSecondary, style = CodeSm)
        }

        Spacer(modifier = Modifier.height(12.dp))
        Text(
            text = when {
                sync == SyncStatus.LOCAL_DRAFT -> "Draft saved on this device. Queue it to upload."
                sync == SyncStatus.QUEUED -> "Queued. It uploads automatically when the server is reachable."
                sync == SyncStatus.UPLOADING -> "Uploading to the server."
                sync == SyncStatus.UPLOAD_FAILED -> "Upload failed. The data is still on this device."
                serverStatus == null -> "Uploaded and submitted. Server status is not available right now."
                isAnalysisFinished(serverStatus) -> "Uploaded, submitted and analysed. Server status: $serverStatus."
                isAnalysisFailed(serverStatus) -> "AI analysis failed on the server (status $serverStatus). It can be re-run from the operations console."
                serverStatus.uppercase() == "PROCESSING" -> "The server is analysing the photos."
                else -> "Uploaded and submitted (server status $serverStatus). AI analysis is started from the operations console."
            },
            color = TextSecondary,
            style = MaterialTheme.typography.bodySmall
        )
    }
}

@Composable
private fun PipelineStep(title: String, caption: String, state: StepState, modifier: Modifier = Modifier) {
    val color: Color
    val icon: ImageVector
    when (state) {
        StepState.DONE -> { color = SuccessEmerald; icon = Icons.Default.Check }
        StepState.ACTIVE -> { color = AccentBright; icon = Icons.Default.Sync }
        StepState.FAILED -> { color = ErrorRose; icon = Icons.Default.PriorityHigh }
        StepState.WAITING -> { color = TextMuted; icon = Icons.Default.HourglassEmpty }
    }
    Column(modifier = modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            modifier = Modifier
                .size(34.dp)
                .clip(CircleShape)
                .background(if (state == StepState.WAITING) SurfaceCard else color.copy(alpha = 0.18f))
                .border(1.dp, color.copy(alpha = 0.6f), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(18.dp))
        }
        Spacer(modifier = Modifier.height(6.dp))
        Text(title, color = if (state == StepState.WAITING) TextSecondary else TextPrimary, style = MaterialTheme.typography.labelMedium, maxLines = 1)
        Text(caption, color = color, style = CodeSm, maxLines = 1)
    }
}

@Composable
private fun AiResultsCard(
    state: ServerInspectionState?,
    loading: Boolean,
    error: String?,
    media: List<InspectionMedia>,
    onRetry: () -> Unit,
    onOpenPhoto: (Int) -> Unit
) {
    FieldCard {
        val ai = aiStatusInfo(state?.status)
        SectionTitle(
            "AI Analysis",
            icon = Icons.Default.Memory,
            trailing = { if (state != null) StatusPill(ai.label.uppercase(), ai.color, ai.icon) }
        )
        Spacer(modifier = Modifier.height(12.dp))

        when {
            state == null && loading -> Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(color = Accent, modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                Spacer(modifier = Modifier.width(10.dp))
                Text("Checking the server for analysis results...", color = TextSecondary, style = MaterialTheme.typography.bodySmall)
            }

            state == null -> MessageCard(
                kind = MessageKind.WARNING,
                title = "Analysis results unavailable",
                message = error ?: "The server could not be reached.",
                actionLabel = "Retry",
                onAction = onRetry
            )

            isAnalysisFailed(state.status) -> MessageCard(
                kind = MessageKind.ERROR,
                title = "AI analysis failed",
                message = "The server reported status ${state.status}. No result was produced. Re-run the analysis from the operations console."
            )

            !isAnalysisFinished(state.status) -> MessageCard(
                kind = MessageKind.INFO,
                title = if (state.status.uppercase() == "PROCESSING") "Analysis running" else "Awaiting analysis",
                message = if (state.status.uppercase() == "PROCESSING") {
                    "The server is analysing the photos. This screen refreshes automatically."
                } else {
                    "The inspection is submitted. AI analysis is started from the operations console; results appear here when it finishes."
                }
            )

            state.detections.isEmpty() -> MessageCard(
                kind = MessageKind.SUCCESS,
                title = "Analysis completed",
                message = "No damage detected above the configured confidence threshold."
            )

            else -> {
                val detections = state.detections
                val heuristic = detections.count { it.isHeuristic }
                Text(
                    text = if (detections.size == 1) "1 detection" else "${detections.size} detections",
                    color = TextPrimary,
                    style = MaterialTheme.typography.titleSmall
                )
                if (heuristic > 0) {
                    Spacer(modifier = Modifier.height(8.dp))
                    MessageCard(
                        kind = MessageKind.WARNING,
                        title = "Heuristic results",
                        message = "$heuristic of ${detections.size} came from the rule-based fallback, not the trained model. Their scores are not probabilities; treat them as unverified."
                    )
                }
                Spacer(modifier = Modifier.height(10.dp))
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    detections.forEach { det ->
                        val photoIndex = media.indexOfFirst { it.serverId != null && it.serverId == det.mediaId }
                        DetectionRow(det, photoIndex, onOpenPhoto)
                    }
                }
            }
        }

        if (state != null && isAnalysisFinished(state.status)) {
            Spacer(modifier = Modifier.height(12.dp))
            Row(verticalAlignment = Alignment.Top) {
                Icon(Icons.Default.VerifiedUser, contentDescription = null, tint = SuccessEmeraldSoft, modifier = Modifier.size(14.dp))
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = "Human review: detections are candidates until a reviewer confirms or rejects them in the operations console. Review decisions are not shown in this app.",
                    color = TextSecondary,
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }
    }
}

@Composable
private fun DetectionRow(det: ServerDetection, photoIndex: Int, onOpenPhoto: (Int) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(SurfaceLowest, RoundedCornerShape(12.dp))
            .border(
                1.dp,
                if (det.isHeuristic) WarningAmber.copy(alpha = 0.4f) else BorderDark,
                RoundedCornerShape(12.dp)
            )
            .padding(12.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = det.damageType.replace('_', ' '),
                color = TextPrimary,
                style = MaterialTheme.typography.titleSmall,
                modifier = Modifier.weight(1f)
            )
            if (det.severity != null) {
                StatusPill(det.severity.uppercase(), severityColor(det.severity))
            }
        }
        Spacer(modifier = Modifier.height(6.dp))
        StatusPill(
            label = det.methodLabel(),
            color = det.methodColor(),
            icon = if (det.isHeuristic) Icons.Default.WarningAmber else Icons.Default.Memory
        )
        Spacer(modifier = Modifier.height(6.dp))
        Text(det.scoreText(), color = if (det.isHeuristic) WarningAmber else TextOnSurface, style = CodeSm)
        det.modelText()?.let { Text("Model: $it", color = TextSecondary, style = CodeSm) }
        if (det.severity != null) {
            Text("Severity is assessed by rules, not by the model.", color = TextMuted, style = CodeSm)
        }
        if (photoIndex >= 0) {
            Spacer(modifier = Modifier.height(6.dp))
            Row(
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .clickable { onOpenPhoto(photoIndex) }
                    .heightIn(min = 40.dp)
                    .padding(vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(Icons.Default.Image, contentDescription = null, tint = AccentBright, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(6.dp))
                Text("View on photo ${photoIndex + 1}", color = AccentBright, style = MaterialTheme.typography.labelMedium)
            }
        }
    }
}

@Composable
private fun GpsCard(insp: Inspection) {
    FieldCard {
        val hasGps = insp.latitude != null && insp.longitude != null
        SectionTitle(
            "GPS Location",
            icon = Icons.Default.LocationOn,
            trailing = {
                StatusPill(
                    if (hasGps) "GPS RECORDED" else "NO GPS",
                    if (hasGps) SuccessEmerald else TextSecondary,
                    if (hasGps) Icons.Default.GpsFixed else Icons.Default.GpsOff
                )
            }
        )
        Spacer(modifier = Modifier.height(12.dp))
        if (hasGps) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                ValueTile("Latitude", "%.6f".format(insp.latitude), modifier = Modifier.weight(1f))
                ValueTile("Longitude", "%.6f".format(insp.longitude), modifier = Modifier.weight(1f))
            }
            Spacer(modifier = Modifier.height(10.dp))
            ValueTile(
                label = "Accuracy",
                value = insp.accuracyMeters?.let { "±%.1f m (%s)".format(it, accuracyLabel(it)) } ?: "Not reported",
                valueColor = accuracyColor(insp.accuracyMeters),
                modifier = Modifier.fillMaxWidth()
            )
        } else {
            Text("No GPS coordinates were recorded for this inspection.", color = TextSecondary, style = MaterialTheme.typography.bodySmall)
        }
    }
}

private fun confirmationOf(media: InspectionMedia, state: ServerInspectionState?, serverChecked: Boolean): ServerConfirmation = when {
    media.serverId.isNullOrEmpty() -> ServerConfirmation.NOT_UPLOADED
    !serverChecked || state == null -> ServerConfirmation.UNAVAILABLE
    state.media.any { it.id == media.serverId } -> ServerConfirmation.CONFIRMED
    else -> ServerConfirmation.NOT_LISTED
}

@Composable
private fun ConfirmationLine(confirmation: ServerConfirmation) {
    val (text, color, icon) = when (confirmation) {
        ServerConfirmation.CONFIRMED -> Triple("Confirmed by server", SuccessEmerald, Icons.Default.CloudDone)
        ServerConfirmation.NOT_LISTED -> Triple("Not confirmed by server", WarningAmber, Icons.Default.WarningAmber)
        ServerConfirmation.NOT_UPLOADED -> Triple("Not uploaded yet", TextSecondary, Icons.Default.CloudQueue)
        ServerConfirmation.UNAVAILABLE -> Triple("Server check unavailable", TextSecondary, Icons.Default.CloudOff)
    }
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(12.dp))
        Spacer(modifier = Modifier.width(4.dp))
        Text(text, color = color, style = CodeSm, maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

@Composable
private fun PhotosCard(
    media: List<InspectionMedia>,
    serverState: ServerInspectionState?,
    serverChecked: Boolean,
    onOpen: (Int) -> Unit
) {
    FieldCard {
        SectionTitle(
            "Media / Photos",
            icon = Icons.Default.PhotoLibrary,
            trailing = { Text(if (media.size == 1) "1 photo" else "${media.size} photos", color = TextSecondary, style = CodeSm) }
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            "Photos stored on this device, checked against the server's media list. Tap a photo to view it full screen.",
            color = TextSecondary,
            style = MaterialTheme.typography.bodySmall
        )
        Spacer(modifier = Modifier.height(12.dp))

        if (media.isEmpty()) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.HideImage, contentDescription = null, tint = TextMuted, modifier = Modifier.size(20.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text("No photos attached to this inspection.", color = TextSecondary, style = MaterialTheme.typography.bodySmall)
            }
            return@FieldCard
        }

        // Two photos per row; each tile is a full-size touch target.
        media.chunked(2).forEachIndexed { rowIndex, row ->
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                row.forEachIndexed { columnIndex, item ->
                    val index = rowIndex * 2 + columnIndex
                    val detectionCount = serverState?.detections?.count { it.mediaId != null && it.mediaId == item.serverId } ?: 0
                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(12.dp))
                            .clickable { onOpen(index) }
                    ) {
                        Box {
                            LocalThumbnail(
                                path = item.localFilePath,
                                maxDimensionPx = 480,
                                contentDescription = "Photo ${index + 1} of this inspection",
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .aspectRatio(4f / 3f)
                                    .clip(RoundedCornerShape(12.dp))
                                    .border(1.dp, BorderDark, RoundedCornerShape(12.dp))
                            )
                            if (detectionCount > 0) {
                                Text(
                                    text = if (detectionCount == 1) "1 detection" else "$detectionCount detections",
                                    color = Color.White,
                                    style = CodeSm,
                                    modifier = Modifier
                                        .align(Alignment.TopStart)
                                        .padding(6.dp)
                                        .background(Color.Black.copy(alpha = 0.7f), RoundedCornerShape(6.dp))
                                        .padding(horizontal = 6.dp, vertical = 2.dp)
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            File(item.localFilePath).name,
                            color = TextOnSurface,
                            style = CodeSm,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        Text(
                            "${formatFileSize(item.fileSizeBytes)} · ${item.uploadStatus.name}",
                            color = when (item.uploadStatus) {
                                UploadStatus.COMPLETED -> SuccessEmerald
                                UploadStatus.FAILED -> ErrorRose
                                UploadStatus.UPLOADING -> AccentBright
                                UploadStatus.PENDING -> TextSecondary
                            },
                            style = CodeSm
                        )
                        ConfirmationLine(confirmationOf(item, serverState, serverChecked))
                    }
                }
                if (row.size == 1) Spacer(modifier = Modifier.weight(1f))
            }
            Spacer(modifier = Modifier.height(12.dp))
        }
    }
}
