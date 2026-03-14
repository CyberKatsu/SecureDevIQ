"""Sticky top navigation bar. Shown on all authenticated pages."""
import reflex as rx

from securedeviq.state import AppState


def navbar() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.icon("shield-check", size=24, color="#6366f1"),
                rx.text(
                    "SecureDevIQ",
                    font_size="1.25rem",
                    font_weight="700",
                    color="#6366f1",
                ),
                spacing="2",
            ),
            rx.spacer(),
            rx.hstack(
                rx.link(
                    rx.button("Challenge", variant="ghost", color_scheme="indigo"),
                    href="/challenge",
                ),
                rx.link(
                    rx.button("Dashboard", variant="ghost", color_scheme="indigo"),
                    href="/dashboard",
                ),
                rx.button(
                    "Logout",
                    variant="ghost",
                    color_scheme="gray",
                    on_click=AppState.logout,
                ),
                spacing="2",
            ),
        ),
        position="sticky",
        top="0",
        z_index="100",
        bg="white",
        border_bottom="1px solid #e5e7eb",
        padding_x="2rem",
        padding_y="0.75rem",
        width="100%",
    )
