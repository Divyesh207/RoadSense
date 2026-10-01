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
import com.roadintelligence.field.domain.model.SyncStatus
import com.roadintelligence.field.domain.repository.InspectionRepository
import com.roadintelligence.field.domain.repository.SyncRepository
import com.roadintelligence.field.ui.components.CommonTopBar
import com.roadintelligence.field.ui.components.StatusBadge
import com.roadintelligence.field.ui.theme.*
import kotlinx.coroutines.launch
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun InspectionDetailScreen(
    localId: String,
    inspectionRepository: InspectionRepository,
    syncRepository: SyncRepository,
    onNavigateBack: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    val inspection by inspectionRepository.getInspectionById(localId).collectAsState(initial = null)

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
    ) {
        CommonTopBar(
            title = "Inspection Details",
            canNavigateBack = true,
            onNavigateBack = onNavigateBack
        )

        if (inspection == null) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = PrimaryCyan)
            }
        } else {
            val insp = inspection!!
            val dateStr = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date(insp.capturedAt))

            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp),
                contentPadding = PaddingValues(bottom = 32.dp)
            ) {
                // Header Card
                item {
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
                                Text(
                                    text = insp.roadName ?: "Unassigned Road",
                                    color = TextPrimary,
                                    fontSize = 18.sp,
                                    fontWeight = FontWeight.Bold
                                )
                                StatusBadge(status = insp.syncStatus)
                            }
                            if (insp.segmentNumber != null) {
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = "Segment #${insp.segmentNumber}",
                                    color = PrimaryCyan,
                                    fontSize = 14.sp
                                )
                            }
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(
                                text = "Captured: $dateStr",
                                color = TextMuted,
                                fontSize = 12.sp
                            )
                            if (insp.serverId != null) {
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = "Server ID: ${insp.serverId}",
                                    color = SuccessEmerald,
                                    fontSize = 12.sp
                                )
                            }
                        }
                    }
                    Spacer(modifier = Modifier.height(16.dp))
                }

                // Sync Error Alert if present
                if (insp.lastSyncError != null) {
                    item {
                        Surface(
                            modifier = Modifier.fillMaxWidth(),
                            color = ErrorRose.copy(alpha = 0.15f),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Row(
                                modifier = Modifier.padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(Icons.Default.ErrorOutline, contentDescription = null, tint = ErrorRose)
                                Spacer(modifier = Modifier.width(8.dp))
                                Column {
                                    Text("Sync Failure", color = ErrorRose, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                    Text(insp.lastSyncError ?: "", color = ErrorRose, fontSize = 12.sp)
                                }
                            }
                        }
                        Spacer(modifier = Modifier.height(16.dp))
                    }
                }

                // GPS Location Card
                item {
                    Text("GPS Coordinates", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        color = SurfaceDark,
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            if (insp.latitude != null && insp.longitude != null) {
                                Text(
                                    text = "Latitude: %.6f".format(insp.latitude),
                                    color = TextPrimary,
                                    fontSize = 14.sp
                                )
                                Text(
                                    text = "Longitude: %.6f".format(insp.longitude),
                                    color = TextPrimary,
                                    fontSize = 14.sp
                                )
                                Text(
                                    text = "Accuracy: ±%.1f meters".format(insp.accuracyMeters ?: 0f),
                                    color = if ((insp.accuracyMeters ?: 100f) < 15f) SuccessEmerald else WarningAmber,
                                    fontSize = 13.sp
                                )
                            } else {
                                Text("No GPS coordinates recorded", color = TextMuted, fontSize = 13.sp)
                            }
                        }
                    }
                    Spacer(modifier = Modifier.height(16.dp))
                }

                // Notes Card
                if (!insp.notes.isNullOrBlank()) {
                    item {
                        Text("Inspector Notes", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                        Spacer(modifier = Modifier.height(8.dp))
                        Surface(
                            modifier = Modifier.fillMaxWidth(),
                            color = SurfaceDark,
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text(
                                text = insp.notes ?: "",
                                color = TextSecondary,
                                fontSize = 13.sp,
                                modifier = Modifier.padding(14.dp)
                            )
                        }
                        Spacer(modifier = Modifier.height(16.dp))
                    }
                }

                // Captured Media Evidence
                item {
                    Text("Visual Evidence (${insp.mediaList.size})", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                }

                if (insp.mediaList.isEmpty()) {
                    item {
                        Surface(
                            modifier = Modifier.fillMaxWidth(),
                            color = SurfaceDark,
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text("No photos attached", color = TextMuted, fontSize = 13.sp, modifier = Modifier.padding(16.dp))
                        }
                    }
                } else {
                    items(insp.mediaList) { media ->
                        val file = File(media.localFilePath)
                        val sizeKb = if (file.exists()) file.length() / 1024 else 0
                        Surface(
                            modifier = Modifier.fillMaxWidth(),
                            color = SurfaceDark,
                            shape = RoundedCornerShape(10.dp)
                        ) {
                            Row(
                                modifier = Modifier.padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(Icons.Default.Image, contentDescription = null, tint = PrimaryCyan)
                                Spacer(modifier = Modifier.width(12.dp))
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(file.name, color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.Medium)
                                    Text("$sizeKb KB • ${media.uploadStatus}", color = TextMuted, fontSize = 11.sp)
                                }
                                if (media.uploadStatus.name == "COMPLETED") {
                                    Icon(Icons.Default.CheckCircle, contentDescription = "Uploaded", tint = SuccessEmerald)
                                }
                            }
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                    }
                }

                // Action Buttons (Queue / Retry / Delete)
                item {
                    Spacer(modifier = Modifier.height(24.dp))
                    if (insp.syncStatus == SyncStatus.LOCAL_DRAFT || insp.syncStatus == SyncStatus.UPLOAD_FAILED) {
                        Button(
                            onClick = {
                                coroutineScope.launch {
                                    inspectionRepository.queueForUpload(insp.localId)
                                    syncRepository.triggerManualSync()
                                }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan),
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(48.dp)
                        ) {
                            Icon(Icons.Default.Sync, contentDescription = null, tint = Color.Black)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = if (insp.syncStatus == SyncStatus.UPLOAD_FAILED) "Retry Upload" else "Queue for Upload",
                                color = Color.Black,
                                fontWeight = FontWeight.Bold
                            )
                        }
                        Spacer(modifier = Modifier.height(12.dp))
                    }

                    if (insp.syncStatus == SyncStatus.LOCAL_DRAFT) {
                        OutlinedButton(
                            onClick = {
                                coroutineScope.launch {
                                    inspectionRepository.deleteDraft(insp.localId)
                                    onNavigateBack()
                                }
                            },
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = ErrorRose),
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(48.dp)
                        ) {
                            Text("Delete Draft")
                        }
                    }
                }
            }
        }
    }
}
