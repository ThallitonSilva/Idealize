import flet as ft
from ui.base_view import BaseView
from database import get_db_connection
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64

class DashboardView(BaseView):
    def __init__(self, page: ft.Page):
        super().__init__(page, "/", "Dashboard")

    def build_content(self):
        conn = get_db_connection()
        c = conn.cursor()

        # Key metrics
        c.execute("SELECT SUM(total_price) as rev FROM quotes WHERE status = 'Approved'")
        rev_row = c.fetchone()
        revenue = rev_row['rev'] if rev_row and rev_row['rev'] else 0.0

        c.execute("SELECT COUNT(*) as cnt FROM quotes WHERE status = 'Approved'")
        approved_count = c.fetchone()['cnt']

        c.execute("SELECT COUNT(*) as cnt FROM quotes WHERE status IN ('Draft', 'Sent')")
        open_count = c.fetchone()['cnt']

        # Top 5 products sold
        c.execute('''
            SELECT qi.description, SUM(qi.quantity) as total_qty
            FROM quote_items qi
            JOIN quotes q ON qi.quote_id = q.id
            WHERE q.status = 'Approved'
            GROUP BY qi.description
            ORDER BY total_qty DESC
            LIMIT 5
        ''')
        top_products = c.fetchall()

        conn.close()

        # Generate a simple chart if data exists
        chart_image = None
        if top_products:
            labels = [p['description'][:15] + "..." if len(p['description']) > 15 else p['description'] for p in top_products]
            values = [p['total_qty'] for p in top_products]

            fig, ax = plt.subplots(figsize=(5, 3))
            ax.bar(labels, values, color='#1976D2')
            ax.set_title('Top 5 Products Sold')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            buf = BytesIO()
            fig.savefig(buf, format='png')
            buf.seek(0)
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)

            chart_image = ft.Image(src_base64=img_str, width=500, height=300)

        top_prod_controls = [ft.Text("Top 5 Products", weight=ft.FontWeight.BOLD)]
        for i, p in enumerate(top_products):
            top_prod_controls.append(ft.Text(f"{i+1}. {p['description']} (Qty: {p['total_qty']})"))

        if not top_products:
            top_prod_controls.append(ft.Text("No sales data yet."))

        return ft.Container(
            content=ft.ListView([
                ft.Text(f"Welcome back, {self.username}!", size=30, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row([
                    self._create_metric_card("Total Revenue", f"R$ {revenue:,.2f}", ft.Icons.MONEY, ft.Colors.GREEN_700),
                    self._create_metric_card("Approved Quotes", str(approved_count), ft.Icons.CHECK_CIRCLE, ft.Colors.BLUE_700),
                    self._create_metric_card("Open Quotes", str(open_count), ft.Icons.PENDING_ACTIONS, ft.Colors.ORANGE_700),
                ], alignment=ft.MainAxisAlignment.START, spacing=20),
                ft.Container(height=30),
                ft.Row([
                    ft.Column(top_prod_controls, expand=1),
                    ft.Container(content=chart_image, expand=2) if chart_image else ft.Container()
                ], vertical_alignment=ft.CrossAxisAlignment.START)
            ]),
            padding=20,
            expand=True
        )

    def _create_metric_card(self, title, value, icon, color):
        return ft.Card(
            content=ft.Container(
                content=ft.Row([
                    ft.Icon(icon, size=40, color=color),
                    ft.Column([
                        ft.Text(title, size=14, color=ft.Colors.GREY_700),
                        ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=color)
                    ])
                ]),
                padding=20,
                width=250
            )
        )
