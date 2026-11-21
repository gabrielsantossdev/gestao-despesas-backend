# Sistema de Gestão de Despesas Compartilhadas

API RESTful desenvolvida para a disciplina de **Engenharia de Software II**, voltada ao gerenciamento de contas compartilhadas em repúblicas estudantis, viagens e grupos, com cálculo automático de saldos, simplificação de dívidas cruzadas e exibição de chave PIX para quitação.

## Arquitetura e Tecnologias

O sistema foi estruturado como um **Monólito Modular em Camadas**, garantindo separação de responsabilidades e baixo acoplamento:

* **Linguagem:** Python 3.12+
* **Framework Web:** FastAPI
* **ORM e Banco de Dados:** SQLAlchemy + SQLite
* **Validação de Dados:** Pydantic
* **Testes Automatizados:** Pytest

### Estrutura de Pastas

```text
gestao-despesas-backend/
├── app/
│   ├── __init__.py
│   ├── database.py      # Configuração da conexão SQLite e sessão do banco
│   ├── models.py        # Entidades relacionais (Usuario, Grupo, GrupoMembro, Despesa, Divisao)
│   ├── schemas.py       # Contratos de entrada/saída e validações Pydantic
│   ├── repositories.py  # Camada de persistência e operações CRUD no banco
│   ├── services.py      # Regras de negócio, cálculo de divisões e simplificação de dívidas
│   ├── controllers.py   # Endpoints RESTful organizados por domínio
│   └── main.py          # Inicialização da aplicação FastAPI e tratamento global de exceções
├── tests/
│   ├── __init__.py
│   └── test_api.py      # Testes automatizados de integração e regras de negócio
├── requirements.txt
└── README.md