package com.roadintelligence.field.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.roadintelligence.field.domain.model.SyncStatus
import com.roadintelligence.field.ui.theme.*

@Composable
fun StatusBadge(status: SyncStatus) {
    val (bgColor, textColor, label) = when (status) {
        SyncStatus.LOCAL_DRAFT -> Triple(Color(0xFF334155), Color(0xFF94A3B8), "LOCAL DRAFT")
        SyncStatus.QUEUED -> Triple(Color(0xFF1E3A8A), Color(0xFF93C5FD), "QUEUED")
        SyncStatus.UPLOADING -> Triple(Color(0xFF065F46), Color(0xFF6EE7B7), "UPLOADING")
        SyncStatus.UPLOADED -> Triple(Color(0xFF047857), Color(0xFFA7F3D0), "UPLOADED")
        SyncStatus.PROCESSING -> Triple(Color(0xFF78350F), Color(0xFFFDE68A), "PROCESSING")
        SyncStatus.COMPLETED -> Triple(Color(0xFF064E3B), Color(0xFF34D399), "COMPLETED")
        SyncStatus.UPLOAD_FAILED -> Triple(Color(0xFF881337), Color(0xFFFDA4AF), "UPLOAD FAILED")
    }

    Box(
        modifier = Modifier
            .background(bgColor, shape = RoundedCornerShape(12.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = label,
            color = textColor,
            fontSize = 11.sp,
            fontWeight = FontWeight.SemiBold
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CommonTopBar(
    title: String,
    canNavigateBack: Boolean = false,
    onNavigateBack: () -> Unit = {},
    actions: @Composable RowScope.() -> Unit = {}
) {
    TopAppBar(
        title = {
            Text(
                text = title,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )
        },
        navigationIcon = {
            if (canNavigateBack) {
                IconButton(onClick = onNavigateBack) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = "Back",
                        tint = TextPrimary
                    )
                }
            }
        },
        actions = actions,
        colors = TopAppBarDefaults.topAppBarColors(
            containerColor = SurfaceDark
        )
    )
}

enum class NavItem(val label: String, val icon: ImageVector) {
    HOME("Home", Icons.Default.Home),
    NEW_INSPECTION("New", Icons.Default.AddCircleOutline),
    SYNC_QUEUE("Sync", Icons.Default.Sync),
    PROFILE("Profile", Icons.Default.Person)
}

@Composable
fun FieldBottomNavBar(
    selectedItem: NavItem,
    onItemSelected: (NavItem) -> Unit
) {
    NavigationBar(
        containerColor = SurfaceDark,
        tonalElevation = 8.dp
    ) {
        NavItem.values().forEach { item ->
            NavigationBarItem(
                selected = selectedItem == item,
                onClick = { onItemSelected(item) },
                icon = {
                    Icon(
                        imageVector = item.icon,
                        contentDescription = item.label,
                        tint = if (selectedItem == item) PrimaryCyan else TextMuted
                    )
                },
                label = {
                    Text(
                        text = item.label,
                        fontSize = 12.sp,
                        fontWeight = if (selectedItem == item) FontWeight.Bold else FontWeight.Normal,
                        color = if (selectedItem == item) PrimaryCyan else TextMuted
                    )
                }
            )
        }
    }
}

@Composable
fun ConnectivityBanner(isOnline: Boolean) {
    if (!isOnline) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(WarningAmber.copy(alpha = 0.15f))
                .padding(horizontal = 16.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = Icons.Default.CloudOff,
                contentDescription = "Offline Mode",
                tint = WarningAmber,
                modifier = Modifier.size(16.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "Offline Mode — Inspections are saved locally & queued for sync",
                color = WarningAmber,
                fontSize = 12.sp
            )
        }
    }
}
