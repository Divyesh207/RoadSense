package com.roadintelligence.field.ui.screens

import android.Manifest
import android.util.Log
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.roadintelligence.field.domain.model.InspectionMedia
import com.roadintelligence.field.domain.model.UploadStatus
import com.roadintelligence.field.domain.repository.InspectionRepository
import com.roadintelligence.field.ui.components.LocalThumbnail
import com.roadintelligence.field.ui.components.PrimaryButton
import com.roadintelligence.field.ui.components.accuracyColor
import com.roadintelligence.field.ui.permissions.hasAllPermissions
import com.roadintelligence.field.ui.theme.*
import kotlinx.coroutines.launch
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

/**
 * CameraX still-photo capture. [roadLabel] and the GPS values are display-only context taken from
 * the inspection form; they do not change what is captured or stored.
 */
@Composable
fun CameraCaptureScreen(
    inspectionLocalId: String,
    inspectionRepository: InspectionRepository,
    onNavigateBack: () -> Unit,
    roadLabel: String? = null,
    hasGpsFix: Boolean = false,
    gpsAccuracyMeters: Float? = null
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val coroutineScope = rememberCoroutineScope()

    // Normally granted before navigating here (NewInspectionScreen); this covers a
    // permission revoked in Settings while the app was in the background.
    if (!context.hasAllPermissions(arrayOf(Manifest.permission.CAMERA))) {
        CameraPermissionMissing(onNavigateBack)
        return
    }

    var imageCapture by remember { mutableStateOf<ImageCapture?>(null) }
    var lensFacing by remember { mutableStateOf(CameraSelector.LENS_FACING_BACK) }
    var flashMode by remember { mutableStateOf(ImageCapture.FLASH_MODE_AUTO) }
    var capturedCount by remember { mutableStateOf(0) }
    var lastCapturedPath by remember { mutableStateOf<String?>(null) }
    var isCapturing by remember { mutableStateOf(false) }
    var captureError by remember { mutableStateOf<String?>(null) }

    // Check count of existing media
    LaunchedEffect(Unit) {
        val mediaList = inspectionRepository.getMediaForInspection(inspectionLocalId)
        capturedCount = mediaList.size
        if (lastCapturedPath == null) lastCapturedPath = mediaList.lastOrNull()?.localFilePath
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        // CameraX Preview View
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                val previewView = PreviewView(ctx)
                val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)
                cameraProviderFuture.addListener({
                    val cameraProvider = cameraProviderFuture.get()
                    val preview = Preview.Builder().build().also {
                        it.setSurfaceProvider(previewView.surfaceProvider)
                    }

                    val capture = ImageCapture.Builder()
                        .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                        .setFlashMode(flashMode)
                        .build()
                    imageCapture = capture

                    val cameraSelector = CameraSelector.Builder()
                        .requireLensFacing(lensFacing)
                        .build()

                    try {
                        cameraProvider.unbindAll()
                        cameraProvider.bindToLifecycle(
                            lifecycleOwner,
                            cameraSelector,
                            preview,
                            capture
                        )
                    } catch (e: Exception) {
                        Log.e(CAMERA_TAG, "CameraX bindToLifecycle failed", e)
                    }
                }, ContextCompat.getMainExecutor(ctx))

                previewView
            }
        )

        // Top overlay: back, inspection context, flash
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.TopCenter)
                .background(Color.Black.copy(alpha = 0.55f))
                .padding(horizontal = 12.dp, vertical = 10.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(
                    onClick = onNavigateBack,
                    modifier = Modifier.background(GlassBar, CircleShape)
                ) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = Color.White)
                }

                Spacer(modifier = Modifier.width(10.dp))

                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = roadLabel ?: "No road selected",
                        color = Color.White,
                        style = MaterialTheme.typography.labelLarge,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        val gpsColor = if (hasGpsFix) accuracyColor(gpsAccuracyMeters) else TextSecondary
                        Icon(
                            imageVector = if (hasGpsFix) Icons.Default.GpsFixed else Icons.Default.GpsOff,
                            contentDescription = null,
                            tint = gpsColor,
                            modifier = Modifier.size(12.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = when {
                                !hasGpsFix -> "No GPS fix captured yet"
                                gpsAccuracyMeters != null -> "GPS fix ±%.1f m".format(gpsAccuracyMeters)
                                else -> "GPS fix captured"
                            },
                            color = gpsColor,
                            style = CodeSm
                        )
                    }
                }

                // Flash mode toggle
                IconButton(
                    onClick = {
                        flashMode = when (flashMode) {
                            ImageCapture.FLASH_MODE_AUTO -> ImageCapture.FLASH_MODE_ON
                            ImageCapture.FLASH_MODE_ON -> ImageCapture.FLASH_MODE_OFF
                            else -> ImageCapture.FLASH_MODE_AUTO
                        }
                        imageCapture?.flashMode = flashMode
                    },
                    modifier = Modifier.background(GlassBar, CircleShape)
                ) {
                    val icon = when (flashMode) {
                        ImageCapture.FLASH_MODE_ON -> Icons.Default.FlashOn
                        ImageCapture.FLASH_MODE_OFF -> Icons.Default.FlashOff
                        else -> Icons.Default.FlashAuto
                    }
                    val description = when (flashMode) {
                        ImageCapture.FLASH_MODE_ON -> "Flash on"
                        ImageCapture.FLASH_MODE_OFF -> "Flash off"
                        else -> "Flash auto"
                    }
                    Icon(icon, contentDescription = description, tint = Color.White)
                }
            }

            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(GlassBar, RoundedCornerShape(10.dp))
                    .padding(horizontal = 10.dp, vertical = 6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(Icons.Default.Info, contentDescription = null, tint = PrimaryCyanBright, modifier = Modifier.size(14.dp))
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = captureError ?: "Frame the damage with surrounding road visible",
                    color = if (captureError != null) ErrorSoft else Color.White,
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }

        // Bottom Capture Controls
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .background(Color.Black.copy(alpha = 0.7f))
                .padding(vertical = 18.dp, horizontal = 20.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Last capture and photo count
                Box(modifier = Modifier.size(64.dp), contentAlignment = Alignment.Center) {
                    LocalThumbnail(
                        path = lastCapturedPath,
                        maxDimensionPx = 200,
                        contentDescription = "Last captured photo",
                        modifier = Modifier
                            .size(56.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .border(2.dp, Color.White.copy(alpha = 0.7f), RoundedCornerShape(12.dp))
                    )
                    Box(
                        modifier = Modifier
                            .align(Alignment.TopEnd)
                            .background(PrimaryCyan, CircleShape)
                            .defaultMinSize(minWidth = 22.dp, minHeight = 22.dp)
                            .padding(horizontal = 5.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(capturedCount.toString(), color = OnPrimaryCyan, style = CodeSm, fontWeight = FontWeight.Bold)
                    }
                }

                // Shutter Button
                Box(
                    modifier = Modifier
                        .size(76.dp)
                        .border(4.dp, Color.White, CircleShape)
                        .padding(7.dp)
                        .background(if (isCapturing) Color.Gray else PrimaryCyan, CircleShape)
                        .clickable(enabled = !isCapturing, onClickLabel = "Capture photo") {
                            val capture = imageCapture ?: return@clickable
                            isCapturing = true
                            captureError = null

                            val outputDir = File(context.filesDir, "inspections/$inspectionLocalId")
                            if (!outputDir.exists()) outputDir.mkdirs()

                            val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
                            val photoFile = File(outputDir, "IMG_$timeStamp.jpg")

                            val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()
                            capture.takePicture(
                                outputOptions,
                                ContextCompat.getMainExecutor(context),
                                object : ImageCapture.OnImageSavedCallback {
                                    override fun onImageSaved(outputFileResults: ImageCapture.OutputFileResults) {
                                        isCapturing = false
                                        lastCapturedPath = photoFile.absolutePath
                                        capturedCount += 1

                                        // Persist media to Room database
                                        coroutineScope.launch {
                                            val media = InspectionMedia(
                                                localId = UUID.randomUUID().toString(),
                                                inspectionLocalId = inspectionLocalId,
                                                localFilePath = photoFile.absolutePath,
                                                mediaType = "IMAGE",
                                                mimeType = "image/jpeg",
                                                fileSizeBytes = photoFile.length(),
                                                uploadStatus = UploadStatus.PENDING
                                            )
                                            inspectionRepository.addMediaToInspection(media)
                                        }
                                    }

                                    override fun onError(exception: ImageCaptureException) {
                                        isCapturing = false
                                        captureError = "Capture failed — try again"
                                        Log.e(CAMERA_TAG, "takePicture failed", exception)
                                    }
                                }
                            )
                        },
                    contentAlignment = Alignment.Center
                ) {
                    if (isCapturing) {
                        CircularProgressIndicator(color = Color.White, modifier = Modifier.size(24.dp))
                    }
                }

                // Switch Camera Lens Button
                IconButton(
                    onClick = {
                        lensFacing = if (lensFacing == CameraSelector.LENS_FACING_BACK) {
                            CameraSelector.LENS_FACING_FRONT
                        } else {
                            CameraSelector.LENS_FACING_BACK
                        }
                    },
                    modifier = Modifier
                        .size(56.dp)
                        .background(GlassBar, CircleShape)
                ) {
                    Icon(
                        Icons.Default.Cameraswitch,
                        contentDescription = "Switch Camera",
                        tint = Color.White,
                        modifier = Modifier.size(26.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            PrimaryButton(
                text = if (capturedCount == 0) "Done" else "Done — review $capturedCount photo" + if (capturedCount == 1) "" else "s",
                icon = Icons.Default.Check,
                onClick = onNavigateBack,
                modifier = Modifier.fillMaxWidth()
            )
        }
    }
}

private const val CAMERA_TAG = "CameraCapture"

@Composable
private fun CameraPermissionMissing(onNavigateBack: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .glassBackground()
            .padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                modifier = Modifier
                    .size(64.dp)
                    .background(WarningAmber.copy(alpha = 0.12f), RoundedCornerShape(18.dp))
                    .border(1.dp, WarningAmber.copy(alpha = 0.4f), RoundedCornerShape(18.dp)),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.NoPhotography, contentDescription = null, tint = WarningAmber, modifier = Modifier.size(32.dp))
            }
            Spacer(modifier = Modifier.height(14.dp))
            Text("Camera permission required", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                "Go back and tap Capture Photo Evidence to allow camera access.",
                color = TextSecondary,
                style = MaterialTheme.typography.bodySmall,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center
            )
            Spacer(modifier = Modifier.height(18.dp))
            PrimaryButton(text = "Back", onClick = onNavigateBack, modifier = Modifier.fillMaxWidth())
        }
    }
}
