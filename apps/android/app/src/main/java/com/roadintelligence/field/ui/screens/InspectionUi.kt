package com.roadintelligence.field.ui.screens

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.HourglassEmpty
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import com.roadintelligence.field.data.repository.ServerDetection
import com.roadintelligence.field.domain.model.Inspection
import com.roadintelligence.field.ui.theme.ErrorRose
import com.roadintelligence.field.ui.theme.AccentBright
import com.roadintelligence.field.ui.theme.InfoSky
import com.roadintelligence.field.ui.theme.SuccessEmerald
import com.roadintelligence.field.ui.theme.TextSecondary
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

// Presentation helpers shared by the inspection list, detail and sync screens.
// They only format values that exist locally or were returned by the server.

/** "#7e4a1d7f" once the server has assigned an ID, otherwise the local ID marked as local. */
fun Inspection.displayId(): String =
    if (!serverId.isNullOrEmpty()) "#${serverId.take(8)}" else "Local #${localId.take(8)}"

fun formatDateTime(millis: Long): String =
    SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date(millis))

fun formatFileSize(bytes: Long): String = when {
    bytes <= 0L -> "—"
    bytes < 1024 * 1024 -> "${bytes / 1024} KB"
    else -> "%.1f MB".format(bytes / (1024.0 * 1024.0))
}

data class AiStatusInfo(val label: String, val color: Color, val icon: ImageVector)

/**
 * AI analysis state derived from the server's inspection status. AI analysis is started from the
 * operations console, so a SUBMITTED inspection is waiting, not failed.
 */
fun aiStatusInfo(serverStatus: String?): AiStatusInfo = when (serverStatus?.uppercase()) {
    null -> AiStatusInfo("AI status unavailable", TextSecondary, Icons.Default.CloudOff)
    "SUBMITTED" -> AiStatusInfo("Awaiting AI analysis", TextSecondary, Icons.Default.Schedule)
    "PROCESSING" -> AiStatusInfo("AI analysis running", InfoSky, Icons.Default.Memory)
    "PROCESSED", "ANALYZED", "COMPLETED" -> AiStatusInfo("AI analysis completed", SuccessEmerald, Icons.Default.CheckCircle)
    "PROCESSING_FAILED", "FAILED" -> AiStatusInfo("AI analysis failed", ErrorRose, Icons.Default.ErrorOutline)
    else -> AiStatusInfo("Not submitted", TextSecondary, Icons.Default.HourglassEmpty)
}

fun isAnalysisFinished(serverStatus: String?): Boolean =
    serverStatus?.uppercase() in setOf("PROCESSED", "ANALYZED", "COMPLETED")

fun isAnalysisFailed(serverStatus: String?): Boolean =
    serverStatus?.uppercase() in setOf("PROCESSING_FAILED", "FAILED")

/** How a detection was produced, in the server's own terms. */
fun ServerDetection.methodLabel(): String = when {
    isHeuristic -> "HEURISTIC · UNVERIFIED"
    detectionMethod == "TRAINED_MODEL" -> "TRAINED AI"
    detectionMethod == "MANUAL" -> "MANUAL ENTRY"
    else -> "METHOD UNKNOWN"
}

fun ServerDetection.methodColor(): Color = when {
    isHeuristic -> com.roadintelligence.field.ui.theme.WarningAmber
    detectionMethod == "TRAINED_MODEL" -> AccentBright
    else -> TextSecondary
}

/** "Model confidence 0.43" only for trained-model output; heuristic scores are not probabilities. */
fun ServerDetection.scoreText(): String {
    val value = score?.let { "%.2f".format(it) } ?: "—"
    return when {
        isHeuristic -> "Heuristic score $value (not a probability)"
        scoreType == "MODEL_CONFIDENCE" -> "Model confidence $value"
        else -> "Score $value"
    }
}

fun ServerDetection.modelText(): String? =
    modelName?.let { name -> if (modelVersion.isNullOrBlank()) name else "$name · $modelVersion" }
