package com.roadintelligence.field.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CloudSync
import androidx.compose.material.icons.filled.DirectionsCar
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.roadintelligence.field.domain.model.Inspection
import com.roadintelligence.field.domain.model.SyncStatus
import com.roadintelligence.field.domain.repository.InspectionRepository
import com.roadintelligence.field.domain.repository.RoadRepository
import com.roadintelligence.field.domain.repository.SyncRepository
import com.roadintelligence.field.ui.components.CommonTopBar
import com.roadintelligence.field.ui.components.ConnectivityBanner
import com.roadintelligence.field.ui.components.StatusBadge
import com.roadintelligence.field.ui.theme.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun HomeScreen(
    inspectionRepository: InspectionRepository,
    roadRepository: RoadRepository,
    syncRepository: SyncRepository,
    onNavigateToNewInspection: () -> Unit,
    onNavigateToDetail: (String) -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    val inspections by inspectionRepository.getAllInspections().collectAsState(initial = emptyList())
    var isRefreshing by remember { mutableStateOf(false) }

    val draftsCount = inspections.count { it.syncStatus == SyncStatus.LOCAL_DRAFT }
    val queuedCount = inspections.count { it.syncStatus == SyncStatus.QUEUED || it.syncStatus == SyncStatus.UPLOADING }
    val failedCount = inspections.count { it.syncStatus == SyncStatus.UPLOAD_FAILED }
    val completedCount = inspections.count { it.syncStatus == SyncStatus.COMPLETED }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
    ) {
        CommonTopBar(
            title = "Field Inspections",
            actions = {
                IconButton(onClick = {
                    isRefreshing = true
                    coroutineScope.launch {
                        roadRepository.syncRoadsFromServer()
                        syncRepository.triggerManualSync()
                        isRefreshing = false
                    }
                }) {
                    Icon(
                        imageVector = Icons.Default.Refresh,
                        contentDescription = "Refresh Data & Sync",
                        tint = PrimaryCyan
                    )
                }
            }
        )

        ConnectivityBanner(isOnline = true)

        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 16.dp),
            contentPadding = PaddingValues(bottom = 24.dp)
        ) {
            // Stats Grid
            item {
                Spacer(modifier = Modifier.height(16.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    StatCard("Drafts", draftsCount.toString(), Color(0xFF94A3B8), Modifier.weight(1f))
                    StatCard("Queued", queuedCount.toString(), PrimaryCyan, Modifier.weight(1f))
                    StatCard("Failed", failedCount.toString(), if (failedCount > 0) ErrorRose else Color(0xFF64748B), Modifier.weight(1f))
                    StatCard("Synced", completedCount.toString(), SuccessEmerald, Modifier.weight(1f))
                }
                Spacer(modifier = Modifier.height(20.dp))
            }

            // Primary Action Button
            item {
                Button(
                    onClick = onNavigateToNewInspection,
                    colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp)
                ) {
                    Icon(Icons.Default.Add, contentDescription = null, tint = Color.Black)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "New Road Inspection",
                        color = Color.Black,
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp
                    )
                }
                Spacer(modifier = Modifier.height(24.dp))
            }

            // Section Header
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Recent Inspections (${inspections.size})",
                        color = TextPrimary,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
                Spacer(modifier = Modifier.height(12.dp))
            }

            if (inspections.isEmpty()) {
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
                            Icon(Icons.Default.DirectionsCar, contentDescription = null, tint = TextMuted, modifier = Modifier.size(48.dp))
                            Spacer(modifier = Modifier.height(12.dp))
                            Text("No inspections yet", color = TextSecondary, fontWeight = FontWeight.SemiBold)
                            Spacer(modifier = Modifier.height(4.dp))
                            Text("Tap 'New Road Inspection' above to capture road evidence.", color = TextMuted, fontSize = 13.sp)
                        }
                    }
                }
            } else {
                items(inspections, key = { it.localId }) { inspection ->
                    InspectionCard(
                        inspection = inspection,
                        onClick = { onNavigateToDetail(inspection.localId) }
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                }
            }
        }
    }
}

@Composable
fun StatCard(label: String, value: String, accentColor: Color, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier,
        color = SurfaceDark,
        shape = RoundedCornerShape(10.dp)
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(value, fontSize = 20.sp, fontWeight = FontWeight.Bold, color = accentColor)
            Text(label, fontSize = 11.sp, color = TextSecondary)
        }
    }
}

@Composable
fun InspectionCard(
    inspection: Inspection,
    onClick: () -> Unit
) {
    val dateStr = SimpleDateFormat("MMM dd, yyyy HH:mm", Locale.getDefault()).format(Date(inspection.capturedAt))

    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        color = SurfaceDark,
        shape = RoundedCornerShape(12.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = inspection.roadName ?: "Unassigned Road",
                        color = TextPrimary,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold
                    )
                    if (inspection.segmentNumber != null) {
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "• Seg #${inspection.segmentNumber}",
                            color = PrimaryCyan,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = dateStr,
                    color = TextMuted,
                    fontSize = 12.sp
                )
                if (inspection.latitude != null && inspection.longitude != null) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "GPS: %.5f, %.5f (±%.1fm)".format(
                            inspection.latitude,
                            inspection.longitude,
                            inspection.accuracyMeters ?: 0f
                        ),
                        color = TextSecondary,
                        fontSize = 11.sp
                    )
                }
            }

            Column(horizontalAlignment = Alignment.End) {
                StatusBadge(status = inspection.syncStatus)
                if (inspection.lastSyncError != null) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Sync error",
                        color = ErrorRose,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
    }
}
