"""
pages/index.py  —  Login / Register landing page (route: /)
"""
import reflex as rx
from securedeviq.state import AppState


def auth_page() -> rx.Component:
    return rx.box(
        rx.center(
            rx.vstack(
                # ── Brand header ───────────────────────────────────────────
                rx.vstack(
                    rx.hstack(
                        rx.icon("shield-check", size=40, color="#6366f1"),
                        rx.text(
                            "SecureDevIQ",
                            font_size="2rem",
                            font_weight="800",
                            color="#1e1b4b",
                        ),
                        spacing="3",
                        align="center",
                    ),
                    rx.text(
                        "Train your eye for security vulnerabilities in AI-generated code.",
                        color="#6b7280",
                        text_align="center",
                        max_width="26rem",
                    ),
                    align="center",
                    spacing="2",
                ),

                # ── Auth card ──────────────────────────────────────────────
                rx.card(
                    rx.tabs.root(
                        rx.tabs.list(
                            rx.tabs.trigger("Login", value="login"),
                            rx.tabs.trigger("Register", value="register"),
                            width="100%",
                        ),

                        # Login tab
                        rx.tabs.content(
                            rx.vstack(
                                rx.input(
                                    placeholder="Username",
                                    value=AppState.username,
                                    on_change=AppState.set_username,
                                    width="100%",
                                ),
                                rx.input(
                                    placeholder="Password",
                                    type="password",
                                    value=AppState.password,
                                    on_change=AppState.set_password,
                                    width="100%",
                                ),
                                rx.cond(
                                    AppState.auth_error != "",
                                    rx.callout(
                                        AppState.auth_error,
                                        color_scheme="red",
                                        variant="soft",
                                    ),
                                ),
                                rx.button(
                                    "Login",
                                    on_click=AppState.login,
                                    width="100%",
                                    color_scheme="indigo",
                                ),
                                spacing="3",
                                padding_top="1rem",
                            ),
                            value="login",
                        ),

                        # Register tab
                        rx.tabs.content(
                            rx.vstack(
                                rx.input(
                                    placeholder="Username",
                                    value=AppState.username,
                                    on_change=AppState.set_username,
                                    width="100%",
                                ),
                                rx.input(
                                    placeholder="Email",
                                    type="email",
                                    value=AppState.email,
                                    on_change=AppState.set_email,
                                    width="100%",
                                ),
                                rx.input(
                                    placeholder="Password (min 8 chars)",
                                    type="password",
                                    value=AppState.password,
                                    on_change=AppState.set_password,
                                    width="100%",
                                ),
                                rx.cond(
                                    AppState.auth_error != "",
                                    rx.callout(
                                        AppState.auth_error,
                                        color_scheme="red",
                                        variant="soft",
                                    ),
                                ),
                                rx.button(
                                    "Create Account",
                                    on_click=AppState.register,
                                    width="100%",
                                    color_scheme="indigo",
                                ),
                                spacing="3",
                                padding_top="1rem",
                            ),
                            value="register",
                        ),

                        default_value="login",
                    ),
                    width="22rem",
                    padding="1.5rem",
                ),

                # ── Feature bullets ────────────────────────────────────────
                rx.hstack(
                    _feature_badge("code", "Python · SQL · Bash"),
                    _feature_badge("zap", "AI-powered feedback"),
                    _feature_badge("trending-up", "Track your progress"),
                    spacing="4",
                    flex_wrap="wrap",
                    justify="center",
                ),

                spacing="8",
                align="center",
                padding_y="4rem",
            ),
        ),
        min_height="100vh",
        bg="linear-gradient(135deg, #f0f0ff 0%, #fff 60%)",
    )


def _feature_badge(icon: str, label: str) -> rx.Component:
    return rx.hstack(
        rx.icon(icon, size=16, color="#6366f1"),
        rx.text(label, font_size="0.85rem", color="#374151"),
        bg="white",
        border="1px solid #e5e7eb",
        border_radius="full",
        padding_x="0.75rem",
        padding_y="0.35rem",
        spacing="2",
    )
