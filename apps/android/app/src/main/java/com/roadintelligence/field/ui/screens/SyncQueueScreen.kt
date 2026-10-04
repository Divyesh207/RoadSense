package com.roadintelligence.field.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.roadintelligence.field.data.repository.InspectionRemoteRepository
import com.roadintelligence.field.domain.model.Inspection
import com.roadintelligence.field.domain.model.SyncQueueItem
import com.roadintelligence.field.domain.model.SyncStatus
import com.roadintelligence.field.domain.repository.InspectionRepository
import com.roadintelligence.field.domain.repository.SyncRepository
import com.roadintelligence.field.ui.components.*
import com.roadintelligence.field.ui.theme.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun SyncQueueScreen(
    syncRepository: SyncRepository,
    inspectionRepository: InspectionRepository,
    inspectionRemote: InspectionRemoteRepository,
    onNavigateBack: () -> Unit,
    onOpenInspection: (String) -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    val queueItems by syncRepository.getSyncQueue().collectAsState(initial = emptyList())
    // Road and segment names for the queue rows come from the local inspection records.
    val inspections by inspectionRepository.getAllInspections().collectAsState(initial = emptyList())
    val byLocalId = remember(inspections) { inspections.associateBy { it.localId } }
    var isSyncing by remember { mutableStateOf(false) }
    var refreshTick by remember { mutableStateOf(0) }

    val deviceOnline by rememberDeviceOnline()
    val server by rememberServerReachability(inspectionRemote, refreshTick)

    val pending = queueItems.count { it.status == SyncStatus.QUEUED || it.status == SyncStatus.UPLOADING }
    val failed = queueItems.count { it.status == SyncStatus.UPLOAD_FAILED }
    val completed = queueItems.count { it.status == SyncStatus.COMPLETED }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .glassBackground()
    ) {
        CommonTopBar(
            title = "Sync Queue",
            overline = "Upload & Sync",
            actions = {
                val chip = serverChip(server, deviceOnline)
                ConnectionChip(chip.label, chip.color, modifier = Modifier.padding(end = 8.dp))
            }
        )

        ConnectivityBanner(isOnline = deviceOnline || server == com.roadintelligence.field.data.repository.ServerReachability.REACHABLE)

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                FieldCard {
                    Row(verticalAlignment = Alignment.Top) {
                        Icon(Icons.Default.CloudSync, contentDescription = null, tint = PrimaryCyanBright, modifier = Modifier.size(22.dp))
                        Spacer(modifier = Modifier.width(10.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text("Automatic background sync", color = TextPrimary, style = MaterialTheme.typography.titleSmall)
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                "Queued inspections upload over Wi-Fi or cellular when the server is reachable. Nothing is lost while offline.",
                                color = TextSecondary,
                                style = MaterialTheme.typography.bodySmall
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        ValueTile("Pending", pending.toString(), Modifier.weight(1f), valueColor = if (pending > 0) SecondaryBlueSoft else TextSecondary)
                        ValueTile("Failed", failed.toString(), Modifier.weight(1f), valueColor = if (failed > 0) ErrorRose else TextSecondary)
                        ValueTile("Completed", completed.toString(), Modifier.weight(1f), valueColor = if (completed > 0) SuccessEmerald else TextSecondary)
                    }
                    Spacer(modifier = Modifier.height(12.dp))
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        PrimaryButton(
                            text = "Sync Now",
                            icon = Icons.Default.Sync,
                            loading = isSyncing,
                            onClick = {
                                isSyncing = true
                                coroutineScope.launch {
                                    syncRepository.triggerManualSync()
                                    refreshTick++
                                    isSyncing = false
                                }
                            },
                            modifier = Modifier.fillMaxWidth()
                        )
                        SecondaryButton(
                            text = "Clear Completed",
                            icon = Icons.Default.DeleteSweep,
                            enabled = completed > 0,
                            onClick = { coroutineScope.launch { syncRepository.clearCompleted() } },
                            height = 48.dp,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
            }

            item {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Queue", color = TextPrimary, style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                    Text(if (queueItems.size == 1) "1 item" else "${queueItems.size} items", color = TextSecondary, style = CodeSm)
                }
            }

            if (queueItems.isEmpty()) {
                item {
                    EmptyState(
                        icon = Icons.Default.CloudDone,
                        title = "Sync queue is empty",
                        message = "There is nothing waiting to upload from this device."
                    )
                }
            } else {
                items(queueItems, key = { it.id }) { item ->
                    SyncQueueItemCard(
                        item = item,
                        inspection = byLocalId[item.inspectionLocalId],
                        onOpen = { onOpenInspection(item.inspectionLocalId) },
                        onRetry = { coroutineScope.launch { syncRepository.retryFailedItem(item.id) } }
                    )
                }
            }
        }
    }
}

@Composable
fun SyncQueueItemCard(
    item: SyncQueueItem,
    inspection: Inspection?,
    onOpen: () -> Unit,
    onRetry: () -> Unit
) {
    val dateStr = SimpleDateFormat("HH:mm:ss (MMM dd)", Locale.getDefault()).format(Date(item.createdAt))
    val failed = item.status == SyncStatus.UPLOAD_FAILED

    FieldCard(
        borderColor = if (failed) ErrorRose.copy(alpha = 0.45f) else BorderDark,
        modifier = Modifier
            .clip(RoundedCornerShape(16.dp))
            .clickable(enabled = inspection != null, onClick = onOpen)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = inspection?.displayId() ?: "Local #${item.inspectionLocalId.take(8)}",
                color = PrimaryCyanBright,
                style = CodeMd,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.weight(1f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            StatusBadge(status = item.status)
        }
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            text = when {
                inspection == null -> "Inspection record no longer on this device"
                else -> inspection.roadName ?: "Unassigned road"
            },
            color = if (inspection == null) TextSecondary else TextPrimary,
            style = MaterialTheme.typography.titleSmall,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = buildString {
                if (inspection?.segmentNumber != null) append("Seg #${inspection.segmentNumber} · ")
                append("queued $dateStr · attempts ${item.attemptCount}")
            },
            color = TextSecondary,
            style = CodeSm
        )

        if (item.status == SyncStatus.UPLOADING) {
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

        if (item.lastError != null) {
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
                Text(item.lastError, color = ErrorSoft, style = MaterialTheme.typography.bodySmall)
            }
            Spacer(modifier = Modifier.height(10.dp))
            SecondaryButton(
                text = "Retry",
                icon = Icons.Default.Refresh,
                contentColor = ErrorSoft,
                onClick = onRetry,
                height = 48.dp,
                modifier = Modifier.fillMaxWidth()
            )
        }
    }
}
