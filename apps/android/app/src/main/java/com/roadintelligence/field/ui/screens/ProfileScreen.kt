package com.roadintelligence.field.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ExitToApp
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.roadintelligence.field.BuildConfig
import com.roadintelligence.field.data.repository.InspectionRemoteRepository
import com.roadintelligence.field.domain.model.SyncStatus
import com.roadintelligence.field.domain.repository.AuthRepository
import com.roadintelligence.field.domain.repository.InspectionRepository
import com.roadintelligence.field.ui.components.*
import com.roadintelligence.field.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun ProfileScreen(
    authRepository: AuthRepository,
    inspectionRepository: InspectionRepository,
    inspectionRemote: InspectionRemoteRepository,
    onLogout: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    val session = authRepository.getCurrentSession()
    val inspections by inspectionRepository.getAllInspections().collectAsState(initial = emptyList())
    val unsynced = inspections.count { it.syncStatus != SyncStatus.COMPLETED }
    var confirmSignOut by remember { mutableStateOf(false) }

    val deviceOnline by rememberDeviceOnline()
    val server by rememberServerReachability(inspectionRemote)

    val displayName = session?.fullName?.takeIf { it.isNotBlank() } ?: session?.email ?: "Not signed in"
    val initials = displayName.split(" ", "@", ".").filter { it.isNotBlank() }.take(2)
        .joinToString("") { it.first().uppercase() }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .glassBackground()
    ) {
        CommonTopBar(title = "Profile", overline = "Road Intelligence")

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            FieldCard {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(60.dp)
                            .background(PrimaryCyan.copy(alpha = 0.15f), RoundedCornerShape(18.dp))
                            .border(1.dp, PrimaryCyan.copy(alpha = 0.35f), RoundedCornerShape(18.dp)),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(initials.ifBlank { "?" }, color = PrimaryCyanBright, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    }
                    Spacer(modifier = Modifier.width(14.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(displayName, color = TextPrimary, style = MaterialTheme.typography.titleMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        if (session?.email != null && session.email != displayName) {
                            Text(session.email, color = TextSecondary, style = CodeSm, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }
                        Spacer(modifier = Modifier.height(6.dp))
                        StatusPill(
                            label = (session?.role?.takeIf { it.isNotBlank() } ?: "ROLE NOT SET").replace('_', ' '),
                            color = PrimaryCyanBright,
                            icon = Icons.Default.Badge
                        )
                    }
                }
            }

            FieldCard {
                SectionTitle("Organization", icon = Icons.Default.Business)
                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    text = session?.organizationName?.takeIf { it.isNotBlank() } ?: "Organization not set",
                    color = TextPrimary,
                    style = MaterialTheme.typography.bodyLarge
                )
                if (!session?.organizationId.isNullOrBlank()) {
                    Spacer(modifier = Modifier.height(2.dp))
                    Text("ID ${session?.organizationId}", color = TextMuted, style = CodeSm, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
            }

            FieldCard {
                SectionTitle(
                    "Connection",
                    icon = Icons.Default.Dns,
                    trailing = {
                        val chip = serverChip(server, deviceOnline)
                        ConnectionChip(chip.label, chip.color)
                    }
                )
                Spacer(modifier = Modifier.height(10.dp))
                ValueTile("Server", BuildConfig.API_BASE_URL, modifier = Modifier.fillMaxWidth())
                Spacer(modifier = Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    ValueTile("On this device", "${inspections.size} inspections", Modifier.weight(1f))
                    ValueTile(
                        "Not yet synced",
                        unsynced.toString(),
                        Modifier.weight(1f),
                        valueColor = if (unsynced > 0) WarningAmber else SuccessEmerald
                    )
                }
            }

            FieldCard {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    RiSymbol(size = 44.dp)
                    Spacer(modifier = Modifier.width(12.dp))
                    Column {
                        Text("Road Intelligence Field", color = TextPrimary, style = MaterialTheme.typography.titleSmall)
                        Text("Version ${BuildConfig.VERSION_NAME} (${BuildConfig.BUILD_TYPE})", color = TextSecondary, style = CodeSm)
                    }
                }
                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    "Offline-first road evidence collection: photos and GPS are saved on this device and uploaded for AI analysis on the server.",
                    color = TextSecondary,
                    style = MaterialTheme.typography.bodySmall
                )
            }

            SecondaryButton(
                text = "Sign Out",
                icon = Icons.AutoMirrored.Filled.ExitToApp,
                contentColor = ErrorRose,
                onClick = { confirmSignOut = true },
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(8.dp))
        }
    }

    if (confirmSignOut) {
        AlertDialog(
            onDismissRequest = { confirmSignOut = false },
            containerColor = SurfaceCard,
            title = { Text("Sign out?", color = TextPrimary) },
            text = {
                Text(
                    text = if (unsynced > 0) {
                        "$unsynced inspection(s) on this device are not synced yet. They stay on the device and upload after you sign in again."
                    } else {
                        "You will need to sign in again to capture or upload inspections."
                    },
                    color = TextSecondary
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    confirmSignOut = false
                    coroutineScope.launch {
                        authRepository.logout()
                        onLogout()
                    }
                }) { Text("Sign Out", color = ErrorRose) }
            },
            dismissButton = {
                TextButton(onClick = { confirmSignOut = false }) { Text("Cancel", color = TextOnSurface) }
            }
        )
    }
}
