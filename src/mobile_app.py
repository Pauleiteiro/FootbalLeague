import flet as ft
import requests

API_URL = "http://127.0.0.1:8000"

def main(page: ft.Page):
    # Mobile Screen configs
    page.title = "Terças FC"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 370
    page.window_height = 700


    # Functions ( Communicate with API)

    def create_player(e):
        name = name.input.value
        if not name:
            page.snack_bar = ft.SnackBar(ft.Text("Escreve um nome!"))
            page.snack_bar.open = True
            page.update()
            return

        try:
            # Backend request
            response = requests.post(f"{API_URL}/players", json={"name": name})

            if response.status_code == 200:
                page.snack_bar = ft.SnackBar(ft.Text(f"Jogador {name} criado! ✅"))
                name_input.value = ""

            else:
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro. Jogador já criado. ❌"))

        except:
            page.snack_bar = ft.SnackBar(ft.Text("Erro de conexão ao servidor. ⚠️"))

        page.snack_bar.open = True
        page.update()

    # --- UI ---

    # Title
    title = ft.Text("Gestão de liga ⚽", size = 30, weight="bold")
