# 📚 Base de Conhecimento — Marketing & Vendas (eWorks)

> **Propósito:** Centralizar conhecimento de marketing e vendas coletado de influencers, cursos, experimentos e pesquisas — para uso operacional da eWorks e desenvolvimento de produtos no eWorks OS.

---

## 🗂️ Estrutura

```
marketing-sales/
├── influencers/          ← Perfis de influencers e criadores de conteúdo
├── ferramentas/          ← Ferramentas de CRM, automação, analytics, ads
├── estrategias/          ← Frameworks, táticas, playbooks de marketing e vendas
├── conceitos/            ← Definições: ICP, funil, MQL/SQL, SPIN, AIDA...
├── aplicacao-eworks/     ← Como cada item se aplica à eWorks e ao eWorks OS
├── _templates/           ← Templates padrão para cada categoria
└── _README.md            ← Este arquivo
```

---

## 📥 Como Adicionar Conhecimento

Diga ao agente B.IA algo como:

> *"Aprendi com o [Influencer] que [insight/estratégia]. Aplica-se a [contexto]."*

O agente vai:
1. Criar ou atualizar a nota do influencer em `influencers/`
2. Criar ou atualizar a nota da estratégia em `estrategias/` ou `conceitos/`
3. Criar ou atualizar a nota da ferramenta em `ferramentas/` (se aplicável)
4. Registrar a aplicação prática em `aplicacao-eworks/`
5. Fazer commit no repo `eworks-cloud/eworks-os`

---

## 🏷️ Sistema de Tags

Todas as notas usam frontmatter YAML com as seguintes tags:

| Tag | Valores |
|-----|---------|
| `categoria` | `influencer` / `ferramenta` / `estrategia` / `conceito` |
| `topico` | `inbound` / `outbound` / `vendas` / `automacao` / `ads` / `conteudo` / `crm` / `social-media` / `email` / `seo` / `analytics` |
| `aplicavel_eworks` | `true` / `false` |
| `fonte` | nome do influencer ou fonte |
| `data_adicao` | YYYY-MM-DD |
| `revisado` | `true` / `false` |

---

## 🔗 Índice de Influencers

| Influencer | Nicho Principal | Nota |
|---|---|---|
| *(adicionar conforme forem sendo criados)* | | |

---

## 🔗 Índice de Ferramentas

| Ferramenta | Categoria | Nota |
|---|---|---|
| *(adicionar conforme forem sendo criados)* | | |

---

## 🔗 Índice de Estratégias

| Estratégia | Tópico | Nota |
|---|---|---|
| *(adicionar conforme forem sendo criados)* | | |

---

## 🔗 Aplicações no eWorks OS

| Módulo eWorks OS | Insights Aplicados |
|---|---|
| *(adicionar conforme forem sendo identificados)* | |

---

*Mantido por B.IA — atualizado automaticamente a cada novo insight capturado.*
