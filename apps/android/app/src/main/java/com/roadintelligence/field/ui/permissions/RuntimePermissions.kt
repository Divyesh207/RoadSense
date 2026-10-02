package com.roadintelligence.field.ui.permissions

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.platform.LocalContext
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

/** Result of a contextual runtime permission request. */
enum class PermissionResult {
    GRANTED,

    /** Denied, but the system dialog can be shown again. */
    DENIED,

    /** Denied with "Don't ask again" (or blocked by policy): only App Settings can grant it. */
    PERMANENTLY_DENIED
}

fun Context.hasAnyPermission(permissions: Array<String>): Boolean =
    permissions.any { ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED }

fun Context.hasAllPermissions(permissions: Array<String>): Boolean =
    permissions.all { ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED }

private fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}

/** Opens this app's system settings page so the user can grant a permanently denied permission. */
fun Context.openAppSettings() {
    startActivity(
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", packageName, null))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    )
}

/**
 * Returns a function that requests [permissions] when the user invokes a feature that needs them.
 * If they are already granted, [onResult] receives GRANTED immediately without showing a dialog.
 *
 * @param requireAll true when every permission is required (camera); false when any one is enough
 *   (location: Android 12+ users may grant only approximate/coarse location).
 */
@Composable
fun rememberPermissionRequest(
    permissions: Array<String>,
    requireAll: Boolean,
    onResult: (PermissionResult) -> Unit
): () -> Unit {
    val context = LocalContext.current
    val currentOnResult = rememberUpdatedState(onResult)

    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        val granted = if (requireAll) {
            permissions.all { results[it] == true || context.hasAllPermissions(arrayOf(it)) }
        } else {
            results.values.any { it } || context.hasAnyPermission(permissions)
        }
        val result = when {
            granted -> PermissionResult.GRANTED
            // After a denial, no rationale means the system will not show the dialog again.
            context.findActivity()?.let { activity ->
                permissions.none { ActivityCompat.shouldShowRequestPermissionRationale(activity, it) }
            } == true -> PermissionResult.PERMANENTLY_DENIED
            else -> PermissionResult.DENIED
        }
        currentOnResult.value(result)
    }

    return remember(permissions.joinToString(), requireAll) {
        {
            val alreadyGranted = if (requireAll) context.hasAllPermissions(permissions) else context.hasAnyPermission(permissions)
            if (alreadyGranted) currentOnResult.value(PermissionResult.GRANTED) else launcher.launch(permissions)
        }
    }
}
