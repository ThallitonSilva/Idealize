import flet as ft
from ui.base_view import BaseView
from database import get_db_connection
import csv
import os
from datetime import datetime

class CatalogView(BaseView):
    def __init__(self, page: ft.Page):
        super().__init__(page, "/catalog", "Catálogo")
        self.catalog_list = ft.ListView(expand=True, spacing=10)
        self.settings = self._load_settings()
        self.load_catalog()

    def _load_settings(self):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT key, value FROM settings")
        s = {row['key']: row['value'] for row in c.fetchall()}
        conn.close()
        return s

    def load_catalog(self):
        self.catalog_list.controls.clear()

        conn = get_db_connection()
        c = conn.cursor()

        # Load non-kit products and their dynamic costs
        c.execute('''
            SELECT p.id, p.name, p.description, p.base_price,
                   pc.id as pc_id, pc.variation_name, pc.material_id, pc.width_cm, pc.height_cm, pc.machine_time_min, pc.manual_time_min, pc.extra_costs,
                   m.cost_per_cm2, m.name as mat_name
            FROM products p
            LEFT JOIN product_components pc ON p.id = pc.product_id
            LEFT JOIN materials m ON pc.material_id = m.id
            WHERE p.is_kit = 0
            ORDER BY p.name, pc.variation_name
        ''')
        products = c.fetchall()

        # Load kits
        c.execute('''
            SELECT * FROM products WHERE is_kit = 1 ORDER BY name
        ''')
        kits = c.fetchall()

        conn.close()

        if not products and not kits:
            self.catalog_list.controls.append(ft.Text("Nenhum produto no catálogo ainda.", italic=True))
        else:
            # Display Standard Products with Dynamic Pricing Calculation
            for p in products:
                current_cost = self._calculate_product_cost(p)

                # We can calculate a standard retail price for display
                markup = 2.0  # Default display markup
                display_price = current_cost * markup

                variation_label = p['variation_name'] if p['variation_name'] else 'Padrão'
                title_text = f"{p['name']} ({variation_label})"

                self.catalog_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=15,
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(title_text, size=18, weight=ft.FontWeight.BOLD),
                                    ft.Row([
                                        ft.IconButton(ft.Icons.ADD_BOX, tooltip="Adicionar Variação", on_click=lambda e, pid=p['id'], pname=p['name']: self.show_add_variation_dialog(pid, pname)),
                                        ft.Container(content=ft.Text("Produto", size=10, color=ft.Colors.WHITE), bgcolor=ft.Colors.BLUE_700, padding=3, border_radius=3)
                                    ])
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Text(f"Material: {p['mat_name']} | Dim: {p['width_cm']}x{p['height_cm']}cm"),
                                ft.Text(f"Custo Base: R$ {current_cost:.2f} | Preço de Venda Est.: R$ {display_price:.2f}", weight=ft.FontWeight.W_500, color=ft.Colors.GREEN_700)
                            ])
                        )
                    )
                )

            # Display Kits
            for k in kits:
                kit_cost = self._calculate_kit_cost(k['id'])
                markup = 2.0
                display_price = kit_cost * markup

                if k['kit_discount_type'] == 'Fixed':
                    display_price -= k['kit_discount_value']
                elif k['kit_discount_type'] == 'Percentage':
                    display_price *= (1 - (k['kit_discount_value'] / 100.0))

                self.catalog_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=15,
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(k['name'], size=18, weight=ft.FontWeight.BOLD),
                                    ft.Container(content=ft.Text("Kit", size=10, color=ft.Colors.BLACK), bgcolor=ft.Colors.AMBER_400, padding=3, border_radius=3)
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Text(k['description'] or "Um kit de produtos compostos."),
                                ft.Text(f"Custo Base Total: R$ {kit_cost:.2f} | Preço do Kit: R$ {display_price:.2f}", weight=ft.FontWeight.W_500, color=ft.Colors.GREEN_700)
                            ])
                        )
                    )
                )

    def _calculate_product_cost(self, p):
        if not p['material_id']: return float(p['base_price'] or 0.0)

        cost_cm2 = float(p['cost_per_cm2'] or 0.0)
        loss_factor = float(self.settings.get('global_loss_factor_percent', '10')) / 100.0
        mach_cost_min = float(self.settings.get('machine_minute_cost_cached', '0'))
        man_cost_min = float(self.settings.get('labor_minute_cost', '0'))

        area = float(p['width_cm'] or 0) * float(p['height_cm'] or 0)
        mat_cost = area * cost_cm2 * (1 + loss_factor)

        op_cost = (float(p['machine_time_min'] or 0) * mach_cost_min) + (float(p['manual_time_min'] or 0) * man_cost_min)
        extra = float(p['extra_costs'] or 0.0)

        return mat_cost + op_cost + extra

    def _calculate_kit_cost(self, kit_id):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            SELECT ki.quantity, p.id, p.base_price,
                   pc.material_id, pc.width_cm, pc.height_cm, pc.machine_time_min, pc.manual_time_min, pc.extra_costs,
                   m.cost_per_cm2
            FROM kit_items ki
            JOIN products p ON ki.component_product_id = p.id
            LEFT JOIN product_components pc ON p.id = pc.product_id
            LEFT JOIN materials m ON pc.material_id = m.id
            WHERE ki.kit_product_id = ?
        ''', (kit_id,))
        items = c.fetchall()
        conn.close()

        total_cost = 0.0
        for item in items:
            total_cost += self._calculate_product_cost(item) * item['quantity']

        return total_cost

    def show_add_product_dialog(self, e):
        # UI for adding a standard product
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, name FROM materials ORDER BY name")
        materials = c.fetchall()
        conn.close()

        name_input = ft.TextField(label="Nome do Produto")
        desc_input = ft.TextField(label="Descrição", multiline=True)

        mat_dd = ft.Dropdown(label="Material", options=[ft.dropdown.Option(str(m['id']), m['name']) for m in materials])
        w_input = ft.TextField(label="Largura (cm)", keyboard_type=ft.KeyboardType.NUMBER)
        h_input = ft.TextField(label="Altura (cm)", keyboard_type=ft.KeyboardType.NUMBER)
        mach_input = ft.TextField(label="Tempo de Máquina (min)", keyboard_type=ft.KeyboardType.NUMBER)
        man_input = ft.TextField(label="Tempo Manual (min)", keyboard_type=ft.KeyboardType.NUMBER)
        extra_input = ft.TextField(label="Custos Fixos Extras (R$)", keyboard_type=ft.KeyboardType.NUMBER)

        dlg = None

        def save_product(e):
            if not name_input.value or not mat_dd.value:
                self.page.overlay.append(ft.SnackBar(ft.Text("O Nome e o Material são obrigatórios."), bgcolor=ft.Colors.RED, open=True))
                self.page.update()
                return

            try:
                w_val = float(w_input.value or 0)
                h_val = float(h_input.value or 0)
                mach_val = float(mach_input.value or 0)
                man_val = float(man_input.value or 0)
                extra_val = float(extra_input.value or 0)
            except ValueError:
                self.page.overlay.append(ft.SnackBar(ft.Text("Valores numéricos inválidos nos campos de medidas/custos."), bgcolor=ft.Colors.RED, open=True))
                self.page.update()
                return

            conn = get_db_connection()
            c = conn.cursor()
            c.execute("INSERT INTO products (name, description, is_kit) VALUES (?, ?, 0)", (name_input.value, desc_input.value))
            prod_id = c.lastrowid

            c.execute('''
                INSERT INTO product_components (product_id, material_id, width_cm, height_cm, machine_time_min, manual_time_min, extra_costs)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (prod_id, mat_dd.value, w_val, h_val, mach_val, man_val, extra_val))

            conn.commit()
            conn.close()

            dlg.open = False
            self.load_catalog()
            self.page.update()

        def close_dlg(e):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Adicionar Novo Produto"),
            content=ft.Column([
                name_input, desc_input,
                ft.Text("Receita do Componente", weight=ft.FontWeight.BOLD),
                mat_dd, ft.Row([w_input, h_input]), ft.Row([mach_input, man_input]), extra_input
            ], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dlg),
                ft.ElevatedButton("Salvar Produto", on_click=save_product, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
            ]
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def show_add_variation_dialog(self, product_id, product_name):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, name FROM materials ORDER BY name")
        materials = c.fetchall()
        conn.close()

        var_name_input = ft.TextField(label="Nome da Variação (ex. Acrílico Preto)")
        mat_dd = ft.Dropdown(label="Material", options=[ft.dropdown.Option(str(m['id']), m['name']) for m in materials])
        w_input = ft.TextField(label="Largura (cm)", keyboard_type=ft.KeyboardType.NUMBER)
        h_input = ft.TextField(label="Altura (cm)", keyboard_type=ft.KeyboardType.NUMBER)
        mach_input = ft.TextField(label="Tempo de Máquina (min)", keyboard_type=ft.KeyboardType.NUMBER)
        man_input = ft.TextField(label="Tempo Manual (min)", keyboard_type=ft.KeyboardType.NUMBER)
        extra_input = ft.TextField(label="Custos Fixos Extras (R$)", keyboard_type=ft.KeyboardType.NUMBER)

        dlg = None

        def save_variation(e):
            if not var_name_input.value or not mat_dd.value:
                self.page.overlay.append(ft.SnackBar(ft.Text("O Nome da Variação e o Material são obrigatórios."), bgcolor=ft.Colors.RED, open=True))
                self.page.update()
                return

            try:
                w_val = float(w_input.value or 0)
                h_val = float(h_input.value or 0)
                mach_val = float(mach_input.value or 0)
                man_val = float(man_input.value or 0)
                extra_val = float(extra_input.value or 0)
            except ValueError:
                self.page.overlay.append(ft.SnackBar(ft.Text("Valores numéricos inválidos nos campos de medidas/custos."), bgcolor=ft.Colors.RED, open=True))
                self.page.update()
                return

            conn = get_db_connection()
            c = conn.cursor()

            c.execute('''
                INSERT INTO product_components (product_id, variation_name, material_id, width_cm, height_cm, machine_time_min, manual_time_min, extra_costs)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (product_id, var_name_input.value, mat_dd.value, w_val, h_val, mach_val, man_val, extra_val))

            conn.commit()
            conn.close()

            dlg.open = False
            self.load_catalog()
            self.page.update()

        def close_dlg(e):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(f"Adicionar Variação para: {product_name}"),
            content=ft.Column([
                var_name_input,
                ft.Text("Receita da Variação", weight=ft.FontWeight.BOLD),
                mat_dd, ft.Row([w_input, h_input]), ft.Row([mach_input, man_input]), extra_input
            ], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dlg),
                ft.ElevatedButton("Salvar Variação", on_click=save_variation, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
            ]
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def show_add_kit_dialog(self, e):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, name FROM products WHERE is_kit = 0 ORDER BY name")
        standard_products = c.fetchall()
        conn.close()

        kit_name_input = ft.TextField(label="Nome do Kit")
        kit_desc_input = ft.TextField(label="Descrição do Kit", multiline=True)
        discount_type_dd = ft.Dropdown(label="Tipo de Desconto", options=[ft.dropdown.Option("Fixed", "Fixo"), ft.dropdown.Option("Percentage", "Porcentagem")])
        discount_value_input = ft.TextField(label="Valor do Desconto", keyboard_type=ft.KeyboardType.NUMBER)

        selected_components = []
        components_listview = ft.ListView(height=100, spacing=5)

        comp_dd = ft.Dropdown(label="Selecionar Produto", options=[ft.dropdown.Option(str(p['id']), p['name']) for p in standard_products])
        comp_qty = ft.TextField(label="Qtd", value="1", keyboard_type=ft.KeyboardType.NUMBER, width=60)

        def add_component_to_kit(e):
            if comp_dd.value:
                p_id = comp_dd.value
                qty = int(comp_qty.value or 1)
                p_name = next(p['name'] for p in standard_products if str(p['id']) == p_id)
                selected_components.append({'id': p_id, 'qty': qty, 'name': p_name})
                components_listview.controls.append(ft.Text(f"{qty}x {p_name}"))
                self.page.update()

        dlg = None

        def save_kit(e):
            if not kit_name_input.value or not selected_components:
                self.page.overlay.append(ft.SnackBar(ft.Text("O Nome e pelo menos 1 componente são obrigatórios."), bgcolor=ft.Colors.RED, open=True))
                self.page.update()
                return

            conn = get_db_connection()
            c = conn.cursor()

            discount_type = discount_type_dd.value if discount_type_dd.value else None
            discount_val = float(discount_value_input.value or 0)

            c.execute("INSERT INTO products (name, description, is_kit, kit_discount_type, kit_discount_value) VALUES (?, ?, 1, ?, ?)",
                      (kit_name_input.value, kit_desc_input.value, discount_type, discount_val))
            kit_id = c.lastrowid

            for comp in selected_components:
                c.execute("INSERT INTO kit_items (kit_product_id, component_product_id, quantity) VALUES (?, ?, ?)", (kit_id, comp['id'], comp['qty']))

            conn.commit()
            conn.close()

            dlg.open = False
            self.load_catalog()
            self.page.update()

        def close_dlg(e):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Criar Novo Kit"),
            content=ft.Column([
                kit_name_input, kit_desc_input,
                ft.Row([discount_type_dd, discount_value_input]),
                ft.Divider(),
                ft.Text("Componentes do Kit", weight=ft.FontWeight.BOLD),
                ft.Row([comp_dd, comp_qty, ft.IconButton(ft.Icons.ADD, on_click=add_component_to_kit)]),
                components_listview
            ], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dlg),
                ft.ElevatedButton("Salvar Kit", on_click=save_kit, bgcolor=ft.Colors.AMBER_600, color=ft.Colors.BLACK)
            ]
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def export_csv(self, e):
        conn = get_db_connection()
        c = conn.cursor()

        c.execute('''
            SELECT p.name, p.description, p.is_kit, p.base_price,
                   pc.material_id, pc.width_cm, pc.height_cm, pc.machine_time_min, pc.manual_time_min, pc.extra_costs,
                   m.cost_per_cm2, m.name as mat_name
            FROM products p
            LEFT JOIN product_components pc ON p.id = pc.product_id
            LEFT JOIN materials m ON pc.material_id = m.id
            WHERE p.is_kit = 0
            ORDER BY p.name
        ''')
        products = c.fetchall()

        c.execute('SELECT * FROM products WHERE is_kit = 1 ORDER BY name')
        kits = c.fetchall()
        conn.close()

        exports_dir = os.path.join(os.getcwd(), "exports")
        if not os.path.exists(exports_dir):
            os.makedirs(exports_dir)

        filename = f"catalog_export_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        filepath = os.path.join(exports_dir, filename)

        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Tipo", "Nome", "Descrição", "Custo Base", "Preço de Venda Est."])

            for p in products:
                cost = self._calculate_product_cost(p)
                price = cost * 2.0
                writer.writerow(["Produto", p['name'], p['description'] or '', f"{cost:.2f}", f"{price:.2f}"])

            for k in kits:
                cost = self._calculate_kit_cost(k['id'])
                price = cost * 2.0
                if k['kit_discount_type'] == 'Fixed':
                    price -= k['kit_discount_value']
                elif k['kit_discount_type'] == 'Percentage':
                    price *= (1 - (k['kit_discount_value'] / 100.0))
                writer.writerow(["Kit", k['name'], k['description'] or '', f"{cost:.2f}", f"{price:.2f}"])

        self.page.overlay.append(ft.SnackBar(ft.Text(f"Exportado para {filename}"), bgcolor=ft.Colors.GREEN_700, open=True))
        self.page.run_task(self.page.launch_url, f"/{filename}")
        self.page.update()

    def build_content(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Catálogo de Produtos", size=24, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.ElevatedButton("Exportar CSV", icon=ft.Icons.DOWNLOAD, on_click=self.export_csv, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
                        ft.ElevatedButton("Criar Kit", icon=ft.Icons.LIBRARY_ADD, on_click=self.show_add_kit_dialog, bgcolor=ft.Colors.AMBER_400, color=ft.Colors.BLACK),
                        ft.ElevatedButton("Adicionar Produto", icon=ft.Icons.ADD, on_click=self.show_add_product_dialog, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
                    ])
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text("Os preços se ajustam automaticamente quando os custos operacionais ou de materiais mudam nos Módulos 1 e 2.", italic=True, size=12),
                ft.Divider(),
                self.catalog_list
            ], expand=True),
            padding=20,
            expand=True
        )
