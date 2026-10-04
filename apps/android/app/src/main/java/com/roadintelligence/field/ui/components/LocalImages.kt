package com.roadintelligence.field.ui.components

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.util.LruCache
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BrokenImage
import androidx.compose.material.icons.filled.HideImage
import androidx.compose.material.icons.filled.Image
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.State
import androidx.compose.runtime.produceState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import com.roadintelligence.field.ui.theme.SurfaceLowest
import com.roadintelligence.field.ui.theme.TextMuted
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

/** Result of decoding a photo stored on this device. */
sealed class LocalImage {
    object Loading : LocalImage()
    object Missing : LocalImage()
    data class Ready(val bitmap: Bitmap, val sourceWidth: Int, val sourceHeight: Int) : LocalImage()
}

// Downsampled, rotation-corrected bitmaps keyed by "path@size"; sized in kilobytes.
private val bitmapCache = object : LruCache<String, LocalImage.Ready>(24 * 1024) {
    override fun sizeOf(key: String, value: LocalImage.Ready): Int = value.bitmap.byteCount / 1024
}

/**
 * Decodes the inspection photo at [path] no larger than needed for [maxDimensionPx] and applies the
 * EXIF orientation written by CameraX, so the image is shown the way it was framed.
 */
suspend fun loadLocalImage(path: String, maxDimensionPx: Int): LocalImage = withContext(Dispatchers.IO) {
    val key = "$path@$maxDimensionPx"
    bitmapCache.get(key)?.let { return@withContext it }
    val file = File(path)
    if (!file.exists() || file.length() == 0L) return@withContext LocalImage.Missing
    try {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(path, bounds)
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return@withContext LocalImage.Missing

        var sample = 1
        while (maxOf(bounds.outWidth, bounds.outHeight) / (sample * 2) >= maxDimensionPx) sample *= 2
        val decoded = BitmapFactory.decodeFile(path, BitmapFactory.Options().apply { inSampleSize = sample })
            ?: return@withContext LocalImage.Missing

        val orientation = ExifInterface(path).getAttributeInt(
            ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL
        )
        val degrees = when (orientation) {
            ExifInterface.ORIENTATION_ROTATE_90 -> 90f
            ExifInterface.ORIENTATION_ROTATE_180 -> 180f
            ExifInterface.ORIENTATION_ROTATE_270 -> 270f
            else -> 0f
        }
        val upright = if (degrees == 0f) decoded else {
            Bitmap.createBitmap(decoded, 0, 0, decoded.width, decoded.height, Matrix().apply { postRotate(degrees) }, true)
                .also { if (it != decoded) decoded.recycle() }
        }
        val swapped = degrees == 90f || degrees == 270f
        val ready = LocalImage.Ready(
            bitmap = upright,
            sourceWidth = if (swapped) bounds.outHeight else bounds.outWidth,
            sourceHeight = if (swapped) bounds.outWidth else bounds.outHeight
        )
        bitmapCache.put(key, ready)
        ready
    } catch (e: Exception) {
        LocalImage.Missing
    } catch (e: OutOfMemoryError) {
        LocalImage.Missing
    }
}

@Composable
fun rememberLocalImage(path: String?, maxDimensionPx: Int): State<LocalImage> =
    produceState<LocalImage>(initialValue = LocalImage.Loading, path, maxDimensionPx) {
        value = if (path == null) LocalImage.Missing else loadLocalImage(path, maxDimensionPx)
    }

/** Cropped thumbnail of a photo stored on this device; shows a neutral tile while loading or if missing. */
@Composable
fun LocalThumbnail(
    path: String?,
    modifier: Modifier = Modifier,
    maxDimensionPx: Int = 320,
    contentDescription: String? = null
) {
    val image = rememberLocalImage(path, maxDimensionPx).value
    Box(modifier = modifier.background(SurfaceLowest), contentAlignment = Alignment.Center) {
        if (path == null) {
            // The inspection has no photo at all (not a missing file).
            Icon(Icons.Default.HideImage, contentDescription = "No photo", tint = TextMuted, modifier = Modifier.size(22.dp))
        } else when (image) {
            is LocalImage.Ready -> Image(
                bitmap = image.bitmap.asImageBitmap(),
                contentDescription = contentDescription,
                contentScale = ContentScale.Crop,
                modifier = Modifier.matchParentSize()
            )
            LocalImage.Missing -> Icon(
                Icons.Default.BrokenImage,
                contentDescription = "Photo file not found on this device",
                tint = TextMuted,
                modifier = Modifier.size(22.dp)
            )
            LocalImage.Loading -> Icon(Icons.Default.Image, contentDescription = null, tint = TextMuted, modifier = Modifier.size(22.dp))
        }
    }
}
