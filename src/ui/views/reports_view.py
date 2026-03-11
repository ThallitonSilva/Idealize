import flet as ft
from ui.base_view import BaseView
from database import get_db_connection
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import csv
import os
from datetime import datetime

class ReportsView(BaseView):
    def __init__(self, page: ft.Page):
        super().__init__(page, "/reports", "Relatórios")

    def build_content(self):
        conn = get_db_connection()
        c = conn.cursor()

        # Profitability by Customer
        c.execute('''
            SELECT c.name, SUM(q.total_price) as revenue, SUM(q.total_cost) as costs, SUM(q.total_price - q.total_cost) as profit
            FROM quotes q
            JOIN customers c ON q.customer_id = c.id
            WHERE q.status = 'Approved'
            GROUP BY c.name
            ORDER BY profit DESC
        ''')
        profit_by_cust = c.fetchall()

        # Input Price Evolution (Simple average per month)
        c.execute('''
            SELECT m.name, strftime('%Y-%m', p.purchase_date) as month, AVG(p.cost_price / (m.area_cm2 * p.quantity)) as avg_cost_cm2
            FROM purchases p
            JOIN materials m ON p.material_id = m.id
            WHERE m.area_cm2 > 0
            GROUP BY m.name, month
            ORDER BY m.name, month
        ''')
        price_evolution = c.fetchall()

        # Supplier Price Comparison
        c.execute('''
            SELECT m.name as mat_name, s.name as sup_name, AVG(p.cost_price / (m.area_cm2 * p.quantity)) as avg_cost_cm2
            FROM purchases p
            JOIN materials m ON p.material_id = m.id
            JOIN suppliers s ON p.supplier_id = s.id
            WHERE m.area_cm2 > 0
            GROUP BY m.name, s.name
            ORDER BY m.name, avg_cost_cm2
        ''')
        supplier_comparison = c.fetchall()

        conn.close()

        # Profitability Table
        dt_columns = [
            ft.DataColumn(ft.Text("Cliente")),
            ft.DataColumn(ft.Text("Receita (R$)", text_align="right")),
            ft.DataColumn(ft.Text("Custos (R$)", text_align="right")),
            ft.DataColumn(ft.Text("Lucro (R$)", text_align="right"))
        ]

        dt_rows = []
        for row in profit_by_cust:
            dt_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(row['name'])),
                        ft.DataCell(ft.Text(f"{row['revenue']:.2f}")),
                        ft.DataCell(ft.Text(f"{row['costs']:.2f}")),
                        ft.DataCell(ft.Text(f"{row['profit']:.2f}", color=ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD)),
                    ]
                )
            )

        profit_table = ft.DataTable(columns=dt_columns, rows=dt_rows) if dt_rows else ft.Text("Nenhum dado disponível.")

        # Price Evolution Chart
        chart_image = None
        if price_evolution:
            df = pd.DataFrame(price_evolution, columns=['name', 'month', 'avg_cost_cm2'])
            fig, ax = plt.subplots(figsize=(8, 4))
            for name, group in df.groupby('name'):
                ax.plot(group['month'], group['avg_cost_cm2'], marker='o', label=name)

            ax.set_title('Evolução do Custo do Material por cm²')
            ax.set_xlabel('Mês')
            ax.set_ylabel('Custo Médio / cm² (R$)')
            plt.xticks(rotation=45)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.tight_layout()

            buf = BytesIO()
            fig.savefig(buf, format='png')
            buf.seek(0)
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)

            chart_image = ft.Image(src_base64=img_str, width=800, height=400)

        # Supplier Comparison Chart
        supplier_chart_image = None
        if supplier_comparison:
            df_sup = pd.DataFrame(supplier_comparison, columns=['mat_name', 'sup_name', 'avg_cost_cm2'])

            # Pivot table to make plotting grouped bars easier
            pivot_df = df_sup.pivot(index='mat_name', columns='sup_name', values='avg_cost_cm2')

            fig2, ax2 = plt.subplots(figsize=(8, 4))
            pivot_df.plot(kind='bar', ax=ax2)

            ax2.set_title('Custo do Material por Fornecedor')
            ax2.set_xlabel('Material')
            ax2.set_ylabel('Custo Médio / cm² (R$)')
            plt.xticks(rotation=45, ha='right')
            ax2.legend(title='Fornecedor', bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.tight_layout()

            buf2 = BytesIO()
            fig2.savefig(buf2, format='png')
            buf2.seek(0)
            img_str2 = base64.b64encode(buf2.read()).decode('utf-8')
            plt.close(fig2)

            supplier_chart_image = ft.Image(src_base64=img_str2, width=800, height=400)

        def export_csv(e):
            exports_dir = os.path.join(os.getcwd(), "exports")
            if not os.path.exists(exports_dir):
                os.makedirs(exports_dir)

            filename = f"relatorio_lucratividade_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
            filepath = os.path.join(exports_dir, filename)

            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Cliente", "Receita", "Custos", "Lucro"])
                for row in profit_by_cust:
                    writer.writerow([row['name'], f"{row['revenue']:.2f}", f"{row['costs']:.2f}", f"{row['profit']:.2f}"])

            self.page.overlay.append(ft.SnackBar(ft.Text(f"Exportado para {filename}"), bgcolor=ft.Colors.GREEN_700, open=True))
            self.page.launch_url(f"/{filename}")
            self.page.update()

        return ft.Container(
            content=ft.ListView([
                ft.Row([
                    ft.Text("Business Intelligence & Relatórios", size=24, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("Exportar Lucratividade para CSV", icon=ft.Icons.DOWNLOAD, on_click=export_csv, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),

                ft.Text("Lucratividade por Cliente", size=20, weight=ft.FontWeight.W_600),
                profit_table,
                ft.Container(height=30),

                ft.Text("Evolução do Preço do Insumo (Custo por cm²)", size=20, weight=ft.FontWeight.W_600),
                chart_image if chart_image else ft.Text("Nenhum dado de compra disponível para gerar gráfico."),
                ft.Container(height=30),

                ft.Text("Comparação de Preços entre Fornecedores", size=20, weight=ft.FontWeight.W_600),
                supplier_chart_image if supplier_chart_image else ft.Text("Dados insuficientes para comparar fornecedores.")
            ], expand=True, spacing=10),
            padding=20,
            expand=True
        )
