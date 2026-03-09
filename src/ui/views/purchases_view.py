import flet as ft
from ui.base_view import BaseView
from database import get_db_connection
from datetime import datetime

class PurchasesView(BaseView):
    def __init__(self, page: ft.Page):
        super().__init__(page, "/purchases", "Purchases")
        self.purchases_list = ft.ListView(expand=True, spacing=10)
        self.load_purchases()

    def load_purchases(self):
        self.purchases_list.controls.clear()

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            SELECT p.*, m.name as material_name, s.name as supplier_name
            FROM purchases p
            JOIN materials m ON p.material_id = m.id
            JOIN suppliers s ON p.supplier_id = s.id
            ORDER BY p.purchase_date DESC
        ''')
        purchases = c.fetchall()
        conn.close()

        if not purchases:
            self.purchases_list.controls.append(ft.Text("No purchases registered yet.", italic=True))
        else:
            for p in purchases:
                qty = p['quantity'] if 'quantity' in p.keys() else 1.0
                self.purchases_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Column([
                                ft.Text(f"{p['material_name']} from {p['supplier_name']}", size=16, weight=ft.FontWeight.BOLD),
                                ft.Text(f"Date: {p['purchase_date']} | Qty: {qty} | Total Cost: R$ {p['cost_price']:.2f}"),
                                ft.Text(f"Lot Code: {p['lot_code'] or 'N/A'}")
                            ])
                        )
                    )
                )

    def show_add_dialog(self, e):
        def close_dlg(e):
            self.page.dialog.open = False
            self.page.update()

        def save_purchase(e):
            mat_id = material_dropdown.value
            sup_id = supplier_dropdown.value
            date_val = date_input.value
            cost_val = cost_input.value
            qty_val = qty_input.value
            lot_code = lot_input.value

            if not mat_id or not sup_id or not date_val or not cost_val or not qty_val:
                error_text.value = "Material, Supplier, Date, Quantity and Cost are required."
                error_text.visible = True
                self.page.update()
                return

            try:
                cost_val = float(cost_val)
                qty_val = float(qty_val)
            except ValueError:
                error_text.value = "Cost and Quantity must be valid numbers."
                error_text.visible = True
                self.page.update()
                return

            conn = get_db_connection()
            c = conn.cursor()

            # Insert purchase
            c.execute('''
                INSERT INTO purchases (material_id, supplier_id, purchase_date, cost_price, quantity, lot_code)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (mat_id, sup_id, date_val, cost_val, qty_val, lot_code))

            # Update material costs
            c.execute("SELECT area_cm2, area_m2 FROM materials WHERE id = ?", (mat_id,))
            material = c.fetchone()

            if material and material['area_cm2']:
                total_area_cm2 = material['area_cm2'] * qty_val
                total_area_m2 = material['area_m2'] * qty_val

                cost_per_cm2 = cost_val / total_area_cm2 if total_area_cm2 > 0 else 0
                cost_per_m2 = cost_val / total_area_m2 if total_area_m2 > 0 else 0
                c.execute('''
                    UPDATE materials
                    SET cost_per_cm2 = ?, cost_per_m2 = ?
                    WHERE id = ?
                ''', (cost_per_cm2, cost_per_m2, mat_id))

            conn.commit()
            conn.close()

            self.load_purchases()
            close_dlg(e)

        # Load dropdowns
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, name FROM materials")
        materials = c.fetchall()
        c.execute("SELECT id, name FROM suppliers")
        suppliers = c.fetchall()
        conn.close()

        material_dropdown = ft.Dropdown(
            label="Material",
            options=[ft.dropdown.Option(str(m['id']), m['name']) for m in materials]
        )
        supplier_dropdown = ft.Dropdown(
            label="Supplier",
            options=[ft.dropdown.Option(str(s['id']), s['name']) for s in suppliers]
        )
        date_input = ft.TextField(label="Purchase Date (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))
        qty_input = ft.TextField(label="Quantity (Sheets/Plates/Units)", value="1", keyboard_type=ft.KeyboardType.NUMBER)
        cost_input = ft.TextField(label="Total Cost Price", keyboard_type=ft.KeyboardType.NUMBER)
        lot_input = ft.TextField(label="Lot Code (Optional)")
        error_text = ft.Text(color=ft.colors.RED, visible=False)

        dialog = ft.AlertDialog(
            title=ft.Text("Register Purchase"),
            content=ft.Column([
                material_dropdown, supplier_dropdown, date_input, qty_input, cost_input, lot_input, error_text
            ], tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.ElevatedButton("Save", on_click=save_purchase, bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE)
            ]
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def build_content(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Purchase History", size=24, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("Register Purchase", icon=ft.icons.ADD, on_click=self.show_add_dialog, bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                self.purchases_list
            ], expand=True),
            padding=20,
            expand=True
        )
