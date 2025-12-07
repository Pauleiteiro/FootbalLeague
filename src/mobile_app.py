import flet as ft
import requests
import datetime

# Configuration: API Backend URL
API_URL = "http://127.0.0.1:8000"

def main(page: ft.Page):
    # --- APP CONFIGURATION ---
    page.title = "Terças FC App"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 400
    page.window_height = 800
    page.padding = 15
    # scroll="auto" helps on smaller screens
    page.scroll = ft.ScrollMode.AUTO

    # --- BACKEND COMMUNICATION LOGIC ---
    def get_data_from_api(endpoint):
        """Fetches data from the FastAPI backend."""
        try:
            res = requests.get(f"{API_URL}/{endpoint}")
            return res.json() if res.status_code == 200 else []
        except Exception as e:
            print(f"Connection Error: {e}")
            return []

    # --- LOGIC: RESET CHAMPIONSHIP (DANGER ZONE) ---
    def confirm_reset(e):
        """Sends the DELETE request to clear all matches."""
        try:
            res = requests.delete(f"{API_URL}/reset/")
            if res.status_code == 200:
                page.dialog.open = False
                page.update()

                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Campeonato Reiniciado! 🆕"),
                    bgcolor=ft.colors.GREEN
                )
                page.snack_bar.open = True

                # Refresh table (it will be empty now)
                update_leaderboard()
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Erro ao reiniciar"), bgcolor=ft.colors.RED)
                page.snack_bar.open = True
                page.update()
        except Exception as error:
            print(error)

    def close_dialog(e):
        page.dialog.open = False
        page.update()

    # The Pop-up Window for Reset Confirmation
    reset_dialog = ft.AlertDialog(
        title=ft.Text("Reiniciar Campeonato? ⚠️"),
        content=ft.Text("Isto vai apagar TODOS os jogos e pontos.\nOs jogadores mantêm-se.\nTem a certeza?"),
        actions=[
            ft.TextButton("Cancelar", on_click=close_dialog),
            ft.TextButton("Sim, Apagar Tudo", on_click=confirm_reset, style=ft.ButtonStyle(color=ft.colors.RED)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def open_reset_dialog(e):
        page.dialog = reset_dialog
        reset_dialog.open = True
        page.update()

    # --- UI COMPONENTS: LEADERBOARD TAB ---

    # 1. The Data Table (Visuals)
    # FIX: Removed 'width' argument to prevent errors on older Flet versions
    leaderboard_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Pos")),
            ft.DataColumn(ft.Text("Nome")),
            ft.DataColumn(ft.Text("PTS"), numeric=True, tooltip="Pontos"),
            ft.DataColumn(ft.Text("J"), numeric=True, tooltip="Jogos"),
            ft.DataColumn(ft.Text("V"), numeric=True, tooltip="Vitórias"),
            ft.DataColumn(ft.Text("E"), numeric=True, tooltip="Empates"),
            ft.DataColumn(ft.Text("D"), numeric=True, tooltip="Derrotas"),
        ],
        rows=[],
        column_spacing=15,
        heading_row_height=40,
    )

    def update_leaderboard():
        """Fetches fresh data and rebuilds the table rows."""
        data = get_data_from_api("table/")

        # Clear existing rows
        leaderboard_table.rows.clear()

        # Populate with new data
        for i, player in enumerate(data):
            leaderboard_table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(i + 1))), # Rank
                    ft.DataCell(ft.Text(player['name'], size=13, weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(str(player['points']), color=ft.colors.YELLOW, weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(str(player['games_played']))),
                    ft.DataCell(ft.Text(str(player['wins']), color=ft.colors.GREEN)),
                    ft.DataCell(ft.Text(str(player['draws']), color=ft.colors.BLUE)),
                    ft.DataCell(ft.Text(str(player['losses']), color=ft.colors.RED)),
                ])
            )
        page.update()

    # 2. Rules Section (Static Text based on your PDF)
    rules_section = ft.Column([
        ft.Divider(),
        ft.Text("REGULAMENTO:", weight=ft.FontWeight.BOLD, size=16),
        ft.Text("• VITÓRIA = 3 PONTOS"),
        ft.Text("• EMPATE = 2 PONTOS"),
        ft.Text("• DERROTA = 1 PONTO"),
        ft.Text("• ÚLTIMO JOGO = PONTOS A DOBRAR", color=ft.colors.YELLOW),
        ft.Text("• FALTA COMPARÊNCIA = -3 PONTOS"),
        ft.Text("Critério Desempate: Maior nº Jogos", size=12, italic=True, color=ft.colors.GREY_400),
    ], spacing=5)

    # --- UI COMPONENTS: ADMIN TAB ---

    # Inputs for Game Registration
    team_a_input = ft.TextField(label="IDs Equipa A (ex: 1, 2)", hint_text="1, 2, 3")
    team_b_input = ft.TextField(label="IDs Equipa B (ex: 4, 5)", hint_text="4, 5, 6")

    result_dropdown = ft.Dropdown(
        label="Resultado Final",
        options=[
            ft.dropdown.Option("TEAM_A", "Vitória Equipa A"),
            ft.dropdown.Option("TEAM_B", "Vitória Equipa B"),
            ft.dropdown.Option("DRAW", "Empate"),
        ]
    )

    double_points_checkbox = ft.Checkbox(label="Último Jogo (Pontos x2)?", fill_color=ft.colors.YELLOW)

    def save_game_result(e):
        """Sends the match data to the backend."""
        try:
            # Convert string input "1, 2" into list of integers [1, 2]
            ids_a = [int(x.strip()) for x in team_a_input.value.split(",") if x.strip()]
            ids_b = [int(x.strip()) for x in team_b_input.value.split(",") if x.strip()]

            # Construct Payload
            payload = {
                "date": str(datetime.date.today()),
                "result": result_dropdown.value,
                "team_a_players": ids_a,
                "team_b_players": ids_b,
                "is_double_points": double_points_checkbox.value
            }

            # Post to API
            res = requests.post(f"{API_URL}/matches/", json=payload)

            if res.status_code == 200:
                page.snack_bar = ft.SnackBar(ft.Text("Jogo Gravado com Sucesso! ✅"), bgcolor=ft.colors.GREEN)
                team_a_input.value = ""
                team_b_input.value = ""
                update_leaderboard()
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Erro ao gravar jogo ❌"), bgcolor=ft.colors.RED)

        except Exception as error:
            page.snack_bar = ft.SnackBar(ft.Text(f"Erro técnico: {error}"), bgcolor=ft.colors.RED)

        page.snack_bar.open = True
        page.update()

    save_game_btn = ft.ElevatedButton(
        text="Gravar Resultado",
        on_click=save_game_result,
        height=50,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
    )

    # Input for Creating New Player
    new_player_input = ft.TextField(label="Nome do Novo Jogador")

    def create_player(e):
        name = new_player_input.value
        if name:
            try:
                requests.post(f"{API_URL}/players/", json={"name": name})
                page.snack_bar = ft.SnackBar(ft.Text(f"Jogador {name} criado!"), bgcolor=ft.colors.GREEN)
                new_player_input.value = ""
                page.snack_bar.open = True
                page.update()
            except:
                pass

    create_player_btn = ft.ElevatedButton("Criar Jogador", on_click=create_player)

    # Danger Zone Button
    reset_btn = ft.ElevatedButton(
        text="Reiniciar Época (Reset)",
        icon=ft.Icons.DELETE_FOREVER,
        color=ft.colors.WHITE,
        bgcolor=ft.colors.RED_700,
        on_click=open_reset_dialog
    )

    # --- MAIN LAYOUT (TABS) ---
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            # Tab 1: Leaderboard
            ft.Tab(
                text="Tabela",
                icon=ft.Icons.LEADERBOARD,
                content=ft.Column([
                    ft.Text("Classificação 🏆", size=25, weight=ft.FontWeight.BOLD),
                    # Wrap table in Row for horizontal scrolling on small phones
                    ft.Row([leaderboard_table], scroll="always"),
                    rules_section
                ], scroll=ft.ScrollMode.AUTO)
            ),
            # Tab 2: Admin Panel
            ft.Tab(
                text="Admin",
                icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                content=ft.Column([
                    ft.Text("Registar Jogo ⚽", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(height=10),
                    team_a_input,
                    team_b_input,
                    result_dropdown,
                    double_points_checkbox,
                    ft.Container(height=10),
                    save_game_btn,

                    ft.Divider(),

                    ft.Text("Gestão de Jogadores", size=16, weight=ft.FontWeight.BOLD),
                    new_player_input,
                    create_player_btn,

                    ft.Divider(),

                    ft.Text("Zona de Perigo", size=16, weight=ft.FontWeight.BOLD, color=ft.colors.RED),
                    reset_btn,
                    ft.Container(height=20)
                ], scroll=ft.ScrollMode.AUTO)
            )
        ],
        expand=True
    )

    # Add tabs to page
    page.add(tabs)

    # Initial Data Load
    update_leaderboard()

# Run the App
if __name__ == "__main__":
    ft.app(target=main)