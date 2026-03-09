import flet as ft
from ui.router import AppRouter
from database import init_db

def main(page: ft.Page):
    # Ensure database is initialized before UI loads
    init_db()
    page.title = "Idealize Personalizados"
    page.theme_mode = ft.ThemeMode.LIGHT

    # Initialize the AppRouter
    router = AppRouter(page)

    # Event handlers
    page.on_route_change = router.route_change
    page.on_view_pop = router.view_pop

    # Check if a user is logged in
    user_id = page.session.get("user_id")

    if user_id:
        page.go("/")
    else:
        page.go("/login")

if __name__ == "__main__":
    import os
    if not os.path.exists("exports"):
        os.makedirs("exports")
    ft.run(main, assets_dir="exports")
