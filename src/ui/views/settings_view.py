import flet as ft
from ui.base_view import BaseView
from database import get_db_connection

class SettingsView(BaseView):
    def __init__(self, page: ft.Page):
        super().__init__(page, "/settings", "Configurações")
        self.load_settings()

    def load_settings(self):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT key, value FROM settings")
        settings_dict = {row['key']: row['value'] for row in c.fetchall()}

        c.execute("SELECT * FROM pricing_profiles")
        self.profiles = c.fetchall()
        conn.close()

        # Global Loss Factor
        self.loss_factor_input = ft.TextField(
            label="Fator de Perda Global (%)",
            value=settings_dict.get('global_loss_factor_percent', '10'),
            keyboard_type=ft.KeyboardType.NUMBER
        )

        # Labor Minute Cost
        self.labor_cost_input = ft.TextField(
            label="Custo do Minuto de Trabalho (R$)",
            value=settings_dict.get('labor_minute_cost', '0.50'),
            keyboard_type=ft.KeyboardType.NUMBER
        )

        # Machine Minute Cost calculation fields
        self.machine_cost_input = ft.TextField(label="Custo da Máquina (R$)", value=settings_dict.get('machine_monthly_cost', '0'))
        self.machine_life_input = ft.TextField(label="Vida Útil (Meses)", value=settings_dict.get('machine_useful_life_months', '60'))
        self.energy_kwh_input = ft.TextField(label="Consumo de Energia (kW/h)", value=settings_dict.get('machine_energy_kwh', '0'))
        self.kwh_cost_input = ft.TextField(label="Custo por kWh (R$)", value=settings_dict.get('kwh_cost', '0'))
        self.working_hours_input = ft.TextField(label="Horas de Trabalho Mensais", value=settings_dict.get('machine_monthly_hours', '160'))
        self.maintenance_input = ft.TextField(label="Manutenção Mensal (R$)", value=settings_dict.get('machine_maintenance_cost', '0'))
        self.other_fixed_input = ft.TextField(label="Outros Custos Fixos (R$)", value=settings_dict.get('other_fixed_costs', '0'))

        self.machine_minute_cost_display = ft.Text(
            f"Custo do Minuto de Máquina Calculado: R$ {settings_dict.get('machine_minute_cost_cached', '0.00')}",
            weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700
        )

        # Taxes
        self.tax_rate_input = ft.TextField(
            label="Taxa Global de Impostos (ex. ISS %)",
            value=settings_dict.get('tax_rate_percent', '0'),
            keyboard_type=ft.KeyboardType.NUMBER
        )

        self.update_content()

    def calculate_machine_cost(self, e=None):
        try:
            m_cost = float(self.machine_cost_input.value or 0)
            m_life = float(self.machine_life_input.value or 1)
            energy = float(self.energy_kwh_input.value or 0)
            kwh = float(self.kwh_cost_input.value or 0)
            hours = float(self.working_hours_input.value or 1)
            maint = float(self.maintenance_input.value or 0)
            fixed = float(self.other_fixed_input.value or 0)

            depreciation_monthly = m_cost / m_life if m_life > 0 else 0
            energy_monthly = energy * kwh * hours
            total_monthly = depreciation_monthly + energy_monthly + maint + fixed

            minutes = hours * 60
            minute_cost = total_monthly / minutes if minutes > 0 else 0

            self.machine_minute_cost_display.value = f"Custo do Minuto de Máquina Calculado: R$ {minute_cost:.4f}"
            self.page.update()
            return minute_cost
        except ValueError:
            self.machine_minute_cost_display.value = "Erro: Valores de entrada inválidos."
            self.page.update()
            return 0.0

    def save_settings(self, e):
        minute_cost = self.calculate_machine_cost()

        settings_to_save = {
            'global_loss_factor_percent': self.loss_factor_input.value,
            'labor_minute_cost': self.labor_cost_input.value,
            'machine_monthly_cost': self.machine_cost_input.value,
            'machine_useful_life_months': self.machine_life_input.value,
            'machine_energy_kwh': self.energy_kwh_input.value,
            'kwh_cost': self.kwh_cost_input.value,
            'machine_monthly_hours': self.working_hours_input.value,
            'machine_maintenance_cost': self.maintenance_input.value,
            'other_fixed_costs': self.other_fixed_input.value,
            'machine_minute_cost_cached': str(round(minute_cost, 4)),
            'tax_rate_percent': self.tax_rate_input.value
        }

        conn = get_db_connection()
        c = conn.cursor()
        for k, v in settings_to_save.items():
            c.execute("UPDATE settings SET value = ? WHERE key = ?", (v, k))
        conn.commit()
        conn.close()

        # Provide feedback
        self.page.overlay.append(ft.SnackBar(ft.Text("Configurações salvas com sucesso!"), bgcolor=ft.Colors.GREEN_700, open=True))
        self.page.update()

    def show_add_profile_dialog(self, e):
        dlg = None

        name_input = ft.TextField(label="Nome do Perfil")
        markup_input = ft.TextField(label="Multiplicador (Markup)", value="2.0", keyboard_type=ft.KeyboardType.NUMBER)
        margin_input = ft.TextField(label="Margem de Lucro %", value="100", keyboard_type=ft.KeyboardType.NUMBER)

        def save_profile(e):
            if not name_input.value:
                self.page.overlay.append(ft.SnackBar(ft.Text("O nome do perfil é obrigatório"), bgcolor=ft.Colors.RED, open=True))
                self.page.update()
                return

            conn = get_db_connection()
            c = conn.cursor()
            c.execute("INSERT INTO pricing_profiles (name, markup_multiplier, profit_margin_percent) VALUES (?, ?, ?)",
                      (name_input.value, float(markup_input.value or 1), float(margin_input.value or 0)))
            conn.commit()
            conn.close()

            dlg.open = False
            self.load_settings()
            self.update_content()
            self.page.go("/settings") # Refresh the view

        def close_dlg(e):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Adicionar Perfil de Preço"),
            content=ft.Column([name_input, markup_input, margin_input], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dlg),
                ft.ElevatedButton("Salvar", on_click=save_profile)
            ]
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def delete_profile(self, profile_id):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM pricing_profiles WHERE id = ?", (profile_id,))
        conn.commit()
        conn.close()

        self.load_settings()
        self.update_content()
        self.page.go("/settings") # Refresh the view

    def update_content(self):
        profiles_list = ft.ListView(height=150, spacing=5)
        for p in self.profiles:
            profiles_list.controls.append(
                ft.ListTile(
                    title=ft.Text(p['name']),
                    subtitle=ft.Text(f"Markup: {p['markup_multiplier']}x | Margem: {p['profit_margin_percent']}%"),
                    trailing=ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=lambda e, pid=p['id']: self.delete_profile(pid))
                )
            )

        self.content_container = ft.Container(
            content=ft.ListView(
                [
                    ft.Text("Configurações Gerais", size=24, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Row([self.loss_factor_input, self.labor_cost_input, self.tax_rate_input]),

                    ft.Text("Cálculo do Custo do Minuto de Máquina", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Row([self.machine_cost_input, self.machine_life_input]),
                    ft.Row([self.energy_kwh_input, self.kwh_cost_input, self.working_hours_input]),
                    ft.Row([self.maintenance_input, self.other_fixed_input]),
                    ft.ElevatedButton("Recalcular", on_click=self.calculate_machine_cost),
                    self.machine_minute_cost_display,

                    ft.Row([
                        ft.Text("Perfis de Preço", size=20, weight=ft.FontWeight.BOLD),
                        ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=ft.Colors.BLUE_700, on_click=self.show_add_profile_dialog)
                    ]),
                    ft.Divider(),
                    profiles_list,

                    ft.Container(height=20),
                    ft.ElevatedButton("Salvar Configurações", on_click=self.save_settings, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE, width=200)
                ],
                expand=True,
                spacing=10
            ),
            padding=20,
            expand=True
        )

    def build_content(self):
        return self.content_container
