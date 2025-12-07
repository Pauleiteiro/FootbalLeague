import flet as ft
import requests
import datetime
import threading
import time

# --- CONFIGURAÇÃO ---
# IMPORTANTE: Quando partilhares com amigos, este IP tem de ser o do servidor na Cloud
# Para já, no teu PC, mantém assim:
API_URL = "http://127.0.0.1:8000"
ADMIN_PASSWORD = "1234"  # <--- A TUA PASSWORD AQUI

def main(page: ft.Page):
    page.title = "Terças FC"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 400
    page.window_height = 800
    page.padding = 10

    # Variáveis Globais
    team_a_selected = []
    team_b_selected = []

    # Estado da Sessão (Login)
    state = {"is_admin": False}

    # --- FUNÇÕES AUXILIARES ---
    def show_msg(texto, cor="green"):
        page.snack_bar = ft.SnackBar(content=ft.Text(texto), bgcolor=cor)
        page.snack_bar.open = True
        page.update()

    def get_api(path):
        try:
            r = requests.get(f"{API_URL}/{path}")
            return r.json() if r.status_code == 200 else []
        except: return []

    # --- 1. TABELA CLASSIFICATIVA ---
    tabela = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Pos")),
            ft.DataColumn(ft.Text("Nome")),
            ft.DataColumn(ft.Text("P"), numeric=True),
            ft.DataColumn(ft.Text("J"), numeric=True),
            ft.DataColumn(ft.Text("V"), numeric=True),
            ft.DataColumn(ft.Text("E"), numeric=True),
            ft.DataColumn(ft.Text("D"), numeric=True),
        ], rows=[], column_spacing=10
    )

    def atualizar_tabela():
        dados = get_api("table/")
        tabela.rows.clear()
        for i, p in enumerate(dados):
            tabela.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(i+1))),
                ft.DataCell(ft.Text(p['name'], weight="bold", size=13)),
                ft.DataCell(ft.Text(str(p['points']), color="yellow", weight="bold")),
                ft.DataCell(ft.Text(str(p['games_played']))),
                ft.DataCell(ft.Text(str(p['wins']), color="green")),
                ft.DataCell(ft.Text(str(p['draws']), color="blue")),
                ft.DataCell(ft.Text(str(p['losses']), color="red")),
            ]))
        page.update()

    # --- AUTO-UPDATE (Loop em background) ---
    def auto_refresh_loop():
        while True:
            time.sleep(10) # Atualiza a cada 10 segundos
            try:
                atualizar_tabela()
            except: pass

    # Inicia o thread de atualização automática
    threading.Thread(target=auto_refresh_loop, daemon=True).start()

    # --- 2. TEXTO EXATO DA IMAGEM ---
    # Aqui está o texto exatamente como pediste, copiado da imagem
    campeoes_texto = ft.Column([
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
    ], spacing=2)

    regras_texto = ft.Column([
        ft.Divider(),
        ft.Text("VITÓRIA = 3 PONTOS"),
        ft.Text("EMPATE = 2 PONTOS"),
        ft.Text("DERROTA = 1 PONTO"),
        ft.Container(height=5),
        ft.Text("* PENALIZAÇÃO DE -3 PONTOS POR FALTA DE COMPARÊNCIA", size=12),
        ft.Text("1º CRITÉRIO DE DESEMPATE: MAIOR NUMERO DE JOGOS REALIZADOS", size=12, weight="bold"),
        ft.Text("SEMANALMENTE AS EQUIPAS SÃO ESCOLHIDAS PELO 1º E 2º CLASSIFICADOS", size=12),
        ft.Text("SÓ ENTRA NA TABELA QUEM TIVER PELO MENOS 50% DO TOTAL JOGOS REALIZADOS", size=12),
        campeoes_texto
    ], spacing=5)

    # --- 3. LÓGICA DE LOGIN (PASSWORD) ---
    pass_input = ft.TextField(label="Palavra-Passe", password=True, can_reveal_password=True)

    def verificar_password(e):
        if pass_input.value == ADMIN_PASSWORD:
            state["is_admin"] = True
            show_msg("Acesso Permitido! 🔓")
            # Recarrega a página para mostrar o conteúdo Admin
            page.go("/admin_unlocked")
            construir_layout()
        else:
            show_msg("Senha Errada! 🔒", "red")

    btn_login = ft.ElevatedButton("Entrar", on_click=verificar_password)

    login_container = ft.Column([
        ft.Text("Área Restrita", size=20, weight="bold"),
        ft.Text("Insere a password de administrador:"),
        pass_input,
        btn_login
    ], alignment=ft.MainAxisAlignment.CENTER)

    # --- 4. CONTEÚDO ADMIN (Só aparece depois do login) ---
    col_a = ft.Column(); col_b = ft.Column()

    def carregar_jogadores():
        jogadores = get_api("players/")
        col_a.controls.clear(); col_b.controls.clear()
        team_a_selected.clear(); team_b_selected.clear()

        for p in jogadores:
            cba = ft.Checkbox(label=p['name']); cba.data = p['id']
            team_a_selected.append(cba); col_a.controls.append(cba)
            cbb = ft.Checkbox(label=p['name']); cbb.data = p['id']
            team_b_selected.append(cbb); col_b.controls.append(cbb)
        page.update()

    dd_res = ft.Dropdown(label="Resultado", options=[
        ft.dropdown.Option("TEAM_A", "Vitória Equipa A"), ft.dropdown.Option("TEAM_B", "Vitória equipa B"), ft.dropdown.Option("DRAW", "Empate")
    ])
    chk_x2 = ft.Checkbox(label="Pontos x2?", fill_color="yellow")

    def gravar_jogo(e):
        print("Botão Clicado...") # Vai aparecer no terminal
        try:
            ids_a = [c.data for c in team_a_selected if c.value]
            ids_b = [c.data for c in team_b_selected if c.value]

            # Validação Básica
            if not ids_a or not ids_b:
                page.dialog = ft.AlertDialog(title=ft.Text("Erro"), content=ft.Text("Faltam jogadores nas equipas!"))
                page.dialog.open = True
                page.update()
                return

            if not dd_res.value:
                page.dialog = ft.AlertDialog(title=ft.Text("Erro"), content=ft.Text("Quem ganhou o jogo? Escolhe o resultado."))
                page.dialog.open = True
                page.update()
                return

            payload = {
                "date": str(datetime.date.today()),
                "result": dd_res.value,
                "team_a_players": ids_a,
                "team_b_players": ids_b,
                "is_double_points": chk_x2.value
            }

            print(f"A enviar: {payload}") # Debug no terminal

            res = requests.post(f"{API_URL}/matches/", json=payload)

            if res.status_code == 200:
                show_msg("JOGO GRAVADO COM SUCESSO! ⚽", "green")
                # Limpar tudo
                for c in team_a_selected + team_b_selected: c.value = False
                dd_res.value = None
                atualizar_tabela()
            else:
                # ERRO DO SERVIDOR - MOSTRAR POPUP
                erro_detalhe = res.text
                print(f"Erro 422 ou 500: {erro_detalhe}")
                page.dialog = ft.AlertDialog(
                    title=ft.Text(f"Erro {res.status_code}"),
                    content=ft.Text(f"O servidor recusou os dados.\nVerifica se o main.py tem 'is_double_points'.\nDetalhe: {erro_detalhe}")
                )
                page.dialog.open = True
                page.update()

        except Exception as ex:
            print(f"Erro Técnico: {ex}")
            page.dialog = ft.AlertDialog(title=ft.Text("Erro Técnico"), content=ft.Text(str(ex)))
            page.dialog.open = True
            page.update()

    btn_gravar = ft.ElevatedButton("Gravar Jogo", on_click=gravar_jogo)

    new_name = ft.TextField(label="Novo Jogador", expand=True)
    def criar_j(e):
        if new_name.value:
            requests.post(f"{API_URL}/players/", json={"name": new_name.value})
            show_msg("Criado!"); new_name.value=""; carregar_jogadores(); atualizar_tabela()
    btn_criar = ft.ElevatedButton("Criar", on_click=criar_j)

    # Reset
    def reset_click(e):
        if btn_reset.text == "Reiniciar Época (Reset)":
            btn_reset.text = "Tens a Certeza?"; btn_reset.bgcolor = "orange"; page.update()
        elif "C" in btn_reset.text:
            requests.delete(f"{API_URL}/reset/"); show_msg("Reiniciado!"); btn_reset.text="Reiniciar Época (Reset)"; btn_reset.bgcolor="red"; atualizar_tabela(); page.update()
    btn_reset = ft.ElevatedButton("Reiniciar Época (Reset)", bgcolor="red", color="white", on_click=reset_click)

    # Layout Admin (Protegido)
    admin_content = ft.Column([
        ft.Text("Painel Admin 🔐", size=20, weight="bold", color="green"),
        ft.Text("Registar Jogo", weight="bold"),
        ft.Row([ft.Text("Equipas"), ft.IconButton(ft.Icons.REFRESH, on_click=lambda e: carregar_jogadores())]),
        ft.Container(content=ft.Row([
            ft.Column([ft.Text("Eq. A", color="green"), col_a], expand=True, scroll="auto"),
            ft.VerticalDivider(width=1),
            ft.Column([ft.Text("Eq. B", color="blue"), col_b], expand=True, scroll="auto")
        ]), height=200, border=ft.border.all(1, "grey"), padding=5),
        dd_res, chk_x2, btn_gravar,
        ft.Divider(),
        ft.Text("Gestão", weight="bold"),
        ft.Row([new_name, btn_criar]),
        ft.Container(height=10),
        ft.Text("Perigo", color="red"), btn_reset
    ], scroll="auto")

    # --- CONSTRUÇÃO DO LAYOUT PRINCIPAL ---
    def construir_layout():
        # Define o conteúdo da Aba Admin com base no login
        conteudo_aba_admin = admin_content if state["is_admin"] else login_container

        # Recria as tabs
        tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="Classificação", icon=ft.Icons.LEADERBOARD, content=ft.Column([
                    ft.Text("Tabela Atual", size=20, weight="bold"),
                    ft.Row([tabela], scroll="always"),
                    regras_texto
                ], scroll="auto")),

                ft.Tab(text="Admin", icon=ft.Icons.LOCK if not state["is_admin"] else ft.Icons.LOCK_OPEN, content=conteudo_aba_admin)
            ],
            expand=True
        )
        page.clean()
        page.add(tabs)

    # Início
    construir_layout()
    atualizar_tabela()
    carregar_jogadores()

if __name__ == "__main__":
    ft.app(target=main)