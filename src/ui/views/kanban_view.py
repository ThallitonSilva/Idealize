import flet as ft
from ui.base_view import BaseView
from database import get_db_connection

class KanbanView(BaseView):
    def __init__(self, page: ft.Page):
        super().__init__(page, "/kanban", "Quadro Kanban")

        self.statuses = ['To Do', 'In Production', 'In Finishing', 'Ready for Delivery', 'Completed']
        self.status_labels = {
            'To Do': 'A Fazer',
            'In Production': 'Em Produção',
            'In Finishing': 'Em Acabamento',
            'Ready for Delivery': 'Pronto para Entrega',
            'Completed': 'Concluído'
        }
        # Instead of storing columns in a dict and updating them, we will rebuild the board each time
        self.load_orders()

    def load_orders(self):
        self.board_columns = {s: [] for s in self.statuses}

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            SELECT o.*, q.total_price, c.name as customer_name
            FROM orders o
            JOIN quotes q ON o.quote_id = q.id
            JOIN customers c ON q.customer_id = c.id
            ORDER BY o.created_at DESC
        ''')
        orders = c.fetchall()

        order_items = {}
        for o in orders:
            c.execute('SELECT description, quantity FROM quote_items WHERE quote_id = ?', (o['quote_id'],))
            order_items[o['id']] = c.fetchall()

        conn.close()

        for o in orders:
            status = o['status']
            if status in self.board_columns:

                items_text = "\n".join([f"- {i['quantity']}x {i['description']}" for i in order_items[o['id']]])

                card_content = ft.Container(
                    width=250,
                    padding=15,
                    border_radius=8,
                    bgcolor=ft.Colors.WHITE,
                    border=ft.Border.all(1, ft.Colors.GREY_300),
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=3, color=ft.Colors.GREY_400),
                    content=ft.Column([
                        ft.Text(f"Pedido #{o['id']}", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                        ft.Text(f"Cliente: {o['customer_name']}", weight=ft.FontWeight.W_600),
                        ft.Text(items_text, size=12, color=ft.Colors.GREY_700),
                        ft.Divider(height=1, color=ft.Colors.GREY_200),
                        ft.Text(f"Valor: R$ {o['total_price']:.2f}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
                    ], spacing=5)
                )

                draggable_card = ft.Draggable(
                    group="orders",
                    data=str(o['id']), # Data must be string for easier handling
                    content=card_content,
                    content_feedback=ft.Container(
                        width=250, padding=15, border_radius=8, bgcolor=ft.Colors.BLUE_100,
                        border=ft.Border.all(2, ft.Colors.BLUE_700),
                        content=ft.Text(f"Movendo Pedido #{o['id']}", weight=ft.FontWeight.BOLD)
                    )
                )

                self.board_columns[status].append(draggable_card)

    def handle_accept(self, e: ft.DragTargetEvent):
        order_id = int(e.page.get_control(e.src_id).data)
        new_status = e.control.data

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            UPDATE orders
            SET status = ?, updated_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (new_status, order_id))
        conn.commit()
        conn.close()

        self.load_orders()
        self.page.go("/kanban") # Refresh the view to redraw the board
        self.page.update()

    def build_content(self):
        kanban_board = ft.Row(
            spacing=20,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START,
            expand=True,
            scroll=ft.ScrollMode.AUTO
        )

        colors_map = {
            'To Do': ft.Colors.GREY_200,
            'In Production': ft.Colors.AMBER_100,
            'In Finishing': ft.Colors.PURPLE_100,
            'Ready for Delivery': ft.Colors.BLUE_100,
            'Completed': ft.Colors.GREEN_100
        }

        for status in self.statuses:
            target_column = ft.DragTarget(
                group="orders",
                data=status,
                on_accept=self.handle_accept,
                content=ft.Container(
                    width=280,
                    padding=10,
                    border_radius=10,
                    bgcolor=colors_map[status],
                    content=ft.Column([
                        ft.Container(
                            padding=10,
                            bgcolor=ft.Colors.WHITE,
                            border_radius=8,
                            content=ft.Text(self.status_labels[status], weight=ft.FontWeight.BOLD, size=16, text_align="center")
                        ),
                        ft.Column(self.board_columns[status], spacing=10, scroll=ft.ScrollMode.AUTO)
                    ], expand=True, spacing=15),
                    expand=True
                )
            )
            kanban_board.controls.append(target_column)

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Kanban de Produção", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text("Arraste e solte os pedidos para atualizar o status.", italic=True, color=ft.Colors.GREY_700)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                ft.Container(content=kanban_board, expand=True)
            ], expand=True),
            padding=20,
            expand=True
        )
