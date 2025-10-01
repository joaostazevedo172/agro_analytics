from flask import Flask, render_template, request, flash, redirect, url_for
import cx_Oracle
from datetime import datetime
import sys

# Inicializa o Flask
app = Flask(__name__)

# CHAVE SECRETA: Essencial para 'flash' e 'session'
app.secret_key = 'secret_key'

# Configurações do banco de dados e variáveis globais
INSTANT_CLIENT_DIR = r"C:\oracle\instantclient_21_9\instantclient-basic-windows.x64-23.9.0.25.07\instantclient_23_9" 
try:
    cx_Oracle.init_oracle_client(lib_dir=INSTANT_CLIENT_DIR)
except Exception as e:
    pass

LIMITE_ALERTA_RISCO = 10.0
CULTURA_ATUAL = "CANA-DE-AÇÚCAR"
PRECO_TONELADA_SIMULADO = 130.00

# Funções de cálculo e lógica agronômica (sem alterações)
def calcular_perda_percentual(perda_tha, produtividade_esperada_tha):
    if produtividade_esperada_tha > 0:
        return (perda_tha / produtividade_esperada_tha) * 100
    return 0.0

def simular_api_localidade(estado):
    estado = estado.strip().upper()
    MAPA_VIABILIDADE_CANASIMULADO = {
        'SP': ('CENTRO-SUL', True), 'GO': ('CENTRO-SUL', True), 'MG': ('CENTRO-SUL', True), 
        'AL': ('NORDESTE', True), 'PE': ('NORDESTE', True), 'RJ': ('OUTRAS', True), 
        'SC': ('OUTRAS', False)
    }
    regiao, viabilidade = MAPA_VIABILIDADE_CANASIMULADO.get(estado, ('OUTRAS', False))
    motivo = "Solo argiloso, temperatura ideal." if viabilidade else "Condições desfavoráveis."
    return regiao, viabilidade, motivo

def avaliar_epoca_plantio(mes_plantio, regiao):
    mes_plantio = int(mes_plantio)
    if regiao == 'CENTRO-SUL':
        if 10 <= mes_plantio <= 12 or 1 <= mes_plantio <= 4:
            return True, "Época ideal (Plantio de Ano e Meio/Meia-Safra)."
        else:
            return False, "Risco de seca/geada (Plantio fora da janela de chuva)."
    else:
        return True, "Época considerada neutra/ideal para esta região."

def simular_controle_pragas(mes_plantio):
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

def estimar_perda_planejada(estado_uf, mes_plantio):
    perda_base = 5.0
    motivos = []
    
    regiao, viabilidade_ok, _ = simular_api_localidade(estado_uf)
    epoca_ok, motivo_epoca = avaliar_epoca_plantio(mes_plantio, regiao)
    risco_praga, motivo_praga = simular_controle_pragas(mes_plantio)
    
    if not epoca_ok:
        perda_base += 3.0
        motivos.append(f"Época de plantio sub-ótima: {motivo_epoca}")
    if not viabilidade_ok:
        perda_base += 4.0
        motivos.append("Viabilidade da área baixa.")
    if risco_praga == "Alto":
        perda_base += 2.0
        motivos.append(f"Risco de pragas alto: {motivo_praga}")
    
    motivo_final = " | ".join(motivos) if motivos else "Condições ideais de plantio."
    perda_estimada = round(max(5.0, perda_base), 2)
    return perda_estimada, motivo_final

# Função de conexão com o Oracle (sem alterações)
def conectar_oracle():
    try:
        tns_string = (
            f"(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=oracle.fiap.com.br)(PORT=1521)))"
            f"(CONNECT_DATA=(SERVICE_NAME=ORCL)(SERVER=DEDICATED))"
            f"(ENABLE=BROKEN)(EXPIRE_TIME=10))" 
        )
        connection = cx_Oracle.connect(user="rm566701", password="fiap25", dsn=tns_string)
        return connection
    except Exception as e:
        print(f"Erro de Conexão com Oracle: {e}")
        return None

# Função para carregar dados históricos (sem alterações)
def carregar_dados_oracle():
    connection = conectar_oracle()
    registros = []
    if connection:
        cursor = connection.cursor()
        try:
            # Note: UF e MES_PLANTIO não estão neste SELECT. Adicione-os se precisar exibi-los.
            cursor.execute(f"SELECT id, talhao, maquina_id, produtividade_esperada_tha, perda_registrada_tha, data_colheita, preco_tonelada FROM COLHEITAS")
            dados_db = cursor.fetchall()
            for reg in dados_db:
                perda_perc = calcular_perda_percentual(reg[4], reg[3])
                preco_usado = reg[6] if reg[6] is not None else PRECO_TONELADA_SIMULADO
                prejuizo_por_ha = reg[4] * preco_usado
                registros.append({
                    'id': reg[0],
                    'talhao': reg[1],
                    'maquina': reg[2],
                    'perda_perc': f"{perda_perc:.2f}%",
                    'prejuizo_ha': f"R$ {prejuizo_por_ha:.2f}",
                    'status': "ALTO RISCO" if perda_perc > LIMITE_ALERTA_RISCO else "OK",
                })
        except Exception as e:
            print(f"Erro ao carregar dados do DB: {e}")
        finally:
            if connection:
                connection.close()
    return registros

# Rota para o formulário de planejamento (sem alterações)
@app.route('/')
def home_form():
    return render_template('dashboard.html', action='form')

# Rota para a análise e exibição dos resultados (ajustado para passar variáveis raw/display)
@app.route('/analyze', methods=['POST'])
def analyze_data():
    try:
        estado_uf = request.form['uf'].upper()
        mes = int(request.form['mes'])
        produtividade_esp = float(request.form['produtividade'])
        talhao = request.form['talhao']
        maquina_id = request.form['maquina_id']
        
        regiao, viabilidade, motivo_viabilidade = simular_api_localidade(estado_uf)
        epoca_ideal, motivo_epoca = avaliar_epoca_plantio(mes, regiao)
        risco_praga, recomendacao_praga = simular_controle_pragas(mes)
        sugestao_colheita = "Fase 1: Abril/2025; Fase 2: Junho/2025; Fase 3: Agosto/2025"
        perda_estimada_raw, motivo_perda_estimada = estimar_perda_planejada(estado_uf, mes)
        
        prejuizo_estimado_por_ha = perda_estimada_raw * PRECO_TONELADA_SIMULADO

        contexto = {
            'action': 'result',
            'uf': estado_uf,
            'mes': mes,
            'viabilidade': 'BOA' if viabilidade else 'BAIXA',
            'motivo_viabilidade': motivo_viabilidade,
            'epoca_status': 'IDEAL' if epoca_ideal else 'RISCO',
            'motivo_epoca': motivo_epoca,
            'risco_praga': risco_praga,
            'recomendacao_praga': recomendacao_praga,
            'perda_estimada_display': f"{perda_estimada_raw:.2f} t/ha", 
            'perda_estimada_raw': perda_estimada_raw, 
            'prejuizo_estimado': f"R$ {prejuizo_estimado_por_ha:.2f}",
            'sugestao_colheita': sugestao_colheita,
            'preco_tonelada': f"R$ {PRECO_TONELADA_SIMULADO:.2f}",
            'talhao': talhao,
            'maquina_id': maquina_id,
            'produtividade': produtividade_esp
        }
        
        return render_template('dashboard.html', **contexto)

    except Exception as e:
        flash(f"Erro no processamento da análise: {e}. Verifique se os dados de UF, Mês e Produtividade estão corretos.", "error")
        return redirect(url_for('home_form'))


# Rota para visualizar o dashboard com dados históricos (sem alterações)
@app.route('/dashboard')
def dashboard_view():
    dados_analiticos = carregar_dados_oracle()
    prejuizo_total_geral = sum(float(reg['prejuizo_ha'].replace('R$ ', '').replace(',', '.')) for reg in dados_analiticos if reg['prejuizo_ha'].replace('R$ ', '').replace(',', '.').replace('.', '', 1).isdigit())
    
    contexto = {
        'action': 'dashboard',
        'registros': dados_analiticos,
        'prejuizo_total': f"R$ {prejuizo_total_geral:.2f}",
    }
    
    return render_template('dashboard.html', **contexto)


@app.route('/save_to_db', methods=['POST'])
def save_to_db():
    connection = None
    try:
        # 1. Obter e limpar dados (CORREÇÃO: Incluir uf, mes e produtividade)
        uf = request.form['uf'] # <--- Linha que estava faltando ou fora de ordem!
        mes = int(request.form['mes'])
        produtividade = float(request.form['produtividade'])
        
        # Limpa e converte a perda estimada
        perda_estimada_raw = request.form['perda_estimada']
        perda_estimada = float(perda_estimada_raw.replace(' t/ha', '').strip()) 
        
        talhao = request.form['talhao']
        maquina_id = request.form['maquina_id']

        # 2. Conexão e Inserção no DB
        connection = conectar_oracle()
        if connection:
            cursor = connection.cursor()
            
            # SQL: Inclui UF e MES_PLANTIO.
            sql_insert = """
                INSERT INTO COLHEITAS (ID, uf, mes_plantio, produtividade_esperada_tha, perda_registrada_tha, talhao, maquina_id, data_colheita, preco_tonelada)
                VALUES (COLHEITAS_SEQ.NEXTVAL, :uf, :mes_plantio, :produtividade, :perda_estimada, :talhao, :maquina_id, SYSDATE, :preco_tonelada)
            """
            
            cursor.execute(sql_insert, {
                'uf': uf, 
                'mes_plantio': mes, # Usando a variável 'mes' agora
                'produtividade': produtividade, 
                'perda_estimada': perda_estimada, 
                'talhao': talhao, 
                'maquina_id': maquina_id,
                'preco_tonelada': PRECO_TONELADA_SIMULADO 
            })
            connection.commit()
            cursor.close()

            flash(f"Planejamento para o Talhão {talhao} salvo com sucesso! Perda registrada: {perda_estimada:.2f} t/ha.", "success")
        else:
            flash("Erro ao conectar ao banco de dados. A conexão com o Oracle falhou.", "error")

    except Exception as e:
        # Tratamento de erro final para o DB
        flash(f"Erro inesperado ao salvar: Certifique-se de que as colunas ID, UF e MES_PLANTIO existem e a SEQUENCE está correta. Detalhe: {e}", "error")
    
    finally:
        if connection:
            connection.close()

    return redirect(url_for('home_form'))


if __name__ == '__main__':
    app.run(debug=True)