# **Agro_Analytics - Sistema de Planejamento e Análise Agronômica**

### **Visão Geral do Projeto**

O **Agro_Analytics** é um sistema desenvolvido para realizar análise agronômica e planejamento de colheitas, focado na cultura da Cana-de-Açúcar. Através de uma interface simples e intuitiva, o sistema permite realizar simulações sobre viabilidade de plantio, riscos de pragas, períodos ideais para plantio e estimativas de perdas na produção. O sistema também se integra com o banco de dados Oracle para persistência de dados, permitindo o gerenciamento eficiente de registros históricos de colheita.

O principal objetivo é fornecer um planejamento detalhado e inteligente para maximizar a produtividade e minimizar perdas no processo agrícola.

---

### **Componentes Principais do Sistema**

#### **1. Planejamento Agronômico**

* Simulação de viabilidade de plantio de cana-de-açúcar, com base na região (UF) e época do ano.
* Estimativa de perdas com base em fatores como época de plantio, risco de pragas e qualidade do solo.
* Sugestão de colheita escalonada para otimizar o processo.

#### **2. Análise de Riscos**

* **Risco de Pragas**: Avalia o risco de pragas, como a Broca da Cana, com base nas condições climáticas e mês de plantio.
* **Época de Plantio**: Verifica se o mês de plantio escolhido é ideal, com base nas condições meteorológicas da região.

#### **3. Persistência de Dados**

* Integração com um banco de dados Oracle para registrar os dados de colheitas e perdas estimadas.
* Funcionalidade para visualizar relatórios analíticos sobre as perdas percentuais, status das máquinas e talhões.

---

### **Estrutura de Pastas**

A organização do projeto é a seguinte:

```
Agro_Analytics/

├── documentacao              # Código principal da aplicação (Flask)
    ├──README.md
├──static
    ├──requirements.txt

├── templates/             # Arquivos HTML para o front-end

    ├── dashboard.html     # Dashboard para visualização dos dados
├──agro_analytics.sql
├──analytics.py
├──app.py

```

---

### **Como Usar o Projeto**

#### **1. Instalar Dependências**

Crie um ambiente virtual (opcional, mas recomendado) e instale as dependências utilizando o `requirements.txt`:

```bash
pip install -r requirements.txt
```

#### **2. Configurar o Banco de Dados Oracle**

1. **Instale o Oracle Instant Client**: É necessário configurar o Oracle Instant Client para permitir a conexão com o banco de dados.
2. **Crie a tabela e a sequência no banco de dados Oracle**: Utilize o script DDL fornecido para configurar as tabelas e sequências no seu banco de dados.

#### **3. Rodar o Servidor**

Inicie o servidor Flask com o seguinte comando:

```bash
python app.py
```

Acesse a aplicação no navegador em [http://localhost:5000](http://localhost:5000).

```bash
python analytics.py (para rodar no terminal)
```

#### **4. Usando o Sistema**

* **Cadastro de Colheitas**: Insira as informações sobre o talhão, máquina e produtividade esperada para gerar um planejamento de colheita.
* **Análise de Viabilidade**: O sistema fornecerá uma análise sobre a viabilidade do plantio, época de plantio ideal, e risco de pragas.
* **Relatórios**: Visualize relatórios analíticos sobre as perdas e status das máquinas e talhões.

---

### **Estrutura de Dados**

O banco de dados contém a tabela `COLHEITAS`, que armazena os seguintes campos:

* `ID`: Identificador único da colheita (gerado automaticamente pela sequência).
* `UF`: Unidade Federativa (Estado) onde o plantio foi realizado.
* `MES_PLANTIO`: Mês de plantio.
* `TALHAO`: Identificação do talhão de plantio.
* `MAQUINA_ID`: Identificação da máquina ou colhedora utilizada.
* `PRODUTIVIDADE_ESPERADA_THA`: Produtividade esperada em toneladas por hectare.
* `PERDA_REGISTRADA_THA`: Perda de produtividade registrada em toneladas por hectare.
* `DATA_COLHEITA`: Data da colheita.
* `PRECO_TONELADA`: Preço da tonelada de cana.
* `AREA_TOTAL_HA`: Área total em hectares (opcional).

---

### **Conversão de Dados para JSON**

A conversão dos dados em **JSON** é realizada no terminal com o código `analytics.py`. Esse arquivo permite salvar os registros de colheitas em um arquivo JSON e carregar dados de um arquivo JSON, proporcionando mais flexibilidade para armazenar e transferir os dados.

#### **Funções de Conversão para JSON:**

1. **Salvar em JSON**: Os registros de colheita podem ser salvos em um arquivo JSON com o comando:

   ```python
   salvar_em_json(dados, nome_arquivo="registros_colheita.json")
   ```

2. **Carregar de JSON**: Para carregar os dados de um arquivo JSON, utilize o comando:

   ```python
   registros = carregar_de_json(nome_arquivo="registros_colheita.json")
   ```

3. **Formato do Arquivo JSON**: O arquivo JSON contém um array de objetos, com cada objeto representando uma colheita, e os campos de cada colheita são armazenados em formato chave-valor.


### **Demonstração em Vídeo**

Para entender melhor como o sistema funciona, assista à demonstração em vídeo:

* **Link do Vídeo:** [Demonstração do Agro_Analytics](https://www.youtube.com/watch?v=5ZzWfqERmik)

---

### **Repositório no GitHub**

O código-fonte completo do projeto está disponível no GitHub. Você pode clonar o repositório e colaborar com melhorias ou ajustes:

* **Link do Repositório:** [GitHub - Agro_Analytics](https://github.com/joaostazevedo172/agro_analytics)

---

### **Autores**

* **Autores:** Maria Luiza Oliveira Carvalho, Miriã Leal Mantovani, João Pedro Santos Azevedo e Rodrigo de Souza Freitas.

