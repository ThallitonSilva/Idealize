import flet as ft

class BaseView:
    def __init__(self, page: ft.Page, route: str, title: str):
        self.page = page
        self.route = route
        self.title = title

        from database import get_db_connection

        # Determine current user role securely from backend
        user_id = getattr(self.page, "user_id", None)
        self.role = None
        self.username = None

        if user_id:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT role, username FROM users WHERE id = ?", (user_id,))
            user_row = c.fetchone()
            conn.close()
            if user_row:
                self.role = user_row['role']
                self.username = user_row['username']

        self.appbar = ft.AppBar(
            title=ft.Text(self.title, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.BLUE_700,
            actions=[
                ft.IconButton(ft.Icons.LOGOUT, on_click=self.logout, tooltip="Sair", icon_color=ft.Colors.WHITE)
            ]
        )

        # Build Navigation Rail based on Role
        destinations = [
            ft.NavigationRailDestination(
                icon=ft.Icons.DASHBOARD_OUTLINED, selected_icon=ft.Icons.DASHBOARD, label="Painel"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.MONEY_OUTLINED, selected_icon=ft.Icons.MONEY, label="Orçamentos"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.VIEW_KANBAN_OUTLINED, selected_icon=ft.Icons.VIEW_KANBAN, label="Kanban"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.CATEGORY_OUTLINED, selected_icon=ft.Icons.CATEGORY, label="Catálogo"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.PEOPLE_OUTLINED, selected_icon=ft.Icons.PEOPLE, label="Clientes"
            ),
        ]

        self.routes_map = [
            "/", "/quotes", "/kanban", "/catalog", "/customers"
        ]

        if self.role == 'Admin':
            destinations.extend([
                ft.NavigationRailDestination(
                    icon=ft.Icons.LAYERS_OUTLINED, selected_icon=ft.Icons.LAYERS, label="Materiais"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.LOCAL_SHIPPING_OUTLINED, selected_icon=ft.Icons.LOCAL_SHIPPING, label="Fornecedores"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SHOPPING_CART_OUTLINED, selected_icon=ft.Icons.SHOPPING_CART, label="Compras"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ANALYTICS_OUTLINED, selected_icon=ft.Icons.ANALYTICS, label="Relatórios"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label="Configurações"
                ),
            ])
            self.routes_map.extend([
                "/materials", "/suppliers", "/purchases", "/reports", "/settings"
            ])

        selected_idx = self.routes_map.index(self.route) if self.route in self.routes_map else 0

        self.nav_rail = ft.NavigationRail(
            selected_index=selected_idx,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            extended=True,
            destinations=destinations,
            on_change=self.nav_change
        )

    def nav_change(self, e):
        idx = e.control.selected_index
        if idx < len(self.routes_map):
            self.page.go(self.routes_map[idx])

    def logout(self, e):
        self.page.user_id = None
        self.page.go("/login")

    def get_view(self):
        return ft.View(
            route=self.route,
            appbar=self.appbar,
            controls=[
                ft.Row(
                    [
                        self.nav_rail,
                        ft.VerticalDivider(width=1),
                        self.build_content()
                    ],
                    expand=True
                )
            ]
        )

    def build_content(self):
        return ft.Container(content=ft.Text("Empty Content"), expand=True, padding=20)
