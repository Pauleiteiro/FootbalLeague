import flet as ft
import requests
import datetime
import threading
import time

# =============================================================================
# CONFIGURATION
# =============================================================================
API_URL = "https://tercas-fc-api.onrender.com"

# Role Access Credentials
ADMIN_PASSWORD = "1234"      # Master Access (All Tabs)
TREASURER_PASSWORD = "money" # Treasury Tab Only
MANAGER_PASSWORD = "bola"    # Game Registration Tab Only

# =============================================================================
# MAIN APPLICATION
# =============================================================================
def main(page: ft.Page):
    # --- Page Configuration ---
    page.title = "Terças FC"
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 10

    # --- Application State ---
    state = {
        "role": None,  # Can be 'admin', 'treasurer', 'manager' or None
    }

    # Global references
    team_a_checkboxes = []
    team_b_checkboxes = []

    # =========================================================================
    # 1. UI COMPONENT DEFINITIONS (INPUTS & CONTAINERS)
    # =========================================================================
    # We define these FIRST so the logic functions can find them.

    # -- Treasury Inputs --
    debt_list_view = ft.Column()
    payment_amount_input = ft.TextField(label="Valor (€)", width=100, keyboard_type=ft.KeyboardType.NUMBER)
    payer_dropdown = ft.Dropdown(label="Quem pagou?", expand=True)

    # -- Game Inputs --
    col_team_a = ft.Column()
    col_team_b = ft.Column()
    champion_dropdown = ft.Dropdown(label="Quem ganhou a época?")

    result_dropdown = ft.Dropdown(
        label="Resultado",
        options=[
            ft.dropdown.Option("TEAM_A", "Vitória A"),
            ft.dropdown.Option("TEAM_B", "Vitória B"),
            ft.dropdown.Option("DRAW", "Empate")
        ]
    )

    # FIX: Variable name matches usage below
    double_points_chk = ft.Checkbox(label="Pontos x2?", fill_color="yellow")

    new_player_input = ft.TextField(label="Novo Jogador")

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
        except Exception as e:
            print(f"API Error: {e}")
            return []

    # =========================================================================
    # 3. LEADERBOARD LOGIC
    # =========================================================================
    leaderboard_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Pos")),
            ft.DataColumn(ft.Text("Nome")),
            ft.DataColumn(ft.Text("P"), numeric=True),
            ft.DataColumn(ft.Text("J"), numeric=True),
            ft.DataColumn(ft.Text("V"), numeric=True),
            ft.DataColumn(ft.Text("E"), numeric=True),
            ft.DataColumn(ft.Text("D"), numeric=True),
        ],
        rows=[],
        column_spacing=5
    )

    def refresh_leaderboard():
        data = fetch_api("table/")
        leaderboard_table.rows.clear()
        for i, player in enumerate(data):
            leaderboard_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(i + 1))),
                        ft.DataCell(ft.Text(player['name'], weight="bold", size=13)),
                        ft.DataCell(ft.Text(str(player['points']), color="yellow", weight="bold")),
                        ft.DataCell(ft.Text(str(player['games_played']))),
                        ft.DataCell(ft.Text(str(player['wins']), color="green")),
                        ft.DataCell(ft.Text(str(player['draws']), color="blue")),
                        ft.DataCell(ft.Text(str(player['losses']), color="red")),
                    ]
                )
            )
        page.update()

    def auto_update_loop():
        while True:
            time.sleep(15)
            try: refresh_leaderboard()
            except: pass
    threading.Thread(target=auto_update_loop, daemon=True).start()

    # =========================================================================
    # 4. HISTORY & RULES
    # =========================================================================
    new_champions_container = ft.Column()

    def refresh_new_champions():
        champions = fetch_api("champions/")
        new_champions_container.controls.clear()
        if champions:
            new_champions_container.controls.append(ft.Text("NOVOS CAMPEÕES (App):", weight="bold", size=12, color="green"))
            for c in champions:
                trophies = "🏆" * c['titles']
                new_champions_container.controls.append(
                    ft.Row([ft.Text(f"{c['name'].upper()} =", weight="bold"), ft.Text(trophies)], spacing=5)
                )
        page.update()

    static_history_view = ft.Column(
        controls=[
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
            new_champions_container
        ],
        spacing=2
    )

    rules_text_view = ft.Column(
        controls=[
            ft.Divider(),
            ft.Text("VITÓRIA = 3 PONTOS"),
            ft.Text("EMPATE = 2 PONTOS"),
            ft.Text("DERROTA = 1 PONTO"),
            ft.Container(height=10),
            ft.Text("* PENALIZAÇÃO DE -3 PONTOS POR FALTA DE COMPARÊNCIA", size=12),
            ft.Text("1º CRITÉRIO DE DESEMPATE: MAIOR NUMERO DE JOGOS REALIZADOS", size=12, weight="bold"),
            ft.Text("SEMANALMENTE AS EQUIPAS SÃO ESCOLHIDAS PELO 1º E 2º CLASSIFICADOS", size=12),
            ft.Text("SÓ ENTRA NA TABELA QUEM TIVER PELO MENOS 50% DO TOTAL JOGOS REALIZADOS", size=12),
            static_history_view
        ],
        spacing=5
    )

    # =========================================================================
    # 5. TREASURY LOGIC
    # =========================================================================
    def refresh_treasury_data():
        players = fetch_api("players/all")
        debt_list_view.controls.clear()
        payer_dropdown.options.clear()
        total_debt = 0.0

        for p in players:
            payer_dropdown.options.append(ft.dropdown.Option(key=str(p['id']), text=p['name']))
            balance = p['balance']
            color = "red" if balance < 0 else "green"
            if balance < 0: total_debt += balance
            debt_list_view.controls.append(ft.Row([
                ft.Text(p['name'], weight="bold"),
                ft.Text(f"{balance:.2f}€", color=color, weight="bold")
            ], alignment="spaceBetween"))

        debt_list_view.controls.append(ft.Divider())
        debt_list_view.controls.append(ft.Text(f"Dívida Total da Liga: {total_debt:.2f}€", color="red", weight="bold"))
        page.update()

    def submit_payment(e):
        if not payer_dropdown.value or not payment_amount_input.value: return
        try:
            amount = float(payment_amount_input.value)
            payload = {"player_id": int(payer_dropdown.value), "amount": amount}
            res = requests.post(f"{API_URL}/players/pay", json=payload)
            if res.status_code == 200:
                show_toast(f"Pagamento de {amount}€ aceite!", "green")
                payment_amount_input.value = ""
                refresh_treasury_data()
            else: show_toast("Erro ao processar", "red")
        except: show_toast("Valor inválido", "red")

    # BUTTON DEFINITION (AFTER HANDLER)
    btn_submit_payment = ft.ElevatedButton("Registar Pagamento 💰", on_click=submit_payment)

    # =========================================================================
    # 6. ADMIN / GAME LOGIC
    # =========================================================================
    def refresh_admin_data():
        players = fetch_api("players/")
        col_team_a.controls.clear()
        col_team_b.controls.clear()
        team_a_checkboxes.clear()
        team_b_checkboxes.clear()
        champion_dropdown.options.clear()

        for p in players:
            cb_a = ft.Checkbox(label=p['name'], value=False); cb_a.data = p['id']
            team_a_checkboxes.append(cb_a); col_team_a.controls.append(cb_a)

            cb_b = ft.Checkbox(label=p['name'], value=False); cb_b.data = p['id']
            team_b_checkboxes.append(cb_b); col_team_b.controls.append(cb_b)

            champion_dropdown.options.append(ft.dropdown.Option(p['name']))
        page.update()

    def submit_game(e):
        ids_a = [cb.data for cb in team_a_checkboxes if cb.value]
        ids_b = [cb.data for cb in team_b_checkboxes if cb.value]

        if not ids_a or not ids_b:
            show_toast("Falta informação nas equipas", "red"); return

        try:
            # FIX: Using 'double_points_chk' correctly here
            payload = {
                "date": str(datetime.date.today()),
                "result": result_dropdown.value,
                "team_a_players": ids_a,
                "team_b_players": ids_b,
                "is_double_points": double_points_chk.value
            }
            requests.post(f"{API_URL}/matches/", json=payload)
            show_toast("Jogo Gravado! (-3€ a cada jogador)", "green")
            refresh_treasury_data()
            refresh_leaderboard()
            for cb in team_a_checkboxes + team_b_checkboxes: cb.value = False
            page.update()
        except Exception as err: show_toast(f"Erro: {err}", "red")

    btn_submit_game = ft.ElevatedButton("Gravar Jogo (Custa 3€)", on_click=submit_game)

    def close_season_handler(e):
        if not champion_dropdown.value: show_toast("Escolhe o Campeão!", "red"); return
        if btn_close_season.text == "Fechar Época":
            btn_close_season.text = "Tens a Certeza?"; btn_close_season.bgcolor = "orange"; page.update(); return
        try:
            requests.post(f"{API_URL}/season/close", json={"champion_name": champion_dropdown.value, "season_name": "Época"})
            show_toast("Época Fechada!", "green")
            refresh_new_champions(); refresh_leaderboard()
            btn_close_season.text = "Fechar Época"; btn_close_season.bgcolor = "red"
        except: show_toast("Erro ao fechar época", "red")

    btn_close_season = ft.ElevatedButton("Fechar Época", bgcolor="red", color="white", on_click=close_season_handler)

    def create_player_handler(e):
        if new_player_input.value:
            try:
                requests.post(f"{API_URL}/players/", json={"name": new_player_input.value})
                show_toast("Criado!", "green")
                refresh_admin_data(); new_player_input.value = ""
            except: show_toast("Erro: Jogador já existe?", "red")

    btn_create_player = ft.ElevatedButton("Criar", on_click=create_player_handler)

    # =========================================================================
    # 7. LOGIN SYSTEM
    # =========================================================================
    password_input = ft.TextField(label="Senha", password=True)

    def handle_login(e):
        val = password_input.value
        if val == ADMIN_PASSWORD:
            state["role"] = "admin"; show_toast("Bem-vindo Admin 👑"); build_main_layout()
        elif val == TREASURER_PASSWORD:
            state["role"] = "treasurer"; show_toast("Bem-vindo Tesoureiro 💰"); build_main_layout()
        elif val == MANAGER_PASSWORD:
            state["role"] = "manager"; show_toast("Bem-vindo Marcador ⚽"); build_main_layout()
        else: show_toast("Senha errada", "red")

    login_view = ft.Column([
        ft.Text("Área Restrita", size=20, weight="bold"),
        password_input,
        ft.ElevatedButton("Entrar", on_click=handle_login),
        ft.TextButton("Voltar à Tabela", on_click=lambda e: build_main_layout())
    ], alignment="center", horizontal_alignment="center")

    def navigate_to_login(e):
        page.clean(); page.add(login_view)

    # =========================================================================
    # 8. LAYOUT BUILDER
    # =========================================================================
    def build_main_layout():
        page.clean()
        page.appbar = ft.AppBar(
            title=ft.Text("Terças FC"), center_title=False, bgcolor="surface_variant",
            actions=[ft.IconButton(ft.Icons.PERSON, on_click=navigate_to_login, tooltip="Login")]
        )

        # Tab 1: League (Public)
        tabs_list = [ft.Tab(text="Liga", icon=ft.Icons.LEADERBOARD, content=ft.Column([
            ft.Text("Classificação", size=20, weight="bold"),
            ft.Row([leaderboard_table], scroll="always"),
            rules_text_view
        ], scroll="auto"))]

        # Tab 2: Treasury
        if state["role"] in ["admin", "treasurer"]:
            refresh_treasury_data()
            tabs_list.append(ft.Tab(text="Tesouraria", icon=ft.Icons.EURO, content=ft.Column([
                ft.Text("Gestão de Dívidas", size=20),
                ft.Row([payer_dropdown, payment_amount_input], alignment="center"),
                btn_submit_payment, ft.Divider(), debt_list_view
            ], scroll="auto")))

        # Tab 3: Admin
        if state["role"] in ["admin", "manager"]:
            refresh_admin_data()
            tabs_list.append(ft.Tab(text="Admin", icon=ft.Icons.SETTINGS, content=ft.Column([
                ft.Text("Registar Jogo", weight="bold"),
                ft.Container(content=ft.Row([
                    ft.Column([ft.Text("Eq. A", color="green"), col_team_a], expand=True, scroll="auto"),
                    ft.VerticalDivider(),
                    ft.Column([ft.Text("Eq. B", color="blue"), col_team_b], expand=True, scroll="auto")
                ]), height=250, border=ft.border.all(1, "grey"), padding=5),
                result_dropdown, double_points_chk, btn_submit_game, ft.Divider(),
                ft.Text("Gestão", weight="bold"), ft.Row([new_player_input, btn_create_player]), ft.Divider(),
                ft.Text("Fim de Época", color="red"), champion_dropdown, btn_close_season
            ], scroll="auto")))

        page.add(ft.Tabs(selected_index=0, tabs=tabs_list, expand=True))

    # --- Start ---
    refresh_leaderboard(); refresh_new_champions(); build_main_layout()

app = ft.app(target=main, export_asgi_app=True)