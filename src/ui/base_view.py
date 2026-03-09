import flet as ft

class BaseView:
    def __init__(self, page: ft.Page, route: str, title: str):
        self.page = page
        self.route = route
        self.title = title

        # Determine current user role
        user = self.page.session.get("user")
        self.role = user['role'] if user else None

        self.appbar = ft.AppBar(
            title=ft.Text(self.title, color=ft.colors.WHITE),
            bgcolor=ft.colors.BLUE_700,
            actions=[
                ft.IconButton(ft.icons.LOGOUT, on_click=self.logout, tooltip="Logout", icon_color=ft.colors.WHITE)
            ]
        )

        # Build Navigation Rail based on Role
        destinations = [
            ft.NavigationRailDestination(
                icon=ft.icons.DASHBOARD_OUTLINED, selected_icon=ft.icons.DASHBOARD, label="Dashboard"
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.MONEY_OUTLINED, selected_icon=ft.icons.MONEY, label="Quotes"
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.VIEW_KANBAN_OUTLINED, selected_icon=ft.icons.VIEW_KANBAN, label="Kanban"
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.CATEGORY_OUTLINED, selected_icon=ft.icons.CATEGORY, label="Catalog"
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.PEOPLE_OUTLINED, selected_icon=ft.icons.PEOPLE, label="Customers"
            ),
        ]

        self.routes_map = [
            "/", "/quotes", "/kanban", "/catalog", "/customers"
        ]

        if self.role == 'Admin':
            destinations.extend([
                ft.NavigationRailDestination(
                    icon=ft.icons.LAYERS_OUTLINED, selected_icon=ft.icons.LAYERS, label="Materials"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.LOCAL_SHIPPING_OUTLINED, selected_icon=ft.icons.LOCAL_SHIPPING, label="Suppliers"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.SHOPPING_CART_OUTLINED, selected_icon=ft.icons.SHOPPING_CART, label="Purchases"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.ANALYTICS_OUTLINED, selected_icon=ft.icons.ANALYTICS, label="Reports"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.SETTINGS_OUTLINED, selected_icon=ft.icons.SETTINGS, label="Settings"
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
        self.page.session.clear()
        self.page.go("/login")

    def get_view(self):
        return ft.View(
            self.route,
            [
                self.appbar,
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
