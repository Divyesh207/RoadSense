package com.roadintelligence.field.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.roadintelligence.field.R
import com.roadintelligence.field.domain.model.SyncStatus
import com.roadintelligence.field.ui.theme.*

// ---------------------------------------------------------------------------------------------
// Branding
// ---------------------------------------------------------------------------------------------

/** The simplified RI symbol of the official Road Intelligence logo. */
@Composable
fun RiSymbol(size: Dp = 36.dp, modifier: Modifier = Modifier) {
    Image(
        painter = painterResource(R.drawable.ri_symbol),
        contentDescription = "Road Intelligence",
        modifier = modifier.size(size)
    )
}

// ---------------------------------------------------------------------------------------------
// Status pills
// ---------------------------------------------------------------------------------------------

/** Pill with an icon and a label; status is never conveyed by colour alone. */
@Composable
fun StatusPill(
    label: String,
    color: Color,
    icon: ImageVector? = null,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .background(color.copy(alpha = 0.15f), RoundedCornerShape(999.dp))
            .border(1.dp, color.copy(alpha = 0.35f), RoundedCornerShape(999.dp))
            .padding(horizontal = 9.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        if (icon != null) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(12.dp))
            Spacer(modifier = Modifier.width(4.dp))
        }
        Text(
            text = label,
            color = color,
            style = CodeSm,
            fontWeight = FontWeight.SemiBold,
            maxLines = 1
        )
    }
}

data class SyncStatusStyle(val label: String, val color: Color, val icon: ImageVector)

fun syncStatusStyle(status: SyncStatus): SyncStatusStyle = when (status) {
    SyncStatus.LOCAL_DRAFT -> SyncStatusStyle("LOCAL DRAFT", TextSecondary, Icons.Default.Edit)
    SyncStatus.QUEUED -> SyncStatusStyle("QUEUED", SecondaryBlueSoft, Icons.Default.Schedule)
    SyncStatus.UPLOADING -> SyncStatusStyle("UPLOADING", PrimaryCyanBright, Icons.Default.CloudUpload)
    SyncStatus.UPLOADED -> SyncStatusStyle("UPLOADED", SuccessEmeraldSoft, Icons.Default.CloudDone)
    SyncStatus.PROCESSING -> SyncStatusStyle("PROCESSING", ReviewPurple, Icons.Default.Memory)
    SyncStatus.COMPLETED -> SyncStatusStyle("SYNCED", SuccessEmerald, Icons.Default.CheckCircle)
    SyncStatus.UPLOAD_FAILED -> SyncStatusStyle("UPLOAD FAILED", ErrorRose, Icons.Default.ErrorOutline)
}

@Composable
fun StatusBadge(status: SyncStatus, modifier: Modifier = Modifier) {
    val style = syncStatusStyle(status)
    StatusPill(label = style.label, color = style.color, icon = style.icon, modifier = modifier)
}

/** Colour for a server-side severity / status word. Unknown values stay neutral. */
fun severityColor(severity: String?): Color = when (severity?.uppercase()) {
    "CRITICAL" -> ErrorRose
    "HIGH" -> WarningOrange
    "MEDIUM" -> WarningAmber
    "LOW" -> SuccessEmerald
    else -> TextSecondary
}

// ---------------------------------------------------------------------------------------------
// Layout building blocks
// ---------------------------------------------------------------------------------------------

@Composable
fun FieldCard(
    modifier: Modifier = Modifier,
    borderColor: Color = BorderDark,
    containerColor: Color = SurfaceDark,
    contentPadding: PaddingValues = PaddingValues(16.dp),
    content: @Composable ColumnScope.() -> Unit
) {
    // Glass panel. The default look is the shared glass fill and highlighted edge; a caller
    // that passes its own colours (status-tinted cards) gets those on the same shape.
    val isDefault = borderColor == BorderDark && containerColor == SurfaceDark
    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(GlassShape)
            .then(if (isDefault) Modifier.background(GlassFill, GlassShape) else Modifier.background(containerColor, GlassShape))
            .border(
                if (isDefault) BorderStroke(1.dp, GlassEdge) else BorderStroke(1.dp, borderColor),
                GlassShape
            )
            .padding(contentPadding),
        content = content
    )
}

/** Small uppercase label used above values and sections. */
@Composable
fun FieldLabel(text: String, color: Color = TextSecondary, modifier: Modifier = Modifier) {
    Text(
        text = text.uppercase(),
        color = color,
        style = CodeSm,
        letterSpacing = 0.6.sp,
        modifier = modifier
    )
}

@Composable
fun SectionTitle(
    title: String,
    icon: ImageVector? = null,
    trailing: @Composable (() -> Unit)? = null
) {
    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
        if (icon != null) {
            Icon(icon, contentDescription = null, tint = PrimaryCyan, modifier = Modifier.size(18.dp))
            Spacer(modifier = Modifier.width(8.dp))
        }
        Text(
            text = title,
            color = TextPrimary,
            style = MaterialTheme.typography.titleSmall,
            modifier = Modifier.weight(1f)
        )
        if (trailing != null) trailing()
    }
}

/** A labelled value inside an inset tile (used for coordinates, accuracy, IDs). */
@Composable
fun ValueTile(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
    valueColor: Color = TextPrimary,
    mono: Boolean = true
) {
    Column(
        modifier = modifier
            .background(SurfaceLowest, RoundedCornerShape(12.dp))
            .border(1.dp, BorderDark, RoundedCornerShape(12.dp))
            .padding(horizontal = 12.dp, vertical = 10.dp)
    ) {
        FieldLabel(label)
        Spacer(modifier = Modifier.height(3.dp))
        Text(
            text = value,
            color = valueColor,
            style = if (mono) CodeMd else MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold
        )
    }
}

enum class MessageKind { ERROR, WARNING, INFO, SUCCESS }

@Composable
fun MessageCard(
    kind: MessageKind,
    title: String?,
    message: String,
    modifier: Modifier = Modifier,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null
) {
    val (color, icon) = when (kind) {
        MessageKind.ERROR -> ErrorRose to Icons.Default.ErrorOutline
        MessageKind.WARNING -> WarningAmber to Icons.Default.WarningAmber
        MessageKind.INFO -> PrimaryCyanBright to Icons.Default.Info
        MessageKind.SUCCESS -> SuccessEmerald to Icons.Default.CheckCircle
    }
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = color.copy(alpha = 0.10f),
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, color.copy(alpha = 0.35f))
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.Top) {
                Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(20.dp))
                Spacer(modifier = Modifier.width(10.dp))
                Column(modifier = Modifier.weight(1f)) {
                    if (title != null) {
                        Text(title, color = color, style = MaterialTheme.typography.labelLarge)
                        Spacer(modifier = Modifier.height(2.dp))
                    }
                    Text(message, color = TextOnSurface, style = MaterialTheme.typography.bodySmall)
                }
            }
            if (actionLabel != null && onAction != null) {
                Spacer(modifier = Modifier.height(10.dp))
                OutlinedButton(
                    onClick = onAction,
                    border = BorderStroke(1.dp, color.copy(alpha = 0.6f)),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = color),
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.heightIn(min = 48.dp)
                ) {
                    Text(actionLabel, style = MaterialTheme.typography.labelLarge)
                }
            }
        }
    }
}

@Composable
fun EmptyState(
    icon: ImageVector,
    title: String,
    message: String,
    modifier: Modifier = Modifier,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null
) {
    FieldCard(modifier = modifier, contentPadding = PaddingValues(28.dp)) {
        Column(modifier = Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                modifier = Modifier
                    .size(52.dp)
                    .background(SurfaceCard, RoundedCornerShape(16.dp))
                    .border(1.dp, BorderDark, RoundedCornerShape(16.dp)),
                contentAlignment = Alignment.Center
            ) {
                Icon(icon, contentDescription = null, tint = PrimaryCyanBright, modifier = Modifier.size(26.dp))
            }
            Spacer(modifier = Modifier.height(12.dp))
            Text(title, color = TextPrimary, style = MaterialTheme.typography.titleSmall)
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                message,
                color = TextSecondary,
                style = MaterialTheme.typography.bodySmall,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center
            )
            if (actionLabel != null && onAction != null) {
                Spacer(modifier = Modifier.height(14.dp))
                PrimaryButton(text = actionLabel, onClick = onAction, modifier = Modifier.fillMaxWidth())
            }
        }
    }
}

// ---------------------------------------------------------------------------------------------
// Buttons and inputs
// ---------------------------------------------------------------------------------------------

@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null,
    enabled: Boolean = true,
    loading: Boolean = false,
    height: Dp = 52.dp
) {
    Button(
        onClick = onClick,
        enabled = enabled && !loading,
        colors = ButtonDefaults.buttonColors(
            containerColor = PrimaryCyan,
            contentColor = OnPrimaryCyan,
            disabledContainerColor = SurfaceCard,
            disabledContentColor = TextMuted
        ),
        shape = RoundedCornerShape(12.dp),
        contentPadding = PaddingValues(horizontal = 12.dp),
        modifier = modifier.height(height)
    ) {
        if (loading) {
            CircularProgressIndicator(color = OnPrimaryCyan, modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
        } else {
            if (icon != null) {
                Icon(icon, contentDescription = null, modifier = Modifier.size(20.dp))
                Spacer(modifier = Modifier.width(8.dp))
            }
            Text(text, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold, maxLines = 1)
        }
    }
}

@Composable
fun SecondaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null,
    enabled: Boolean = true,
    contentColor: Color = TextPrimary,
    height: Dp = 52.dp
) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled,
        border = BorderStroke(1.dp, if (contentColor == TextPrimary) BorderDark else contentColor.copy(alpha = 0.5f)),
        colors = ButtonDefaults.outlinedButtonColors(containerColor = SurfaceCard, contentColor = contentColor),
        shape = RoundedCornerShape(12.dp),
        contentPadding = PaddingValues(horizontal = 12.dp),
        modifier = modifier.height(height)
    ) {
        if (icon != null) {
            Icon(icon, contentDescription = null, modifier = Modifier.size(18.dp))
            Spacer(modifier = Modifier.width(8.dp))
        }
        Text(text, style = MaterialTheme.typography.labelLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

@Composable
fun fieldTextFieldColors(): TextFieldColors = OutlinedTextFieldDefaults.colors(
    focusedBorderColor = PrimaryCyan,
    unfocusedBorderColor = BorderDark,
    disabledBorderColor = BorderDark,
    focusedTextColor = TextPrimary,
    unfocusedTextColor = TextPrimary,
    disabledTextColor = TextMuted,
    focusedContainerColor = SurfaceLowest,
    unfocusedContainerColor = SurfaceLowest,
    disabledContainerColor = SurfaceLowest,
    focusedLabelColor = PrimaryCyanBright,
    unfocusedLabelColor = TextSecondary,
    disabledLabelColor = TextMuted,
    cursorColor = PrimaryCyan,
    focusedLeadingIconColor = PrimaryCyanBright,
    unfocusedLeadingIconColor = TextSecondary,
    focusedTrailingIconColor = TextSecondary,
    unfocusedTrailingIconColor = TextSecondary
)

// ---------------------------------------------------------------------------------------------
// App bars and navigation
// ---------------------------------------------------------------------------------------------

/**
 * Top bar: back arrow or the RI symbol, a title with an optional small overline, and actions.
 */
@Composable
fun CommonTopBar(
    title: String,
    canNavigateBack: Boolean = false,
    onNavigateBack: () -> Unit = {},
    overline: String? = null,
    showLogo: Boolean = !canNavigateBack,
    actions: @Composable RowScope.() -> Unit = {}
) {
    Column {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(GlassBar)
                .heightIn(min = 60.dp)
                .padding(start = if (canNavigateBack) 4.dp else 16.dp, end = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            if (canNavigateBack) {
                IconButton(onClick = onNavigateBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = TextPrimary)
                }
            }
            if (showLogo) {
                RiSymbol(size = 34.dp)
                Spacer(modifier = Modifier.width(10.dp))
            }
            Column(modifier = Modifier.weight(1f)) {
                if (overline != null) {
                    Text(
                        overline.uppercase(),
                        color = PrimaryCyanBright,
                        style = CodeSm,
                        letterSpacing = 1.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                Text(
                    text = title,
                    color = TextPrimary,
                    style = MaterialTheme.typography.titleLarge,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
            actions()
        }
        HorizontalDivider(color = BorderDark, thickness = 1.dp)
    }
}

/** Compact connection chip for the top bar. */
@Composable
fun ConnectionChip(label: String, color: Color, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier
            .background(color.copy(alpha = 0.12f), RoundedCornerShape(999.dp))
            .border(1.dp, color.copy(alpha = 0.3f), RoundedCornerShape(999.dp))
            .padding(horizontal = 10.dp, vertical = 5.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(modifier = Modifier.size(7.dp).clip(CircleShape).background(color))
        Spacer(modifier = Modifier.width(6.dp))
        Text(label, color = color, style = CodeSm, fontWeight = FontWeight.SemiBold, maxLines = 1)
    }
}

enum class NavItem(val label: String, val icon: ImageVector) {
    HOME("Home", Icons.Default.Home),
    NEW_INSPECTION("New", Icons.Default.AddCircleOutline),
    SYNC_QUEUE("Queue", Icons.Default.Sync),
    PROFILE("Profile", Icons.Default.Person)
}

@Composable
fun FieldBottomNavBar(
    selectedItem: NavItem,
    onItemSelected: (NavItem) -> Unit,
    syncBadgeCount: Int = 0
) {
    // Floating glass bar: rounded, inset from the screen edges, above the system navigation.
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(BackgroundDark)
            .padding(start = 12.dp, end = 12.dp, top = 6.dp, bottom = 8.dp)
    ) {
        NavigationBar(
            containerColor = Color.Transparent,
            tonalElevation = 0.dp,
            windowInsets = WindowInsets(0, 0, 0, 0),
            modifier = Modifier
                .height(68.dp)
                .clip(RoundedCornerShape(22.dp))
                .background(GlassFill, RoundedCornerShape(22.dp))
                .border(BorderStroke(1.dp, GlassEdge), RoundedCornerShape(22.dp))
        ) {
            NavItem.values().forEach { item ->
                val selected = selectedItem == item
                NavigationBarItem(
                    selected = selected,
                    onClick = { onItemSelected(item) },
                    icon = {
                        if (item == NavItem.SYNC_QUEUE && syncBadgeCount > 0) {
                            BadgedBox(badge = {
                                Badge(containerColor = PrimaryCyan, contentColor = OnPrimaryCyan) {
                                    Text(syncBadgeCount.toString(), style = CodeSm)
                                }
                            }) {
                                Icon(item.icon, contentDescription = "${item.label}, $syncBadgeCount pending")
                            }
                        } else {
                            Icon(item.icon, contentDescription = item.label)
                        }
                    },
                    label = {
                        Text(
                            text = item.label,
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium
                        )
                    },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = PrimaryCyanBright,
                        selectedTextColor = PrimaryCyanBright,
                        unselectedIconColor = TextSecondary,
                        unselectedTextColor = TextSecondary,
                        indicatorColor = PrimaryCyan.copy(alpha = 0.20f)
                    )
                )
            }
        }
    }
}

@Composable
fun ConnectivityBanner(isOnline: Boolean) {
    if (!isOnline) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(WarningAmber.copy(alpha = 0.14f))
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(Icons.Default.CloudOff, contentDescription = null, tint = WarningAmber, modifier = Modifier.size(16.dp))
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "Offline — inspections are saved on this device and queued for sync.",
                color = WarningAmber,
                style = MaterialTheme.typography.bodySmall
            )
        }
    }
}
