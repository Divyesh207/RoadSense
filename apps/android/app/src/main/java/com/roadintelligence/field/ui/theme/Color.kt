package com.roadintelligence.field.ui.theme

import androidx.compose.ui.graphics.Color

// Road Intelligence design tokens, shared with the web console (apps/web/app/globals.css):
// black surfaces, white text, grey secondary text, thin translucent white edges. Primary actions
// and selection are white; colour is reserved for status.

// Backgrounds
val BackgroundDark = Color(0xFF050506)        // page background
val SurfaceSolid = Color(0xFF0F0F10)          // opaque surface: dialogs, menus, sheets, bars
val SurfaceSolidHigh = Color(0xFF18181B)      // opaque raised surface
val SurfaceLowest = Color(0x80000000)         // recessed wells inside a surface

// Surfaces (neutral white tint)
val SurfaceDark = Color(0x0AFFFFFF)           // card / bar (4 %)
val SurfaceContainer = Color(0x0FFFFFFF)      // stronger surface (6 %)
val SurfaceCard = Color(0x14FFFFFF)           // insets, chips, disabled controls (8 %)
val SurfaceHighest = Color(0x24FFFFFF)        // pressed / highlighted (14 %)
val BorderDark = Color(0x1AFFFFFF)            // edge (10 %)
val OutlineVariant = Color(0x33FFFFFF)        // stronger edge (20 %)
val GlassHighlight = Color(0x38FFFFFF)        // top edge highlight of a glass panel
val GlassBar = Color(0xF20A0A0B)              // bars over scrolling content (95 %)

// Primary action and selection
val Accent = Color(0xFFFFFFFF)
val AccentBright = Color(0xFFF3F4F6)
val AccentDim = Color(0xFFD4D4D8)
val OnAccent = Color(0xFF000000)
val NeutralSoft = Color(0xFFD4D4D8)           // quiet emphasis: secondary values and links

// Functional / status
val SuccessEmerald = Color(0xFF10B981)
val SuccessEmeraldSoft = Color(0xFF4EDEA3)
val OnSuccess = Color(0xFF003824)
val WarningAmber = Color(0xFFF59E0B)
val WarningOrange = Color(0xFFFB923C)
val ErrorRose = Color(0xFFEF4444)
val ErrorSoft = Color(0xFFFFBEB6)
val ErrorContainer = Color(0xFF93000A)
val InfoSky = Color(0xFF38BDF8)               // in progress: uploading, AI analysis running

// Text
val TextPrimary = Color(0xFFFFFFFF)
val TextOnSurface = Color(0xFFE5E5E8)
val TextSecondary = Color(0xFFA1A1AA)
val TextMuted = Color(0xFF71717A)
