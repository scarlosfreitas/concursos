import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import pandas as pd
import datetime as dt
import os
import yaml
from dotenv import load_dotenv
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt

load_dotenv()

class ExtractorState(TypedDict):
    driver: Any
    fisco_escolhido: Optional[str]
    ranking_url: str
    numero_insercoes: int
    pagina_corrente: int
    numero_paginas: int
    lista_pontos: List[Dict[str, Any]]
    lista_acertos: List[Dict[str, Any]]
    lista_erros: List[Dict[str, Any]]
    lista_brancos: List[Dict[str, Any]]
    lista_percentual: List[Dict[str, Any]]

def wait_for_page_load(driver):
    while True:
        page_state = driver.execute_script('return document.readyState;')
        if page_state == 'complete':
            break
        time.sleep(1)

def get_navegacao(driver):
    div_paginador = driver.find_element(By.XPATH, '//div[@id="form:tabView:dataTable0_paginator_top"]')
    
    numero_insercoes = int(div_paginador.find_element(By.XPATH, './/span[@class="ui-paginator-current"]').text.split()[0].replace('.',''))
    numero_paginas = numero_insercoes//50+1
    pagina_corrente = int(div_paginador.find_element(By.XPATH, './/a[contains(@class,"ui-state-active")]').text)
    
    return numero_insercoes, pagina_corrente, numero_paginas
    
def bt_navegacao(driver, tp_navegacao):
    div_paginador = driver.find_element(By.XPATH, '//div[@id="form:tabView:dataTable0_paginator_top"]')
    bt = div_paginador.find_element(By.XPATH, './/a[contains(@class, "ui-paginator-' + tp_navegacao + '")]')
    
    try:
        bt.click()
        print('Navegação do tipo: ' + tp_navegacao)
    except:
        print('Navegação não foi possível: ' + tp_navegacao)

def get_col_names(elemento_th):
    nome_colunas = []
    for coluna in elemento_th:
        texto = coluna.text.replace('.','')
        
        if texto == '#':
            texto = 'posicao'

        if texto != '':
            nome_colunas.append(texto)    

    for coluna in nome_colunas:
        indices_repetido = [i for i, c in enumerate(nome_colunas) if c == coluna]
        if len(indices_repetido) > 1:
            for i in range(len(indices_repetido)):
                nome_colunas[indices_repetido[i]] = nome_colunas[indices_repetido[i]] + '_' + str(i + 1)
            
    return nome_colunas

# --- LANGGRAPH NODES ---

def init_browser(state: ExtractorState) -> ExtractorState:
    print("Iniciando o navegador...")
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=145)
    
    print("Acessando a página de login...")
    driver.get("https://olhonavaga.com.br/login")
    wait_for_page_load(driver)
    
    return {"driver": driver, "lista_pontos": [], "lista_acertos": [], "lista_erros": [], "lista_brancos": [], "lista_percentual": []}

def perform_login(state: ExtractorState) -> ExtractorState:
    driver = state["driver"]
    
    email = os.getenv("EMAIL_OLHO_NA_VAGA", "scarlosfreitas@gmail.com")
    senha = os.getenv("SENHA_OLHO_NA_VAGA", "gv8b3t22yh8r")

    print(f"Efetuando login com: {email}")
    driver.find_element(By.NAME, "form:email").send_keys(email)
    driver.find_element(By.NAME, "form:password").send_keys(senha)
    
    print("Clicando no botão de login...")
    driver.find_element(By.NAME, "form:signInButton").click()
    
    wait_for_page_load(driver)
    return state

def wait_for_captcha(state: ExtractorState) -> ExtractorState:
    print("Aguardando intervenção humana (CAPTCHA) via LangGraph Interrupt...")
    # Essa função pausa o Grafo e permite que a UI do LangGraph continue apenas quando você mandar "Resume"
    response = interrupt("Vá ao navegador e resolva o CAPTCHA 'Não sou um robô'. Após o login carregar na página inicial, clique em 'Resume' aqui no LangGraph Studio.")
    
    wait_for_page_load(state["driver"])
    return state

def select_ranking(state: ExtractorState) -> ExtractorState:
    yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rankings.yaml')
    with open(yaml_path, 'r', encoding='utf-8') as f:
        dict_fisco = yaml.safe_load(f)
    if dict_fisco is None:
        dict_fisco = {}
    
    print("Rankings disponíveis:")
    for key in dict_fisco.keys():
        print(f" - {key}")
        
    fisco_escolhido = state.get("fisco_escolhido")
    if not fisco_escolhido or fisco_escolhido not in dict_fisco:
        fisco_escolhido = 'sefaz-pi'
        
    ranking_url = dict_fisco[fisco_escolhido]
    print(f"\nSelecionado: {fisco_escolhido}")
    
    return {"fisco_escolhido": fisco_escolhido, "ranking_url": ranking_url}

def load_ranking(state: ExtractorState) -> ExtractorState:
    driver = state["driver"]
    print(f"Acessando o ranking...")
    driver.get(state["ranking_url"])
    wait_for_page_load(driver)
    time.sleep(3) 

    numero_insercoes, pagina_corrente, numero_paginas = get_navegacao(driver)
    print(f"Fisco: {state['fisco_escolhido'].upper()} Inserções: {numero_insercoes} Pagina: {pagina_corrente}/{numero_paginas}")
    
    if pagina_corrente != 1:
        bt_navegacao(driver, 'first')
        time.sleep(5)
        _, pagina_corrente, _ = get_navegacao(driver)
        
    return {
        "numero_insercoes": numero_insercoes,
        "pagina_corrente": pagina_corrente,
        "numero_paginas": numero_paginas
    }

def extract_page(state: ExtractorState) -> ExtractorState:
    driver = state["driver"]
    pagina_corrente = state["pagina_corrente"]
    numero_paginas = state["numero_paginas"]
    
    print(f"Extraindo Pagina {pagina_corrente}/{numero_paginas}")
    
    thead_ranking = driver.find_elements(By.XPATH, '//thead[@id="form:tabView:dataTable0_head"]')
    tbody_ranking = driver.find_elements(By.XPATH, '//tbody[@id="form:tabView:dataTable0_data"]')
    
    elemento_hbody = thead_ranking[0]
    elemento_tbody = tbody_ranking[0]
    
    nome_colunas = get_col_names(elemento_hbody.find_elements(By.TAG_NAME, "th"))
    linhas = elemento_tbody.find_elements(By.XPATH, './/tr[@data-ri]')
    print(f"Quantidade de linhas: {len(linhas)}", end='')
    
    l_pontos, l_acertos, l_erros, l_brancos, l_percentual = [], [], [], [], []
    
    for linha in linhas:
        celulas = linha.find_elements(By.TAG_NAME, "td")
        if not celulas: continue
            
        registro = {'posicao':celulas[0].text, 'usuario':celulas[1].text}
        r_pontos, r_acertos, r_erros, r_brancos, r_percentual = registro.copy(), registro.copy(), registro.copy(), registro.copy(), registro.copy()
    
        for n_col in range(len(nome_colunas) - 2):
            nome_coluna = nome_colunas[n_col + 2]
            lista_valores = celulas[n_col+2].text.replace('|','').split()
    
            if len(lista_valores) >= 4:
                pontos, acertos, erros  = lista_valores[0:3]
                percentual = lista_valores[-1]
            if len(lista_valores) > 4:
                brancos = lista_valores[-2]
            else:
                brancos = 0
            if len(lista_valores) == 0:
                pontos, percentual = 0, '0%'
            elif len(lista_valores) < 4:
                pontos, percentual = lista_valores[0], lista_valores[-1]
    
            r_pontos[nome_coluna], r_percentual[nome_coluna] = pontos, percentual
            if len(lista_valores) >= 4:
                r_acertos[nome_coluna], r_erros[nome_coluna], r_brancos[nome_coluna] = acertos, erros, brancos
        
        l_pontos.append(r_pontos)
        l_acertos.append(r_acertos)
        l_erros.append(r_erros)
        l_brancos.append(r_brancos)
        l_percentual.append(r_percentual)
        print('.', end='')
    
    print('')
    return {
        "lista_pontos": state["lista_pontos"] + l_pontos,
        "lista_acertos": state["lista_acertos"] + l_acertos,
        "lista_erros": state["lista_erros"] + l_erros,
        "lista_brancos": state["lista_brancos"] + l_brancos,
        "lista_percentual": state["lista_percentual"] + l_percentual
    }

def should_continue(state: ExtractorState) -> str:
    if state["pagina_corrente"] < state["numero_paginas"]:
        return "next_page"
    return "save_data"

def next_page(state: ExtractorState) -> ExtractorState:
    driver = state["driver"]
    bt_navegacao(driver, 'next')
    time.sleep(5)
    
    # Update current page from DOM to ensure sync
    _, pagina_corrente, _ = get_navegacao(driver)
    return {"pagina_corrente": pagina_corrente}

def save_data(state: ExtractorState) -> ExtractorState:
    print("\nEstruturando os dados extraídos...")
    df_pontos = pd.DataFrame(state["lista_pontos"], dtype='string')
    df_acertos = pd.DataFrame(state["lista_acertos"], dtype='string')
    df_erros = pd.DataFrame(state["lista_erros"], dtype='string')
    df_brancos = pd.DataFrame(state["lista_brancos"], dtype='string')
    df_percentual = pd.DataFrame(state["lista_percentual"], dtype='string')

    df_pontos['tipo'] = 'pontos'
    df_acertos['tipo'] = 'acertos'
    df_erros['tipo'] = 'erros'
    df_brancos['tipo'] = 'brancos'
    df_percentual['tipo'] = 'percentual'
    
    print("Consolidando o arquivo final...")
    df_unified = pd.concat([df_pontos, df_acertos, df_erros, df_brancos, df_percentual], ignore_index=True)

    string_data = dt.datetime.now().strftime("%Y-%m-%d")
    string_hora = dt.datetime.now().strftime("%H-%M")
    
    pasta_destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', state["fisco_escolhido"], string_data)
    os.makedirs(pasta_destino, exist_ok=True)
    
    file_path = os.path.join(pasta_destino, f'{state["fisco_escolhido"]}_consolidado_{string_hora}.parquet')
    
    print(f"Salvando dados em {file_path}...")
    df_unified.to_parquet(file_path, compression='snappy')
    
    print(f'Sucesso! Arquivo extraído e salvo.')
    
    print("Fechando o navegador...")
    state["driver"].quit()
    return state

from langgraph.checkpoint.memory import MemorySaver

graph_builder = StateGraph(ExtractorState)

graph_builder.add_node("init_browser", init_browser)
graph_builder.add_node("perform_login", perform_login)
graph_builder.add_node("wait_for_captcha", wait_for_captcha)
graph_builder.add_node("select_ranking", select_ranking)
graph_builder.add_node("load_ranking", load_ranking)
graph_builder.add_node("extract_page", extract_page)
graph_builder.add_node("next_page", next_page)
graph_builder.add_node("save_data", save_data)

graph_builder.set_entry_point("init_browser")
graph_builder.add_edge("init_browser", "perform_login")
graph_builder.add_edge("perform_login", "wait_for_captcha")
graph_builder.add_edge("wait_for_captcha", "select_ranking")
graph_builder.add_edge("select_ranking", "load_ranking")
graph_builder.add_edge("load_ranking", "extract_page")

graph_builder.add_conditional_edges(
    "extract_page",
    should_continue,
    {
        "next_page": "next_page",
        "save_data": "save_data"
    }
)

graph_builder.add_edge("next_page", "extract_page")
graph_builder.add_edge("save_data", END)

memory = MemorySaver()
app = graph_builder.compile(checkpointer=memory)

def run():
    print("Para utilizar com o LangGraph Studio, execute o comando: npx @langchain/langgraph-cli dev")
    print("Ou então: uvx --from langgraph-cli langgraph dev")
    
    config = {"configurable": {"thread_id": "1"}}
    print("Iniciando rotina em terminal padrão (Atenção: A interrupção pode não funcionar da mesma maneira que no painel Studio)...")
    
    for event in app.stream({"fisco_escolhido": "sefaz-pi"}, config):
        for value in event.values():
            print("Executado nó:", value)

if __name__ == "__main__":
    run()
