package com.roadintelligence.field

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import com.roadintelligence.field.ui.components.FieldBottomNavBar
import com.roadintelligence.field.ui.components.NavItem
import com.roadintelligence.field.ui.screens.*
import com.roadintelligence.field.ui.theme.RoadIntelligenceFieldTheme

sealed class Screen {
    object Login : Screen()
    object Home : Screen()
    object NewInspection : Screen()
    data class Camera(val inspectionLocalId: String) : Screen()
    data class Detail(val inspectionLocalId: String) : Screen()
    object SyncQueue : Screen()
    object Profile : Screen()
}

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val app = RoadIntelligenceApp.instance

        setContent {
            RoadIntelligenceFieldTheme {
                val authRepository = app.authRepository
                val roadRepository = app.roadRepository
                val inspectionRepository = app.inspectionRepository
                val syncRepository = app.syncRepository

                var currentScreen by remember {
                    mutableStateOf<Screen>(
                        if (authRepository.isSessionValid()) Screen.Home else Screen.Login
                    )
                }

                var selectedNavTab by remember { mutableStateOf(NavItem.HOME) }

                when (val screen = currentScreen) {
                    is Screen.Login -> {
                        LoginScreen(
                            authRepository = authRepository,
                            onLoginSuccess = {
                                currentScreen = Screen.Home
                                selectedNavTab = NavItem.HOME
                            }
                        )
                    }

                    is Screen.Camera -> {
                        CameraCaptureScreen(
                            inspectionLocalId = screen.inspectionLocalId,
                            inspectionRepository = inspectionRepository,
                            onNavigateBack = {
                                currentScreen = Screen.NewInspection
                            }
                        )
                    }

                    is Screen.Detail -> {
                        InspectionDetailScreen(
                            localId = screen.inspectionLocalId,
                            inspectionRepository = inspectionRepository,
                            syncRepository = syncRepository,
                            onNavigateBack = {
                                currentScreen = Screen.Home
                            }
                        )
                    }

                    else -> {
                        Scaffold(
                            bottomBar = {
                                FieldBottomNavBar(
                                    selectedItem = selectedNavTab,
                                    onItemSelected = { tab ->
                                        selectedNavTab = tab
                                        currentScreen = when (tab) {
                                            NavItem.HOME -> Screen.Home
                                            NavItem.NEW_INSPECTION -> Screen.NewInspection
                                            NavItem.SYNC_QUEUE -> Screen.SyncQueue
                                            NavItem.PROFILE -> Screen.Profile
                                        }
                                    }
                                )
                            }
                        ) { innerPadding ->
                            Box(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(innerPadding)
                            ) {
                                when (selectedNavTab) {
                                    NavItem.HOME -> {
                                        HomeScreen(
                                            inspectionRepository = inspectionRepository,
                                            roadRepository = roadRepository,
                                            syncRepository = syncRepository,
                                            onNavigateToNewInspection = {
                                                selectedNavTab = NavItem.NEW_INSPECTION
                                                currentScreen = Screen.NewInspection
                                            },
                                            onNavigateToDetail = { localId ->
                                                currentScreen = Screen.Detail(localId)
                                            }
                                        )
                                    }

                                    NavItem.NEW_INSPECTION -> {
                                        NewInspectionScreen(
                                            inspectionRepository = inspectionRepository,
                                            roadRepository = roadRepository,
                                            syncRepository = syncRepository,
                                            onNavigateBack = {
                                                selectedNavTab = NavItem.HOME
                                                currentScreen = Screen.Home
                                            },
                                            onNavigateToCamera = { localId ->
                                                currentScreen = Screen.Camera(localId)
                                            }
                                        )
                                    }

                                    NavItem.SYNC_QUEUE -> {
                                        SyncQueueScreen(
                                            syncRepository = syncRepository,
                                            onNavigateBack = {
                                                selectedNavTab = NavItem.HOME
                                                currentScreen = Screen.Home
                                            }
                                        )
                                    }

                                    NavItem.PROFILE -> {
                                        ProfileScreen(
                                            authRepository = authRepository,
                                            onLogout = {
                                                currentScreen = Screen.Login
                                            }
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
