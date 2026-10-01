package com.roadintelligence.field.ui.screens

import androidx.compose.foundation.background
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.roadintelligence.field.domain.model.SyncQueueItem
import com.roadintelligence.field.domain.model.SyncStatus
import com.roadintelligence.field.domain.repository.SyncRepository
import com.roadintelligence.field.ui.components.CommonTopBar
import com.roadintelligence.field.ui.components.StatusBadge
import com.roadintelligence.field.ui.theme.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun SyncQueueScreen(
    syncRepository: SyncRepository,
    onNavigateBack: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    val queueItems by syncRepository.getSyncQueue().collectAsState(initial = emptyList())
    var isSyncing by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
    ) {
        CommonTopBar(
            title = "Background Sync Queue",
            canNavigateBack = true,
            onNavigateBack = onNavigateBack,
            actions = {
                if (queueItems.any { it.status == SyncStatus.COMPLETED }) {
                    IconButton(onClick = {
                        coroutineScope.launch {
                            syncRepository.clearCompleted()
                        }
                    }) {
                        Icon(Icons.Default.DeleteSweep, contentDescription = "Clear Completed", tint = TextMuted)
                    }
                }
            }
        )

        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            contentPadding = PaddingValues(bottom = 32.dp)
        ) {
            // Manual Trigger Banner
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = SurfaceDark,
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text("WorkManager Background Sync", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            Text("Automatically uploads queued inspections over WiFi or cellular", color = TextMuted, fontSize = 12.sp)
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Button(
                            onClick = {
                                isSyncing = true
                                coroutineScope.launch {
                                    syncRepository.triggerManualSync()
                                    isSyncing = false
                                }
                            },
                            enabled = !isSyncing,
                            colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            if (isSyncing) {
                                CircularProgressIndicator(color = Color.Black, modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                            } else {
                                Icon(Icons.Default.Sync, contentDescription = null, tint = Color.Black, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Sync Now", color = Color.Black, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                            }
                        }
                    }
                }
                Spacer(modifier = Modifier.height(20.dp))
            }

            item {
                Text(
                    text = "Sync Items (${queueItems.size})",
                    color = TextPrimary,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(12.dp))
            }

            if (queueItems.isEmpty()) {
                item {
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        color = SurfaceDark,
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(32.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Icon(Icons.Default.CloudDone, contentDescription = null, tint = SuccessEmerald, modifier = Modifier.size(44.dp))
                            Spacer(modifier = Modifier.height(10.dp))
                            Text("Sync Queue is Empty", color = TextPrimary, fontWeight = FontWeight.SemiBold)
                            Spacer(modifier = Modifier.height(4.dp))
                            Text("All inspections and media have been successfully synchronized.", color = TextMuted, fontSize = 12.sp)
                        }
                    }
                }
            } else {
                items(queueItems, key = { it.id }) { item ->
                    SyncQueueItemCard(
                        item = item,
                        onRetry = {
                            coroutineScope.launch {
                                syncRepository.retryFailedItem(item.id)
                            }
                        }
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                }
            }
        }
    }
}

@Composable
fun SyncQueueItemCard(
    item: SyncQueueItem,
    onRetry: () -> Unit
) {
    val dateStr = SimpleDateFormat("HH:mm:ss (MMM dd)", Locale.getDefault()).format(Date(item.createdAt))

    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = SurfaceDark,
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Inspection #${item.inspectionLocalId.take(8)}",
                    color = TextPrimary,
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp
                )
                StatusBadge(status = item.status)
            }
            Spacer(modifier = Modifier.height(6.dp))
            Text("Operation: ${item.operation} • Attempts: ${item.attemptCount}", color = TextMuted, fontSize = 12.sp)
            Text("Created: $dateStr", color = TextMuted, fontSize = 11.sp)

            if (item.lastError != null) {
                Spacer(modifier = Modifier.height(8.dp))
                Surface(
                    color = ErrorRose.copy(alpha = 0.15f),
                    shape = RoundedCornerShape(6.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = item.lastError,
                        color = ErrorRose,
                        fontSize = 11.sp,
                        modifier = Modifier.padding(8.dp)
                    )
                }
                Spacer(modifier = Modifier.height(8.dp))
                Button(
                    onClick = onRetry,
                    colors = ButtonDefaults.buttonColors(containerColor = ErrorRose.copy(alpha = 0.8f)),
                    shape = RoundedCornerShape(6.dp),
                    modifier = Modifier.align(Alignment.End)
                ) {
                    Icon(Icons.Default.Refresh, contentDescription = null, tint = Color.White, modifier = Modifier.size(14.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Retry", color = Color.White, fontSize = 12.sp)
                }
            }
        }
    }
}
