import reflex as rx

config = rx.Config(
    app_name="securedeviq",
    # Reflex's backend WebSocket port (separate from the FastAPI backend)
    backend_port=8001,
    frontend_port=3000,
    # Tailwind-style theming — Reflex handles the CSS pipeline
    tailwind={},
)
