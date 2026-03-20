"""
securedeviq/state.py
────────────────────
Global application state for the Reflex frontend.

All API calls to the FastAPI backend are made here — pages contain only
layout and component logic, never raw HTTP calls.

Design decisions:
- httpx.AsyncClient is created per-call rather than shared, because Reflex
  event handlers run in an async context and a shared client creates
  lifecycle complexity with the Reflex event loop.
- Tokens are stored in rx.State vars (in-memory per-session). For a
  production app, consider rx.Cookie or server-side session storage.
- All vars that drive UI are typed (str, bool, list[dict], etc.) so
  Reflex can serialise them to the frontend without surprises.
"""
import os
import json
from typing import Any, Optional

import httpx
import reflex as rx

CATEGORIES = [
    ("", "AI picks"),
    ("prompt_injection", "Prompt Injection"),
    ("memory_issues", "Memory Issues"),
    ("insecure_defaults", "Insecure Defaults"),
    ("missing_sanitisation", "Missing Sanitisation"),
    ("hardcoded_secrets", "Hardcoded Secrets"),
]

CATEGORY_KEY_TO_LABEL = {key: label for key, label in CATEGORIES}
CATEGORY_LABEL_TO_KEY = {label: key for key, label in CATEGORIES}

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


class AppState(rx.State):
    # ── Auth ──────────────────────────────────────────────────────────────────
    token: str = ""
    username: str = ""
    email: str = ""
    password: str = ""
    auth_error: str = ""
    is_authenticated: bool = False

    # ── Challenge ─────────────────────────────────────────────────────────────
    current_challenge: dict = {}
    selected_language: str = "python"
    selected_difficulty: str = "junior"
    selected_category: str = ""  # empty = AI picks
    user_answer: str = ""
    is_loading_challenge: bool = False
    challenge_error: str = ""

    # ── Submission / results ──────────────────────────────────────────────────
    submission_result: dict = {}
    is_submitting: bool = False
    submission_error: str = ""

    # ── Dashboard ─────────────────────────────────────────────────────────────
    dashboard_data: dict = {}
    is_loading_dashboard: bool = False
    dashboard_total_attempts: int = 0
    dashboard_overall_average_score: float = 0.0
    dashboard_challenges_completed: int = 0
    dashboard_total_challenges_available: int = 0

    # ── Computed helpers ──────────────────────────────────────────────────────
    @rx.var
    def has_challenge(self) -> bool:
        return bool(self.current_challenge)

    @rx.var
    def has_result(self) -> bool:
        return bool(self.submission_result)

    @rx.var
    def dashboard_category_breakdown(self) -> list[dict[str, Any]]:
        data = self.dashboard_data.get("category_breakdown", [])
        return data if isinstance(data, list) else []

    @rx.var
    def dashboard_difficulty_breakdown(self) -> list[dict[str, Any]]:
        data = self.dashboard_data.get("difficulty_breakdown", [])
        return data if isinstance(data, list) else []

    @rx.var
    def dashboard_recent_submissions(self) -> list[dict[str, Any]]:
        data = self.dashboard_data.get("recent_submissions", [])
        return data if isinstance(data, list) else []

    @rx.var
    def score_colour(self) -> str:
        score = self.submission_result.get("score", 0)
        if score >= 8:
            return "green"
        if score >= 5:
            return "orange"
        return "red"

    @rx.var
    def score_border_color(self) -> str:
        score = self.submission_result.get("score", 0)
        if score >= 8:
            return "4px solid #22c55e"
        if score >= 5:
            return "4px solid #f97316"
        return "4px solid #ef4444"

    @rx.var
    def score_feedback_message(self) -> str:
        score = self.submission_result.get("score", 0)
        if score >= 8:
            return "Excellent work! You've got a sharp eye for this vulnerability."
        if score >= 5:
            return "Good effort — you identified the key issue but missed some details."
        return "Keep practising — review the explanation below carefully."

    @rx.var
    def correct_findings_list(self) -> list[str]:
        raw = self.submission_result.get("correct_findings", "")
        return [f.strip() for f in raw.split("\n") if f.strip()] if raw else []

    @rx.var
    def missed_findings_list(self) -> list[str]:
        raw = self.submission_result.get("missed_findings", "")
        return [f.strip() for f in raw.split("\n") if f.strip()] if raw else []

    # ── Auth handlers ─────────────────────────────────────────────────────────
    def set_username(self, value: str):
        self.username = value

    def set_email(self, value: str):
        self.email = value

    def set_password(self, value: str):
        self.password = value

    async def register(self):
        self.auth_error = ""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/auth/register",
                json={"username": self.username, "email": self.email, "password": self.password},
            )
        if resp.status_code == 201:
            await self.login()
        else:
            detail = resp.json().get("detail", "Registration failed")
            self.auth_error = detail

    async def login(self):
        self.auth_error = ""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/auth/token",
                data={"username": self.username, "password": self.password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if resp.status_code == 200:
            self.token = resp.json()["access_token"]
            self.is_authenticated = True
            return rx.redirect("/challenge")
        self.auth_error = "Incorrect username or password"

    def logout(self):
        self.token = ""
        self.is_authenticated = False
        self.current_challenge = {}
        self.submission_result = {}
        return rx.redirect("/")

    # ── Challenge handlers ────────────────────────────────────────────────────
    def set_language(self, value: str):
        self.selected_language = value

    def set_difficulty(self, value: str):
        self.selected_difficulty = value

    def set_category(self, value: str):
        self.selected_category = value

    def set_answer(self, value: str):
        self.user_answer = value

    @rx.var
    def get_category_label(self) -> str:
        """Return the display label for the currently selected category."""
        return CATEGORY_KEY_TO_LABEL.get(self.selected_category, "AI picks")

    def handle_category_selection(self, label: str):
        """Convert a label to its key and set the category."""
        key = CATEGORY_LABEL_TO_KEY.get(label, "")
        self.set_category(key)

    async def load_challenge(self):
        if not self.is_authenticated:
            return rx.redirect("/")
        self.is_loading_challenge = True
        self.challenge_error = ""
        self.current_challenge = {}
        self.submission_result = {}
        self.user_answer = ""

        payload: dict = {
            "language": self.selected_language,
            "difficulty": self.selected_difficulty,
        }
        if self.selected_category:
            payload["vuln_category"] = self.selected_category

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/challenges/generate",
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"},
            )

        self.is_loading_challenge = False
        if resp.status_code == 201:
            self.current_challenge = resp.json()
        else:
            detail = "Failed to generate challenge"
            try:
                payload = resp.json()
                if isinstance(payload, dict):
                    detail = payload.get("detail", detail)
            except json.JSONDecodeError:
                body_text = (resp.text or "").strip()
                if body_text:
                    detail = body_text
            self.challenge_error = detail

    # ── Submission handlers ───────────────────────────────────────────────────
    async def submit_answer(self):
        if not self.current_challenge or not self.user_answer.strip():
            self.submission_error = "Please write your analysis before submitting."
            return
        self.is_submitting = True
        self.submission_error = ""

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/submissions",
                json={
                    "challenge_id": self.current_challenge["id"],
                    "user_answer": self.user_answer,
                },
                headers={"Authorization": f"Bearer {self.token}"},
            )

        self.is_submitting = False
        if resp.status_code == 201:
            self.submission_result = resp.json()
            return rx.redirect("/results")
        self.submission_error = resp.json().get("detail", "Submission failed")

    # ── Dashboard handler ─────────────────────────────────────────────────────
    async def load_dashboard(self):
        if not self.is_authenticated:
            return rx.redirect("/")
        self.is_loading_dashboard = True
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BACKEND_URL}/api/dashboard",
                headers={"Authorization": f"Bearer {self.token}"},
            )
        self.is_loading_dashboard = False
        if resp.status_code == 200:
            data = resp.json()
            self.dashboard_data = data
            self.dashboard_total_attempts = int(data.get("total_attempts", 0) or 0)
            self.dashboard_overall_average_score = float(data.get("overall_average_score", 0.0) or 0.0)
            self.dashboard_challenges_completed = int(data.get("challenges_completed", 0) or 0)
            self.dashboard_total_challenges_available = int(data.get("total_challenges_available", 0) or 0)
