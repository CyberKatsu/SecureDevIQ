"""
securedeviq/securedeviq.py
──────────────────────────
Reflex app entry point. Registers all pages and exports the `app` object
that Reflex's CLI picks up from rxconfig.py.
"""
import reflex as rx

from securedeviq.pages.index import auth_page
from securedeviq.pages.challenge import challenge_page
from securedeviq.pages.results import results_page
from securedeviq.pages.dashboard import dashboard_page

app = rx.App(
    theme=rx.theme(
        appearance="inherit",
        accent_color="indigo",
        radius="medium",
    ),
)

app.add_page(auth_page, route="/", title="SecureDevIQ — Login")
app.add_page(challenge_page, route="/challenge", title="SecureDevIQ — Challenge")
app.add_page(results_page, route="/results", title="SecureDevIQ — Results")
app.add_page(dashboard_page, route="/dashboard", title="SecureDevIQ — Dashboard")
