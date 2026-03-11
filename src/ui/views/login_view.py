import flet as ft
from ui.base_view import BaseView
from database import get_db_connection
import hashlib

class LoginView(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__("/login", [])
        self._app_page = page

        self.username_input = ft.TextField(label="Usuário", autofocus=True)
        self.password_input = ft.TextField(label="Senha", password=True, can_reveal_password=True)
        self.error_text = ft.Text(color=ft.Colors.RED_400, visible=False)

        self.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.LOCK_PERSON, size=50, color=ft.Colors.BLUE_700),
                        ft.Text("Idealize Personalizados", size=24, weight=ft.FontWeight.BOLD),
                        self.username_input,
                        self.password_input,
                        ft.ElevatedButton("Entrar", on_click=self.login, width=200, style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)),
                        self.error_text
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True
            )
        ]

    def login(self, e):
        username = self.username_input.value
        password = self.password_input.value

        if not username or not password:
            self.show_error("Por favor, insira o usuário e a senha.")
            return

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, username, role, password_hash, salt FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user:
            salt = bytes.fromhex(user["salt"])
            computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex()

            if computed_hash == user["password_hash"]:
                self._app_page.user_id = user["id"]
                self._app_page.go("/")
                return

        self.show_error("Credenciais inválidas.")

    def show_error(self, message):
        self.error_text.value = message
        self.error_text.visible = True
        self._app_page.update()

    def get_view(self):
        return self
