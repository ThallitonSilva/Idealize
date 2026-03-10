import flet as ft
from ui.base_view import BaseView
from database import get_db_connection

class SuppliersView(BaseView):
    def __init__(self, page: ft.Page):
        super().__init__(page, "/suppliers", "Suppliers")
        self.suppliers_list = ft.ListView(expand=True, spacing=10)
        self.load_suppliers()

    def load_suppliers(self):
        self.suppliers_list.controls.clear()

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM suppliers ORDER BY name")
        suppliers = c.fetchall()
        conn.close()

        if not suppliers:
            self.suppliers_list.controls.append(ft.Text("No suppliers registered yet.", italic=True))
        else:
            for supplier in suppliers:
                self.suppliers_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Column([
                                ft.Text(supplier['name'], size=16, weight=ft.FontWeight.BOLD),
                                ft.Text(f"Phone: {supplier['contact_phone'] or 'N/A'} | Email: {supplier['contact_email'] or 'N/A'}"),
                                ft.Text(f"Address: {supplier['address'] or 'N/A'}")
                            ])
                        )
                    )
                )

    def show_add_dialog(self, e):
        def close_dlg(e):
            self.page.dialog.open = False
            self.page.update()

        def save_supplier(e):
            name = name_input.value
            if not name:
                error_text.value = "Name is required."
                error_text.visible = True
                self.page.update()
                return

            phone = phone_input.value
            email = email_input.value
            address = address_input.value

            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO suppliers (name, contact_phone, contact_email, address)
                VALUES (?, ?, ?, ?)
            ''', (name, phone, email, address))
            conn.commit()
            conn.close()

            self.load_suppliers()
            close_dlg(e)

        name_input = ft.TextField(label="Supplier Name")
        phone_input = ft.TextField(label="Phone")
        email_input = ft.TextField(label="Email")
        address_input = ft.TextField(label="Address")
        error_text = ft.Text(color=ft.Colors.RED, visible=False)

        dialog = ft.AlertDialog(
            title=ft.Text("Add Supplier"),
            content=ft.Column([
                name_input, phone_input, email_input, address_input, error_text
            ], tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.ElevatedButton("Save", on_click=save_supplier, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
            ]
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def build_content(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Suppliers", size=24, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("Add Supplier", icon=ft.Icons.ADD, on_click=self.show_add_dialog, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                self.suppliers_list
            ], expand=True),
            padding=20,
            expand=True
        )
