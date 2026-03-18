import flet as ft
from ui.base_view import BaseView
from database import get_db_connection
import csv
import os
from datetime import datetime

class CustomersView(BaseView):
    def __init__(self, page: ft.Page):
        super().__init__(page, "/customers", "Clientes")
        self.customers_list = ft.ListView(expand=True, spacing=10)
        self.load_customers()

    def load_customers(self):
        self.customers_list.controls.clear()

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM customers ORDER BY name")
        customers = c.fetchall()
        conn.close()

        if not customers:
            self.customers_list.controls.append(ft.Text("Nenhum cliente registrado ainda.", italic=True))
        else:
            for customer in customers:
                self.customers_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Column([
                                ft.Text(customer['name'], size=16, weight=ft.FontWeight.BOLD),
                                ft.Text(f"Telefone: {customer['phone'] or 'N/A'} | E-mail: {customer['email'] or 'N/A'}"),
                                ft.Text(f"Endereço: {customer['address'] or 'N/A'}")
                            ])
                        )
                    )
                )

    def show_add_dialog(self, e):
        dialog = None

        def close_dlg(e):
            dialog.open = False
            self.page.update()

        def save_customer(e):
            name = name_input.value
            if not name:
                error_text.value = "O nome é obrigatório."
                error_text.visible = True
                self.page.update()
                return

            phone = phone_input.value
            email = email_input.value
            address = address_input.value

            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO customers (name, phone, email, address)
                VALUES (?, ?, ?, ?)
            ''', (name, phone, email, address))
            conn.commit()
            conn.close()

            self.load_customers()
            close_dlg(e)

        name_input = ft.TextField(label="Nome do Cliente")
        phone_input = ft.TextField(label="Telefone")
        email_input = ft.TextField(label="E-mail")
        address_input = ft.TextField(label="Endereço")
        error_text = ft.Text(color=ft.Colors.RED, visible=False)

        dialog = ft.AlertDialog(
            title=ft.Text("Adicionar Cliente"),
            content=ft.Column([
                name_input, phone_input, email_input, address_input, error_text
            ], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dlg),
                ft.ElevatedButton("Salvar", on_click=save_customer, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
            ]
        )

        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def export_csv(self, e):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM customers ORDER BY name")
        customers = c.fetchall()
        conn.close()

        exports_dir = os.path.join(os.getcwd(), "exports")
        if not os.path.exists(exports_dir):
            os.makedirs(exports_dir)

        filename = f"clientes_exportacao_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        filepath = os.path.join(exports_dir, filename)

        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Nome", "Telefone", "E-mail", "Endereço"])
            for row in customers:
                writer.writerow([row['id'], row['name'], row['phone'], row['email'], row['address']])

        self.page.overlay.append(ft.SnackBar(ft.Text(f"Exportado para {filename}"), bgcolor=ft.Colors.GREEN_700, open=True))
        self.page.run_task(self.page.launch_url, f"/{filename}")
        self.page.update()

    def build_content(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Clientes (Mini-CRM)", size=24, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.ElevatedButton("Exportar CSV", icon=ft.Icons.DOWNLOAD, on_click=self.export_csv, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
                        ft.ElevatedButton("Adicionar Cliente", icon=ft.Icons.ADD, on_click=self.show_add_dialog, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
                    ])
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                self.customers_list
            ], expand=True),
            padding=20,
            expand=True
        )
