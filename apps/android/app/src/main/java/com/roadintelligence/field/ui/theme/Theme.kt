package com.roadintelligence.field.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val DarkColorScheme = darkColorScheme(
    primary = Accent,
    onPrimary = OnAccent,
    primaryContainer = Accent,
    onPrimaryContainer = OnAccent,
    secondary = NeutralSoft,
    onSecondary = OnAccent,
    tertiary = SuccessEmeraldSoft,
    onTertiary = OnSuccess,
    background = BackgroundDark,
    onBackground = TextOnSurface,
    // Material's own containers (dialogs, menus, sheets) must stay opaque to be readable.
    surface = SurfaceSolid,
    onSurface = TextOnSurface,
    surfaceVariant = SurfaceSolidHigh,
    surfaceContainerLowest = BackgroundDark,
    surfaceContainerLow = SurfaceSolid,
    surfaceContainer = SurfaceSolid,
    surfaceContainerHigh = SurfaceSolidHigh,
    surfaceContainerHighest = SurfaceSolidHigh,
    onSurfaceVariant = TextSecondary,
    outline = BorderDark,
    outlineVariant = OutlineVariant,
    error = ErrorRose,
    onError = Color.White,
    errorContainer = ErrorContainer,
    onErrorContainer = Color(0xFFFFDAD6)
)

/** Monospace face for IDs, coordinates, accuracy, sizes and timestamps (stands in for JetBrains Mono). */
val MonoFamily = FontFamily.Monospace

val CodeSm = TextStyle(fontFamily = MonoFamily, fontSize = 11.sp, lineHeight = 14.sp, fontWeight = FontWeight.Medium)
val CodeMd = TextStyle(fontFamily = MonoFamily, fontSize = 13.sp, lineHeight = 18.sp, fontWeight = FontWeight.Medium)
val CodeLg = TextStyle(fontFamily = MonoFamily, fontSize = 15.sp, lineHeight = 22.sp, fontWeight = FontWeight.SemiBold)

// Type scale shared with the web console. The system sans stands in for Inter (no font is bundled,
// to keep the APK small); headings are medium weight with slightly tight tracking, as on the web.
private val FieldTypography = Typography(
    headlineLarge = TextStyle(fontSize = 30.sp, lineHeight = 36.sp, fontWeight = FontWeight.Medium, letterSpacing = (-0.6).sp),
    headlineMedium = TextStyle(fontSize = 24.sp, lineHeight = 30.sp, fontWeight = FontWeight.Medium, letterSpacing = (-0.4).sp),
    headlineSmall = TextStyle(fontSize = 20.sp, lineHeight = 26.sp, fontWeight = FontWeight.Medium, letterSpacing = (-0.3).sp),
    titleLarge = TextStyle(fontSize = 20.sp, lineHeight = 26.sp, fontWeight = FontWeight.Medium, letterSpacing = (-0.3).sp),
    titleMedium = TextStyle(fontSize = 16.sp, lineHeight = 22.sp, fontWeight = FontWeight.Medium),
    titleSmall = TextStyle(fontSize = 14.sp, lineHeight = 20.sp, fontWeight = FontWeight.Medium),
    bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 20.sp),
    bodySmall = TextStyle(fontSize = 12.sp, lineHeight = 16.sp),
    labelLarge = TextStyle(fontSize = 14.sp, lineHeight = 20.sp, fontWeight = FontWeight.Medium),
    labelMedium = TextStyle(fontSize = 12.sp, lineHeight = 16.sp, fontWeight = FontWeight.Medium),
    labelSmall = TextStyle(fontSize = 11.sp, lineHeight = 14.sp, fontWeight = FontWeight.Medium)
)

private val FieldShapes = Shapes(
    extraSmall = RoundedCornerShape(4.dp),
    small = RoundedCornerShape(8.dp),
    medium = RoundedCornerShape(10.dp),
    large = RoundedCornerShape(12.dp),
    extraLarge = RoundedCornerShape(16.dp)
)

@Composable
fun RoadIntelligenceFieldTheme(content: @Composable () -> Unit) {
    // The field app is dark-only, like the operations console.
    MaterialTheme(
        colorScheme = DarkColorScheme,
        typography = FieldTypography,
        shapes = FieldShapes,
        content = content
    )
}
