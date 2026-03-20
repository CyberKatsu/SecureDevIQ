"""
pages/results.py  —  Submission results view (route: /results)

Displays the AI evaluation after a user submits their vulnerability analysis:
  • Score ring (colour-coded: green ≥8, orange ≥5, red <5)
  • Correct findings (what they got right)
  • Missed findings (what they overlooked)
  • Full plain-English explanation from Claude
  • Actionable fix suggestion
  • Buttons: Try Again (same challenge) | New Challenge
"""
import reflex as rx
from securedeviq.components.navbar import navbar
from securedeviq.state import AppState


def results_page() -> rx.Component:
    return rx.cond(
        AppState.is_authenticated,
        rx.box(
            navbar(),
            rx.box(
                rx.cond(
                    AppState.has_result,
                    _results_content(),
                    # Guard: redirect if arriving without a result
                    rx.center(
                        rx.vstack(
                            rx.text("No result to display.", color="#6b7280"),
                            rx.link(
                                rx.button("Go to Challenge", color_scheme="indigo"),
                                href="/challenge",
                            ),
                            spacing="4",
                            align="center",
                        ),
                        padding_y="6rem",
                    ),
                ),
                max_width="48rem",
                margin="0 auto",
                padding="2rem",
            ),
        ),
    )


def _results_content() -> rx.Component:
    return rx.vstack(
        # ── Score header ───────────────────────────────────────────────────
        rx.card(
            rx.hstack(
                # Score ring
                rx.center(
                    rx.vstack(
                        rx.heading(
                            AppState.submission_result.get("score", "0"),
                            size="8",
                            color=AppState.score_colour,
                            font_weight="800",
                        ),
                        rx.text("/ 10", color="#9ca3af", font_size="1rem"),
                        spacing="0",
                        align="center",
                    ),
                    width="6rem",
                    height="6rem",
                    border_radius="50%",
                    border=AppState.score_border_color,
                ),
                rx.vstack(
                    rx.heading("Analysis Complete", size="5"),
                    rx.text(
                        AppState.score_feedback_message,
                        color="#6b7280",
                        font_size="0.9rem",
                    ),
                    spacing="1",
                    align="start",
                ),
                spacing="6",
                align="center",
                width="100%",
            ),
            width="100%",
            padding="1.5rem",
        ),

        # ── Correct findings ───────────────────────────────────────────────
        rx.cond(
            AppState.correct_findings_list.length() > 0,
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.icon("check_check", size=18, color="#22c55e"),
                        rx.text("What you got right", font_weight="600", color="#166534"),
                        spacing="2",
                    ),
                    rx.vstack(
                        rx.foreach(
                            AppState.correct_findings_list,
                            lambda finding: rx.hstack(
                                rx.icon("check", size=14, color="#22c55e"),
                                rx.text(finding, font_size="0.9rem"),
                                spacing="2",
                                align="start",
                            ),
                        ),
                        spacing="2",
                        width="100%",
                        align="start",
                    ),
                    spacing="3",
                    width="100%",
                    align="start",
                ),
                bg="#f0fdf4",
                border="1px solid #bbf7d0",
                width="100%",
                padding="1.25rem",
            ),
        ),

        # ── Missed findings ────────────────────────────────────────────────
        rx.cond(
            AppState.missed_findings_list.length() > 0,
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.icon("message_circle_warning", size=18, color="#f97316"),
                        rx.text("What you missed", font_weight="600", color="#9a3412"),
                        spacing="2",
                    ),
                    rx.vstack(
                        rx.foreach(
                            AppState.missed_findings_list,
                            lambda finding: rx.hstack(
                                rx.icon("x", size=14, color="#f97316"),
                                rx.text(finding, font_size="0.9rem"),
                                spacing="2",
                                align="start",
                            ),
                        ),
                        spacing="2",
                        width="100%",
                        align="start",
                    ),
                    spacing="3",
                    width="100%",
                    align="start",
                ),
                bg="#fff7ed",
                border="1px solid #fed7aa",
                width="100%",
                padding="1.25rem",
            ),
        ),

        # ── Full explanation ───────────────────────────────────────────────
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("message-square", size=18, color="#6366f1"),
                    rx.text("Full Explanation", font_weight="600"),
                    spacing="2",
                ),
                rx.text(
                    AppState.submission_result.get("explanation", ""),
                    font_size="0.9rem",
                    color="#374151",
                    line_height="1.6",
                ),
                spacing="3",
                width="100%",
                align="start",
            ),
            width="100%",
            padding="1.25rem",
        ),

        # ── Fix suggestion ─────────────────────────────────────────────────
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("wrench", size=18, color="#0ea5e9"),
                    rx.text("How to Fix It", font_weight="600", color="#0c4a6e"),
                    spacing="2",
                ),
                rx.text(
                    AppState.submission_result.get("fix_suggestion", ""),
                    font_size="0.9rem",
                    color="#0c4a6e",
                    line_height="1.6",
                    font_family="monospace",
                    white_space="pre-wrap",
                ),
                spacing="3",
                width="100%",
                align="start",
            ),
            bg="#f0f9ff",
            border="1px solid #bae6fd",
            width="100%",
            padding="1.25rem",
        ),

        # ── Action buttons ─────────────────────────────────────────────────
        rx.hstack(
            rx.link(
                rx.button(
                    rx.icon("refresh-cw", size=16),
                    " Try Again",
                    variant="outline",
                    color_scheme="gray",
                ),
                href="/challenge",
            ),
            rx.button(
                rx.icon("arrow-right", size=16),
                " New Challenge",
                on_click=AppState.load_challenge,
                color_scheme="indigo",
            ),
            rx.link(
                rx.button(
                    rx.icon("bar-chart-2", size=16),
                    " View Dashboard",
                    variant="outline",
                    color_scheme="indigo",
                ),
                href="/dashboard",
            ),
            spacing="3",
            justify="center",
            width="100%",
        ),

        spacing="4",
        width="100%",
        align="start",
    )
