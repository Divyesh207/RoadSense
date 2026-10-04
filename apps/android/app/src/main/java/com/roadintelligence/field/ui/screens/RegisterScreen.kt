package com.roadintelligence.field.ui.screens

import android.util.Patterns
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Business
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PersonAdd
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.roadintelligence.field.ui.components.FieldCard
import com.roadintelligence.field.ui.components.MessageCard
import com.roadintelligence.field.ui.components.MessageKind
import com.roadintelligence.field.ui.components.PrimaryButton
import com.roadintelligence.field.ui.components.RiSymbol
import com.roadintelligence.field.ui.components.SecondaryButton
import com.roadintelligence.field.ui.components.fieldTextFieldColors
import com.roadintelligence.field.ui.theme.*

private const val MIN_PASSWORD_LENGTH = 8

/** Field-level problems found before anything would be sent. */
data class RegistrationErrors(
    val fullName: String? = null,
    val email: String? = null,
    val organization: String? = null,
    val password: String? = null,
    val confirmPassword: String? = null
) {
    val hasAny: Boolean
        get() = listOf(fullName, email, organization, password, confirmPassword).any { it != null }
}

fun validateRegistration(
    fullName: String,
    email: String,
    organization: String,
    password: String,
    confirmPassword: String
): RegistrationErrors = RegistrationErrors(
    fullName = if (fullName.trim().length < 2) "Enter your full name." else null,
    email = when {
        email.isBlank() -> "Enter your email address."
        !Patterns.EMAIL_ADDRESS.matcher(email.trim()).matches() -> "Enter a valid email address."
        else -> null
    },
    organization = if (organization.trim().length < 2) "Enter your organization." else null,
    password = when {
        password.length < MIN_PASSWORD_LENGTH -> "Use at least $MIN_PASSWORD_LENGTH characters."
        password.none { it.isLetter() } || password.none { it.isDigit() } -> "Include a letter and a number."
        else -> null
    },
    confirmPassword = when {
        confirmPassword.isEmpty() -> "Re-enter the password."
        confirmPassword != password -> "Passwords do not match."
        else -> null
    }
)

/**
 * Account request form. The platform API exposes only login, refresh, profile and logout
 * (services/api/app/api/v1/endpoints/auth.py): there is no registration endpoint, so this
 * screen validates the entry and then says plainly that no account was created. Nothing is
 * stored on the device and no local account is made.
 */
@Composable
fun RegisterScreen(onBackToLogin: () -> Unit) {
    var fullName by rememberSaveable { mutableStateOf("") }
    var email by rememberSaveable { mutableStateOf("") }
    var organization by rememberSaveable { mutableStateOf("") }
    // Passwords are kept out of saved instance state.
    var password by remember { mutableStateOf("") }
    var confirmPassword by remember { mutableStateOf("") }
    var passwordVisible by rememberSaveable { mutableStateOf(false) }
    var confirmVisible by rememberSaveable { mutableStateOf(false) }
    var errors by remember { mutableStateOf(RegistrationErrors()) }
    var checked by rememberSaveable { mutableStateOf(false) }

    BackHandler { onBackToLogin() }

    fun submit() {
        errors = validateRegistration(fullName, email, organization, password, confirmPassword)
        checked = !errors.hasAny
        if (checked) {
            // No endpoint to call: drop the passwords rather than hold them.
            password = ""
            confirmPassword = ""
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
            .verticalScroll(rememberScrollState())
            .imePadding()
            .padding(horizontal = 20.dp, vertical = 16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBackToLogin) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back to sign in", tint = TextPrimary)
            }
            Spacer(modifier = Modifier.width(4.dp))
            RiSymbol(size = 32.dp)
            Spacer(modifier = Modifier.width(10.dp))
            Column {
                Text("Create Account", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                Text("Field Inspection", color = PrimaryCyanBright, style = CodeSm)
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        MessageCard(
            kind = MessageKind.INFO,
            title = "Self-registration is not available yet",
            message = "This server does not accept sign-ups from the app. Accounts are created by your " +
                "road authority administrator. You can check your details here, but no account will be created.",
            modifier = Modifier.widthIn(max = 460.dp)
        )

        Spacer(modifier = Modifier.height(14.dp))

        FieldCard(modifier = Modifier.widthIn(max = 460.dp), contentPadding = PaddingValues(18.dp)) {
            if (checked) {
                MessageCard(
                    kind = MessageKind.WARNING,
                    title = "No account was created",
                    message = "Your details are valid, but the server has no registration service, so nothing " +
                        "was sent or saved. Ask your administrator to create an account for ${email.trim()}.",
                    actionLabel = "Back to sign in",
                    onAction = onBackToLogin
                )
                Spacer(modifier = Modifier.height(14.dp))
            }

            RegisterField(
                value = fullName,
                onValueChange = { fullName = it; errors = errors.copy(fullName = null); checked = false },
                label = "Full Name",
                icon = Icons.Default.Person,
                error = errors.fullName,
                keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Words, imeAction = ImeAction.Next)
            )
            Spacer(modifier = Modifier.height(12.dp))
            RegisterField(
                value = email,
                onValueChange = { email = it; errors = errors.copy(email = null); checked = false },
                label = "Email Address",
                icon = Icons.Default.Email,
                error = errors.email,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email, imeAction = ImeAction.Next)
            )
            Spacer(modifier = Modifier.height(12.dp))
            RegisterField(
                value = organization,
                onValueChange = { organization = it; errors = errors.copy(organization = null); checked = false },
                label = "Organization",
                icon = Icons.Default.Business,
                error = errors.organization,
                keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Words, imeAction = ImeAction.Next)
            )
            Spacer(modifier = Modifier.height(12.dp))
            RegisterField(
                value = password,
                onValueChange = { password = it; errors = errors.copy(password = null); checked = false },
                label = "Password",
                icon = Icons.Default.Lock,
                error = errors.password,
                supporting = "At least $MIN_PASSWORD_LENGTH characters, with a letter and a number.",
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = ImeAction.Next),
                passwordVisible = passwordVisible,
                onTogglePassword = { passwordVisible = !passwordVisible }
            )
            Spacer(modifier = Modifier.height(12.dp))
            RegisterField(
                value = confirmPassword,
                onValueChange = { confirmPassword = it; errors = errors.copy(confirmPassword = null); checked = false },
                label = "Confirm Password",
                icon = Icons.Default.Lock,
                error = errors.confirmPassword,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = ImeAction.Done),
                keyboardActions = KeyboardActions(onDone = { submit() }),
                passwordVisible = confirmVisible,
                onTogglePassword = { confirmVisible = !confirmVisible }
            )

            Spacer(modifier = Modifier.height(20.dp))

            PrimaryButton(
                text = "Check Details",
                icon = Icons.Default.PersonAdd,
                onClick = { submit() },
                height = 56.dp,
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(10.dp))
            SecondaryButton(
                text = "Back to Sign In",
                onClick = onBackToLogin,
                modifier = Modifier.fillMaxWidth()
            )
        }

        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "Nothing entered here is stored on this device.",
            color = TextMuted,
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.Center
        )
    }
}

@Composable
private fun RegisterField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    icon: ImageVector,
    error: String?,
    keyboardOptions: KeyboardOptions,
    keyboardActions: KeyboardActions = KeyboardActions.Default,
    supporting: String? = null,
    passwordVisible: Boolean? = null,
    onTogglePassword: (() -> Unit)? = null
) {
    val isPassword = passwordVisible != null && onTogglePassword != null
    val helper = error ?: supporting
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        leadingIcon = { Icon(icon, contentDescription = null) },
        trailingIcon = if (isPassword) {
            {
                IconButton(onClick = onTogglePassword!!) {
                    Icon(
                        imageVector = if (passwordVisible == true) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                        contentDescription = if (passwordVisible == true) "Hide password" else "Show password"
                    )
                }
            }
        } else null,
        isError = error != null,
        supportingText = if (helper != null) {
            { Text(helper, color = if (error != null) ErrorSoft else TextMuted) }
        } else null,
        singleLine = true,
        visualTransformation = if (isPassword && passwordVisible != true) PasswordVisualTransformation() else VisualTransformation.None,
        keyboardOptions = keyboardOptions,
        keyboardActions = keyboardActions,
        colors = fieldTextFieldColors(),
        shape = MaterialTheme.shapes.medium,
        modifier = Modifier.fillMaxWidth()
    )
}
