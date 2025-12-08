import flet as ft
import requests
import datetime
import threading
import time
import json
import os # Importante para ler as senhas do sistema

# =============================================================================
# CONFIGURATION
# =============================================================================
API_URL = "https://tercas-fc-api.onrender.com"

# SECURITY: Read passwords from Environment Variables
# If not set (local testing), defaults to "1234", "money", "bola"
ADMIN_PASSWORD = os.getenv("ADMIN_PASS", "1234")
TREASURER_PASSWORD = os.getenv("TREASURER_PASS", "money")
MANAGER_PASSWORD = os.getenv("MANAGER_PASS", "bola")

# =============================================================================
# MAIN APP
# =============================================================================
def main(page: ft.Page):
    page.title = "Terças FC"
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 10

    state = {"role": None}
    team_a_checkboxes = []
    team_b_checkboxes = []

    # =========================================================================
    # UI DEFINITIONS
    # =========================================================================

    # Treasury
    input_payment_amount = ft.TextField(label="Valor (€)", width=100, keyboard_type=ft.KeyboardType.NUMBER)
    dropdown_payer = ft.Dropdown(label="Quem pagou?", expand=True)
    column_debt_list = ft.Column()

    # Admin / Game
    column_team_a = ft.Column()
    column_team_b = ft.Column()

    dropdown_champion = ft.Dropdown(label="Quem ganhou a época?")
    dropdown_remove_champion = ft.Dropdown(label="Remover Título de quem?", expand=True)

    dropdown_gr_a = ft.Dropdown(label="GR Equipa A (Não Paga)", expand=True)
    dropdown_gr_b = ft.Dropdown(label="GR Equipa B (Não Paga)", expand=True)

    dropdown_result = ft.Dropdown(
        label="Resultado",
        options=[ft.dropdown.Option("TEAM_A", "Vitória A"), ft.dropdown.Option("TEAM_B", "Vitória B"), ft.dropdown.Option("DRAW", "Empate")]
    )
    checkbox_double_points = ft.Checkbox(label="Pontos x2?", fill_color="yellow")
    input_new_player = ft.TextField(label="Novo Jogador")

    # History
    dropdown_history_season = ft.Dropdown(label="Escolher Época", expand=True)
    container_history_table = ft.Row(scroll=ft.ScrollMode.ALWAYS)

    # Login
    input_password = ft.TextField(label="Senha", password=True, on_submit=lambda e: login_handler(e))

    # =========================================================================
    # HELPERS
    # =========================================================================
    def show_toast(message: str, color: str = "green"):
        page.open(ft.SnackBar(content=ft.Text(message), bgcolor=color))

    def fetch_api(endpoint: str):
        try:
            r = requests.get(f"{API_URL}/{endpoint}")
            return r.json() if r.status_code == 200 else []
        except: return []

    def format_form_icons(form_list):
        """Converts ['W', 'L', 'D'] into icons."""
        icons = ""
        for res in form_list:
            if res == "W": icons += "✅"
            elif res == "L": icons += "❌"
            elif res == "D": icons += "➖"
        return icons

    # =========================================================================
    # LOGIC HANDLERS
    # =========================================================================

    # -- Leaderboard (NOW WITH FORM) --
    table_leaderboard = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Pos")),
            ft.DataColumn(ft.Text("Nome")),
            ft.DataColumn(ft.Text("P"), numeric=True),
            ft.DataColumn(ft.Text("J"), numeric=True),
            # New Column: Form
            ft.DataColumn(ft.Text("Forma")),
            ft.DataColumn(ft.Text("V"), numeric=True),
            ft.DataColumn(ft.Text("E"), numeric=True),
            ft.DataColumn(ft.Text("D"), numeric=True),
        ], rows=[], column_spacing=10
    )

    def refresh_leaderboard():
        data = fetch_api("table/")
        table_leaderboard.rows.clear()
        for i, p in enumerate(data):
            # Safe get for form (in case API is old cache)
            form_data = p.get('form', [])
            form_visuals = format_form_icons(form_data)

            table_leaderboard.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(i+1))),
                ft.DataCell(ft.Text(p['name'], weight="bold", size=13)),
                ft.DataCell(ft.Text(str(p['points']), color="yellow", weight="bold")),
                ft.DataCell(ft.Text(str(p['games_played']))),
                # Form Cell
                ft.DataCell(ft.Text(form_visuals, size=10)),
                ft.DataCell(ft.Text(str(p['wins']), color="green")),
                ft.DataCell(ft.Text(str(p['draws']), color="blue")),
                ft.DataCell(ft.Text(str(p['losses']), color="red")),
            ]))
        page.update()

    # -- Champions --
    column_new_champions = ft.Column()
    def refresh_champions():
        champions = fetch_api("champions/")
        column_new_champions.controls.clear(); dropdown_remove_champion.options.clear()
        if champions:
            column_new_champions.controls.append(ft.Text("NOVOS CAMPEÕES (App):", weight="bold", size=12, color="green"))
            for c in champions:
                trophies = "🏆" * c['titles']
                column_new_champions.controls.append(ft.Row([ft.Text(f"{c['name'].upper()} =", weight="bold"), ft.Text(trophies)], spacing=5))
                dropdown_remove_champion.options.append(ft.dropdown.Option(c['name']))
        page.update()

    # -- Treasury --
    def refresh_treasury():
        players = fetch_api("players/all")
        column_debt_list.controls.clear(); dropdown_payer.options.clear()
        total_debt = 0.0
        for p in players:
            dropdown_payer.options.append(ft.dropdown.Option(key=str(p['id']), text=p['name']))
            balance = p['balance']; color = "red" if balance < 0 else "green"
            if balance < 0: total_debt += balance
            column_debt_list.controls.append(ft.Row([ft.Text(p['name'], weight="bold"), ft.Text(f"{balance:.2f}€", color=color, weight="bold")], alignment="spaceBetween"))
        column_debt_list.controls.append(ft.Divider())
        column_debt_list.controls.append(ft.Text(f"Total em Falta: {total_debt:.2f}€", color="red", weight="bold"))
        page.update()

    def submit_payment(e):
        if not dropdown_payer.value or not input_payment_amount.value: return
        try:
            amt = float(input_payment_amount.value)
            requests.post(f"{API_URL}/players/pay", json={"player_id": int(dropdown_payer.value), "amount": amt})
            show_toast("Aceite!", "green"); input_payment_amount.value=""; refresh_treasury()
        except: show_toast("Erro", "red")

    # -- Admin --
    def refresh_admin_inputs():
        players = fetch_api("players/")
        column_team_a.controls.clear(); column_team_b.controls.clear()
        team_a_checkboxes.clear(); team_b_checkboxes.clear()
        dropdown_champion.options.clear()
        dropdown_gr_a.options.clear(); dropdown_gr_b.options.clear()

        for p in players:
            cba = ft.Checkbox(label=p['name'], value=False); cba.data = p['id']
            team_a_checkboxes.append(cba); column_team_a.controls.append(cba)
            cbb = ft.Checkbox(label=p['name'], value=False); cbb.data = p['id']
            team_b_checkboxes.append(cbb); column_team_b.controls.append(cbb)
            dropdown_champion.options.append(ft.dropdown.Option(p['name']))
            dropdown_gr_a.options.append(ft.dropdown.Option(key=str(p['id']), text=p['name']))
            dropdown_gr_b.options.append(ft.dropdown.Option(key=str(p['id']), text=p['name']))

        refresh_champions()
        page.update()

    def submit_game(e):
        ids_a = [c.data for c in team_a_checkboxes if c.value]
        ids_b = [c.data for c in team_b_checkboxes if c.value]
        if not ids_a or not ids_b: show_toast("Falta jogadores!", "red"); return

        gr_ids = []
        if dropdown_gr_a.value: gr_ids.append(int(dropdown_gr_a.value))
        if dropdown_gr_b.value: gr_ids.append(int(dropdown_gr_b.value))

        try:
            payload = {
                "date": str(datetime.date.today()),
                "result": dropdown_result.value,
                "team_a_players": ids_a, "team_b_players": ids_b,
                "goalkeepers": gr_ids,
                "is_double_points": checkbox_double_points.value
            }
            requests.post(f"{API_URL}/matches/", json=payload)
            show_toast("Gravado!", "green")
            refresh_treasury(); refresh_leaderboard()
            for c in team_a_checkboxes + team_b_checkboxes: c.value = False
            dropdown_gr_a.value = None; dropdown_gr_b.value = None
            page.update()
        except: show_toast("Erro ao gravar", "red")

    def create_player(e):
        if input_new_player.value:
            requests.post(f"{API_URL}/players/", json={"name": input_new_player.value})
            show_toast("Criado!"); input_new_player.value=""; refresh_admin_inputs()

    def remove_champion_handler(e):
        if not dropdown_remove_champion.value: return
        try:
            requests.post(f"{API_URL}/champions/remove", json={"name": dropdown_remove_champion.value})
            show_toast("Título removido", "orange"); refresh_champions()
        except: show_toast("Erro", "red")

    def close_season_handler(e):
        if not dropdown_champion.value: show_toast("Escolhe o Campeão!", "red"); return
        if btn_close_season.text == "Fechar Época": btn_close_season.text = "Tens a Certeza?"; btn_close_season.bgcolor = "orange"; page.update(); return
        try:
            requests.post(f"{API_URL}/season/close", json={"champion_name": dropdown_champion.value, "season_name": "Época"})
            show_toast("Fechado e Arquivado!", "green"); refresh_leaderboard(); refresh_champions()
            btn_close_season.text = "Fechar Época"; btn_close_season.bgcolor = "red"
        except: show_toast("Erro", "red")

    # --- History Logic ---
    def load_archived_season(e):
        if not dropdown_history_season.value: return
        full_hist = dropdown_history_season.data
        season = next((s for s in full_hist if str(s['id']) == dropdown_history_season.value), None)
        if season:
            try:
                raw_data = json.loads(season['data_json'])
                temp_table = ft.DataTable(columns=[ft.DataColumn(ft.Text("Pos")), ft.DataColumn(ft.Text("Nome")), ft.DataColumn(ft.Text("P"), numeric=True)], rows=[])
                for i, p in enumerate(raw_data):
                    temp_table.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(str(i+1))), ft.DataCell(ft.Text(p['name'], weight="bold")), ft.DataCell(ft.Text(str(p['points']), color="yellow"))]))
                container_history_table.controls = [temp_table]
                page.update()
            except: container_history_table.controls = [ft.Text("Erro dados")]

    def delete_history_handler(e):
        if not dropdown_history_season.value: return
        try:
            requests.delete(f"{API_URL}/history/{dropdown_history_season.value}")
            show_toast("Apagado!", "red"); page.close(page.dialog)
        except: show_toast("Erro ao apagar", "red")

    def open_history_dialog(e):
        hist_data = fetch_api("history/")
        dropdown_history_season.options.clear(); container_history_table.controls.clear()
        dropdown_history_season.data = hist_data
        if not hist_data: container_history_table.controls = [ft.Text("Sem histórico.")]
        else:
            for s in hist_data: dropdown_history_season.options.append(ft.dropdown.Option(key=str(s['id']), text=s['season_name']))

        dropdown_history_season.on_change = load_archived_season

        dlg = ft.AlertDialog(
            title=ft.Text("Arquivo"),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([dropdown_history_season, ft.IconButton(ft.Icons.DELETE, icon_color="red", tooltip="Apagar", on_click=delete_history_handler)]),
                    container_history_table
                ], height=400, width=350, scroll="auto")
            )
        )
        page.open(dlg)

    # --- Login ---
    dlg_login = None
    def login_handler(e):
        val = input_password.value
        auth = False
        if val == ADMIN_PASSWORD: state["role"]="admin"; show_toast("Logado como admin 👑"); auth=True
        elif val == TREASURER_PASSWORD: state["role"]="treasurer"; show_toast("Logado como tesoureiro 💰"); auth=True
        elif val == MANAGER_PASSWORD: state["role"]="manager"; show_toast("Logado como manager ⚽"); auth=True
        else: show_toast("Senha errada", "red")

        if auth:
            if dlg_login: page.close(dlg_login)
            build_layout()

    def logout_handler(e):
        state["role"] = None; input_password.value = ""; show_toast("Sessão terminada"); build_layout()

    # =========================================================================
    # BUTTONS & LAYOUT
    # =========================================================================
    btn_submit_payment = ft.ElevatedButton("Registar", on_click=submit_payment)
    btn_submit_game = ft.ElevatedButton("Gravar Jogo (3€)", on_click=submit_game)
    btn_create_player = ft.ElevatedButton("Criar", on_click=create_player)
    btn_remove_champion = ft.ElevatedButton("Remover Título", on_click=remove_champion_handler, color="orange")
    btn_close_season = ft.ElevatedButton("Fechar Época", bgcolor="red", color="white", on_click=close_season_handler)

    btn_history_icon = ft.IconButton(ft.Icons.HISTORY, on_click=open_history_dialog, tooltip="Arquivo")
    btn_logout_icon = ft.IconButton(ft.Icons.LOGOUT, on_click=logout_handler, tooltip="Sair")

    def build_login_view():
        nonlocal dlg_login
        input_password.on_submit = login_handler
        dlg_login = ft.AlertDialog(title=ft.Text("Área Restrita"), content=ft.Column([input_password, ft.ElevatedButton("Entrar", on_click=login_handler)], height=150, alignment="center"))
        page.open(dlg_login)

    btn_login_icon = ft.IconButton(ft.Icons.PERSON, on_click=lambda e: build_login_view(), tooltip="Login")

    view_static_history = ft.Column([
        ft.Divider(), ft.Text("TÍTULOS DE CAMPEÃO (Pavilhão Sécil & Pavilhão Escola Luisa Todi):", weight="bold", size=12),
        ft.Row([ft.Text("RAFAEL =", weight="bold"), ft.Text("🏆")], spacing=5),
        ft.Row([ft.Text("RENATO =", weight="bold"), ft.Text("🏆")], spacing=5),
        ft.Row([ft.Text("RUI =", weight="bold"), ft.Text("🏆")], spacing=5),
        ft.Row([ft.Text("ABDUL =", weight="bold"), ft.Text("🏆")], spacing=5),
        ft.Row([ft.Text("NUNO TAVARES =", weight="bold"), ft.Text("🏆🏆")], spacing=5),
        ft.Row([ft.Text("CASCA =", weight="bold"), ft.Text("🏆🏆")], spacing=5),
        ft.Row([ft.Text("JOÃO SILVA =", weight="bold"), ft.Text("🏆🏆")], spacing=5),
        ft.Row([ft.Text("JOÃO GALOPIM =", weight="bold"), ft.Text("🏆")], spacing=5),
        column_new_champions
    ], spacing=2)

    view_rules = ft.Column([
        ft.Divider(), ft.Text("VITÓRIA = 3 PONTOS | EMPATE = 2 | DERROTA = 1"),
        ft.Text("* -3 PONTOS POR FALTA", size=12), ft.Text("Critério: Nº Jogos | Min 50% Jogos", size=12, weight="bold"),
        view_static_history
    ], spacing=5)

    def build_layout():
        page.clean()
        auth_icon = btn_logout_icon if state["role"] else btn_login_icon
        page.appbar = ft.AppBar(title=ft.Text("Terças FC"), center_title=False, bgcolor="surface_variant", actions=[btn_history_icon, auth_icon])

        tabs = [ft.Tab(text="Liga", icon=ft.Icons.LEADERBOARD, content=ft.Column([ft.Text("Classificação", size=20, weight="bold"), ft.Row([table_leaderboard], scroll="always"), view_rules], scroll="auto"))]

        if state["role"] in ["admin", "treasurer"]:
            refresh_treasury()
            tabs.append(ft.Tab(text="Tesouraria", icon=ft.Icons.EURO, content=ft.Column([ft.Text("Gestão de Dívidas", size=20), ft.Row([dropdown_payer, input_payment_amount], alignment="center"), btn_submit_payment, ft.Divider(), column_debt_list], scroll="auto")))

        if state["role"] in ["admin", "manager"]:
            refresh_admin_inputs()
            admin_content = [
                ft.Text("Registar Jogo", weight="bold"),
                ft.Container(content=ft.Row([ft.Column([ft.Text("Eq. A", color="green"), column_team_a], expand=True, scroll="auto"), ft.VerticalDivider(), ft.Column([ft.Text("Eq. B", color="blue"), column_team_b], expand=True, scroll="auto")]), height=250, border=ft.border.all(1, "grey"), padding=5),
                ft.Text("Guarda-Redes (Não Pagam):", size=12, color="grey"),
                ft.Row([dropdown_gr_a, dropdown_gr_b]),
                dropdown_result, checkbox_double_points, btn_submit_game, ft.Divider(),
                ft.Text("Gestão", weight="bold"), ft.Row([input_new_player, btn_create_player]), ft.Divider(),
            ]
            if state["role"] == "admin":
                admin_content.extend([ft.Text("Perigo / Correções", color="red"), dropdown_champion, btn_close_season, ft.Divider(), dropdown_remove_champion, btn_remove_champion])
            tabs.append(ft.Tab(text="Admin", icon=ft.Icons.SETTINGS, content=ft.Column(admin_content, scroll="auto")))

        page.add(ft.Tabs(selected_index=0, tabs=tabs, expand=True))

    def auto_loop():
        while True:
            time.sleep(15);
            try: refresh_leaderboard()
            except: pass
    threading.Thread(target=auto_loop, daemon=True).start()

    refresh_leaderboard(); refresh_champions(); build_layout()

app = ft.app(target=main, export_asgi_app=True, assets_dir="src/assets")