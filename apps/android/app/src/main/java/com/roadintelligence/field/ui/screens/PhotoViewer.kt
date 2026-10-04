package com.roadintelligence.field.ui.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import com.roadintelligence.field.data.repository.ServerDetection
import com.roadintelligence.field.data.repository.ServerInspectionState
import com.roadintelligence.field.domain.model.InspectionMedia
import com.roadintelligence.field.ui.components.LocalImage
import com.roadintelligence.field.ui.components.rememberLocalImage
import com.roadintelligence.field.ui.theme.*
import java.io.File

/**
 * Full-screen viewer for the photos of one inspection, read from this device's storage.
 * Pinch or double-tap to zoom, drag to pan. Detection boxes come from the server's detections
 * for the same media ID and can be hidden.
 */
@Composable
fun PhotoViewer(
    media: List<InspectionMedia>,
    startIndex: Int,
    serverState: ServerInspectionState?,
    onClose: () -> Unit
) {
    var index by remember { mutableStateOf(startIndex.coerceIn(0, media.lastIndex)) }
    var showBoxes by remember { mutableStateOf(true) }
    var showInfo by remember { mutableStateOf(true) }
    val item = media[index]

    var scale by remember(index) { mutableStateOf(1f) }
    var offset by remember(index) { mutableStateOf(Offset.Zero) }
    var container by remember { mutableStateOf(IntSize.Zero) }

    val image = rememberLocalImage(item.localFilePath, 2048).value
    val detections: List<ServerDetection> = serverState?.detections
        ?.filter { it.mediaId != null && it.mediaId == item.serverId } ?: emptyList()
    val serverMedia = serverState?.media?.firstOrNull { it.id == item.serverId }

    fun clampOffset(candidate: Offset, forScale: Float): Offset {
        val maxX = container.width * (forScale - 1f) / 2f
        val maxY = container.height * (forScale - 1f) / 2f
        return Offset(candidate.x.coerceIn(-maxX, maxX), candidate.y.coerceIn(-maxY, maxY))
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
            // Swallow touches so the screen underneath does not react.
            .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null) {}
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .onSizeChanged { container = it }
                .pointerInput(index) {
                    detectTransformGestures { _, pan, zoom, _ ->
                        val newScale = (scale * zoom).coerceIn(1f, 6f)
                        scale = newScale
                        offset = if (newScale == 1f) Offset.Zero else clampOffset(offset + pan, newScale)
                    }
                }
                .pointerInput(index) {
                    detectTapGestures(
                        onDoubleTap = {
                            if (scale > 1f) {
                                scale = 1f
                                offset = Offset.Zero
                            } else {
                                scale = 2.5f
                            }
                        },
                        onTap = { showInfo = !showInfo }
                    )
                },
            contentAlignment = Alignment.Center
        ) {
            when (image) {
                is LocalImage.Ready -> {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .graphicsLayer(
                                scaleX = scale,
                                scaleY = scale,
                                translationX = offset.x,
                                translationY = offset.y
                            )
                    ) {
                        Image(
                            bitmap = image.bitmap.asImageBitmap(),
                            contentDescription = "Inspection photo ${index + 1} of ${media.size}",
                            contentScale = ContentScale.Fit,
                            modifier = Modifier.fillMaxSize()
                        )
                        if (showBoxes && detections.isNotEmpty()) {
                            val aspect = image.bitmap.width.toFloat() / image.bitmap.height.toFloat()
                            Canvas(modifier = Modifier.fillMaxSize()) {
                                // Rectangle the fitted image occupies inside the container.
                                val fitted = if (size.width / size.height > aspect) {
                                    Size(size.height * aspect, size.height)
                                } else {
                                    Size(size.width, size.width / aspect)
                                }
                                val origin = Offset((size.width - fitted.width) / 2f, (size.height - fitted.height) / 2f)
                                detections.forEach { det ->
                                    val x0 = det.xMin; val y0 = det.yMin; val x1 = det.xMax; val y1 = det.yMax
                                    if (x0 != null && y0 != null && x1 != null && y1 != null) {
                                        drawRect(
                                            color = if (det.isHeuristic) WarningAmber else PrimaryCyanBright,
                                            topLeft = Offset(origin.x + x0 * fitted.width, origin.y + y0 * fitted.height),
                                            size = Size((x1 - x0) * fitted.width, (y1 - y0) * fitted.height),
                                            style = Stroke(width = 3.dp.toPx() / scale)
                                        )
                                    }
                                }
                            }
                        }
                    }
                }

                LocalImage.Loading -> CircularProgressIndicator(color = PrimaryCyan)

                LocalImage.Missing -> Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.padding(32.dp)
                ) {
                    Icon(Icons.Default.BrokenImage, contentDescription = null, tint = TextSecondary, modifier = Modifier.size(40.dp))
                    Spacer(modifier = Modifier.height(10.dp))
                    Text("Photo file not found on this device", color = TextPrimary, style = MaterialTheme.typography.titleSmall)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        "The file may have been removed from app storage. The server does not provide inspection photos for download.",
                        color = TextSecondary,
                        style = MaterialTheme.typography.bodySmall,
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center
                    )
                }
            }
        }

        // Top bar
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.TopCenter)
                .background(Color.Black.copy(alpha = 0.6f))
                .padding(horizontal = 8.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onClose, modifier = Modifier.background(GlassBar, CircleShape)) {
                Icon(Icons.Default.Close, contentDescription = "Close photo viewer", tint = Color.White)
            }
            Spacer(modifier = Modifier.width(10.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text("Photo ${index + 1} of ${media.size}", color = Color.White, style = MaterialTheme.typography.titleSmall)
                Text(File(item.localFilePath).name, color = TextSecondary, style = CodeSm, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            if (detections.isNotEmpty()) {
                IconButton(
                    onClick = { showBoxes = !showBoxes },
                    modifier = Modifier.background(GlassBar, CircleShape)
                ) {
                    Icon(
                        imageVector = if (showBoxes) Icons.Default.Visibility else Icons.Default.VisibilityOff,
                        contentDescription = if (showBoxes) "Hide detection boxes" else "Show detection boxes",
                        tint = PrimaryCyanBright
                    )
                }
            }
        }

        // Previous / next
        if (media.size > 1) {
            if (index > 0) {
                IconButton(
                    onClick = { index-- },
                    modifier = Modifier
                        .align(Alignment.CenterStart)
                        .padding(8.dp)
                        .size(48.dp)
                        .background(GlassBar, CircleShape)
                ) {
                    Icon(Icons.Default.ChevronLeft, contentDescription = "Previous photo", tint = Color.White)
                }
            }
            if (index < media.lastIndex) {
                IconButton(
                    onClick = { index++ },
                    modifier = Modifier
                        .align(Alignment.CenterEnd)
                        .padding(8.dp)
                        .size(48.dp)
                        .background(GlassBar, CircleShape)
                ) {
                    Icon(Icons.Default.ChevronRight, contentDescription = "Next photo", tint = Color.White)
                }
            }
        }

        // Metadata panel (tap the photo to hide or show)
        if (showInfo) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .align(Alignment.BottomCenter)
                    .background(Color.Black.copy(alpha = 0.72f))
                    .padding(horizontal = 16.dp, vertical = 12.dp)
            ) {
                val ready = image as? LocalImage.Ready
                MetaRow("File size", formatFileSize(item.fileSizeBytes))
                if (ready != null) MetaRow("Dimensions", "${ready.sourceWidth} × ${ready.sourceHeight} px")
                MetaRow("Captured", formatDateTime(item.capturedAt))
                MetaRow("Upload", item.uploadStatus.name)
                MetaRow("Server media ID", item.serverId ?: "not uploaded yet")
                if (item.serverId != null) {
                    MetaRow(
                        "Server record",
                        when {
                            serverState == null -> "server check unavailable"
                            serverMedia == null -> "not listed by the server"
                            else -> buildString {
                                append(serverMedia.uploadStatus)
                                serverMedia.fileSizeBytes?.let { append(" · ${formatFileSize(it)}") }
                                serverMedia.originalFilename?.let { append(" · $it") }
                            }
                        },
                        valueColor = when {
                            serverState == null -> TextSecondary
                            serverMedia == null -> WarningAmber
                            else -> SuccessEmerald
                        }
                    )
                }
                if (detections.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(6.dp))
                    detections.forEach { det ->
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(10.dp)
                                    .background(if (det.isHeuristic) WarningAmber else PrimaryCyanBright, RoundedCornerShape(2.dp))
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "${det.damageType.replace('_', ' ')} · ${det.methodLabel()} · ${det.scoreText()}",
                                color = TextOnSurface,
                                style = CodeSm,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                    }
                }
                Spacer(modifier = Modifier.height(4.dp))
                Text("Pinch or double-tap to zoom · tap to hide details", color = TextMuted, style = CodeSm)
            }
        }
    }
}

@Composable
private fun MetaRow(label: String, value: String, valueColor: Color = TextOnSurface) {
    Row(modifier = Modifier.padding(vertical = 1.dp)) {
        Text(label, color = TextSecondary, style = CodeSm, modifier = Modifier.width(118.dp))
        Text(value, color = valueColor, style = CodeSm, maxLines = 2, overflow = TextOverflow.Ellipsis)
    }
}
