import flet as ft
from ui.views.login_view import LoginView
from ui.views.dashboard_view import DashboardView
from ui.views.materials_view import MaterialsView
from ui.views.suppliers_view import SuppliersView
from ui.views.purchases_view import PurchasesView
from ui.views.settings_view import SettingsView
from ui.views.customers_view import CustomersView
from ui.views.quotes_view import QuotesView
from ui.views.kanban_view import KanbanView
from ui.views.catalog_view import CatalogView
from ui.views.reports_view import ReportsView

class AppRouter:
    def __init__(self, page: ft.Page):
        self.page = page
        self.routes = {
            "/login": LoginView,
            "/": DashboardView,
            "/materials": MaterialsView,
            "/suppliers": SuppliersView,
            "/purchases": PurchasesView,
            "/settings": SettingsView,
            "/customers": CustomersView,
            "/quotes": QuotesView,
            "/kanban": KanbanView,
            "/catalog": CatalogView,
            "/reports": ReportsView,
        }

    def route_change(self, route):
        self.page.views.clear()

        # Check authentication
        user_session = self.page.session.get("user")

        if not user_session and self.page.route != "/login":
            self.page.go("/login")
            return

        # Role-based route protection
        admin_only_routes = ["/materials", "/suppliers", "/purchases", "/settings", "/reports"]
        if user_session and user_session.get("role") == "Operator" and self.page.route in admin_only_routes:
            # Unauthorized access attempt
            self.page.go("/")
            return

        # Get the view class
        view_class = self.routes.get(self.page.route, DashboardView)

        # Instantiate and append view
        view_instance = view_class(self.page)
        self.page.views.append(view_instance.get_view())

        self.page.update()

    def view_pop(self, view):
        self.page.views.pop()
        top_view = self.page.views[-1]
        self.page.go(top_view.route)
