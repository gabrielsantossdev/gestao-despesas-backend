# Sistema de Gestão de Despesas Compartilhadas (Rateio Fácil)

Aplicação completa (Back-end RESTful + Interface Web) desenvolvida para a disciplina de **Engenharia de Software II** da **Universidade Federal do Piauí (UFPI — Campus Senador Helvídio Nunes de Barros, Picos)**, sob orientação do Prof. Raí Araújo de Miranda.

O sistema automatiza o controle financeiro de repúblicas estudantis, viagens e grupos de convivência, permitindo cadastrar participantes com chaves PIX, organizar grupos, registrar despesas com diferentes regras de rateio (igualitária, por valor exato ou por percentual) e calcular o balanço líquido com simplificação automática de dívidas.

---

## Integrantes da Equipe
* **Gabriel Santos** (`@gabrielsantossdev`)
* **João Hitalo** (`@joaoHitalo`)

---

## Arquitetura e Estrutura do Projeto

O back-end segue o padrão de **Monólito Modular em Camadas**, com separação clara entre roteamento HTTP, validação de contratos, regras de negócio e persistência relacional, além de servir diretamente a interface web estática:

```text
gestao-despesas-backend/
├── app/
│   ├── __init__.py
│   ├── main.py            # Ponto de entrada FastAPI, CORS, arquivos estáticos e handlers de erro
│   ├── database.py        # Configuração de conexão e sessão SQLAlchemy (SQLite)
│   ├── models.py          # Entidades ORM (Usuario, Grupo, GrupoMembro, Despesa, Divisao)
│   ├── schemas.py         # Contratos Pydantic de entrada, saída e validação de tipos
│   ├── repositories.py    # Camada de acesso a dados (operações CRUD)
│   ├── services.py        # Regras de negócio, rateios e algoritmo de simplificação de dívidas
│   └── controllers.py     # Rotas RESTful (/usuarios, /grupos, /despesas)
├── frontend/
│   ├── index.html         # Estrutura visual das abas (Usuários, Grupos e Despesas/PIX)
│   ├── style.css          # Estilização responsiva da interface
│   └── app.js             # Consumo da API RESTful via Fetch API
├── tests/
│   ├── __init__.py
│   └── test_api.py        # Testes automatizados de integração com Pytest
├── requirements.txt       # Dependências do projeto
└── README.md