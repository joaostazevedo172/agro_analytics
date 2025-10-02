import cx_Oracle
import sys
from datetime import datetime, timedelta
import os 
import shutil 
import time 
import requests 
import json # NOVO: Importa o módulo JSON

# ====================================================================
# CONFIGURAÇÃO DE AMBIENTE E CREDENCIAIS
# ====================================================================

# O CAMINHO DEVE SER O LOCAL EXATO DA OCI.DLL!
INSTANT_CLIENT_DIR = r"C:\oracle\instantclient_21_9\instantclient-basic-windows.x64-23.9.0.25.07\instantclient_23_9" 

try:
    # Este método FORÇA o Python a encontrar o cliente Oracle
    cx_Oracle.init_oracle_client(lib_dir=INSTANT_CLIENT_DIR)
except Exception as e:
    # print(f"Aviso: Falha ao inicializar o cliente Oracle. Usando a configuração de ambiente. {e}")
    pass

# CONFIGURAÇÕES GERAIS E CREDENCIAIS
LIMITE_ALERTA_RISCO = 10.0  # Fixo para Cana-de-Açúcar
CULTURA_ATUAL = "CANA-DE-AÇÚCAR" # Fixo
ARQUIVO_TEXTO_PADRAO = "registros_colheita.txt" # NOVO: Nome do arquivo de texto
ARQUIVO_JSON_PADRAO = "registros_colheita.json" # NOVO: Nome do arquivo JSON

# Dados de conexão com o Oracle (SEUS DADOS INSERIDOS AQUI)
ORACLE_USER = "rm566701"
ORACLE_PASSWORD = "fiap25"
ORACLE_HOST = "oracle.fiap.com.br"
ORACLE_PORT = 1521
ORACLE_SID = "ORCL"
TABELA_COLHEITAS = "COLHEITAS"  # Tabela de registros de colheita
TABELA_PLANEJAMENTO = "PLANEJAMENTO" # NOVA Tabela de planejamento

# Mapeamento para simular viabilidade e REGIONALIZAÇÃO DE PLANTIO
MAPA_VIABILIDADE_CANASIMULADO = {
    'SP': ('CENTRO-SUL', True), 'GO': ('CENTRO-SUL', True), 'MG': ('CENTRO-SUL', True), 'MS': ('CENTRO-SUL', True), 
    'PR': ('CENTRO-SUL', True), 'MT': ('CENTRO-SUL', True), 
    'AL': ('NORDESTE', True), 'PE': ('NORDESTE', True), 'PB': ('NORDESTE', True), 'BA': ('NORDESTE', True),
    'RJ': ('OUTRAS', True), 'ES': ('OUTRAS', True), 'DF': ('OUTRAS', True),
    'CE': ('OUTRAS', False), 'MA': ('OUTRAS', False), 'PI': ('OUTRAS', False), 'PA': ('OUTRAS', False), 'AM': ('OUTRAS', False), 'RR': ('OUTRAS', False), 'AP': ('OUTRAS', False), 'RO': ('OUTRAS', False), 'AC': ('OUTRAS', False), 
    'DF': ('OUTRAS', True), 'SC': ('OUTRAS', False), 'RS': ('OUTRAS', False)
}

# ====================================================================
# FUNÇÕES DE VALIDAÇÃO (Consistência de Dados)
# ====================================================================

def validar_float(mensagem):
    """ Função que força o usuário a digitar um float válido e non-negativo. """
    while True:
        try:
            valor = input(mensagem)
            valor_float = float(valor.replace(',', '.'))
            if valor_float < 0:
                print("⚠️ O valor deve ser non-negativo.")
                continue
            return valor_float
        except ValueError:
            print("❌ ERRO: Por favor, digite um número válido (ex: 95.5 ou 100).")

def validar_data(mensagem, formato='%Y-%m-%d', tentativas=3):
    """ Função que força o usuário a digitar uma data no formato AAAA-MM-DD. """
    tentativas_restantes = tentativas
    while tentativas_restantes > 0:
        data_str = input(mensagem)
        try:
            datetime.strptime(data_str, formato)
            return data_str
        except ValueError:
            tentativas_restantes -= 1
            print(f"❌ ERRO: Formato de data inválido. Você tem {tentativas_restantes} tentativas restantes.")
            if tentativas_restantes == 0:
                sys.exit()

# ====================================================================
# FUNÇÕES DE LÓGICA AGRONÔMICA E ESTIMATIVA
# ====================================================================

def simular_api_localidade(estado):
    """ Simula a consulta de viabilidade de área de plantio de cana por Estado (UF). """
    estado = estado.strip().upper()
    regiao, viabilidade = MAPA_VIABILIDADE_CANASIMULADO.get(estado, ('OUTRAS', False))
    if viabilidade:
        motivo = "Solo argiloso, temperatura ideal."
    else:
        motivo = "Condições desfavoráveis."
    return regiao, viabilidade, motivo

def avaliar_epoca_plantio(mes_plantio, regiao):
    """ Avalia a melhor época de plantio com base na região. """
    mes_plantio = int(mes_plantio)
    if regiao == 'CENTRO-SUL':
        if 10 <= mes_plantio <= 12 or 1 <= mes_plantio <= 4:
            return True, "Época ideal (Plantio de Ano e Meio/Meia-Safra)."
        else:
            return False, "Risco de seca/geada (Plantio fora da janela de chuva)."
    
    elif regiao == 'NORDESTE':
        if 3 <= mes_plantio <= 5:
            return True, "Época ideal (Início das chuvas na região)."
        else:
            return False, "Risco de estresse hídrico (seca)."

    else:
        return True, "Época considerada neutra/ideal para esta região."

def simular_controle_pragas(mes_plantio):
    """ Simula a análise de risco de pragas (Ex: Broca da Cana), dando um motivo. """
    mes = int(mes_plantio)
    
    if mes in [12, 1, 2, 3]:
        risco = "Alto"
        motivo = "Verão/Umidade alta, favorecendo a atividade da Broca da Cana."
    elif mes in [9, 10, 11]:
        risco = "Moderado"
        motivo = "Aumento do risco devido à primavera e retomada do crescimento."
    else:
        risco = "Baixo"
        motivo = "Risco reduzido devido às baixas temperaturas (Inverno)."
        
    return risco, motivo

def planejar_colheita_escalonada():
    """ Gera uma sugestão de planejamento de colheita. """
    hoje = datetime.now()
    inicio_colheita = hoje.replace(month=4, day=1) 
    
    fase1_eng = inicio_colheita.strftime("%b/%Y")
    fase2_eng = (inicio_colheita + timedelta(days=60)).strftime("%b/%Y")
    fase3_eng = (inicio_colheita + timedelta(days=120)).strftime("%b/%Y")
    
    # Tradução para Português
    def formatar_mes_pt(data_str):
        mes_map = {'Jan': 'Jan', 'Feb': 'Fev', 'Mar': 'Mar', 'Apr': 'Abr', 'May': 'Mai', 'Jun': 'Jun',
                   'Jul': 'Jul', 'Aug': 'Ago', 'Sep': 'Set', 'Oct': 'Out', 'Nov': 'Nov', 'Dec': 'Dez'}
        mes_eng = data_str.split('/')[0]
        mes_pt = mes_map.get(mes_eng, mes_eng)
        return data_str.replace(mes_eng, mes_pt)
    
    fase1_pt = formatar_mes_pt(fase1_eng)
    fase2_pt = formatar_mes_pt(fase2_eng)
    fase3_pt = formatar_mes_pt(fase3_eng)
    
    return f"Fase 1: {fase1_pt}; Fase 2: {fase2_pt}; Fase 3: {fase3_pt}"

def estimar_perda_planejada(estado_uf, mes_plantio):
    """
    Estima um valor de perda (em t/ha) baseado nas condições de plantio (modelo agronômico).
    """
    perda_base = 5.0 # Perda base mínima e ideal
    motivos = ["Condições ideais de plantio."]
    
    regiao, viabilidade_ok, _ = simular_api_localidade(estado_uf)

    epoca_ok, motivo_epoca = avaliar_epoca_plantio(mes_plantio, regiao)
    if not epoca_ok:
        perda_base += 3.0
        motivos.append(f"Época de plantio sub-ótima: {motivo_epoca}")
        
    if not viabilidade_ok:
        perda_base += 4.0
        motivos.append("Viabilidade da área baixa.")
        
    risco_praga, motivo_praga = simular_controle_pragas(mes_plantio)
    if 'Alto' in risco_praga:
        perda_base += 2.0 
        motivos.append(f"Risco de pragas alto: {motivo_praga}")

    if len(motivos) > 1 and "Condições ideais de plantio." in motivos:
        motivos.remove("Condições ideais de plantio.")
        
    motivo_final = " | ".join(motivos)
    if not motivo_final:
        motivo_final = "Condições ideais de plantio."
        
    perda_estimada = round(max(5.0, perda_base), 2)
    return perda_estimada, motivo_final


# ====================================================================
# FUNÇÕES DE CADASTRO E ESTRUTURA DE DADOS (AGORA AUTOMATIZADA)
# ====================================================================

def cadastrar_nova_colheita(registros):
    """ 
    Cria um novo dicionário de colheita. Integra o planejamento agronômico
    para realizar a previsão de perda e valorização.
    """
    # NOVO: Acha o próximo ID corretamente, considerando IDs de arquivos também
    max_id = 0
    if registros:
        # Garante que o ID é um número e pega o máximo
        max_id = max(reg.get('id', 0) for reg in registros if isinstance(reg.get('id'), (int, float))) 
    novo_id = int(max_id) + 1
    
    PRECO_TONELADA_SIMULADO = 130.00 # Valor simulado para cálculo financeiro
    
    print("\n--- 1. COLETA DE DADOS GERAIS E PLANEJAMENTO ---")
    
    # 1. LOCALIDADE E ÉPOCA (Inputs para a Estimativa)
    estado_uf = input("1. [PLANEJAMENTO] Informe a UF da colheita (Ex: SP): ").strip().upper()
    while True:
        try:
            mes = int(input("2. [PLANEJAMENTO] Informe o MÊS de plantio (1-12): "))
            if 1 <= mes <= 12: break
            else: print("Mês inválido.")
        except ValueError:
            print("Digite apenas o número do mês.")
    
    # 2. Executa as análises de viabilidade e risco e exibe o relatório
    regiao, viabilidade, motivo_viabilidade = simular_api_localidade(estado_uf)
    epoca_ideal, motivo_epoca = avaliar_epoca_plantio(mes, regiao)
    risco_praga, recomendacao_praga = simular_controle_pragas(mes)
    sugestao_colheita = planejar_colheita_escalonada()

    # 3. Exibe o Planejamento Detalhado (Usabilidade)
    print("\n" + "="*55)
    print(f"      RELATÓRIO DE VIABILIDADE E PLANEJAMENTO DE {estado_uf}      ")
    print("="*55)
    print(f"➡️ REGIÃO: {regiao}")
    print(f"➡️ VIABILIDADE DA ÁREA: {'✅ BOA' if viabilidade else '❌ BAIXA'}. Motivo: {motivo_viabilidade}")
    print(f"➡️ ÉPOCA DE PLANTIO: {'✅ IDEAL' if epoca_ideal else '🟠 RISCO'}. Motivo: {motivo_epoca}")
    print(f"➡️ RISCO DE PRAGAS: {risco_praga}. Recomendação: {recomendacao_praga}")
    print("="*55)
    
    # 4. Obtém a PERDA ESTIMADA e automatiza o PREÇO
    perda_estimada_tha, motivo_perda_estimada = estimar_perda_planejada(estado_uf, mes)
    
    print("\n--- 2. REGISTRO DE DADOS AUTOMÁTICOS ---")
    
    # CAMPOS GERAIS
    talhao = input("3. Identificação do Talhão (Ex: T009): ").strip().upper()
    maquina_id = input("4. ID da Máquina/Colhedora: ").strip().upper()
    
    # PRODUTIVIDADE ESPERADA (ÚLTIMO INPUT NECESSÁRIO)
    produtividade_esp = validar_float("5. Produtividade ESPERADA (t/ha): ")
    
    # A DATA DE COLHEITA É A ULTIMA DATA REGISTRADA NO SISTEMA
    data_colheita = datetime.now().strftime("%Y-%m-%d")

    # EXIBIÇÃO FINAL DA AUTOMATIZAÇÃO
    print(f"\n[INFO] Perda Registrada (t/ha) será: {perda_estimada_tha:.2f} (Estimativa do Sistema)")
    print(f"[INFO] Preço da Tonelada (R$/t) será: R$ {PRECO_TONELADA_SIMULADO:.2f} (Valor Simulado)")

    # CRIAÇÃO DO DICIONÁRIO (CAMPOS DE PERDA E PREÇO SÃO AUTOMÁTICOS)
    novo_registro = {
        "id": novo_id,
        "talhao": talhao,
        "maquina_id": maquina_id,
        "produtividade_esperada_tha": produtividade_esp,
        "perda_registrada_tha": perda_estimada_tha, # DADO ESTIMADO
        "data_colheita": data_colheita,
        "preco_tonelada": PRECO_TONELADA_SIMULADO, # DADO AUTOMÁTICO
        "motivo_perda_estimada": motivo_perda_estimada, # NOVO CAMPO DE MOTIVO
    }
    
    registros.append(novo_registro)
    print(f"\n✅ Registro de Colheita {novo_id} cadastrado com sucesso (em memória).")


# ====================================================================
# NOVAS FUNÇÕES DE PERSISTÊNCIA EM ARQUIVO (TEXTO E JSON)
# ====================================================================

def salvar_em_arquivo_texto(dados, nome_arquivo=ARQUIVO_TEXTO_PADRAO):
    """ Salva a lista de dicionários em um arquivo de texto formatado (CSV simples). """
    try:
        if not dados:
            print("⚠️ Nenhum dado para salvar.")
            return

        # Pega as chaves de um registro para usar como cabeçalho
        chaves = list(dados[0].keys())
        
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            # Escreve o cabeçalho (separado por |)
            f.write("|".join(chaves) + "\n")
            
            # Escreve cada registro
            for reg in dados:
                valores = [str(reg.get(chave, '')) for chave in chaves]
                f.write("|".join(valores) + "\n")
                
        print(f"\n✅ Dados salvos com sucesso em arquivo de texto: {nome_arquivo}")
    except Exception as e:
        print(f"❌ ERRO ao salvar em arquivo de texto: {e}")

def carregar_de_arquivo_texto(nome_arquivo=ARQUIVO_TEXTO_PADRAO):
    """ Carrega a lista de dicionários de um arquivo de texto formatado (CSV simples). """
    registros = []
    try:
        if not os.path.exists(nome_arquivo):
            print(f"⚠️ Arquivo de texto não encontrado: {nome_arquivo}. Iniciando com lista vazia.")
            return []
            
        with open(nome_arquivo, 'r', encoding='utf-8') as f:
            linhas = f.readlines()
            if not linhas:
                print(f"⚠️ Arquivo {nome_arquivo} está vazio.")
                return []
                
            # A primeira linha é o cabeçalho
            chaves = linhas[0].strip().split("|")
            
            # Processa as demais linhas
            for linha in linhas[1:]:
                valores = linha.strip().split("|")
                if len(valores) != len(chaves):
                    print(f"⚠️ Aviso: Linha ignorada por formato inválido: {linha.strip()}")
                    continue
                    
                registro = {}
                for i, chave in enumerate(chaves):
                    valor_str = valores[i]
                    # Tenta converter para o tipo correto (int/float)
                    try:
                        if chave in ['id']:
                            registro[chave] = int(valor_str)
                        elif chave in ['produtividade_esperada_tha', 'perda_registrada_tha', 'preco_tonelada']:
                            registro[chave] = float(valor_str)
                        else:
                            registro[chave] = valor_str
                    except ValueError:
                        registro[chave] = valor_str # Mantém como string se a conversão falhar
                        
                registros.append(registro)

        print(f"\n✅ Dados carregados com sucesso do arquivo de texto: {nome_arquivo}. Total de {len(registros)} registros.")
        return registros
        
    except Exception as e:
        print(f"❌ ERRO ao carregar de arquivo de texto: {e}")
        return []

def salvar_em_json(dados, nome_arquivo=ARQUIVO_JSON_PADRAO):
    """ Salva a lista de dicionários em um arquivo JSON. """
    try:
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        print(f"\n✅ Dados salvos com sucesso em arquivo JSON: {nome_arquivo}")
    except Exception as e:
        print(f"❌ ERRO ao salvar em JSON: {e}")

def carregar_de_json(nome_arquivo=ARQUIVO_JSON_PADRAO):
    """ Carrega a lista de dicionários de um arquivo JSON. """
    try:
        if not os.path.exists(nome_arquivo):
            print(f"⚠️ Arquivo JSON não encontrado: {nome_arquivo}. Iniciando com lista vazia.")
            return []
            
        with open(nome_arquivo, 'r', encoding='utf-8') as f:
            registros = json.load(f)
            
        print(f"\n✅ Dados carregados com sucesso do arquivo JSON: {nome_arquivo}. Total de {len(registros)} registros.")
        return registros
        
    except json.JSONDecodeError:
        print(f"❌ ERRO de decodificação JSON: O arquivo {nome_arquivo} está corrompido ou mal formatado.")
        return []
    except Exception as e:
        print(f"❌ ERRO ao carregar de JSON: {e}")
        return []

# ====================================================================
# FUNÇÕES DE CÁLCULO E ANÁLISE (SUBALGORITMOS)
# ====================================================================

def calcular_perda_percentual(perda_tha, produtividade_esperada_tha):
    """ Função para calcular a perda em percentual. """
    # TRATAMENTO DE ERRO: Garante que se o prod_esp for 0, o cálculo é 0 para evitar a divisão por zero.
    if produtividade_esperada_tha > 0:
        return (perda_tha / produtividade_esperada_tha) * 100
    return 0.0

def calcular_perda_media_por_maquina(registros):
    """ Calcula a perda média percentual por máquina, usando Dicionários para agregação. """
    perdas_por_maquina = {}
    
    for reg in registros:
        # Garante que os valores são numéricos, tratando a possibilidade de 'None' ou strings vazias após o carregamento
        try:
            perda_tha = float(reg.get('perda_registrada_tha') or 0)
            prod_esp = float(reg.get('produtividade_esperada_tha') or 1)
            maquina = reg['maquina_id']
        except (ValueError, TypeError, KeyError):
            continue # Ignora registros mal formatados

        perda_perc = calcular_perda_percentual(perda_tha, prod_esp)
        
        if maquina not in perdas_por_maquina:
            perdas_por_maquina[maquina] = {'total_perda': 0.0, 'contagem': 0}
            
        perdas_por_maquina[maquina]['total_perda'] += perda_perc
        perdas_por_maquina[maquina]['contagem'] += 1
        
    medias_finais = {}
    for maquina, dados in perdas_por_maquina.items():
        media = dados['total_perda'] / dados['contagem']
        medias_finais[maquina] = media
        
    return medias_finais

def exibir_relatorio_analitico(registros):
    """ Apresenta um relatório detalhado e um resumo analítico formatado. """
    if not registros:
        print("\n🚫 Nenhum registro de colheita para analisar.")
        return

    largura_total = 95 # Reduzido para remover a coluna de prejuízo
    print("\n" + "="*largura_total) 
    print(f"         AGRO_ANALYTICS: RELATÓRIO DE PERDAS DE {CULTURA_ATUAL.upper()}             ")
    print(f"OBJETIVO: Identificar operações com perdas acima do limite crítico ({LIMITE_ALERTA_RISCO:.1f}%).")
    print("="*largura_total)
    
    # RELATÓRIO DETALHADO (Usabilidade) - Removendo a coluna de prejuízo
    print(f"{'ID':<4} | {'TALHÃO':<6} | {'MÁQUINA':<18} | {'PERDA %':<8} | {'STATUS':<15} | {'MOTIVO DA PERDA ESTIMADA':<40}")
    print("-" * largura_total)

    for reg in registros:
        # Puxando valores de forma segura (CORREÇÃO DE LEITURA)
        try:
            perda_tha = float(reg.get('perda_registrada_tha', 0) or 0)
            preco_t = float(reg.get('preco_tonelada', 0) or 0) 
            prod_esp = float(reg.get('produtividade_esperada_tha', 1) or 1) 
        except (ValueError, TypeError):
            continue # Pula registros com valores numéricos inválidos

        # CÁLCULOS
        perda_perc = calcular_perda_percentual(perda_tha, prod_esp)
        
        if perda_perc > LIMITE_ALERTA_RISCO:
            status = "🚨 ALTO RISCO" 
        elif perda_perc > (LIMITE_ALERTA_RISCO / 2):
            status = "🟠 ATENÇÃO"
        else:
            status = "✅ OK"
            
        motivo = reg.get('motivo_perda_estimada', 'Não registrado').ljust(40) 
            
        print(f"{reg['id']:<4} | {reg['talhao']:<6} | {reg['maquina_id']:<18} | {perda_perc:<8.2f} | {status:<15} | {motivo}")

    print("="*95)

    # RELATÓRIO SUMÁRIO POR MÁQUINA
    print("\n--- ANÁLISE SUMÁRIA: PERDA MÉDIA POR MÁQUINA ---")
    medias = calcular_perda_media_por_maquina(registros)
    
    if medias:
        for maquina, media in medias.items():
            alerta = "(ALERTA)" if media > LIMITE_ALERTA_RISCO else ""
            print(f"Máquina {maquina}: {media:.2f}% de perda média {alerta}")
    else:
        print("Nenhuma máquina registrada para análise.")
    print("-" * 50)


# ====================================================================
# FUNÇÕES DE CONEXÃO E PERSISTÊNCIA (ORACLE)
# ====================================================================

def conectar_oracle():
    """ 
    Estabelece uma conexão com o banco de dados Oracle.
    Ajuste de Rede: Usa TNS String completa para estabilidade.
    """
    try:
        tns_string = (
            f"(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST={ORACLE_HOST})(PORT={ORACLE_PORT})))"
            f"(CONNECT_DATA=(SERVICE_NAME={ORACLE_SID})(SERVER=DEDICATED))"
            f"(ENABLE=BROKEN)(EXPIRE_TIME=10))" 
        )
        
        connection = cx_Oracle.connect(
            user=ORACLE_USER, 
            password=ORACLE_PASSWORD, 
            dsn=tns_string 
        )
        print("Conexão com Oracle estabelecida com sucesso!")
        return connection
    except cx_Oracle.Error as e:
        print(f"\n[ERRO CRÍTICO] Falha ao conectar com o banco de dados Oracle. Verifique as credenciais e o status do servidor.")
        print(f"Detalhes do Erro: {e}")
        sys.exit(1)

def carregar_dados_oracle(connection):
    """ Carrega os registros de colheita do banco de dados Oracle. """
    cursor = connection.cursor()
    try:
        query = f"SELECT id, talhao, maquina_id, produtividade_esperada_tha, perda_registrada_tha, data_colheita, preco_tonelada FROM {TABELA_COLHEITAS}"
        cursor.execute(query)
        registros = cursor.fetchall()
        print(f"Dados carregados com sucesso. Total de {len(registros)} registros do Oracle.")
        
        registros_dict = []
        for reg in registros:
            registros_dict.append({
                'id': reg[0],
                'talhao': reg[1],
                'maquina_id': reg[2],
                'produtividade_esperada_tha': float(reg[3] or 1), 
                'perda_registrada_tha': float(reg[4] or 0),
                'data_colheita': str(reg[5]).split()[0], # Garante apenas a data
                'preco_tonelada': float(reg[6] or 0),
                'motivo_perda_estimada': 'Não aplicável (DB)'
            })
        return registros_dict

    except cx_Oracle.Error as e:
        print(f"[ERRO] Falha ao carregar os dados do banco de dados: {e}")
        return []
    finally:
        # CORREÇÃO DPI-1010: Verifica se o cursor existe antes de fechar
        if 'cursor' in locals() and cursor:
            try:
                cursor.close()
            except cx_Oracle.Error:
                pass # Ignora o erro se a conexão já estiver fechada/inválida

def salvar_dados_oracle(dados, connection):
    """ 
    Persiste os dados, contornando o erro de Duplicação (ORA-00001).
    Possui a correção para o erro DPI-1010 no bloco finally.
    """
    cursor = connection.cursor()
    try:
        print("\n[INFO] Persistindo novos e antigos registros (Duplicatas serão ignoradas)...")
        
        for registro in dados:
            # Converte a data para o formato correto
            data_colheita_str = str(registro['data_colheita']).split()[0]
            data_colheita_formatada = datetime.strptime(data_colheita_str, '%Y-%m-%d').strftime('%Y-%M-%D')
            
            # Remove chaves não presentes na tabela COLHEITAS
            registro_db = {k: v for k, v in registro.items() if k not in ('motivo_perda_estimada', 'area_total_ha')}
            registro_db['data_colheita'] = data_colheita_formatada 
            
            try:
                sql_insert = f"""
                    INSERT INTO {TABELA_COLHEITAS} (id, talhao, maquina_id, produtividade_esperada_tha, 
                                                     perda_registrada_tha, data_colheita, preco_tonelada) 
                    VALUES (:id, :talhao, :maquina_id, :produtividade_esperada_tha, 
                            :perda_registrada_tha, TO_DATE(:data_colheita, 'YYYY-MM-DD'), :preco_tonelada)
                """
                # Correção: O formato de data no TO_DATE deve ser 'YYYY-MM-DD'
                sql_insert = sql_insert.replace("'YYYY-MM-DD'", "'YYYY-MM-DD'") 
                
                cursor.execute(sql_insert, registro_db)
                
            except cx_Oracle.IntegrityError as e:
                if e.args[0].code == 1:
                    continue # Ignora a duplicata
            except cx_Oracle.Error as e:
                print(f"   [ERRO SQL] Falha na inserção do registro ID {registro['id']}: {e}")
                continue
        
        connection.commit()
        print("\n✅ Persistência de dados finalizada no Oracle.")

    except cx_Oracle.Error as e:
        print(f"[ERRO] Falha ao salvar os dados no banco de dados: {e}")
        connection.rollback()
    finally:
        # ✅ CORREÇÃO DPI-1010: Verifica se o cursor existe antes de fechar
        if 'cursor' in locals() and cursor:
            try:
                cursor.close()
            except cx_Oracle.Error:
                pass # Ignora o erro se a conexão já estiver fechada/inválida

def remover_colheita_oracle(id_remover, connection):
    """ Remove um registro de colheita do banco de dados Oracle. """
    cursor = connection.cursor()
    try:
        cursor.execute(f"DELETE FROM {TABELA_COLHEITAS} WHERE id = :id", {'id': id_remover})
        connection.commit()
        
        if cursor.rowcount > 0:
            print(f"\n✅ Registro {id_remover} removido com sucesso do banco de dados.")
            return True
        else:
            print(f"\n⚠️ ID {id_remover} não encontrado no banco de dados.")
            return False

    except cx_Oracle.Error as e:
        print(f"[ERRO] Falha ao remover o registro do banco de dados: {e}")
        connection.rollback()
        return False
    finally:
        # CORREÇÃO DPI-1010: Verifica se o cursor existe antes de fechar
        if 'cursor' in locals() and cursor:
            try:
                cursor.close()
            except cx_Oracle.Error:
                pass # Ignora o erro se a conexão já estiver fechada/inválida


# ====================================================================
# PROCEDIMENTO PRINCIPAL (FLUXO DO SISTEMA)
# ====================================================================

def menu_salvar_carregar(registros):
    """ Novo submenu para salvar e carregar dados em arquivo. """
    while True:
        print("\n--- OPÇÕES DE ARQUIVO (TEXTO/JSON) ---")
        print("1. Salvar Dados em Arquivo de Texto")
        print("2. Carregar Dados de Arquivo de Texto (Substitui dados em memória)")
        print("3. Salvar Dados em Arquivo JSON")
        print("4. Carregar Dados de Arquivo JSON (Substitui dados em memória)")
        print("5. Retornar ao Menu Principal")
        
        opcao = input("Escolha uma opção: ").strip()
        
        if opcao == '1':
            salvar_em_arquivo_texto(registros)
        elif opcao == '2':
            novos_registros = carregar_de_arquivo_texto()
            if novos_registros is not None:
                # O retorno é a lista de registros atualizada
                return novos_registros 
        elif opcao == '3':
            salvar_em_json(registros)
        elif opcao == '4':
            novos_registros = carregar_de_json()
            if novos_registros is not None:
                # O retorno é a lista de registros atualizada
                return novos_registros
        elif opcao == '5':
            return registros # Retorna a lista atual sem alteração
        else:
            print("❌ Opção inválida. Tente novamente.")

def menu_principal():
    """ Gerencia o loop principal do sistema. (ATUALIZADO) """
    global CULTURA_ATUAL, LIMITE_ALERTA_RISCO

    # 0. CONFIGURAÇÃO INICIAL (Fixo para Cana)
    CULTURA_ATUAL = "CANA-DE-AÇÚCAR"
    LIMITE_ALERTA_RISCO = 10.0 
    print(f"\n--- INICIANDO AGRO_ANALYTICS PARA CULTURA: {CULTURA_ATUAL} ---")

    # 1. Estabelece a conexão (Conexão com Banco de Dados)
    connection = conectar_oracle()
    
    # 2. Carrega os dados do banco (SELECT)
    registros = carregar_dados_oracle(connection)
    
    while True:
        print(f"\n\n--- AGRO_ANALYTICS: CULTURA: {CULTURA_ATUAL.upper()} ---")
        print("1. Cadastrar Novo Registro de Colheita (Com Planejamento Integrado)")
        print("2. Visualizar Relatório Analítico (Perdas)")
        print("3. Remover Registro de Colheita (DB e memória)")
        print("4. Opções de Arquivo (Salvar/Carregar TXT ou JSON)") # NOVO MENU
        print("5. Salvar Dados no Oracle (COMMIT) e Sair") 
        
        opcao = input("Escolha uma opção: ").strip()
        
        if opcao == '1':
            cadastrar_nova_colheita(registros)
        
        elif opcao == '2':
            exibir_relatorio_analitico(registros)
            
        elif opcao == '3':
            if not registros:
                print("\n🚫 Nenhum registro para remover.")
                continue

            try:
                print("\nIDs de Colheitas Atuais (em memória):")
                for reg in registros:
                    print(f" - ID {reg.get('id', 'N/A')}: Talhão {reg.get('talhao', 'N/A')}")
                
                id_remover = int(input("\nInforme o ID do registro a ser removido: "))
                
                # Tenta remover do banco (DELETE)
                removido_do_db = remover_colheita_oracle(id_remover, connection)
                
                # Se removido do DB, atualiza a lista em memória (Coerência)
                if removido_do_db:
                    registros = [reg for reg in registros if reg.get('id') != id_remover]
                
            except ValueError:
                print("❌ ERRO: O ID deve ser um número inteiro.")
        
        elif opcao == '4':
            # CHAMA O NOVO SUBMENU
            registros_atualizados = menu_salvar_carregar(registros)
            if registros_atualizados is not None:
                registros = registros_atualizados # Atualiza a lista em memória
        
        elif opcao == '5':
            # Salva no Oracle e sai
            salvar_dados_oracle(registros, connection) 
            connection.close()
            print("\nSistema encerrado. Sucesso na gestão Agrotech!")
            break
        
        else:
            print("❌ Opção inválida. Tente novamente.")

# Ponto de entrada principal
if __name__ == "__main__":
    menu_principal()