import flet as ft
from ui.base_view import BaseView
from database import get_db_connection

class MaterialsView(BaseView):
    def __init__(self, page: ft.Page):
        super().__init__(page, "/materials", "Materiais")
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
            self.materials_list.controls.append(ft.Text("Nenhum material registrado ainda.", italic=True))
        else:
            for material in materials:
                dims = f"{material['width_cm']}x{material['height_cm']}cm" if material['width_cm'] and material['height_cm'] else "N/A"
                area_cm2 = f"{material['area_cm2']} cm²" if material['area_cm2'] else "N/A"
                area_m2 = f"{material['area_m2']:.4f} m²" if material['area_m2'] else ""

                area_display = f"{area_cm2} ({area_m2})" if area_m2 else area_cm2
                cost_m2 = f"R$ {material['cost_per_m2']:.2f}/m² (R$ {material['cost_per_cm2']:.4f}/cm²)" if material['cost_per_m2'] else "N/A"

                self.materials_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Column([
                                ft.Text(material['name'], size=16, weight=ft.FontWeight.BOLD),
                                ft.Text(f"Tipo/Cor: {material['type_thickness_color']} | Unidade: {material['unit']}"),
                                ft.Text(f"Dimensões: {dims} | Área: {area_display}"),
                                ft.Text(f"Custo: {cost_m2}", color=ft.Colors.GREEN_700, weight=ft.FontWeight.W_600)
                            ])
                        )
                    )
                )

    def show_add_dialog(self, e):
        dialog = None

        def close_dlg(e):
            dialog.open = False
            self.page.update()

        def save_material(e):
            name = name_input.value
            desc = desc_input.value
            unit = unit_dropdown.value

            if not name or not unit:
                error_text.value = "Nome e Unidade são obrigatórios."
                error_text.visible = True
                self.page.update()
                return

            try:
                width = float(width_input.value) if width_input.value else None
                height = float(height_input.value) if height_input.value else None
                cost_val = float(cost_input.value) if cost_input.value else 0.0
            except ValueError:
                error_text.value = "Largura, Altura e Custo devem ser números válidos."
                error_text.visible = True
                self.page.update()
                return

            area_cm2 = None
            area_m2 = None
            cost_per_cm2 = 0.0
            cost_per_m2 = 0.0

            if width and height:
                area_cm2 = width * height
                area_m2 = area_cm2 / 10000.0

                if cost_val > 0:
                    cost_per_cm2 = cost_val / area_cm2
                    cost_per_m2 = cost_val / area_m2

            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO materials (name, type_thickness_color, unit, width_cm, height_cm, area_cm2, area_m2, cost_per_cm2, cost_per_m2)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, desc, unit, width, height, area_cm2, area_m2, cost_per_cm2, cost_per_m2))
            conn.commit()
            conn.close()

            self.load_materials()
            close_dlg(e)

        name_input = ft.TextField(label="Nome do Material")
        desc_input = ft.TextField(label="Tipo / Espessura / Cor")
        unit_dropdown = ft.Dropdown(
            label="Unidade",
            options=[
                ft.dropdown.Option("Plate", "Chapa"),
                ft.dropdown.Option("Sheet", "Folha"),
                ft.dropdown.Option("Meter", "Metro"),
                ft.dropdown.Option("Unit", "Unidade")
            ],
            value="Plate"
        )
        width_input = ft.TextField(label="Largura (cm)", keyboard_type=ft.KeyboardType.NUMBER)
        height_input = ft.TextField(label="Altura (cm)", keyboard_type=ft.KeyboardType.NUMBER)
        cost_input = ft.TextField(label="Preço Pago (Opcional)", keyboard_type=ft.KeyboardType.NUMBER)
        error_text = ft.Text(color=ft.Colors.RED, visible=False)

        dialog = ft.AlertDialog(
            title=ft.Text("Adicionar Material"),
            content=ft.Column([
                name_input, desc_input, unit_dropdown, ft.Row([width_input, height_input]), cost_input, error_text
            ], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dlg),
                ft.ElevatedButton("Salvar", on_click=save_material, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
            ]
        )

        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def build_content(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Catálogo de Materiais", size=24, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("Adicionar Material", icon=ft.Icons.ADD, on_click=self.show_add_dialog, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                self.materials_list
            ], expand=True),
            padding=20,
            expand=True
        )
