# Rateio Fácil — Sistema de Gestão de Despesas Compartilhadas

Back-end RESTful (**FastAPI + SQLite**) com interface web de apoio para controle e divisão de contas em grupo.

O sistema ajuda repúblicas, viagens e grupos de convivência a organizar gastos compartilhados: registra despesas (divisão igual, por valor exato ou por porcentagem), calcula o saldo de cada pessoa, simplifica as dívidas no menor número possível de transferências e exibe a chave PIX do credor com cópia em um clique e baixa de acerto.

## Equipe

- **Gabriel Santos** ([@gabrielsantossdev](https://github.com/gabrielsantossdev))
- **João Hitalo** ([@joaoHitalo](https://github.com/joaoHitalo))

## Funcionalidades

| Requisito | Funcionalidade |
|---|---|
| RF1 | Cadastro e gestão de usuários, grupos e participantes |
| RF2 e RF3 | Registro ilimitado de despesas com divisão igual, por valor exato ou por porcentagem |
| RF4 | Painel de saldos individuais e totais do grupo |
| RF5 | Algoritmo de simplificação de dívidas entre credores e devedores |
| RF6 | Chave PIX do credor com cópia rápida e registro de quitação |
| RF8 | Rede de amizades (apenas amigos podem ser adicionados a um grupo) |
| RF9 | Baixa de acertos via PIX: registra a quitação de uma transferência sugerida e abate os saldos |
| RF10 | Extrato individual detalhado por membro dentro de cada grupo |

> **Nota:** Notificações por e-mail (RF7) não estão incluídas nesta versão.

## Arquitetura

Cliente-Servidor em **Camadas**, com back-end organizado em **Monólito Modular**:

`Frontend → Controllers → Services → Repositories → SQLite`

```text
gestao-despesas-backend/
├── app/
│   ├── main.py            # Entrada FastAPI, CORS, arquivos estáticos e handlers de erro
│   ├── database.py        # Conexão e sessão SQLAlchemy (SQLite)
│   ├── models.py          # Entidades ORM
│   ├── schemas.py         # Contratos Pydantic (validação)
│   ├── repositories.py    # Acesso a dados
│   ├── services.py        # Regras de negócio, rateio e simplificação de dívidas
│   ├── controllers.py     # Rotas REST (/usuarios, /grupos, /despesas)
│   └── seed.py            # Usuários pré-cadastrados para demonstração
├── frontend/              # Interface web (HTML, CSS e JS)
├── tests/test_api.py      # Testes automatizados (Pytest)
├── requirements.txt
└── README.md
```

## Como executar

**Pré-requisitos:** Python 3.10+ e Git.

```bash
git clone https://github.com/gabrielsantossdev/gestao-despesas-backend.git
cd gestao-despesas-backend

python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

pip install -r requirements.txt
uvicorn app.main:app --reload
```

- **Interface web:** http://127.0.0.1:8000/interface
- **Documentação da API (Swagger):** http://127.0.0.1:8000/docs

O banco `despesas_compartilhadas.db` é criado automaticamente na primeira execução. Caso atualize o projeto sobre uma base antiga, apague o arquivo `.db` antes de iniciar o servidor novamente.

### Usuários pré-cadastrados

Esta versão não possui tela de login ou auto-cadastro. Quatro usuários são criados automaticamente ao iniciar (senha padrão: `1234`), e a interface web inicia conectada como **Gabriel Santos** (`Logado como: Gabriel Santos` no topo da tela):

| Nome | E-mail |
|---|---|
| Gabriel Santos | gabriel@rateiofacil.com |
| João Hitalo | joao@rateiofacil.com |
| Ana Clara | ana@rateiofacil.com |
| Lucas Mendes | lucas@rateiofacil.com |

Gabriel e João já começam conectados como amigos; Ana e Lucas ficam disponíveis para testar a busca e adição de amigos por e-mail.

## Testes

```bash
pytest -v -s -W ignore
```

Os testes executam em um banco SQLite em memória e não alteram o banco de dados local.

## Fluxo de trabalho (Git)

Branches por funcionalidade (`feat/...`, `docs/...`) integradas à `main` por Pull Request, seguindo o padrão de commits `feat:`, `fix:`, `test:` e `docs:`.