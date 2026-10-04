package com.roadintelligence.field.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
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
import com.roadintelligence.field.data.repository.ServerInspectionState
import com.roadintelligence.field.domain.model.Inspection
import com.roadintelligence.field.domain.model.InspectionMedia
import com.roadintelligence.field.domain.model.SyncStatus
import com.roadintelligence.field.domain.repository.AuthRepository
import com.roadintelligence.field.domain.repository.InspectionRepository
import com.roadintelligence.field.domain.repository.RoadRepository
import com.roadintelligence.field.domain.repository.SyncRepository
import com.roadintelligence.field.ui.components.*
import com.roadintelligence.field.ui.theme.*
import kotlinx.coroutines.launch

private enum class HomeFilter(val label: String) { ALL("All"), QUEUED("Queued"), DRAFT("Draft"), FAILED("Failed"), SYNCED("Synced") }

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun HomeScreen(
    authRepository: AuthRepository,
    inspectionRepository: InspectionRepository,
    inspectionRemote: InspectionRemoteRepository,
    roadRepository: RoadRepository,
    syncRepository: SyncRepository,
    onNavigateToNewInspection: () -> Unit,
    onNavigateToDetail: (String) -> Unit,
    onNavigateToSync: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    val session = remember { authRepository.getCurrentSession() }
    val inspections by inspectionRepository.getAllInspections().collectAsState(initial = emptyList())
    var isRefreshing by remember { mutableStateOf(false) }
    var refreshTick by remember { mutableStateOf(0) }
    var filter by remember { mutableStateOf(HomeFilter.ALL) }

    val deviceOnline by rememberDeviceOnline()
    val server by rememberServerReachability(inspectionRemote, refreshTick)
    val gps by rememberGpsReadiness(refreshTick)

    val isQueued: (Inspection) -> Boolean = { it.syncStatus == SyncStatus.QUEUED || it.syncStatus == SyncStatus.UPLOADING }
    val draftsCount = inspections.count { it.syncStatus == SyncStatus.LOCAL_DRAFT }
    val queuedCount = inspections.count(isQueued)
    val failedCount = inspections.count { it.syncStatus == SyncStatus.UPLOAD_FAILED }
    val completedCount = inspections.count { it.syncStatus == SyncStatus.COMPLETED }
    val pendingSync = queuedCount + failedCount

    val shown = when (filter) {
        HomeFilter.ALL -> inspections
        HomeFilter.QUEUED -> inspections.filter(isQueued)
        HomeFilter.DRAFT -> inspections.filter { it.syncStatus == SyncStatus.LOCAL_DRAFT }
        HomeFilter.FAILED -> inspections.filter { it.syncStatus == SyncStatus.UPLOAD_FAILED }
        HomeFilter.SYNCED -> inspections.filter { it.syncStatus == SyncStatus.COMPLETED }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
    ) {
        CommonTopBar(
            title = "Home",
            overline = "Road Intelligence",
            actions = {
                IconButton(
                    onClick = {
                        isRefreshing = true
                        coroutineScope.launch {
                            roadRepository.syncRoadsFromServer()
                            syncRepository.triggerManualSync()
                            refreshTick++
                            isRefreshing = false
                        }
                    },
                    enabled = !isRefreshing
                ) {
                    if (isRefreshing) {
                        CircularProgressIndicator(color = PrimaryCyan, modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
                    } else {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh roads and sync now", tint = PrimaryCyanBright)
                    }
                }
            }
        )

        ConnectivityBanner(isOnline = deviceOnline || server == com.roadintelligence.field.data.repository.ServerReachability.REACHABLE)

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Who is signed in, and the state of the things a field inspection depends on
            item {
                FieldCard(contentPadding = PaddingValues(14.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(40.dp)
                                .background(PrimaryCyan.copy(alpha = 0.15f), RoundedCornerShape(12.dp))
                                .border(1.dp, PrimaryCyan.copy(alpha = 0.3f), RoundedCornerShape(12.dp)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(Icons.Default.Person, contentDescription = null, tint = PrimaryCyanBright)
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = session?.fullName?.takeIf { it.isNotBlank() } ?: session?.email ?: "Signed in",
                                color = TextPrimary,
                                style = MaterialTheme.typography.titleSmall,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                            Text(
                                text = session?.organizationName?.takeIf { it.isNotBlank() } ?: "Organization not set",
                                color = TextSecondary,
                                style = MaterialTheme.typography.bodySmall,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(12.dp))
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        val serverInfo = serverChip(server, deviceOnline)
                        ConnectionChip(serverInfo.label, serverInfo.color)
                        val gpsInfo = gpsChip(gps)
                        ConnectionChip(gpsInfo.label, gpsInfo.color)
                        ConnectionChip(
                            label = if (pendingSync == 0) "Nothing to sync" else "$pendingSync pending sync",
                            color = if (failedCount > 0) ErrorRose else if (pendingSync > 0) SecondaryBlueSoft else SuccessEmerald,
                            modifier = Modifier.clickable(onClick = onNavigateToSync)
                        )
                    }
                }
            }

            item {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    StatTile("Drafts", draftsCount, Icons.Default.EditNote, TextSecondary, Modifier.weight(1f))
                    StatTile("Queued", queuedCount, Icons.Default.Schedule, SecondaryBlueSoft, Modifier.weight(1f))
                    StatTile("Failed", failedCount, Icons.Default.WarningAmber, if (failedCount > 0) ErrorRose else TextMuted, Modifier.weight(1f))
                    StatTile("Synced", completedCount, Icons.Default.CheckCircle, SuccessEmerald, Modifier.weight(1f))
                }
            }

            item {
                PrimaryButton(
                    text = "Start New Inspection",
                    icon = Icons.Default.AddCircleOutline,
                    onClick = onNavigateToNewInspection,
                    height = 60.dp,
                    modifier = Modifier.fillMaxWidth()
                )
            }

            if (failedCount > 0) {
                item {
                    MessageCard(
                        kind = MessageKind.ERROR,
                        title = if (failedCount == 1) "1 inspection failed to upload" else "$failedCount inspections failed to upload",
                        message = "The data is still on this device. Open the sync queue to see the reason and retry.",
                        actionLabel = "Open Sync Queue",
                        onAction = onNavigateToSync
                    )
                }
            }

            item {
                Column {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = "Inspection History",
                            color = TextPrimary,
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.weight(1f)
                        )
                        Text("${inspections.size} on this device", color = TextSecondary, style = CodeSm)
                    }
                    Spacer(modifier = Modifier.height(10.dp))
                    Row(
                        modifier = Modifier.horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        FilterPill(HomeFilter.ALL, inspections.size, filter) { filter = it }
                        FilterPill(HomeFilter.QUEUED, queuedCount, filter) { filter = it }
                        FilterPill(HomeFilter.DRAFT, draftsCount, filter) { filter = it }
                        FilterPill(HomeFilter.FAILED, failedCount, filter) { filter = it }
                        FilterPill(HomeFilter.SYNCED, completedCount, filter) { filter = it }
                    }
                }
            }

            if (inspections.isEmpty()) {
                item {
                    EmptyState(
                        icon = Icons.Default.AddRoad,
                        title = "No inspections yet",
                        message = "Tap Start New Inspection to capture road evidence with photos and GPS. Inspections are saved on this device and uploaded when the server is reachable."
                    )
                }
            } else if (shown.isEmpty()) {
                item {
                    EmptyState(
                        icon = Icons.Default.FilterList,
                        title = "Nothing in \"${filter.label}\"",
                        message = "No inspection on this device has this status."
                    )
                }
            } else {
                items(shown, key = { it.localId }) { inspection ->
                    InspectionCard(
                        inspection = inspection,
                        inspectionRepository = inspectionRepository,
                        inspectionRemote = inspectionRemote,
                        refreshKey = refreshTick,
                        onClick = { onNavigateToDetail(inspection.localId) }
                    )
                }
            }
        }
    }
}

@Composable
private fun StatTile(label: String, value: Int, icon: ImageVector, color: Color, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .background(SurfaceDark, RoundedCornerShape(14.dp))
            .border(1.dp, BorderDark, RoundedCornerShape(14.dp))
            .padding(vertical = 12.dp, horizontal = 4.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(18.dp))
        Spacer(modifier = Modifier.height(4.dp))
        Text(value.toString(), color = if (value > 0) color else TextSecondary, style = CodeLg, fontWeight = FontWeight.Bold)
        Text(label.uppercase(), color = TextSecondary, style = CodeSm, maxLines = 1)
    }
}

@Composable
private fun FilterPill(item: HomeFilter, count: Int, selected: HomeFilter, onSelect: (HomeFilter) -> Unit) {
    val isSelected = item == selected
    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(if (isSelected) PrimaryCyan else SurfaceCard)
            .border(1.dp, if (isSelected) PrimaryCyan else BorderDark, RoundedCornerShape(999.dp))
            .clickable { onSelect(item) }
            .heightIn(min = 36.dp)
            .padding(horizontal = 14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = item.label,
            color = if (isSelected) OnPrimaryCyan else TextOnSurface,
            style = MaterialTheme.typography.labelMedium
        )
        Spacer(modifier = Modifier.width(6.dp))
        Text(
            text = count.toString(),
            color = if (isSelected) OnPrimaryCyan else TextSecondary,
            style = CodeSm
        )
    }
}

@Composable
fun InspectionCard(
    inspection: Inspection,
    inspectionRepository: InspectionRepository,
    inspectionRemote: InspectionRemoteRepository,
    refreshKey: Any?,
    onClick: () -> Unit
) {
    // Photos captured for this inspection (Room), for the thumbnail and the photo count.
    val media by produceState(initialValue = emptyList<InspectionMedia>(), inspection.localId, inspection.syncStatus) {
        value = inspectionRepository.getMediaForInspection(inspection.localId)
    }
    // Server state is only requested for inspections the server already has.
    val serverId = inspection.serverId?.takeIf { it.isNotEmpty() && inspection.syncStatus == SyncStatus.COMPLETED }
    val serverState by produceState<ServerInspectionState?>(
        initialValue = serverId?.let { inspectionRemote.cached(it) }, serverId, refreshKey
    ) {
        if (serverId != null) inspectionRemote.fetchState(serverId).getOrNull()?.let { value = it }
    }

    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .clickable(onClick = onClick),
        color = SurfaceDark,
        shape = RoundedCornerShape(16.dp),
        border = androidx.compose.foundation.BorderStroke(
            1.dp,
            if (inspection.syncStatus == SyncStatus.UPLOAD_FAILED) ErrorRose.copy(alpha = 0.45f) else BorderDark
        )
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = inspection.displayId(),
                    color = PrimaryCyanBright,
                    style = CodeMd,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                StatusBadge(status = inspection.syncStatus)
            }

            Spacer(modifier = Modifier.height(8.dp))

            Row {
                Box {
                    LocalThumbnail(
                        path = media.firstOrNull()?.localFilePath,
                        contentDescription = "First photo of this inspection",
                        modifier = Modifier
                            .size(76.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .border(1.dp, BorderDark, RoundedCornerShape(12.dp))
                    )
                    if (media.isNotEmpty()) {
                        Row(
                            modifier = Modifier
                                .align(Alignment.BottomEnd)
                                .padding(4.dp)
                                .background(Color.Black.copy(alpha = 0.65f), RoundedCornerShape(6.dp))
                                .padding(horizontal = 5.dp, vertical = 2.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.PhotoCamera, contentDescription = null, tint = Color.White, modifier = Modifier.size(10.dp))
                            Spacer(modifier = Modifier.width(3.dp))
                            Text(media.size.toString(), color = Color.White, style = CodeSm)
                        }
                    }
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = inspection.roadName ?: "Unassigned road",
                        color = TextPrimary,
                        style = MaterialTheme.typography.titleSmall,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        if (inspection.segmentNumber != null) {
                            Text(
                                text = "SEG #${inspection.segmentNumber}",
                                color = SecondaryBlueSoft,
                                style = CodeSm,
                                modifier = Modifier
                                    .background(SurfaceCard, RoundedCornerShape(6.dp))
                                    .padding(horizontal = 6.dp, vertical = 2.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                        }
                        Text(formatDateTime(inspection.capturedAt), color = TextSecondary, style = CodeSm, maxLines = 1)
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.MyLocation, contentDescription = null, tint = TextMuted, modifier = Modifier.size(12.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        if (inspection.latitude != null && inspection.longitude != null) {
                            Text(
                                text = "%.5f, %.5f".format(inspection.latitude, inspection.longitude),
                                color = TextOnSurface,
                                style = CodeSm
                            )
                            if (inspection.accuracyMeters != null) {
                                Text(
                                    text = " (±%.1f m)".format(inspection.accuracyMeters),
                                    color = accuracyColor(inspection.accuracyMeters),
                                    style = CodeSm
                                )
                            }
                        } else {
                            Text("No GPS recorded", color = TextMuted, style = CodeSm)
                        }
                    }
                }
            }

            // AI status and detection count come from the server; shown only once it has the inspection.
            if (serverId != null) {
                Spacer(modifier = Modifier.height(10.dp))
                HorizontalDivider(color = BorderDark.copy(alpha = 0.6f))
                Spacer(modifier = Modifier.height(8.dp))
                val ai = aiStatusInfo(serverState?.status)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(ai.icon, contentDescription = null, tint = ai.color, modifier = Modifier.size(14.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(ai.label, color = ai.color, style = MaterialTheme.typography.labelMedium, modifier = Modifier.weight(1f))
                    val state = serverState
                    if (state != null && isAnalysisFinished(state.status)) {
                        val n = state.detections.size
                        Text(
                            text = if (n == 1) "1 detection" else "$n detections",
                            color = if (n > 0) WarningAmber else TextSecondary,
                            style = CodeSm
                        )
                    }
                }
            }

            if (inspection.syncStatus == SyncStatus.UPLOADING) {
                Spacer(modifier = Modifier.height(10.dp))
                LinearProgressIndicator(
                    color = PrimaryCyan,
                    trackColor = SurfaceLowest,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(4.dp)
                        .clip(RoundedCornerShape(2.dp))
                )
            }

            if (inspection.syncStatus == SyncStatus.UPLOAD_FAILED && inspection.lastSyncError != null) {
                Spacer(modifier = Modifier.height(10.dp))
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(ErrorRose.copy(alpha = 0.10f), RoundedCornerShape(10.dp))
                        .padding(10.dp),
                    verticalAlignment = Alignment.Top
                ) {
                    Icon(Icons.Default.ErrorOutline, contentDescription = null, tint = ErrorRose, modifier = Modifier.size(14.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = inspection.lastSyncError,
                        color = ErrorSoft,
                        style = MaterialTheme.typography.bodySmall,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
        }
    }
}
