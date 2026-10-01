package com.roadintelligence.field.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
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
import com.roadintelligence.field.domain.repository.AuthRepository
import com.roadintelligence.field.ui.components.CommonTopBar
import com.roadintelligence.field.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun ProfileScreen(
    authRepository: AuthRepository,
    onLogout: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    val session = authRepository.getCurrentSession()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
    ) {
        CommonTopBar(title = "Inspector Profile")

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(16.dp))

            // User Avatar
            Box(
                modifier = Modifier
                    .size(72.dp)
                    .background(PrimaryCyan.copy(alpha = 0.2f), CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Person,
                    contentDescription = null,
                    tint = PrimaryCyan,
                    modifier = Modifier.size(36.dp)
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = session?.fullName ?: "Field Inspector",
                color = TextPrimary,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = session?.email ?: "inspector@example.com",
                color = TextSecondary,
                fontSize = 13.sp
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Organization Card
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = SurfaceDark,
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Current Organization", color = TextMuted, fontSize = 12.sp)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = session?.organizationName ?: "Default Municipality",
                        color = TextPrimary,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Role: ${session?.role ?: "FIELD_INSPECTOR"}", color = PrimaryCyan, fontSize = 13.sp)
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // App Information Card
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = SurfaceDark,
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Application Details", color = TextMuted, fontSize = 12.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Version: 1.0.0 (Phase 14 MVP)", color = TextPrimary, fontSize = 13.sp)
                    Text("Architecture: Jetpack Compose + Room + WorkManager", color = TextSecondary, fontSize = 12.sp)
                    Text("Target: Offline-First Road Evidence Collection", color = TextSecondary, fontSize = 12.sp)
                }
            }

            Spacer(modifier = Modifier.weight(1f))

            // Logout Button
            Button(
                onClick = {
                    coroutineScope.launch {
                        authRepository.logout()
                        onLogout()
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = ErrorRose.copy(alpha = 0.85f)),
                shape = RoundedCornerShape(10.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp)
            ) {
                Icon(Icons.Default.ExitToApp, contentDescription = null, tint = Color.White)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Sign Out", color = Color.White, fontWeight = FontWeight.Bold)
            }

            Spacer(modifier = Modifier.height(20.dp))
        }
    }
}
