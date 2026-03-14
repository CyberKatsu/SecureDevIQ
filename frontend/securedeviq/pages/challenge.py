"""
pages/challenge.py  —  Challenge view (route: /challenge)

Layout:
  ┌─────────────────────────────────────────────┐
  │  Navbar                                     │
  ├──────────────┬──────────────────────────────┤
  │  Settings    │  Code snippet (read-only)    │
  │  panel       │                              │
  │  (language,  │  Answer textarea             │
  │   difficulty,│                              │
  │   category)  │  [Generate]    [Submit]      │
  └──────────────┴──────────────────────────────┘
"""
import reflex as rx
from securedeviq.components.navbar import navbar
from securedeviq.state import AppState

LANGUAGES = ["python", "sql", "bash"]
DIFFICULTIES = ["junior", "mid", "senior"]
CATEGORIES = [
    ("", "AI picks"),
    ("prompt_injection", "Prompt Injection"),
    ("memory_issues", "Memory Issues"),
    ("insecure_defaults", "Insecure Defaults"),
    ("missing_sanitisation", "Missing Sanitisation"),
    ("hardcoded_secrets", "Hardcoded Secrets"),
]


def challenge_page() -> rx.Component:
    return rx.box(
        navbar(),
        rx.box(
            rx.hstack(
                # ── Left panel: settings ───────────────────────────────────
                _settings_panel(),
                # ── Right panel: code + answer ─────────────────────────────
                _code_panel(),
                spacing="6",
                align="start",
                width="100%",
            ),
            max_width="72rem",
            margin="0 auto",
            padding="2rem",
        ),
        on_mount=rx.cond(
            ~AppState.is_authenticated,
            rx.redirect("/"),
        ),
    )


def _settings_panel() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("Challenge Settings", font_weight="600", font_size="1rem"),

            rx.vstack(
                rx.text("Language", font_size="0.85rem", color="#6b7280"),
                rx.select(
                    LANGUAGES,
                    value=AppState.selected_language,
                    on_change=AppState.set_language,
                    width="100%",
                ),
                spacing="1",
                width="100%",
            ),

            rx.vstack(
                rx.text("Difficulty", font_size="0.85rem", color="#6b7280"),
                rx.select(
                    DIFFICULTIES,
                    value=AppState.selected_difficulty,
                    on_change=AppState.set_difficulty,
                    width="100%",
                ),
                spacing="1",
                width="100%",
            ),

            rx.vstack(
                rx.text("Vulnerability Category", font_size="0.85rem", color="#6b7280"),
                rx.select(
                    [label for _, label in CATEGORIES],
                    value=rx.cond(
                        AppState.selected_category == "",
                        "AI picks",
                        AppState.selected_category,
                    ),
                    on_change=lambda v: AppState.set_category(
                        next((k for k, label in CATEGORIES if label == v), "")
                    ),
                    width="100%",
                ),
                spacing="1",
                width="100%",
            ),

            rx.button(
                rx.cond(
                    AppState.is_loading_challenge,
                    rx.spinner(size="2"),
                    rx.icon("refresh-cw", size=16),
                ),
                rx.cond(
                    AppState.is_loading_challenge,
                    " Generating...",
                    " Generate Challenge",
                ),
                on_click=AppState.load_challenge,
                disabled=AppState.is_loading_challenge,
                width="100%",
                color_scheme="indigo",
                variant="solid",
            ),

            rx.cond(
                AppState.challenge_error != "",
                rx.callout(
                    AppState.challenge_error,
                    color_scheme="red",
                    variant="soft",
                ),
            ),

            # ── Difficulty legend ──────────────────────────────────────────
            rx.divider(),
            rx.vstack(
                rx.text("Difficulty guide", font_size="0.8rem", font_weight="600", color="#374151"),
                _difficulty_badge("junior", "green", "One obvious flaw, commonly missed"),
                _difficulty_badge("mid", "orange", "Subtle or context-dependent vuln"),
                _difficulty_badge("senior", "red", "Multi-step exploit chain"),
                spacing="2",
                width="100%",
            ),

            spacing="4",
            width="16rem",
            align="start",
        ),
        padding="1.25rem",
        width="16rem",
        flex_shrink="0",
    )


def _difficulty_badge(level: str, colour: str, description: str) -> rx.Component:
    return rx.hstack(
        rx.badge(level, color_scheme=colour, variant="soft"),
        rx.text(description, font_size="0.75rem", color="#6b7280"),
        spacing="2",
        align="center",
    )


def _code_panel() -> rx.Component:
    return rx.vstack(
        # ── Challenge metadata ─────────────────────────────────────────────
        rx.cond(
            AppState.has_challenge,
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.badge(
                            AppState.current_challenge.get("difficulty", ""),
                            color_scheme="indigo",
                            variant="soft",
                        ),
                        rx.badge(
                            AppState.current_challenge.get("language", ""),
                            color_scheme="gray",
                            variant="outline",
                        ),
                        rx.badge(
                            AppState.current_challenge.get("vuln_category", "").replace("_", " "),
                            color_scheme="orange",
                            variant="soft",
                        ),
                        spacing="2",
                    ),
                    rx.heading(
                        AppState.current_challenge.get("title", ""),
                        size="4",
                    ),
                    rx.text(
                        AppState.current_challenge.get("description", ""),
                        color="#6b7280",
                        font_size="0.9rem",
                    ),
                    spacing="2",
                ),
                width="100%",
                padding="1.25rem",
            ),
        ),

        # ── Code snippet ───────────────────────────────────────────────────
        rx.cond(
            AppState.has_challenge,
            rx.vstack(
                rx.text("Code to review", font_size="0.85rem", font_weight="600", color="#374151"),
                rx.box(
                    rx.code_block(
                        AppState.current_challenge.get("code_snippet", ""),
                        language=AppState.selected_language,
                        show_line_numbers=True,
                        width="100%",
                    ),
                    border="1px solid #e5e7eb",
                    border_radius="0.5rem",
                    overflow="auto",
                    width="100%",
                ),
                spacing="2",
                width="100%",
                align="start",
            ),
            # Placeholder when no challenge loaded
            rx.center(
                rx.vstack(
                    rx.icon("shield", size=48, color="#d1d5db"),
                    rx.text(
                        "Configure your challenge and click Generate",
                        color="#9ca3af",
                        text_align="center",
                    ),
                    spacing="3",
                    align="center",
                ),
                height="16rem",
                border="2px dashed #e5e7eb",
                border_radius="0.5rem",
                width="100%",
            ),
        ),

        # ── Answer input ───────────────────────────────────────────────────
        rx.cond(
            AppState.has_challenge,
            rx.vstack(
                rx.text(
                    "Your analysis",
                    font_size="0.85rem",
                    font_weight="600",
                    color="#374151",
                ),
                rx.text(
                    "Describe: what the vulnerability is, where exactly it appears in the code, "
                    "why it is dangerous, and how an attacker could exploit it.",
                    font_size="0.8rem",
                    color="#9ca3af",
                ),
                rx.text_area(
                    placeholder="e.g. On line 10, the username parameter is interpolated directly into the SQL query using an f-string. This allows SQL injection because...",
                    value=AppState.user_answer,
                    on_change=AppState.set_answer,
                    rows=7,
                    width="100%",
                ),
                rx.cond(
                    AppState.submission_error != "",
                    rx.callout(AppState.submission_error, color_scheme="red", variant="soft"),
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        rx.cond(
                            AppState.is_submitting,
                            rx.spinner(size="2"),
                            rx.icon("send", size=16),
                        ),
                        rx.cond(
                            AppState.is_submitting,
                            " Evaluating...",
                            " Submit for Evaluation",
                        ),
                        on_click=AppState.submit_answer,
                        disabled=AppState.is_submitting,
                        color_scheme="green",
                        variant="solid",
                    ),
                    width="100%",
                ),
                spacing="2",
                width="100%",
                align="start",
            ),
        ),

        spacing="4",
        width="100%",
        align="start",
    )
