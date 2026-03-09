import flet as ft
from ui.base_view import BaseView
from database import get_db_connection

class SettingsView(BaseView):
    def __init__(self, page: ft.Page):
        super().__init__(page, "/settings", "Settings")
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
            label="Global Loss Factor (%)",
            value=settings_dict.get('global_loss_factor_percent', '10'),
            keyboard_type=ft.KeyboardType.NUMBER
        )

        # Labor Minute Cost
        self.labor_cost_input = ft.TextField(
            label="Labor Minute Cost (R$)",
            value=settings_dict.get('labor_minute_cost', '0.50'),
            keyboard_type=ft.KeyboardType.NUMBER
        )

        # Machine Minute Cost calculation fields
        self.machine_cost_input = ft.TextField(label="Machine Cost (R$)", value=settings_dict.get('machine_monthly_cost', '0'))
        self.machine_life_input = ft.TextField(label="Useful Life (Months)", value=settings_dict.get('machine_useful_life_months', '60'))
        self.energy_kwh_input = ft.TextField(label="Energy Consumption (kW/h)", value=settings_dict.get('machine_energy_kwh', '0'))
        self.kwh_cost_input = ft.TextField(label="Cost per kWh (R$)", value=settings_dict.get('kwh_cost', '0'))
        self.working_hours_input = ft.TextField(label="Monthly Working Hours", value=settings_dict.get('machine_monthly_hours', '160'))
        self.maintenance_input = ft.TextField(label="Monthly Maintenance (R$)", value=settings_dict.get('machine_maintenance_cost', '0'))
        self.other_fixed_input = ft.TextField(label="Other Fixed Costs (R$)", value=settings_dict.get('other_fixed_costs', '0'))

        self.machine_minute_cost_display = ft.Text(
            f"Calculated Machine Minute Cost: R$ {settings_dict.get('machine_minute_cost_cached', '0.00')}",
            weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_700
        )

        # Taxes
        self.tax_rate_input = ft.TextField(
            label="Global Tax Rate (e.g., ISS %)",
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

            self.machine_minute_cost_display.value = f"Calculated Machine Minute Cost: R$ {minute_cost:.4f}"
            self.page.update()
            return minute_cost
        except ValueError:
            self.machine_minute_cost_display.value = "Error: Invalid input values."
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
        self.page.overlay.append(ft.SnackBar(ft.Text("Settings saved successfully!"), bgcolor=ft.colors.GREEN_700, open=True))
        self.page.update()

    def update_content(self):
        profiles_list = ft.ListView(height=150, spacing=5)
        for p in self.profiles:
            profiles_list.controls.append(
                ft.ListTile(
                    title=ft.Text(p['name']),
                    subtitle=ft.Text(f"Markup: {p['markup_multiplier']}x | Margin: {p['profit_margin_percent']}%")
                )
            )

        self.content_container = ft.Container(
            content=ft.ListView(
                [
                    ft.Text("General Settings", size=24, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Row([self.loss_factor_input, self.labor_cost_input, self.tax_rate_input]),

                    ft.Text("Machine Minute Cost Calculation", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Row([self.machine_cost_input, self.machine_life_input]),
                    ft.Row([self.energy_kwh_input, self.kwh_cost_input, self.working_hours_input]),
                    ft.Row([self.maintenance_input, self.other_fixed_input]),
                    ft.ElevatedButton("Recalculate", on_click=self.calculate_machine_cost),
                    self.machine_minute_cost_display,

                    ft.Text("Pricing Profiles", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    profiles_list,

                    ft.Container(height=20),
                    ft.ElevatedButton("Save All Settings", on_click=self.save_settings, bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE, width=200)
                ],
                expand=True,
                spacing=10
            ),
            padding=20,
            expand=True
        )

    def build_content(self):
        return self.content_container
