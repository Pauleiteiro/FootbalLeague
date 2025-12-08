import flet as ft
import requests
import datetime
import threading
import time
import json

# =============================================================================
# CONFIGURATION
# =============================================================================
API_URL = "https://tercas-fc-api.onrender.com"

# Credentials
ADMIN_PASSWORD = "1234"      # Master Access
TREASURER_PASSWORD = "money" # Treasury Only
MANAGER_PASSWORD = "bola"    # Games Only

# =============================================================================
# MAIN APPLICATION
# =============================================================================
def main(page: ft.Page):
    # --- Page Setup ---
    page.title = "Terças FC"
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 10

    # --- App State ---
    state = {
        "role": None  # 'admin', 'treasurer', 'manager', or None
    }

    # --- Global Lists (for logic) ---
    team_a_checkboxes = []
    team_b_checkboxes = []

    # =========================================================================
    # 1. DEFINE INPUTS & CONTAINERS (Early Definition)
    # =========================================================================
    # Defining these first prevents "Unresolved reference" errors.

    # -- Treasury Inputs --
    input_payment_amount = ft.TextField(label="Valor (€)", width=100, keyboard_type=ft.KeyboardType.NUMBER)
    dropdown_payer = ft.Dropdown(label="Quem pagou?", expand=True)
    column_debt_list = ft.Column()

    # -- Admin/Game Inputs --
    column_team_a = ft.Column()
    column_team_b = ft.Column()

    dropdown_champion = ft.Dropdown(label="Quem ganhou a época?")
    dropdown_remove_champion = ft.Dropdown(label="Remover Título de quem?", expand=True)

    dropdown_result = ft.Dropdown(
        label="Resultado",
        options=[
            ft.dropdown.Option("TEAM_A", "Vitória A"),
            ft.dropdown.Option("TEAM_B", "Vitória B"),
            ft.dropdown.Option("DRAW", "Empate")
        ]
    )

    checkbox_double_points = ft.Checkbox(label="Pontos x2?", fill_color="yellow")
    input_new_player = ft.TextField(label="Novo Jogador")

    # -- History/Archive Inputs --
    dropdown_history_season = ft.Dropdown(label="Escolher Época", expand=True)
    column_history_content = ft.Column(scroll=ft.ScrollMode.AUTO)

    # -- Login Inputs --
    input_password = ft.TextField(label="Senha", password=True, on_submit=lambda e: login_handler(e))

    # =========================================================================
    # 2. HELPER FUNCTIONS
    # =========================================================================
    def show_toast(message: str, color: str = "green"):
        page.snack_bar = ft.SnackBar(content=ft.Text(message), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    def fetch_api(endpoint: str):
        try:
            response = requests.get(f"{API_URL}/{endpoint}")
            return response.json() if response.status_code == 200 else []
        except: return []

    # =========================================================================
    # 3. LOGIC HANDLERS
    # =========================================================================

    # --- Leaderboard Logic ---
    table_leaderboard = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Pos")), ft.DataColumn(ft.Text("Nome")),
            ft.DataColumn(ft.Text("P"), numeric=True), ft.DataColumn(ft.Text("J"), numeric=True),
            ft.DataColumn(ft.Text("V"), numeric=True), ft.DataColumn(ft.Text("E"), numeric=True),
            ft.DataColumn(ft.Text("D"), numeric=True),
        ], rows=[], column_spacing=5
    )

    def refresh_leaderboard():
        data = fetch_api("table/")
        table_leaderboard.rows.clear()
        for i, p in enumerate(data):
            table_leaderboard.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(i+1))), ft.DataCell(ft.Text(p['name'], weight="bold", size=13)),
                ft.DataCell(ft.Text(str(p['points']), color="yellow", weight="bold")),
                ft.DataCell(ft.Text(str(p['games_played']))), ft.DataCell(ft.Text(str(p['wins']), color="green")),
                ft.DataCell(ft.Text(str(p['draws']), color="blue")), ft.DataCell(ft.Text(str(p['losses']), color="red")),
            ]))
        page.update()

    # --- History/Champions Logic ---
    column_new_champions = ft.Column()

    def refresh_champions():
        champions = fetch_api("champions/")
        column_new_champions.controls.clear()
        dropdown_remove_champion.options.clear() # Update removal list too

        if champions:
            column_new_champions.controls.append(ft.Text("NOVOS CAMPEÕES (App):", weight="bold", size=12, color="green"))
            for c in champions:
                trophies = "🏆" * c['titles']
                column_new_champions.controls.append(
                    ft.Row([ft.Text(f"{c['name'].upper()} =", weight="bold"), ft.Text(trophies)], spacing=5)
                )
                dropdown_remove_champion.options.append(ft.dropdown.Option(c['name']))
        page.update()

    # --- Treasury Logic ---
    def refresh_treasury():
        players = fetch_api("players/all")
        column_debt_list.controls.clear(); dropdown_payer.options.clear()
        total_debt = 0.0

        for p in players:
            dropdown_payer.options.append(ft.dropdown.Option(key=str(p['id']), text=p['name']))
            balance = p['balance']
            color = "red" if balance < 0 else "green"
            if balance < 0: total_debt += balance

            column_debt_list.controls.append(ft.Row([
                ft.Text(p['name'], weight="bold"),
                ft.Text(f"{balance:.2f}€", color=color, weight="bold")
            ], alignment="spaceBetween"))

        column_debt_list.controls.append(ft.Divider())
        column_debt_list.controls.append(ft.Text(f"Total em Falta: {total_debt:.2f}€", color="red", weight="bold"))
        page.update()

    def submit_payment(e):
        if not dropdown_payer.value or not input_payment_amount.value: return
        try:
            amt = float(input_payment_amount.value)
            res = requests.post(f"{API_URL}/players/pay", json={"player_id": int(dropdown_payer.value), "amount": amt})
            if res.status_code == 200:
                show_toast("Pagamento aceite!", "green"); input_payment_amount.value=""; refresh_treasury()
            else: show_toast("Erro ao processar", "red")
        except: show_toast("Valor inválido", "red")

    # --- Admin Logic ---
    def refresh_admin_inputs():
        players = fetch_api("players/")
        column_team_a.controls.clear(); column_team_b.controls.clear()
        team_a_checkboxes.clear(); team_b_checkboxes.clear()
        dropdown_champion.options.clear()

        for p in players:
            # Checkboxes
            cba = ft.Checkbox(label=p['name'], value=False); cba.data = p['id']
            team_a_checkboxes.append(cba); column_team_a.controls.append(cba)

            cbb = ft.Checkbox(label=p['name'], value=False); cbb.data = p['id']
            team_b_checkboxes.append(cbb); column_team_b.controls.append(cbb)

            # Champion list
            dropdown_champion.options.append(ft.dropdown.Option(p['name']))

        refresh_champions() # Also refresh the removal list
        page.update()

    def submit_game(e):
        ids_a = [c.data for c in team_a_checkboxes if c.value]
        ids_b = [c.data for c in team_b_checkboxes if c.value]
        if not ids_a or not ids_b: show_toast("Falta jogadores!", "red"); return

        try:
            payload = {
                "date": str(datetime.date.today()),
                "result": dropdown_result.value,
                "team_a_players": ids_a,
                "team_b_players": ids_b,
                "is_double_points": checkbox_double_points.value
            }
            requests.post(f"{API_URL}/matches/", json=payload)
            show_toast("Jogo Gravado! (-3€)", "green")
            refresh_treasury(); refresh_leaderboard()
            # Reset
            for c in team_a_checkboxes + team_b_checkboxes: c.value = False
            page.update()
        except: show_toast("Erro ao gravar", "red")

    def create_player(e):
        if input_new_player.value:
            requests.post(f"{API_URL}/players/", json={"name": input_new_player.value})
            show_toast("Criado!", "green"); input_new_player.value=""; refresh_admin_inputs()

    def remove_champion_handler(e):
        if not dropdown_remove_champion.value: return
        try:
            requests.post(f"{API_URL}/champions/remove", json={"name": dropdown_remove_champion.value})
            show_toast("Título removido!", "orange"); refresh_champions()
        except: show_toast("Erro", "red")

    def close_season_handler(e):
        if not dropdown_champion.value: show_toast("Escolhe o Campeão!", "red"); return
        if btn_close_season.text == "Fechar Época":
            btn_close_season.text = "Tens a Certeza?"; btn_close_season.bgcolor = "orange"; page.update(); return

        try:
            requests.post(f"{API_URL}/season/close", json={"champion_name": dropdown_champion.value, "season_name": "Época"})
            show_toast("Época Fechada e Arquivada! 🏆", "green")
            refresh_leaderboard(); refresh_champions()
            btn_close_season.text = "Fechar Época"; btn_close_season.bgcolor = "red"
        except: show_toast("Erro", "red")

    # --- Archive/History Logic ---
    def load_archived_season(e):
        if not dropdown_history_season.value: return
        full_hist = dropdown_history_season.data
        season = next((s for s in full_hist if str(s['id']) == dropdown_history_season.value), None)

        if season:
            try:
                raw_data = json.loads(season['data_json'])
                temp_table = ft.DataTable(columns=[ft.DataColumn(ft.Text("Pos")), ft.DataColumn(ft.Text("Nome")), ft.DataColumn(ft.Text("P"), numeric=True)], rows=[])
                for i, p in enumerate(raw_data):
                    temp_table.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(str(i+1))), ft.DataCell(ft.Text(p['name'])), ft.DataCell(ft.Text(str(p['points']), color="yellow"))]))
                column_history_content.controls = [temp_table]
                page.update()
            except: column_history_content.controls = [ft.Text("Erro nos dados arquivados")]

    def open_history_dialog(e):
        hist_data = fetch_api("history/")
        dropdown_history_season.options.clear(); column_history_content.controls.clear()
        dropdown_history_season.data = hist_data # Store raw data

        if not hist_data: column_history_content.controls.append(ft.Text("Sem histórico ainda."))
        else:
            for s in hist_data: dropdown_history_season.options.append(ft.dropdown.Option(key=str(s['id']), text=s['season_name']))

        dropdown_history_season.on_change = load_archived_season
        page.dialog = ft.AlertDialog(title=ft.Text("Arquivo"), content=ft.Container(content=ft.Column([dropdown_history_season, column_history_content], height=400, width=300)))
        page.dialog.open = True
        page.update()

    # --- Login/Logout Logic ---
    def login_handler(e):
        val = input_password.value
        if val == ADMIN_PASSWORD: state["role"]="admin"; show_toast("Olá Admin 👑"); build_layout()
        elif val == TREASURER_PASSWORD: state["role"]="treasurer"; show_toast("Olá Tesoureiro 💰"); build_layout()
        elif val == MANAGER_PASSWORD: state["role"]="manager"; show_toast("Olá Marcador ⚽"); build_layout()
        else: show_toast("Senha errada", "red")

    def logout_handler(e):
        state["role"] = None
        input_password.value = ""
        show_toast("Sessão terminada")
        build_layout()

    # =========================================================================
    # 4. DEFINE BUTTONS (AFTER HANDLERS)
    # =========================================================================
    btn_submit_payment = ft.ElevatedButton("Registar", on_click=submit_payment)
    btn_submit_game = ft.ElevatedButton("Gravar Jogo (3€)", on_click=submit_game)
    btn_create_player = ft.ElevatedButton("Criar", on_click=create_player)
    btn_remove_champion = ft.ElevatedButton("Remover Título", on_click=remove_champion_handler, color="orange")
    btn_close_season = ft.ElevatedButton("Fechar Época", bgcolor="red", color="white", on_click=close_season_handler)

    # Top Bar Buttons
    btn_history_icon = ft.IconButton(ft.Icons.HISTORY, on_click=open_history_dialog, tooltip="Arquivo")
    btn_login_icon = ft.IconButton(ft.Icons.PERSON, on_click=lambda e: build_login_view(), tooltip="Login")
    btn_logout_icon = ft.IconButton(ft.Icons.LOGOUT, on_click=logout_handler, tooltip="Sair")

    # =========================================================================
    # 5. LAYOUT BUILDING
    # =========================================================================

    # Static History View (Always Visible)
    view_static_history = ft.Column([
        ft.Divider(),
        ft.Text("TÍTULOS DE CAMPEÃO (Pavilhão Sécil & Pavilhão Escola Luisa Todi):", weight="bold", size=12),
        ft.Row([ft.Text("RAFAEL =", weight="bold"), ft.Text("🏆")], spacing=5),
        ft.Row([ft.Text("RENATO =", weight="bold"), ft.Text("🏆")], spacing=5),
        ft.Row([ft.Text("RUI =", weight="bold"), ft.Text("🏆")], spacing=5),
        ft.Row([ft.Text("ABDUL =", weight="bold"), ft.Text("🏆")], spacing=5),
        ft.Row([ft.Text("NUNO TAVARES =", weight="bold"), ft.Text("🏆🏆")], spacing=5),
        ft.Row([ft.Text("CASCA =", weight="bold"), ft.Text("🏆🏆")], spacing=5),
        ft.Row([ft.Text("JOÃO SILVA =", weight="bold"), ft.Text("🏆🏆")], spacing=5),
        ft.Row([ft.Text("JOÃO GALOPIM =", weight="bold"), ft.Text("🏆")], spacing=5),
        column_new_champions # Dynamic ones below
    ], spacing=2)

    view_rules = ft.Column([
        ft.Divider(),
        ft.Text("VITÓRIA = 3 PONTOS | EMPATE = 2 | DERROTA = 1"),
        ft.Text("* -3 PONTOS POR FALTA", size=12),
        ft.Text("Critério: Nº Jogos | Min 50% Jogos", size=12, weight="bold"),
        view_static_history
    ], spacing=5)

    def build_login_view():
        page.clean()
        page.add(ft.Column([
            ft.Text("Área Restrita", size=20, weight="bold"),
            input_password,
            ft.ElevatedButton("Entrar", on_click=login_handler),
            ft.TextButton("Voltar", on_click=lambda e: build_layout())
        ], alignment="center", horizontal_alignment="center"))

    def build_layout():
        page.clean()

        # Decide which icon to show (Login or Logout)
        auth_icon = btn_logout_icon if state["role"] else btn_login_icon

        page.appbar = ft.AppBar(
            title=ft.Text("Terças FC"),
            center_title=False,
            bgcolor="surface_variant",
            actions=[btn_history_icon, auth_icon]
        )

        # Tab 1: Liga (Always visible)
        tabs = [ft.Tab(text="Liga", icon=ft.Icons.LEADERBOARD, content=ft.Column([
            ft.Text("Classificação", size=20, weight="bold"),
            ft.Row([table_leaderboard], scroll="always"),
            view_rules
        ], scroll="auto"))]

        # Tab 2: Treasury (Admin or Treasurer)
        if state["role"] in ["admin", "treasurer"]:
            refresh_treasury()
            tabs.append(ft.Tab(text="Tesouraria", icon=ft.Icons.EURO, content=ft.Column([
                ft.Text("Gestão de Dívidas", size=20),
                ft.Row([dropdown_payer, input_payment_amount], alignment="center"),
                btn_submit_payment, ft.Divider(), column_debt_list
            ], scroll="auto")))

        # Tab 3: Admin (Admin or Manager)
        if state["role"] in ["admin", "manager"]:
            refresh_admin_inputs()
            admin_content = [
                ft.Text("Registar Jogo", weight="bold"),
                ft.Container(content=ft.Row([ft.Column([ft.Text("Eq. A", color="green"), column_team_a], expand=True, scroll="auto"), ft.VerticalDivider(), ft.Column([ft.Text("Eq. B", color="blue"), column_team_b], expand=True, scroll="auto")]), height=250, border=ft.border.all(1, "grey"), padding=5),
                dropdown_result, checkbox_double_points, btn_submit_game, ft.Divider(),
                ft.Text("Gestão", weight="bold"), ft.Row([input_new_player, btn_create_player]), ft.Divider(),
            ]
            # Extra dangerous stuff for Admin Only
            if state["role"] == "admin":
                admin_content.extend([
                    ft.Text("Perigo / Correções", color="red"),
                    dropdown_champion, btn_close_season,
                    ft.Divider(),
                    dropdown_remove_champion, btn_remove_champion
                ])

            tabs.append(ft.Tab(text="Admin", icon=ft.Icons.SETTINGS, content=ft.Column(admin_content, scroll="auto")))

        page.add(ft.Tabs(selected_index=0, tabs=tabs, expand=True))

    # --- Start ---
    refresh_leaderboard(); refresh_champions()

    # Loop for auto-update
    def auto_loop():
        while True:
            time.sleep(15)
            try: refresh_leaderboard()
            except: pass
    threading.Thread(target=auto_loop, daemon=True).start()

    build_layout()

# Run
app = ft.app(target=main, export_asgi_app=True)