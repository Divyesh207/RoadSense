package com.roadintelligence.field

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import com.roadintelligence.field.domain.model.SyncStatus
import com.roadintelligence.field.ui.components.FieldBottomNavBar
import com.roadintelligence.field.ui.components.NavItem
import com.roadintelligence.field.ui.screens.*
import com.roadintelligence.field.ui.theme.BackgroundDark
import com.roadintelligence.field.ui.theme.RoadIntelligenceFieldTheme

sealed class Screen {
    object Login : Screen()
    object Register : Screen()
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
                val inspectionRemote = app.inspectionRemote

                var currentScreen by remember {
                    mutableStateOf<Screen>(
                        if (authRepository.isSessionValid()) Screen.Home else Screen.Login
                    )
                }

                var selectedNavTab by remember { mutableStateOf(NavItem.HOME) }

                // Hoisted so the in-progress inspection survives switching to the camera
                // screen; replaced with a fresh form once it is saved/queued or abandoned.
                var inspectionForm by remember { mutableStateOf(NewInspectionFormState()) }

                fun goToTab(tab: NavItem) {
                    selectedNavTab = tab
                    currentScreen = when (tab) {
                        NavItem.HOME -> Screen.Home
                        NavItem.NEW_INSPECTION -> Screen.NewInspection
                        NavItem.SYNC_QUEUE -> Screen.SyncQueue
                        NavItem.PROFILE -> Screen.Profile
                    }
                }

                when (val screen = currentScreen) {
                    is Screen.Login -> {
                        LoginScreen(
                            authRepository = authRepository,
                            onLoginSuccess = {
                                currentScreen = Screen.Home
                                selectedNavTab = NavItem.HOME
                            },
                            onCreateAccount = { currentScreen = Screen.Register }
                        )
                    }

                    is Screen.Register -> {
                        RegisterScreen(onBackToLogin = { currentScreen = Screen.Login })
                    }

                    is Screen.Camera -> {
                        // System back returns to the form, which is still held in inspectionForm.
                        BackHandler { currentScreen = Screen.NewInspection }
                        val form = inspectionForm
                        CameraCaptureScreen(
                            inspectionLocalId = screen.inspectionLocalId,
                            inspectionRepository = inspectionRepository,
                            onNavigateBack = {
                                currentScreen = Screen.NewInspection
                            },
                            roadLabel = form.selectedRoad?.let { road ->
                                form.selectedSegment?.let { "${road.name} · Seg #${it.segmentNumber}" } ?: road.name
                            },
                            hasGpsFix = form.latitude != null && form.longitude != null,
                            gpsAccuracyMeters = form.accuracyMeters
                        )
                    }

                    is Screen.Detail -> {
                        // Returns to the tab the inspection was opened from (Home or Sync).
                        val back = { goToTab(selectedNavTab) }
                        InspectionDetailScreen(
                            localId = screen.inspectionLocalId,
                            authRepository = authRepository,
                            inspectionRepository = inspectionRepository,
                            inspectionRemote = inspectionRemote,
                            syncRepository = syncRepository,
                            onNavigateBack = back
                        )
                    }

                    else -> {
                        // From any other tab, system back goes to Home; on Home it leaves the app.
                        BackHandler(enabled = selectedNavTab != NavItem.HOME) {
                            if (selectedNavTab == NavItem.NEW_INSPECTION) inspectionForm = NewInspectionFormState()
                            goToTab(NavItem.HOME)
                        }

                        val allInspections by inspectionRepository.getAllInspections().collectAsState(initial = emptyList())
                        val pendingSync = allInspections.count {
                            it.syncStatus == SyncStatus.QUEUED ||
                                it.syncStatus == SyncStatus.UPLOADING ||
                                it.syncStatus == SyncStatus.UPLOAD_FAILED
                        }

                        Scaffold(
                            containerColor = BackgroundDark,
                            bottomBar = {
                                FieldBottomNavBar(
                                    selectedItem = selectedNavTab,
                                    onItemSelected = { tab -> goToTab(tab) },
                                    syncBadgeCount = pendingSync
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
                                            authRepository = authRepository,
                                            inspectionRepository = inspectionRepository,
                                            inspectionRemote = inspectionRemote,
                                            roadRepository = roadRepository,
                                            syncRepository = syncRepository,
                                            onNavigateToNewInspection = { goToTab(NavItem.NEW_INSPECTION) },
                                            onNavigateToDetail = { localId ->
                                                currentScreen = Screen.Detail(localId)
                                            },
                                            onNavigateToSync = { goToTab(NavItem.SYNC_QUEUE) }
                                        )
                                    }

                                    NavItem.NEW_INSPECTION -> {
                                        NewInspectionScreen(
                                            form = inspectionForm,
                                            inspectionRepository = inspectionRepository,
                                            roadRepository = roadRepository,
                                            syncRepository = syncRepository,
                                            onNavigateBack = {
                                                inspectionForm = NewInspectionFormState()
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
                                            inspectionRepository = inspectionRepository,
                                            inspectionRemote = inspectionRemote,
                                            onNavigateBack = { goToTab(NavItem.HOME) },
                                            onOpenInspection = { localId ->
                                                currentScreen = Screen.Detail(localId)
                                            }
                                        )
                                    }

                                    NavItem.PROFILE -> {
                                        ProfileScreen(
                                            authRepository = authRepository,
                                            inspectionRepository = inspectionRepository,
                                            inspectionRemote = inspectionRemote,
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
