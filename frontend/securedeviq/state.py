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
from typing import Optional

import httpx
import reflex as rx

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

    # ── Computed helpers ──────────────────────────────────────────────────────
    @rx.var
    def has_challenge(self) -> bool:
        return bool(self.current_challenge)

    @rx.var
    def has_result(self) -> bool:
        return bool(self.submission_result)

    @rx.var
    def score_colour(self) -> str:
        score = self.submission_result.get("score", 0)
        if score >= 8:
            return "green"
        if score >= 5:
            return "orange"
        return "red"

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
            self.challenge_error = resp.json().get("detail", "Failed to generate challenge")

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
            self.dashboard_data = resp.json()
