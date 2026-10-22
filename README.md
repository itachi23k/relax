# Gerador & Indexador de Relatórios Fotográficos (DNIT) - v2.0

Interface gráfica moderna em **PyQt6** para indexação ágil de imagens, gerenciamento explícito de páginas, seleção de fotos via navegação **Up/Down** por subpastas e geração profissional de relatórios fotográficos em PDF no padrão oficial do DNIT.

---

## 🚀 Como Executar

No terminal ou PowerShell, dentro da pasta do projeto:

```powershell
python app.py
```

---

## ✨ Principais Funcionalidades (v2.0)

1. **Área de Prévia Ampliada & Alta Resolução**:
   * Painel de visualização generoso com redimensionamento dinâmico e preservação de proporção.
   * Botão de **Rotação 90°** com renderização instantânea (e preservada no PDF final).
   * Modo **Expandir / Tela Cheia** para inspecionar detalhes da obra em alta resolução.
   * Arquitetura extensível e escalável preparada para futuras ferramentas de **Edição de Imagem Embutida** (recorte, setas/anotações e ajustes de contraste).

2. **Gerenciamento Completo de Páginas**:
   * **Adicionar Páginas** (`➕ Nova Página`): adicione quantas folhas precisar para organizar sua medição.
   * Navegação ágil por abas (`Página 1`, `Página 2`, etc.), com contagem de fotos ativas por folha.
   * **Duplicar Página**: replica estrutura e metadados mantendo a produtividade.
   * **Excluir Página**: remoção segura com diálogo de confirmação.
   * Grid visual com 6 slots por folha no layout padrão oficial DNIT (2 colunas × 3 linhas).

3. **Inclusão de Pastas & Navegação por Subpastas (Up & Down)**:
   * **Incluir Pasta Raiz / Subpastas**: escaneia automaticamente o diretório selecionado e lista todas as subpastas que possuem fotos.
   * **Decisão de Fotos via Up & Down**:
     * Botões `▲ Foto Anterior (Up)` e `▼ Próxima Foto (Down)` integrados tanto no slot quanto no topo da prévia ampliada.
     * **Atalhos de Teclado**: use as teclas `↑ (Cima)` e `↓ (Baixo)` para alternar instantaneamente entre as fotos existentes na subpasta selecionada.
     * Contador de fotos em tempo real (`Foto X de Y`).
   * Ação rápida: **Preencher Página com Subpasta** com 1 clique.

4. **Visão Dupla: Visual DNIT vs. Tabela Geral**:
   * **Modo Visual DNIT**: edição direta nos cards dos 6 slots com miniaturas interativas e campos rápidos.
   * **Modo Tabela Geral / Lote**: visualização consolidada de todas as fotos de todas as páginas para ações em lote (aplicar mesmo serviço, situação e estacas sequenciais com incremento automático).

5. **Cálculo Automático de KM**:
   * Fórmula oficial de estacas: `KM = (Estaca × Metros/Estaca / 1000) + KM Base`.
   * Atualização em tempo real conforme você digita a estaca ou edita parâmetros.

6. **Geração em PDF e XML**:
   * Suporte rigoroso a múltiplas folhas com numeração discreta (`Folha X/N`).
   * Cabeçalho e bloco de assinaturas oficiais repetidos em todas as páginas.
   * Exportação simultânea de arquivo `.xml` correspondente.
   * Salvar e Carregar perfil do projeto em `.json`.

---

## 🏗️ Estrutura do Projeto

* `app.py`: Janela principal, integração entre módulos e sincronização de visões.
* `database.py`: Gerenciador do banco de dados local SQLite (`relatorios_projetos.db`) para múltiplos projetos e persistência de progresso sem necessidade de PDF.
* `models.py`: Modelos de dados escaláveis (`ReportProject`, `ReportPage`, `PhotoSlot`, `FolderManager`).
* `preview_widget.py`: Widget da prévia ampliada com navegação Up/Down e suporte a rotação/edição.
* `page_editor_widget.py`: Editor de páginas com lista vertical e grid DNIT de 6 slots por folha.
* `generator.py`: Motor de desenho de PDF com ReportLab e exportador XML.
# relax
