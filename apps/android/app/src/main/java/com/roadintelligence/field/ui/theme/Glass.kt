package com.roadintelligence.field.ui.theme

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/** Corner radius of glass panels. */
val GlassRadius = 18.dp
val GlassShape = RoundedCornerShape(GlassRadius)

/** Fill of a glass panel: slightly brighter at the top, like light catching the surface. */
val GlassFill: Brush
    get() = Brush.verticalGradient(listOf(SurfaceContainer, SurfaceDark))

/** Edge of a glass panel: a bright top highlight fading into the regular border. */
val GlassEdge: Brush
    get() = Brush.verticalGradient(listOf(GlassHighlight, BorderDark, BorderDark))

/**
 * Ambient page background: deep navy with three soft, static colour pools (cyan, blue, emerald).
 * It is drawn once per frame as plain gradients; nothing animates and nothing is blurred, so it
 * costs almost nothing on a phone. Glass panels are translucent and let it show through.
 */
fun Modifier.glassBackground(): Modifier = this.drawBehind {
    drawRect(BackgroundDark)
    drawRect(
        Brush.radialGradient(
            listOf(PrimaryCyan.copy(alpha = 0.20f), Color.Transparent),
            center = Offset(size.width * 0.08f, -size.height * 0.04f),
            radius = size.maxDimension * 0.62f
        )
    )
    drawRect(
        Brush.radialGradient(
            listOf(SecondaryBlue.copy(alpha = 0.17f), Color.Transparent),
            center = Offset(size.width * 1.02f, size.height * 0.10f),
            radius = size.maxDimension * 0.50f
        )
    )
    drawRect(
        Brush.radialGradient(
            listOf(SuccessEmerald.copy(alpha = 0.08f), Color.Transparent),
            center = Offset(size.width * 0.70f, size.height * 1.05f),
            radius = size.maxDimension * 0.55f
        )
    )
}

/** Glass panel look for any composable: translucent fill, highlighted edge, rounded corners. */
fun Modifier.glassPanel(shape: Shape = GlassShape, radius: Dp = GlassRadius): Modifier = this
    .clip(shape)
    .background(GlassFill, shape)
    .border(BorderStroke(1.dp, GlassEdge), shape)
