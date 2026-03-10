import flet as ft
from ui.base_view import BaseView
from database import get_db_connection

class MaterialsView(BaseView):
    def __init__(self, page: ft.Page):
        super().__init__(page, "/materials", "Materials")
        self.materials_list = ft.ListView(expand=True, spacing=10)
        self.load_materials()

    def load_materials(self):
        self.materials_list.controls.clear()

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM materials ORDER BY name")
        materials = c.fetchall()
        conn.close()

        if not materials:
            self.materials_list.controls.append(ft.Text("No materials registered yet.", italic=True))
        else:
            for material in materials:
                dims = f"{material['width_cm']}x{material['height_cm']}cm" if material['width_cm'] and material['height_cm'] else "N/A"
                area_m2 = f"{material['area_m2']:.4f} m²" if material['area_m2'] else "N/A"
                cost_m2 = f"R$ {material['cost_per_m2']:.2f}/m²" if material['cost_per_m2'] else "N/A"

                self.materials_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Column([
                                ft.Text(material['name'], size=16, weight=ft.FontWeight.BOLD),
                                ft.Text(f"Type/Color: {material['type_thickness_color']} | Unit: {material['unit']}"),
                                ft.Text(f"Dimensions: {dims} | Area: {area_m2}"),
                                ft.Text(f"Cost: {cost_m2}", color=ft.Colors.GREEN_700, weight=ft.FontWeight.W_600)
                            ])
                        )
                    )
                )

    def show_add_dialog(self, e):
        def close_dlg(e):
            self.page.dialog.open = False
            self.page.update()

        def save_material(e):
            name = name_input.value
            desc = desc_input.value
            unit = unit_dropdown.value

            if not name or not unit:
                error_text.value = "Name and Unit are required."
                error_text.visible = True
                self.page.update()
                return

            width = float(width_input.value) if width_input.value else None
            height = float(height_input.value) if height_input.value else None

            area_cm2 = None
            area_m2 = None

            if width and height:
                area_cm2 = width * height
                area_m2 = area_cm2 / 10000.0

            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO materials (name, type_thickness_color, unit, width_cm, height_cm, area_cm2, area_m2)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, desc, unit, width, height, area_cm2, area_m2))
            conn.commit()
            conn.close()

            self.load_materials()
            close_dlg(e)

        name_input = ft.TextField(label="Material Name")
        desc_input = ft.TextField(label="Type / Thickness / Color")
        unit_dropdown = ft.Dropdown(
            label="Unit",
            options=[
                ft.dropdown.Option("Plate"),
                ft.dropdown.Option("Sheet"),
                ft.dropdown.Option("Meter"),
                ft.dropdown.Option("Unit")
            ],
            value="Plate"
        )
        width_input = ft.TextField(label="Width (cm)", keyboard_type=ft.KeyboardType.NUMBER)
        height_input = ft.TextField(label="Height (cm)", keyboard_type=ft.KeyboardType.NUMBER)
        error_text = ft.Text(color=ft.Colors.RED, visible=False)

        dialog = ft.AlertDialog(
            title=ft.Text("Add Material"),
            content=ft.Column([
                name_input, desc_input, unit_dropdown, width_input, height_input, error_text
            ], tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.ElevatedButton("Save", on_click=save_material, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
            ]
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def build_content(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Materials Catalog", size=24, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("Add Material", icon=ft.Icons.ADD, on_click=self.show_add_dialog, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                self.materials_list
            ], expand=True),
            padding=20,
            expand=True
        )
