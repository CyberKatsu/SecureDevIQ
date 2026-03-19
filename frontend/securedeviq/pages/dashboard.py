"""
pages/dashboard.py  —  Progress dashboard (route: /dashboard)

Displays aggregated statistics for the current user:
  • Hero stats: total attempts, average score, completion rate
  • Category performance breakdown (per vulnerability type)
  • Difficulty breakdown (Junior / Mid / Senior)
  • Recent submissions table
"""
import reflex as rx
from securedeviq.components.navbar import navbar
from securedeviq.state import AppState

# Colour map for vuln categories
CATEGORY_COLOURS = {
    "prompt_injection": "violet",
    "memory_issues": "red",
    "insecure_defaults": "orange",
    "missing_sanitisation": "yellow",
    "hardcoded_secrets": "pink",
}

DIFFICULTY_COLOURS = {
    "junior": "green",
    "mid": "orange",
    "senior": "red",
}


def dashboard_page() -> rx.Component:
    return rx.cond(
        AppState.is_authenticated,
        rx.box(
            navbar(),
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.heading("Your Progress", size="6"),
                        rx.spacer(),
                        rx.button(
                            rx.icon("refresh-cw", size=16),
                            " Refresh",
                            on_click=AppState.load_dashboard,
                            variant="outline",
                            color_scheme="gray",
                            size="2",
                        ),
                        width="100%",
                        align="center",
                    ),

                    rx.cond(
                        AppState.is_loading_dashboard,
                        rx.center(rx.spinner(size="3"), padding_y="4rem"),
                        _dashboard_content(),
                    ),

                    spacing="6",
                    width="100%",
                ),
                max_width="72rem",
                margin="0 auto",
                padding="2rem",
            ),
            on_mount=AppState.load_dashboard,
        ),
    )


def _dashboard_content() -> rx.Component:
    return rx.vstack(
        # ── Hero stats row ─────────────────────────────────────────────────
        rx.grid(
            _stat_card(
                "target",
                "Total Attempts",
                AppState.dashboard_data.get("total_attempts", 0),
                "#6366f1",
            ),
            _stat_card(
                "star",
                "Avg Score",
                AppState.dashboard_data.get("overall_average_score", 0.0),
                "#f59e0b",
                suffix=" / 10",
            ),
            _stat_card(
                "check-circle",
                "Challenges Done",
                AppState.dashboard_data.get("challenges_completed", 0),
                "#22c55e",
            ),
            _stat_card(
                "library",
                "Available",
                AppState.dashboard_data.get("total_challenges_available", 0),
                "#0ea5e9",
            ),
            columns="4",
            spacing="4",
            width="100%",
        ),

        # ── Category breakdown ─────────────────────────────────────────────
        rx.card(
            rx.vstack(
                rx.text("Performance by Vulnerability Category", font_weight="600", font_size="1rem"),
                rx.cond(
                    AppState.dashboard_data.get("category_breakdown", []) == [],
                    rx.text("No data yet — complete some challenges!", color="#9ca3af", font_size="0.9rem"),
                    rx.vstack(
                        rx.foreach(
                            AppState.dashboard_data.get("category_breakdown", []),
                            _category_row,
                        ),
                        spacing="3",
                        width="100%",
                    ),
                ),
                spacing="4",
                width="100%",
                align="start",
            ),
            width="100%",
            padding="1.25rem",
        ),

        # ── Difficulty breakdown ───────────────────────────────────────────
        rx.card(
            rx.vstack(
                rx.text("Performance by Difficulty", font_weight="600", font_size="1rem"),
                rx.cond(
                    AppState.dashboard_data.get("difficulty_breakdown", []) == [],
                    rx.text("No data yet — complete some challenges!", color="#9ca3af", font_size="0.9rem"),
                    rx.grid(
                        rx.foreach(
                            AppState.dashboard_data.get("difficulty_breakdown", []),
                            _difficulty_card,
                        ),
                        columns="3",
                        spacing="4",
                        width="100%",
                    ),
                ),
                spacing="4",
                width="100%",
                align="start",
            ),
            width="100%",
            padding="1.25rem",
        ),

        # ── Recent submissions table ───────────────────────────────────────
        rx.card(
            rx.vstack(
                rx.text("Recent Submissions", font_weight="600", font_size="1rem"),
                rx.cond(
                    AppState.dashboard_data.get("recent_submissions", []) == [],
                    rx.text("No submissions yet.", color="#9ca3af", font_size="0.9rem"),
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Date"),
                                rx.table.column_header_cell("Score"),
                                rx.table.column_header_cell("Attempt"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AppState.dashboard_data.get("recent_submissions", []),
                                _submission_row,
                            ),
                        ),
                        width="100%",
                    ),
                ),
                spacing="4",
                width="100%",
                align="start",
            ),
            width="100%",
            padding="1.25rem",
        ),

        # ── CTA ───────────────────────────────────────────────────────────
        rx.center(
            rx.link(
                rx.button(
                    rx.icon("play", size=16),
                    " Start a New Challenge",
                    color_scheme="indigo",
                    size="3",
                ),
                href="/challenge",
            ),
            width="100%",
        ),

        spacing="4",
        width="100%",
    )


def _stat_card(icon: str, label: str, value, colour: str, suffix: str = "") -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.icon(icon, size=24, color=colour),
            rx.text(str(value) + suffix, font_size="2rem", font_weight="700", color=colour),
            rx.text(label, font_size="0.8rem", color="#6b7280"),
            spacing="1",
            align="center",
        ),
        padding="1.25rem",
        text_align="center",
    )


def _category_row(item: dict) -> rx.Component:
    cat = item.get("category", "")
    avg = item.get("average_score", 0.0)
    attempts = item.get("attempts", 0)
    return rx.hstack(
        rx.badge(
            cat.replace("_", " "),
            color_scheme=CATEGORY_COLOURS.get(cat, "gray"),
            variant="soft",
            min_width="12rem",
        ),
        rx.progress(
            value=avg * 10,  # 0–100
            max=100,
            color_scheme=CATEGORY_COLOURS.get(cat, "gray"),
            flex="1",
        ),
        rx.text(f"{avg}/10", font_size="0.85rem", font_weight="600", min_width="3rem"),
        rx.text(f"({attempts} attempt{'s' if attempts != 1 else ''})", font_size="0.75rem", color="#9ca3af"),
        spacing="4",
        width="100%",
        align="center",
    )


def _difficulty_card(item: dict) -> rx.Component:
    diff = item.get("difficulty", "")
    avg = item.get("average_score", 0.0)
    attempts = item.get("attempts", 0)
    colour = DIFFICULTY_COLOURS.get(diff, "gray")
    return rx.card(
        rx.vstack(
            rx.badge(diff, color_scheme=colour, variant="soft"),
            rx.text(f"{avg}", font_size="1.75rem", font_weight="700", color=colour),
            rx.text("/ 10 avg", font_size="0.75rem", color="#9ca3af"),
            rx.text(f"{attempts} attempt{'s' if attempts != 1 else ''}", font_size="0.8rem", color="#6b7280"),
            spacing="1",
            align="center",
        ),
        padding="1rem",
        text_align="center",
        width="100%",
    )


def _submission_row(sub: dict) -> rx.Component:
    score = sub.get("score", 0) or 0
    colour = "green" if score >= 8 else ("orange" if score >= 5 else "red")
    return rx.table.row(
        rx.table.cell(
            rx.text(
                sub.get("submitted_at", "")[:10],  # YYYY-MM-DD
                font_size="0.85rem",
                color="#6b7280",
            ),
        ),
        rx.table.cell(
            rx.badge(f"{score}/10", color_scheme=colour, variant="soft"),
        ),
        rx.table.cell(
            rx.text(f"#{sub.get('attempt_number', 1)}", font_size="0.85rem", color="#6b7280"),
        ),
    )
