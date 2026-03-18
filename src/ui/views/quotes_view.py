import flet as ft
from ui.base_view import BaseView
from database import get_db_connection
from datetime import datetime
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

class QuotesView(BaseView):
    def __init__(self, page: ft.Page):
        super().__init__(page, "/quotes", "Orçamentos")
        self.quotes_list = ft.ListView(expand=True, spacing=10)

        # State for new quote creation
        self.new_quote_items = []
        self.current_total_cost = 0.0
        self.current_total_price = 0.0
        self.settings = self._load_settings()

        self.status_labels = {
            'Draft': 'Rascunho',
            'Sent': 'Enviado',
            'Approved': 'Aprovado',
            'Rejected': 'Rejeitado'
        }

        self.load_quotes()

    def _load_settings(self):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT key, value FROM settings")
        s = {row['key']: row['value'] for row in c.fetchall()}
        conn.close()
        return s

    def load_quotes(self):
        self.quotes_list.controls.clear()

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            SELECT q.*, c.name as customer_name, p.name as profile_name
            FROM quotes q
            JOIN customers c ON q.customer_id = c.id
            LEFT JOIN pricing_profiles p ON q.pricing_profile_id = p.id
            ORDER BY q.created_at DESC
        ''')
        quotes = c.fetchall()
        conn.close()

        if not quotes:
            self.quotes_list.controls.append(ft.Text("Nenhum orçamento encontrado.", italic=True))
        else:
            for q in quotes:

                status_color = ft.Colors.GREY_700
                if q['status'] == 'Approved': status_color = ft.Colors.GREEN_700
                elif q['status'] == 'Rejected': status_color = ft.Colors.RED_700
                elif q['status'] == 'Sent': status_color = ft.Colors.BLUE_700

                display_status = self.status_labels.get(q['status'], q['status'])

                self.quotes_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=15,
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(f"Orçamento #{q['id']} - {q['customer_name']}", size=16, weight=ft.FontWeight.BOLD),
                                    ft.Container(content=ft.Text(display_status, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), bgcolor=status_color, padding=5, border_radius=5)
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Text(f"Data: {q['created_at']} | Perfil: {q['profile_name'] or 'Nenhum'}"),
                                ft.Text(f"Custo Total: R$ {q['total_cost']:.2f} | Preço Final: R$ {q['total_price']:.2f}", weight=ft.FontWeight.W_500) if self.role == "Admin" else ft.Text(f"Preço Final: R$ {q['total_price']:.2f}", weight=ft.FontWeight.W_500),
                                ft.Row([
                                    ft.TextButton("Enviar", on_click=lambda e, qid=q['id']: self.update_quote_status(qid, 'Sent'), visible=(q['status'] == 'Draft')),
                                    ft.TextButton("Aprovar", on_click=lambda e, qid=q['id']: self.approve_quote(qid), visible=(q['status'] in ('Draft', 'Sent'))),
                                    ft.TextButton("Rejeitar", on_click=lambda e, qid=q['id']: self.update_quote_status(qid, 'Rejected'), visible=(q['status'] in ('Draft', 'Sent'))),
                                    ft.TextButton("Duplicar", on_click=lambda e, qid=q['id']: self.version_quote(qid)),
                                    ft.TextButton("PDF", on_click=lambda e, qid=q['id']: self.generate_pdf(qid))
                                ])
                            ])
                        )
                    )
                )

    def update_quote_status(self, quote_id, new_status):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE quotes SET status = ? WHERE id = ?", (new_status, quote_id))
        conn.commit()
        conn.close()

        display_status = self.status_labels.get(new_status, new_status)
        self.page.overlay.append(ft.SnackBar(ft.Text(f"Orçamento marcado como {display_status}!"), bgcolor=ft.Colors.BLUE_700, open=True))
        self.load_quotes()
        self.page.update()

    def version_quote(self, quote_id):
        conn = get_db_connection()
        c = conn.cursor()

        c.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,))
        old_q = c.fetchone()

        if not old_q:
            conn.close()
            return

        new_version = (old_q['version'] or 1) + 1

        c.execute('''
            INSERT INTO quotes (customer_id, created_at, status, total_cost, total_price, pricing_profile_id, version, original_quote_id)
            VALUES (?, datetime('now', 'localtime'), 'Draft', ?, ?, ?, ?, ?)
        ''', (old_q['customer_id'], old_q['total_cost'], old_q['total_price'], old_q['pricing_profile_id'], new_version, quote_id))

        new_q_id = c.lastrowid

        c.execute("SELECT * FROM quote_items WHERE quote_id = ?", (quote_id,))
        old_items = c.fetchall()

        for item in old_items:
            c.execute('''
                INSERT INTO quote_items (quote_id, material_id, description, width_cm, height_cm, machine_time_min, manual_time_min, extra_costs, item_cost, item_price, quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (new_q_id, item['material_id'], item['description'], item['width_cm'], item['height_cm'], item['machine_time_min'], item['manual_time_min'], item['extra_costs'], item['item_cost'], item['item_price'], item['quantity']))

        conn.commit()
        conn.close()

        self.page.overlay.append(ft.SnackBar(ft.Text(f"Nova versão de rascunho criada!"), bgcolor=ft.Colors.GREEN_700, open=True))
        self.load_quotes()
        self.page.update()

    def approve_quote(self, quote_id):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE quotes SET status = 'Approved' WHERE id = ?", (quote_id,))
        c.execute('''
            INSERT INTO orders (quote_id, status, created_at, updated_at)
            VALUES (?, 'To Do', datetime('now', 'localtime'), datetime('now', 'localtime'))
        ''', (quote_id,))
        conn.commit()
        conn.close()

        self.page.overlay.append(ft.SnackBar(ft.Text("Orçamento Aprovado e Pedido Criado!"), bgcolor=ft.Colors.GREEN_700, open=True))
        self.load_quotes()
        self.page.update()

    def generate_pdf(self, quote_id):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            SELECT q.*, c.name, c.phone, c.email, c.address
            FROM quotes q JOIN customers c ON q.customer_id = c.id WHERE q.id = ?
        ''', (quote_id,))
        quote = c.fetchone()

        c.execute('''
            SELECT qi.*, m.name as mat_name
            FROM quote_items qi LEFT JOIN materials m ON qi.material_id = m.id
            WHERE qi.quote_id = ?
        ''', (quote_id,))
        items = c.fetchall()
        conn.close()

        exports_dir = os.path.join(os.getcwd(), "exports")
        if not os.path.exists(exports_dir):
            os.makedirs(exports_dir)

        filename = f"quote_{quote_id}.pdf"
        filepath = os.path.join(exports_dir, filename)

        pdf = canvas.Canvas(filepath, pagesize=A4)
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawString(50, 800, "Idealize Personalizados - Orçamento")

        pdf.setFont("Helvetica", 12)
        pdf.drawString(50, 770, f"Orçamento #{quote['id']} - Data: {quote['created_at']}")
        pdf.drawString(50, 750, f"Cliente: {quote['name']}")
        pdf.drawString(50, 735, f"Telefone: {quote['phone']} | E-mail: {quote['email']}")

        y = 700
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "Descrição")
        pdf.drawString(300, y, "Qtd")
        pdf.drawString(350, y, "Preço Unit.")
        pdf.drawString(450, y, "Total")
        y -= 20

        pdf.setFont("Helvetica", 10)
        for item in items:
            desc = item['description'] or item['mat_name'] or 'Item'
            pdf.drawString(50, y, desc)
            pdf.drawString(300, y, str(item['quantity']))
            pdf.drawString(350, y, f"R$ {item['item_price']:.2f}")
            pdf.drawString(450, y, f"R$ {(item['item_price'] * item['quantity']):.2f}")
            y -= 20

        y -= 20
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(300, y, f"TOTAL FINAL: R$ {quote['total_price']:.2f}")

        pdf.save()

        self.page.overlay.append(ft.SnackBar(ft.Text(f"PDF Gerado: {filename}"), bgcolor=ft.Colors.GREEN_700, open=True))
        self.page.run_task(self.page.launch_url, f"/{filename}")
        self.page.update()

    def save_item_to_catalog(self, item_dict):
        conn = get_db_connection()
        c = conn.cursor()

        c.execute("INSERT INTO products (name, description, is_kit) VALUES (?, ?, 0)", (item_dict['description'], item_dict['description']))
        prod_id = c.lastrowid

        c.execute('''
            INSERT INTO product_components (product_id, material_id, width_cm, height_cm, machine_time_min, manual_time_min, extra_costs)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (prod_id, item_dict['material_id'], float(item_dict['width_cm'] or 0), float(item_dict['height_cm'] or 0), float(item_dict['machine_time_min'] or 0), float(item_dict['manual_time_min'] or 0), float(item_dict['extra_costs'] or 0)))

        conn.commit()
        conn.close()

        self.page.overlay.append(ft.SnackBar(ft.Text("Item salvo no Catálogo como um novo Produto!"), bgcolor=ft.Colors.GREEN_700, open=True))
        self.page.update()

    def show_create_quote_view(self, e):
        self.new_quote_items = []
        self.current_total_cost = 0.0
        self.current_total_price = 0.0

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, name FROM customers ORDER BY name")
        customers = c.fetchall()
        c.execute("SELECT id, name, cost_per_cm2 FROM materials ORDER BY name")
        materials = c.fetchall()
        c.execute("SELECT id, name, markup_multiplier, profit_margin_percent FROM pricing_profiles")
        profiles = c.fetchall()
        conn.close()

        self.materials_data = {str(m['id']): m['cost_per_cm2'] for m in materials}

        customer_dropdown = ft.Dropdown(
            label="Selecionar Cliente",
            options=[ft.dropdown.Option(str(c['id']), c['name']) for c in customers],
            width=300
        )
        profile_dropdown = ft.Dropdown(
            label="Perfil de Preço",
            options=[ft.dropdown.Option(str(p['id']), p['name']) for p in profiles],
            width=300
        )

        items_listview = ft.ListView(height=200, spacing=5)

        total_cost_text = ft.Text("Custo Total: R$ 0.00", weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700, visible=(self.role == "Admin"))
        total_price_text = ft.Text("Preço Final: R$ 0.00", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700, size=18)

        def recalc_totals():
            self.current_total_cost = sum(item['item_cost'] * item['quantity'] for item in self.new_quote_items)

            # Apply profile modifier
            prof_id = profile_dropdown.value
            multiplier = 1.0
            if prof_id:
                prof = next((p for p in profiles if str(p['id']) == prof_id), None)
                if prof and prof['markup_multiplier']:
                    multiplier = float(prof['markup_multiplier'])

            tax_rate = float(self.settings.get('tax_rate_percent', '0')) / 100.0

            self.current_total_price = (self.current_total_cost * multiplier) * (1 + tax_rate)

            total_cost_text.value = f"Custo Total: R$ {self.current_total_cost:.2f}"
            total_price_text.value = f"Preço Final: R$ {self.current_total_price:.2f}"
            self.page.update()

        profile_dropdown.on_change = lambda e: recalc_totals()

        def add_item_dialog(e):
            mat_dd = ft.Dropdown(label="Material", options=[ft.dropdown.Option(str(m['id']), m['name']) for m in materials])
            w_input = ft.TextField(label="Largura (cm)", keyboard_type=ft.KeyboardType.NUMBER)
            h_input = ft.TextField(label="Altura (cm)", keyboard_type=ft.KeyboardType.NUMBER)
            mach_input = ft.TextField(label="Tempo de Máquina (min)", keyboard_type=ft.KeyboardType.NUMBER)
            man_input = ft.TextField(label="Tempo Manual (min)", keyboard_type=ft.KeyboardType.NUMBER)
            extra_input = ft.TextField(label="Custos Extras (R$)", keyboard_type=ft.KeyboardType.NUMBER)
            qty_input = ft.TextField(label="Quantidade", value="1", keyboard_type=ft.KeyboardType.NUMBER)

            live_cost = ft.Text("Custo do Item: R$ 0.00", weight=ft.FontWeight.BOLD, visible=(self.role == "Admin"))

            def calc_item_cost(e_event):
                try:
                    mat_id = mat_dd.value
                    w = float(w_input.value or 0)
                    h = float(h_input.value or 0)
                    mach_time = float(mach_input.value or 0)
                    man_time = float(man_input.value or 0)
                    extra = float(extra_input.value or 0)

                    cost_cm2 = self.materials_data.get(mat_id, 0.0) if mat_id else 0.0
                    loss_factor = float(self.settings.get('global_loss_factor_percent', '10')) / 100.0
                    mach_cost_min = float(self.settings.get('machine_minute_cost_cached', '0'))
                    man_cost_min = float(self.settings.get('labor_minute_cost', '0'))

                    area = w * h
                    mat_cost = area * cost_cm2 * (1 + loss_factor)
                    op_cost = (mach_time * mach_cost_min) + (man_time * man_cost_min)

                    total = mat_cost + op_cost + extra
                    live_cost.value = f"Custo do Item: R$ {total:.2f}"
                    self.page.update()
                    return total
                except Exception:
                    return 0.0

            # Bind real-time calc
            for ctrl in [mat_dd, w_input, h_input, mach_input, man_input, extra_input]:
                ctrl.on_change = calc_item_cost

            dlg = None

            def save_item(e):
                cost = calc_item_cost(None)
                qty = int(qty_input.value or 1)

                # Fetch mat name
                mat_name = next((m['name'] for m in materials if str(m['id']) == mat_dd.value), "Item Personalizado")
                desc = f"{mat_name} ({w_input.value}x{h_input.value}cm)"

                item_dict = {
                    'material_id': mat_dd.value,
                    'description': desc,
                    'width_cm': w_input.value,
                    'height_cm': h_input.value,
                    'machine_time_min': mach_input.value,
                    'manual_time_min': man_input.value,
                    'extra_costs': extra_input.value,
                    'item_cost': cost,
                    'item_price': cost, # base price, modifier applied at quote level
                    'quantity': qty
                }
                self.new_quote_items.append(item_dict)

                items_listview.controls.append(
                    ft.ListTile(
                        title=ft.Text(desc),
                        subtitle=ft.Text(f"Qtd: {qty} | Custo/un: R$ {cost:.2f}") if self.role == "Admin" else ft.Text(f"Qtd: {qty}"),
                        trailing=ft.IconButton(ft.Icons.SAVE, tooltip="Salvar como Produto no Catálogo", on_click=lambda e, i=item_dict: self.save_item_to_catalog(i))
                    )
                )
                recalc_totals()

                dlg.open = False
                self.page.update()

            def close_add_item(e):
                dlg.open = False
                self.page.update()

            dlg = ft.AlertDialog(
                title=ft.Text("Adicionar Item ao Orçamento"),
                content=ft.Column([mat_dd, ft.Row([w_input, h_input]), ft.Row([mach_input, man_input]), ft.Row([extra_input, qty_input]), live_cost], tight=True),
                actions=[
                    ft.TextButton("Cancelar", on_click=close_add_item),
                    ft.ElevatedButton("Adicionar", on_click=save_item)
                ]
            )
            self.page.overlay.append(dlg)
            dlg.open = True
            self.page.update()

        main_dlg = None

        def save_quote(e):
            if not customer_dropdown.value:
                self.page.overlay.append(ft.SnackBar(ft.Text("Selecione um cliente!"), bgcolor=ft.Colors.RED_700, open=True))
                self.page.update()
                return
            if not self.new_quote_items:
                self.page.overlay.append(ft.SnackBar(ft.Text("Adicione pelo menos um item!"), bgcolor=ft.Colors.RED_700, open=True))
                self.page.update()
                return

            conn = get_db_connection()
            c = conn.cursor()

            c.execute('''
                INSERT INTO quotes (customer_id, created_at, status, total_cost, total_price, pricing_profile_id)
                VALUES (?, datetime('now', 'localtime'), 'Draft', ?, ?, ?)
            ''', (customer_dropdown.value, self.current_total_cost, self.current_total_price, profile_dropdown.value))

            quote_id = c.lastrowid

            for item in self.new_quote_items:
                c.execute('''
                    INSERT INTO quote_items (quote_id, material_id, description, width_cm, height_cm, machine_time_min, manual_time_min, extra_costs, item_cost, item_price, quantity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (quote_id, item['material_id'], item['description'], float(item['width_cm'] or 0), float(item['height_cm'] or 0), float(item['machine_time_min'] or 0), float(item['manual_time_min'] or 0), float(item['extra_costs'] or 0), float(item['item_cost'] or 0), float(item['item_price'] or 0), int(item['quantity'] or 1)))

            conn.commit()
            conn.close()

            main_dlg.open = False
            self.load_quotes()
            self.page.update()

        def cancel_quote(e):
            main_dlg.open = False
            self.page.update()

        main_dlg = ft.AlertDialog(
            title=ft.Text("Criar Novo Orçamento"),
            content=ft.Container(
                width=600,
                content=ft.Column([
                    ft.Row([customer_dropdown, profile_dropdown]),
                    ft.Divider(),
                    ft.Row([ft.Text("Itens", weight=ft.FontWeight.BOLD), ft.ElevatedButton("Adicionar Item", on_click=add_item_dialog, icon=ft.Icons.ADD)]),
                    items_listview,
                    ft.Divider(),
                    ft.Row([total_cost_text, total_price_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ], tight=True)
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=cancel_quote),
                ft.ElevatedButton("Salvar Orçamento", on_click=save_quote, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
            ]
        )
        self.page.overlay.append(main_dlg)
        main_dlg.open = True
        self.page.update()

    def build_content(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Orçamentos", size=24, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("Criar Orçamento", icon=ft.Icons.ADD, on_click=self.show_create_quote_view, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                self.quotes_list
            ], expand=True),
            padding=20,
            expand=True
        )
