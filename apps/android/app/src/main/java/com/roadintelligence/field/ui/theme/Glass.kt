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

/** Corner radius of panels (matches --ri-radius on the web). */
val GlassRadius = 12.dp
val GlassShape = RoundedCornerShape(GlassRadius)

/** Fill of a panel: a faint white tint, slightly brighter at the top. */
val GlassFill: Brush
    get() = Brush.verticalGradient(listOf(SurfaceContainer, SurfaceDark))

/** Edge of a panel: a bright top highlight fading into the regular hairline (the liquid-glass edge). */
val GlassEdge: Brush
    get() = Brush.verticalGradient(listOf(GlassHighlight, BorderDark, BorderDark))

/**
 * Page background: near-black with one faint, static neutral highlight at the top. It is drawn
 * as plain gradients; nothing animates and nothing is blurred, so it costs almost nothing on a
 * phone.
 */
fun Modifier.glassBackground(): Modifier = this.drawBehind {
    drawRect(BackgroundDark)
    drawRect(
        Brush.radialGradient(
            listOf(Color.White.copy(alpha = 0.06f), Color.Transparent),
            center = Offset(size.width * 0.5f, -size.height * 0.08f),
            radius = size.maxDimension * 0.55f
        )
    )
}

/** Panel look for any composable: translucent fill, highlighted edge, rounded corners. */
fun Modifier.glassPanel(shape: Shape = GlassShape, radius: Dp = GlassRadius): Modifier = this
    .clip(shape)
    .background(GlassFill, shape)
    .border(BorderStroke(1.dp, GlassEdge), shape)
