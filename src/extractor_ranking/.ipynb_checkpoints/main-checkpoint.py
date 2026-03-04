import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import pandas as pd
import datetime as dt
import os

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

    # trata colunas com nomes repetidos
    for coluna in nome_colunas:
        indices_repetido = [i for i, c in enumerate(nome_colunas) if c == coluna]
        if len(indices_repetido) > 1:
            for i in range(len(indices_repetido)):
                nome_colunas[indices_repetido[i]] = nome_colunas[indices_repetido[i]] + '_' + str(i + 1)
            
    return nome_colunas

def get_ranking_page(driver):
    thead_ranking = driver.find_elements(By.XPATH, '//thead[@id="form:tabView:dataTable0_head"]')
    tbody_ranking = driver.find_elements(By.XPATH, '//tbody[@id="form:tabView:dataTable0_data"]')
    
    elemento_hbody = thead_ranking[0]
    elemento_tbody = tbody_ranking[0]
    
    # Seleciona linhas
    nome_colunas = get_col_names(elemento_hbody.find_elements(By.TAG_NAME, "th"))
    linhas = elemento_tbody.find_elements(By.XPATH, './/tr[@data-ri]')
    print('Quantidade de linhas:', len(linhas),end='')
    
    lista_pontos = []
    lista_acertos = []
    lista_erros = []
    lista_brancos = []
    lista_percentual = []
    
    for linha in linhas:
        # Pega todas as células da linha
        celulas = linha.find_elements(By.TAG_NAME, "td")
        
        if not celulas:
            # Pula se for a linha do cabeçalho
            continue
            
        registro = {
            'posicao':celulas[0].text,
            'usuario':celulas[1].text,
        }
    
        registro_pontos = registro.copy()
        registro_acertos = registro.copy()
        registro_erros = registro.copy()
        registro_brancos = registro.copy()
        registro_percentual = registro.copy()
    
        n_cols = len(nome_colunas) - 2
        
        for n_col in range(n_cols):
            nome_coluna = nome_colunas[n_col + 2]
            
            lista_valores = celulas[n_col+2].text.replace('|','').split()
    
            # Valores normais de disciplina sem brancos
            if len(lista_valores) >= 4:
                pontos, acertos, erros  = lista_valores[0:3]
                percentual = lista_valores[-1]
                
            # Valores normais de disciplina com brancos
            if len(lista_valores) > 4:
                brancos = lista_valores[-2]
            else:
                brancos = 0
                
            if len(lista_valores) == 0:
                pontos  = 0
                percentual = '0%'
            elif len(lista_valores) < 4:
                pontos  = lista_valores[0]
                percentual = lista_valores[-1]
    
            registro_pontos[nome_coluna] = pontos
            registro_percentual[nome_coluna] = percentual
    
            if len(lista_valores) >= 4:
                registro_acertos[nome_coluna] = acertos
                registro_erros[nome_coluna] = erros
                registro_brancos[nome_coluna] = brancos
        
        lista_pontos.append(registro_pontos)
        lista_acertos.append(registro_acertos)
        lista_erros.append(registro_erros)
        lista_brancos.append(registro_brancos)
        lista_percentual.append(registro_percentual)
    
        print('.',end='')
    
    return lista_pontos, lista_acertos, lista_erros, lista_brancos, lista_percentual

def wait_for_page_load(driver):
    while True:
        page_state = driver.execute_script('return document.readyState;')
        if page_state == 'complete':
            break
        time.sleep(1)

def run():
    print("Iniciando o navegador...")

    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=145)
    
    print("Acessando a página de login...")
    driver.get("https://olhonavaga.com.br/login")
    wait_for_page_load(driver)
    
    print("----- CONFIGURAÇÃO DE LOGIN -----")
    email = input("Digite o email (ou pressione Enter para usar scarlosfreitas@gmail.com): ").strip()
    if not email:
        email = "scarlosfreitas@gmail.com"
        
    senha = input("Digite a senha (ou pressione Enter para usar a senha padrão): ").strip()
    if not senha:
        senha = "gv8b3t22yh8r"

    driver.find_element(By.NAME, "form:email").send_keys(email)
    driver.find_element(By.NAME, "form:password").send_keys(senha)
    
    print("Clicando no botão de login...")
    driver.find_element(By.NAME, "form:signInButton").click()
    
    print("\n" + "="*50)
    input("AÇÃO NECESSÁRIA:\n1. Por favor, vá ao navegador e resolva o CAPTCHA 'Não sou um robô'.\n2. Aguarde até que o login seja concluído (a página inicial apareça).\n3. Pressione ENTER aqui no terminal para continuar a extração...")
    print("="*50 + "\n")
    
    wait_for_page_load(driver)
    
    dict_fisco = {
        'sefaz-pi': 'https://olhonavaga.com.br/rankings/ranking?id=80578',
        'sefaz-pr': 'https://olhonavaga.com.br/rankings/ranking?id=79110',
        'sefaz-pe': 'https://olhonavaga.com.br/rankings/ranking?id=49551',
        'sefaz-mg': 'https://olhonavaga.com.br/rankings/ranking?id=47050',
        'sefaz-mt': 'https://olhonavaga.com.br/rankings/ranking?id=52584',
    }
    
    print("Rankings disponíveis:")
    for key in dict_fisco.keys():
        print(f" - {key}")
        
    fisco_escolhido = input("\nDigite o nome do ranking escolhido (padrão: sefaz-pi): ").strip()
    if not fisco_escolhido or fisco_escolhido not in dict_fisco:
        fisco_escolhido = 'sefaz-pi'
        
    print(f"\nAcessando o ranking de {fisco_escolhido}...")
    driver.get(dict_fisco[fisco_escolhido])
    wait_for_page_load(driver)
    
    # Espera extra para renderização dos dados do ranking
    time.sleep(3) 
    
    numero_insercoes, pagina_corrente, numero_paginas = get_navegacao(driver)
    
    print('Fisco: {} Inserções: {} Pagina: {}/{}'.format(fisco_escolhido.upper(), numero_insercoes,pagina_corrente,numero_paginas))
    
    if pagina_corrente != 1:
        bt_navegacao(driver, 'first')
        time.sleep(5)
        
    lista_pontos, lista_acertos, lista_erros, lista_brancos, lista_percentual = [],[],[],[],[]

    for i in range(1,numero_paginas+1):
        _, pagina_corrente, _ = get_navegacao(driver)
        print('Extraindo Pagina {}/{}'.format(pagina_corrente,numero_paginas))
        
        l_pontos, l_acertos, l_erros, l_brancos, l_percentual = get_ranking_page(driver)
        
        lista_pontos.extend(l_pontos)
        lista_acertos.extend(l_acertos)
        lista_erros.extend(l_erros)
        lista_brancos.extend(l_brancos)
        lista_percentual.extend(l_percentual)
        
        print('') # Nova linha após os pontos das linhas da tabela
              
        if pagina_corrente != numero_paginas:
            bt_navegacao(driver, 'next')
            time.sleep(5)
        else:
            print('Fim da extração das páginas.')
            break

    print("\nEstruturando os dados extraídos...")
    df_pontos = pd.DataFrame(lista_pontos, dtype='string')
    df_acertos = pd.DataFrame(lista_acertos, dtype='string')
    df_erros = pd.DataFrame(lista_erros, dtype='string')
    df_brancos = pd.DataFrame(lista_brancos, dtype='string')
    df_percentual = pd.DataFrame(lista_percentual, dtype='string')

    df_pontos['tipo'] = 'pontos'
    df_acertos['tipo'] = 'acertos'
    df_erros['tipo'] = 'erros'
    df_brancos['tipo'] = 'brancos'
    df_percentual['tipo'] = 'percentual'
    
    print("Consolidando o arquivo final...")
    df_unified = pd.concat([df_pontos, df_acertos, df_erros, df_brancos, df_percentual], ignore_index=True)

    string_data = dt.datetime.now().strftime("%Y-%m-%d")
    string_hora = dt.datetime.now().strftime("%H-%M")
    
    pasta_destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', fisco_escolhido, string_data)
    os.makedirs(pasta_destino, exist_ok=True)
    
    file_path = os.path.join(pasta_destino, f'{fisco_escolhido}_consolidado_{string_hora}.parquet')
    
    print(f"Salvando dados em {file_path}...")
    df_unified.to_parquet(file_path, compression='snappy')
    
    print(f'Sucesso! Arquivo extraído e salvo.')
    
    print("Fechando o navegador...")
    driver.quit()

if __name__ == "__main__":
    run()
