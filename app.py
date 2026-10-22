#!/usr/bin/env python3
"""
Gerador & Indexador de Relatórios Fotográficos (DNIT) - Versão 2.0
Interface Gráfica com Suporte a Múltiplas Páginas, Prévia Ampliada,
Navegação Up/Down por Subpastas e Arquitetura Escalável.
"""
import sys
import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QFileDialog, QMessageBox,
    QSplitter, QGroupBox, QFrame, QScrollArea, QAbstractItemView,
    QTabWidget, QListWidget, QListWidgetItem, QDialog, QMenu
)
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor, QKeySequence, QShortcut

import generator
from models import (
    ReportProject, ReportPage, PhotoSlot, FolderManager,
    VALORES_PADRAO_CAMPOS, EXTENSOES_FOTO, calcular_km_estaca
)
from database import DatabaseManager
from preview_widget import LargeImagePreviewWidget
from page_editor_widget import PageEditorWidget


class ProjectManagerDialog(QDialog):
    """Diálogo completo de gerenciamento de múltiplos projetos."""
    def __init__(self, db: DatabaseManager, projeto_atual_id: Optional[int], parent=None):
        super().__init__(parent)
        self.db = db
        self.projeto_atual_id = projeto_atual_id
        self.projeto_selecionado_id: Optional[int] = projeto_atual_id

        self.setWindowTitle("Gerenciador de Projetos de Relatórios")
        self.resize(780, 480)
        self.init_ui()
        self.carregar_projetos()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Cabeçalho explicativo
        top_layout = QHBoxLayout()
        lbl_info = QLabel("<b>Projetos Cadastrados no Banco de Dados Local</b><br>"
                          "<small style='color: #888;'>Selecione um projeto para abrir ou use os comandos ao lado para gerenciar.</small>")
        top_layout.addWidget(lbl_info)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # Conteúdo Central: Tabela + Botões laterais
        content_layout = QHBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Nome do Projeto", "Páginas", "Fotos Ativas", "Última Modificação"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        content_layout.addWidget(self.table, 1)

        # Botões Laterais
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(6)

        self.btn_abrir = QPushButton("📂 Abrir Projeto")
        self.btn_abrir.setStyleSheet("""
            QPushButton {
                background-color: #1e5ba3;
                color: white;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2672cc;
            }
        """)
        self.btn_abrir.clicked.connect(self.abrir_selecionado)
        btn_layout.addWidget(self.btn_abrir)

        btn_novo = QPushButton("➕ Novo Projeto...")
        btn_novo.clicked.connect(self.novo_projeto)
        btn_layout.addWidget(btn_novo)

        btn_duplicar = QPushButton("📋 Duplicar...")
        btn_duplicar.clicked.connect(self.duplicar_projeto)
        btn_layout.addWidget(btn_duplicar)

        btn_renomear = QPushButton("✏️ Renomear...")
        btn_renomear.clicked.connect(self.renomear_projeto)
        btn_layout.addWidget(btn_renomear)

        btn_excluir = QPushButton("🗑️ Excluir...")
        btn_excluir.clicked.connect(self.excluir_projeto)
        btn_layout.addWidget(btn_excluir)

        btn_layout.addStretch()

        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_fechar)

        content_layout.addLayout(btn_layout)
        layout.addLayout(content_layout)

    def carregar_projetos(self):
        projetos = self.db.listar_projetos()
        self.table.setRowCount(len(projetos))

        linha_para_selecionar = -1
        for row, p in enumerate(projetos):
            # ID
            it_id = QTableWidgetItem(str(p["id"]))
            it_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_id.setFlags(it_id.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, it_id)

            # Nome
            nome_txt = p["nome"]
            if p["id"] == self.projeto_atual_id:
                nome_txt += " ★ (Ativo)"
                linha_para_selecionar = row
            it_nome = QTableWidgetItem(nome_txt)
            it_nome.setFlags(it_nome.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if p["id"] == self.projeto_atual_id:
                it_nome.setForeground(QtGui.QBrush(QColor("#4da3ff")))
                it_nome.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(row, 1, it_nome)

            # Páginas
            it_pags = QTableWidgetItem(f"{p['total_paginas']} pág.")
            it_pags.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_pags.setFlags(it_pags.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, it_pags)

            # Fotos
            it_fotos = QTableWidgetItem(f"{p['total_fotos_ativas']} fotos")
            it_fotos.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_fotos.setFlags(it_fotos.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, it_fotos)

            # Data Modificação
            dt_raw = p.get("atualizado_em", "")
            try:
                dt_fmt = datetime.fromisoformat(dt_raw).strftime("%d/%m/%Y %H:%M")
            except Exception:
                dt_fmt = dt_raw
            it_dt = QTableWidgetItem(dt_fmt)
            it_dt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_dt.setFlags(it_dt.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 4, it_dt)

        if linha_para_selecionar >= 0:
            self.table.selectRow(linha_para_selecionar)
        elif self.table.rowCount() > 0:
            self.table.selectRow(0)

    def _obter_id_selecionado(self) -> Optional[int]:
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        item_id = self.table.item(row, 0)
        return int(item_id.text()) if item_id else None

    def _on_double_click(self, row, col):
        self.abrir_selecionado()

    def abrir_selecionado(self):
        pid = self._obter_id_selecionado()
        if pid:
            self.projeto_selecionado_id = pid
            self.accept()

    def novo_projeto(self):
        nome, ok = QtWidgets.QInputDialog.getText(
            self, "Novo Projeto", "Digite o nome para o novo projeto:",
            text=f"Projeto - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        if ok and nome.strip():
            try:
                pid = self.db.criar_projeto(nome.strip(), "")
                self.projeto_selecionado_id = pid
                self.carregar_projetos()
                self.accept()
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Erro ao criar projeto:\n{e}")

    def duplicar_projeto(self):
        pid = self._obter_id_selecionado()
        if not pid:
            return
        row = self.table.selectionModel().selectedRows()[0].row()
        nome_atual = self.table.item(row, 1).text().replace(" ★ (Ativo)", "")
        novo_nome, ok = QtWidgets.QInputDialog.getText(
            self, "Duplicar Projeto", "Nome para a cópia do projeto:",
            text=f"{nome_atual} (Cópia)"
        )
        if ok and novo_nome.strip():
            try:
                novo_id = self.db.duplicar_projeto(pid, novo_nome.strip())
                self.projeto_selecionado_id = novo_id
                self.carregar_projetos()
                self.accept()
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Erro ao duplicar projeto:\n{e}")

    def renomear_projeto(self):
        pid = self._obter_id_selecionado()
        if not pid:
            return
        row = self.table.selectionModel().selectedRows()[0].row()
        nome_atual = self.table.item(row, 1).text().replace(" ★ (Ativo)", "")
        novo_nome, ok = QtWidgets.QInputDialog.getText(
            self, "Renomear Projeto", "Novo nome para o projeto:",
            text=nome_atual
        )
        if ok and novo_nome.strip():
            try:
                self.db.renomear_projeto(pid, novo_nome.strip())
                self.carregar_projetos()
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Erro ao renomear projeto:\n{e}")

    def excluir_projeto(self):
        pid = self._obter_id_selecionado()
        if not pid:
            return
        if self.db.total_projetos() <= 1:
            QMessageBox.warning(self, "Aviso", "Não é possível excluir o único projeto do banco de dados.")
            return

        row = self.table.selectionModel().selectedRows()[0].row()
        nome_atual = self.table.item(row, 1).text().replace(" ★ (Ativo)", "")
        resp = QMessageBox.question(
            self, "Confirmar Exclusão",
            f"Deseja excluir permanentemente o projeto '{nome_atual}'?\nEsta ação não poderá ser desfeita.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.db.excluir_projeto(pid)
            if self.projeto_atual_id == pid:
                self.projeto_selecionado_id = self.db.obter_ultimo_projeto_id()
            self.carregar_projetos()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerador & Indexador de Relatórios Fotográficos (DNIT) - v2.0")
        self.resize(1420, 880)
        self.setMinimumSize(1080, 700)

        self.diretorio_base = os.path.dirname(os.path.abspath(__file__))
        self.db = DatabaseManager()
        self.projeto_atual_id: Optional[int] = None
        self.projeto_atual_nome: str = ""
        self.project = ReportProject()

        self.init_ui()
        self.carregar_dados_iniciais()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Diálogo para Configurações do Contrato e Gerenciamento de Pastas (acessível pelo submenu)
        self.criar_dialogo_configuracoes()

        # Barra Superior de Comandos Globais
        top_bar = self.criar_barra_superior()
        main_layout.addLayout(top_bar)

        # Splitter Principal em 3 Painéis:
        # [0] Esquerda: Navegação Vertical entre Páginas + Gerenciamento
        # [1] Centro: Editor de Páginas (Visual DNIT) / Tabela Geral
        # [2] Direita: Prévia Ampliada da Imagem + Ações Rápidas
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        painel_esquerdo = self.criar_painel_esquerdo()
        self.splitter.addWidget(painel_esquerdo)

        painel_central = self.criar_painel_central()
        self.splitter.addWidget(painel_central)

        painel_direito = self.criar_painel_direito()
        self.splitter.addWidget(painel_direito)

        # Distribuição de espaço: Lista vertical de páginas à esquerda, centro DNIT e prévia à direita
        self.splitter.setStretchFactor(0, 2)  # Esquerda: ~220-250px
        self.splitter.setStretchFactor(1, 5)  # Centro: ~550-650px
        self.splitter.setStretchFactor(2, 5)  # Direita (Prévia Ampliada): ~550-650px
        self.splitter.setSizes([230, 580, 610])

        # Atalho Ctrl+S para salvar progresso no banco de dados local
        self.shortcut_salvar = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        self.shortcut_salvar.activated.connect(lambda: self.salvar_progresso_banco(silencioso=False))

        main_layout.addWidget(self.splitter, 1)

        # Barra de Rodapé / Status
        bottom_bar = self.criar_barra_rodape()
        main_layout.addLayout(bottom_bar)

    def criar_barra_superior(self):
        layout = QHBoxLayout()
        layout.setSpacing(8)

        # 1. Seção de Gerenciamento de Projetos e Progresso no Banco
        lbl_proj = QLabel("<b>Projeto:</b>")
        lbl_proj.setFont(QFont("Segoe UI", 9))
        layout.addWidget(lbl_proj)

        self.cmb_projetos = QComboBox()
        self.cmb_projetos.setToolTip("Selecione o projeto ativo para carregar do banco de dados")
        self.cmb_projetos.setMinimumWidth(220)
        self.cmb_projetos.currentIndexChanged.connect(self._ao_selecionar_projeto_combo)
        layout.addWidget(self.cmb_projetos)

        self.btn_salvar_progresso = QPushButton("💾 Salvar Progresso")
        self.btn_salvar_progresso.setToolTip("Gravar variáveis e indexações no banco de dados local sem gerar PDF [Ctrl+S]")
        self.btn_salvar_progresso.setStyleSheet("""
            QPushButton {
                background-color: #1b6ca8;
                color: white;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2185d0;
            }
        """)
        self.btn_salvar_progresso.clicked.connect(lambda: self.salvar_progresso_banco(silencioso=False))
        layout.addWidget(self.btn_salvar_progresso)

        self.btn_menu_projetos = QPushButton("🗃️ Projetos ▾")
        self.btn_menu_projetos.setToolTip("Gerenciar múltiplos projetos no banco de dados")
        menu_proj = QMenu(self)
        act_novo = menu_proj.addAction("➕ Novo Projeto...")
        act_novo.triggered.connect(self.acao_novo_projeto)
        act_dup = menu_proj.addAction("📋 Duplicar Projeto Atual...")
        act_dup.triggered.connect(self.acao_duplicar_projeto_atual)
        act_ren = menu_proj.addAction("✏️ Renomear Projeto Atual...")
        act_ren.triggered.connect(self.acao_renomear_projeto_atual)
        act_del = menu_proj.addAction("🗑️ Excluir Projeto Atual...")
        act_del.triggered.connect(self.acao_excluir_projeto_atual)
        menu_proj.addSeparator()
        act_ger = menu_proj.addAction("📂 Gerenciador Completo de Projetos...")
        act_ger.triggered.connect(self.acao_abrir_gerenciador_projetos)
        self.btn_menu_projetos.setMenu(menu_proj)
        layout.addWidget(self.btn_menu_projetos)

        layout.addSpacing(10)

        # 2. Configurações de Dados do Relatório e Pastas
        self.btn_menu_contrato = QPushButton("⚙️ Dados do Relatório & Pastas ▾")
        self.btn_menu_contrato.setToolTip("Acessar variáveis do contrato, parâmetros de rodovia e gerenciamento de subpastas")
        menu_contrato = QMenu(self)
        act_contrato = menu_contrato.addAction("📋 Dados do Contrato & Variáveis...")
        act_contrato.triggered.connect(lambda: self.abrir_dialogo_config(aba=0))
        act_pastas = menu_contrato.addAction("📁 Gerenciar Subpastas com Fotos...")
        act_pastas.triggered.connect(lambda: self.abrir_dialogo_config(aba=1))
        menu_contrato.addSeparator()
        act_add_pasta = menu_contrato.addAction("📂 Incluir Pasta Raiz / Subpastas...")
        act_add_pasta.triggered.connect(self.acao_incluir_pastas)
        self.btn_menu_contrato.setMenu(menu_contrato)
        layout.addWidget(self.btn_menu_contrato)

        btn_pasta = QPushButton("📂 Incluir Fotos...")
        btn_pasta.setToolTip("Escaneia pasta e detecta automaticamente subpastas com imagens")
        btn_pasta.clicked.connect(self.acao_incluir_pastas)
        layout.addWidget(btn_pasta)

        # 3. Perfis em arquivo JSON (Exportação/Importação manual)
        menu_json = QMenu(self)
        act_salvar_json = menu_json.addAction("💾 Exportar Perfil JSON...")
        act_salvar_json.triggered.connect(self.salvar_perfil_json)
        act_carregar_json = menu_json.addAction("📥 Importar Perfil JSON...")
        act_carregar_json.triggered.connect(self.carregar_perfil_json)
        btn_perfil_json = QPushButton("📄 Perfil JSON ▾")
        btn_perfil_json.setToolTip("Exportar ou importar dados em arquivos JSON legados")
        btn_perfil_json.setMenu(menu_json)
        layout.addWidget(btn_perfil_json)

        layout.addStretch()

        # 4. Geração do Relatório PDF (quando desejado exportar o arquivo final)
        self.btn_gerar_pdf = QPushButton("🚀 Gerar Relatório PDF")
        self.btn_gerar_pdf.setStyleSheet("""
            QPushButton {
                background-color: #0b6623;
                color: white;
                font-weight: bold;
                padding: 7px 20px;
                font-size: 13px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0d7f2c;
            }
        """)
        self.btn_gerar_pdf.clicked.connect(self.gerar_pdf)
        layout.addWidget(self.btn_gerar_pdf)

        return layout

    def criar_dialogo_configuracoes(self):
        """Cria a janela/diálogo com os dados do contrato e o gerenciador de subpastas."""
        self.dialog_config = QDialog(self)
        self.dialog_config.setWindowTitle("Dados do Contrato, Relatório & Pastas de Fotos")
        self.dialog_config.resize(520, 660)
        dlg_layout = QVBoxLayout(self.dialog_config)
        dlg_layout.setContentsMargins(10, 10, 10, 10)
        dlg_layout.setSpacing(8)

        self.tabs_config = QTabWidget()

        # Aba 1: Variáveis do Relatório
        var_widget = QWidget()
        var_layout = QVBoxLayout(var_widget)
        var_layout.setContentsMargins(6, 6, 6, 6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        form_layout = QVBoxLayout(container)
        form_layout.setSpacing(5)

        self.inputs = {}

        def add_field(label_text, key):
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            edt = QLineEdit()
            form_layout.addWidget(lbl)
            form_layout.addWidget(edt)
            self.inputs[key] = edt
            edt.textChanged.connect(self._ao_alterar_campo_relatorio)

        add_field("Órgão:", "orgao")
        add_field("Regional:", "regional")
        add_field("Título do Relatório:", "titulo")
        add_field("Empresa Contratada:", "empresa")
        add_field("Nº do Contrato:", "contrato")
        add_field("Nº da Medição:", "medicao")
        add_field("Serviços Executados Até:", "servicos_ate")
        add_field("Período Início:", "periodo_inicio")
        add_field("Período Fim:", "periodo_fim")
        add_field("Rodovia:", "rodovia")
        add_field("Empresa Supervisora:", "supervisora")
        add_field("Fiscal do Contrato:", "fiscal")

        # Parâmetros de Cálculo da Rodovia
        param_box = QGroupBox("Cálculo de KM (Estaca → KM)")
        param_layout = QGridLayout(param_box)

        param_layout.addWidget(QLabel("KM Base:"), 0, 0)
        self.inputs["km_base"] = QLineEdit()
        self.inputs["km_base"].textChanged.connect(self._ao_alterar_campo_relatorio)
        param_layout.addWidget(self.inputs["km_base"], 0, 1)

        param_layout.addWidget(QLabel("Metros/Estaca:"), 1, 0)
        self.inputs["metros_estaca"] = QLineEdit()
        self.inputs["metros_estaca"].textChanged.connect(self._ao_alterar_campo_relatorio)
        param_layout.addWidget(self.inputs["metros_estaca"], 1, 1)

        form_layout.addWidget(param_box)

        # Logomarca
        lbl_logo = QLabel("Logomarca:")
        lbl_logo.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        form_layout.addWidget(lbl_logo)

        logo_layout = QHBoxLayout()
        self.inputs["logo_path"] = QLineEdit()
        btn_sel_logo = QPushButton("...")
        btn_sel_logo.setMaximumWidth(30)
        btn_sel_logo.clicked.connect(self.selecionar_logo)
        logo_layout.addWidget(self.inputs["logo_path"])
        logo_layout.addWidget(btn_sel_logo)
        form_layout.addLayout(logo_layout)

        form_layout.addStretch()
        scroll.setWidget(container)
        var_layout.addWidget(scroll)
        self.tabs_config.addTab(var_widget, "📋 Contrato")

        # Aba 2: Gerenciador de Pastas e Subpastas
        pastas_widget = QWidget()
        pastas_layout = QVBoxLayout(pastas_widget)
        pastas_layout.setContentsMargins(6, 6, 6, 6)

        pastas_layout.addWidget(QLabel("<b>Subpastas com Fotos Detectadas:</b>"))
        self.list_subpastas = QListWidget()
        self.list_subpastas.setToolTip("Subpastas disponíveis para escolha de fotos via Up/Down")
        pastas_layout.addWidget(self.list_subpastas, 1)

        btn_add_raiz = QPushButton("➕ Incluir Outra Pasta...")
        btn_add_raiz.clicked.connect(self.acao_incluir_pastas)
        pastas_layout.addWidget(btn_add_raiz)

        btn_criar_pag_subpasta = QPushButton("⚡ Criar Página com esta Subpasta")
        btn_criar_pag_subpasta.setToolTip("Cria uma nova folha contendo as fotos da subpasta selecionada")
        btn_criar_pag_subpasta.clicked.connect(self._criar_pagina_de_subpasta_selecionada)
        pastas_layout.addWidget(btn_criar_pag_subpasta)

        self.tabs_config.addTab(pastas_widget, "📁 Subpastas")

        dlg_layout.addWidget(self.tabs_config, 1)

        # Rodapé do diálogo
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        btn_fechar = QPushButton("Concluir / Fechar")
        btn_fechar.clicked.connect(self.dialog_config.accept)
        btn_bar.addWidget(btn_fechar)
        dlg_layout.addLayout(btn_bar)

    def abrir_dialogo_config(self, aba: int = 0):
        self.tabs_config.setCurrentIndex(aba)
        self.dialog_config.exec()

    def criar_painel_esquerdo(self):
        """Painel de navegação vertical entre páginas com botões Nova Página, Duplicar e Excluir."""
        painel = QFrame()
        painel.setFrameShape(QFrame.Shape.StyledPanel)
        painel.setStyleSheet("""
            QFrame {
                background-color: #212327;
                border-radius: 6px;
            }
        """)
        layout = QVBoxLayout(painel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Cabeçalho do Painel
        header_layout = QHBoxLayout()
        lbl_titulo = QLabel("📑 <b>Páginas</b>")
        lbl_titulo.setFont(QFont("Segoe UI", 10))
        lbl_titulo.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(lbl_titulo)
        header_layout.addStretch()

        self.lbl_paginas_badge = QLabel("1 pág.")
        self.lbl_paginas_badge.setStyleSheet("color: #4da3ff; font-weight: bold; font-size: 11px;")
        header_layout.addWidget(self.lbl_paginas_badge)
        layout.addLayout(header_layout)

        # Botão Nova Página
        self.btn_nav_add_pag = QPushButton("➕ Nova Página")
        self.btn_nav_add_pag.setToolTip("Adicionar uma nova página ao relatório")
        self.btn_nav_add_pag.setStyleSheet("""
            QPushButton {
                background-color: #1e5ba3;
                color: white;
                font-weight: bold;
                padding: 7px;
                font-size: 11px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2672cc;
            }
        """)
        self.btn_nav_add_pag.clicked.connect(self.acao_adicionar_pagina)
        layout.addWidget(self.btn_nav_add_pag)

        # Ações de Gerenciamento de Página: Duplicar e Excluir
        btn_grid = QHBoxLayout()
        btn_grid.setSpacing(4)

        self.btn_nav_dup_pag = QPushButton("📋 Duplicar")
        self.btn_nav_dup_pag.setToolTip("Duplicar a página selecionada com suas fotos e dados")
        self.btn_nav_dup_pag.clicked.connect(self.acao_duplicar_pagina)
        btn_grid.addWidget(self.btn_nav_dup_pag)

        self.btn_nav_del_pag = QPushButton("🗑️ Excluir")
        self.btn_nav_del_pag.setToolTip("Excluir a página selecionada do relatório")
        self.btn_nav_del_pag.clicked.connect(self.acao_remover_pagina)
        btn_grid.addWidget(self.btn_nav_del_pag)

        layout.addLayout(btn_grid)

        # Botões para reordenar páginas verticalmente (Subir / Descer)
        order_grid = QHBoxLayout()
        order_grid.setSpacing(4)

        self.btn_nav_move_up = QPushButton("▲ Subir")
        self.btn_nav_move_up.setToolTip("Mover página selecionada para cima na ordem do relatório")
        self.btn_nav_move_up.clicked.connect(self.acao_mover_pagina_cima)
        order_grid.addWidget(self.btn_nav_move_up)

        self.btn_nav_move_down = QPushButton("▼ Descer")
        self.btn_nav_move_down.setToolTip("Mover página selecionada para baixo na ordem do relatório")
        self.btn_nav_move_down.clicked.connect(self.acao_mover_pagina_baixo)
        order_grid.addWidget(self.btn_nav_move_down)

        layout.addLayout(order_grid)

        # Lista Vertical de Navegação entre Páginas
        self.list_paginas = QListWidget()
        self.list_paginas.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_paginas.setStyleSheet("""
            QListWidget {
                background-color: #17181a;
                border: 1px solid #36393f;
                border-radius: 5px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 10px 10px;
                margin-bottom: 4px;
                border-radius: 4px;
                background-color: #24272c;
                color: #dcddde;
                font-size: 11px;
                font-weight: 500;
            }
            QListWidget::item:hover {
                background-color: #2e3239;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #2a82da;
                color: #ffffff;
                font-weight: bold;
                border-left: 4px solid #7289da;
            }
        """)
        self.list_paginas.currentRowChanged.connect(self._ao_trocar_pagina_lista)
        self.list_paginas.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_paginas.customContextMenuRequested.connect(self._abrir_menu_contexto_paginas)
        layout.addWidget(self.list_paginas, 1)

        return painel

    def _abrir_menu_contexto_paginas(self, pos: QPoint):
        menu = QMenu(self)
        act_add = menu.addAction("➕ Nova Página")
        act_add.triggered.connect(self.acao_adicionar_pagina)
        act_dup = menu.addAction("📋 Duplicar Página")
        act_dup.triggered.connect(self.acao_duplicar_pagina)
        act_del = menu.addAction("🗑️ Excluir Página")
        act_del.triggered.connect(self.acao_remover_pagina)
        menu.addSeparator()
        act_up = menu.addAction("▲ Mover para Cima")
        act_up.triggered.connect(self.acao_mover_pagina_cima)
        act_down = menu.addAction("▼ Mover para Baixo")
        act_down.triggered.connect(self.acao_mover_pagina_baixo)
        menu.addSeparator()
        act_fill = menu.addAction("⚡ Preencher com Subpasta...")
        act_fill.triggered.connect(self.page_editor._preencher_pagina_com_subpasta)
        menu.exec(self.list_paginas.mapToGlobal(pos))

    def criar_painel_central(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.center_tabs = QTabWidget()

        # Aba 1: Editor Visual de Páginas (Padrão DNIT)
        self.page_editor = PageEditorWidget(self.project)
        self.page_editor.slot_selected.connect(self._ao_selecionar_slot_da_pagina)
        self.page_editor.photo_navigated.connect(self._ao_navegar_foto_slot)
        self.page_editor.subfolder_selected.connect(self._ao_selecionar_subpasta_slot)
        self.page_editor.project_modified.connect(self._ao_modificar_projeto)
        self.page_editor.page_changed.connect(self._ao_pagina_mudou)
        self.center_tabs.addTab(self.page_editor, "📐 Visual de Páginas (DNIT)")

        # Aba 2: Tabela Completa (Ações em Massa)
        tabela_widget = self.criar_tabela_geral_widget()
        self.center_tabs.addTab(tabela_widget, "📋 Tabela Geral / Lote")

        self.center_tabs.currentChanged.connect(self._ao_trocar_aba_central)
        layout.addWidget(self.center_tabs)

        return container

    def criar_tabela_geral_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Painel de Edição em Lote
        lote_group = QGroupBox("⚡ Ações em Lote")
        lote_layout = QGridLayout(lote_group)
        lote_layout.setContentsMargins(6, 6, 6, 6)

        lote_layout.addWidget(QLabel("Serviço:"), 0, 0)
        self.edt_lote_servico = QLineEdit()
        self.edt_lote_servico.setPlaceholderText("ex: REGULARIZAÇÃO DE SUBLEITO")
        lote_layout.addWidget(self.edt_lote_servico, 0, 1)

        btn_aplicar_servico = QPushButton("Aplicar Serviço")
        btn_aplicar_servico.clicked.connect(self.aplicar_servico_em_lote)
        lote_layout.addWidget(btn_aplicar_servico, 0, 2)

        lote_layout.addWidget(QLabel("Situação:"), 0, 3)
        self.cmb_lote_situacao = QComboBox()
        self.cmb_lote_situacao.addItems(["ANTES", "DURANTE", "DEPOIS"])
        lote_layout.addWidget(self.cmb_lote_situacao, 0, 4)

        btn_aplicar_situacao = QPushButton("Aplicar Situação")
        btn_aplicar_situacao.clicked.connect(self.aplicar_situacao_em_lote)
        lote_layout.addWidget(btn_aplicar_situacao, 0, 5)

        lote_layout.addWidget(QLabel("Estaca Inicial:"), 1, 0)
        self.edt_lote_estaca_ini = QLineEdit("780")
        self.edt_lote_estaca_ini.setMaximumWidth(80)
        lote_layout.addWidget(self.edt_lote_estaca_ini, 1, 1)

        lote_layout.addWidget(QLabel("Passo:"), 1, 3)
        self.edt_lote_estaca_passo = QLineEdit("1")
        self.edt_lote_estaca_passo.setMaximumWidth(60)
        lote_layout.addWidget(self.edt_lote_estaca_passo, 1, 4)

        btn_aplicar_estacas = QPushButton("Preencher Estacas")
        btn_aplicar_estacas.clicked.connect(self.aplicar_estacas_em_lote)
        lote_layout.addWidget(btn_aplicar_estacas, 1, 5)

        layout.addWidget(lote_group)

        # Tabela Geral
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Incluir", "Página", "Slot", "Arquivo", "Estaca", "KM Calc.", "Situação", "Serviço"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.itemSelectionChanged.connect(self._ao_selecionar_linha_tabela)
        self.table.cellChanged.connect(self._ao_alterar_celula_tabela)

        layout.addWidget(self.table, 1)
        return widget

    def criar_painel_direito(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Widget de Prévia Ampliada
        self.preview_widget = LargeImagePreviewWidget()
        self.preview_widget.set_folder_manager(self.project.folder_manager)
        self.preview_widget.photo_navigated.connect(self._on_preview_photo_navigated)
        self.preview_widget.folder_selected.connect(self._on_preview_folder_selected)
        self.preview_widget.rotation_changed.connect(self._on_preview_rotation_changed)
        layout.addWidget(self.preview_widget, 1)

        # Bloco de Edição da Foto Selecionada
        self.form_foto = QGroupBox("Edição da Foto Selecionada")
        self.form_foto.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        f_layout = QGridLayout(self.form_foto)
        f_layout.setContentsMargins(8, 8, 8, 8)
        f_layout.setSpacing(6)

        f_layout.addWidget(QLabel("Estaca:"), 0, 0)
        self.quick_estaca = QLineEdit()
        self.quick_estaca.setPlaceholderText("ex: 780")
        self.quick_estaca.textChanged.connect(self.quick_atualizar_estaca)
        f_layout.addWidget(self.quick_estaca, 0, 1)

        f_layout.addWidget(QLabel("KM:"), 0, 2)
        self.quick_km = QLabel("-")
        self.quick_km.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.quick_km.setStyleSheet("color: #88c0d0;")
        f_layout.addWidget(self.quick_km, 0, 3)

        f_layout.addWidget(QLabel("Situação:"), 1, 0)
        self.quick_situacao = QComboBox()
        self.quick_situacao.addItems(["DURANTE", "ANTES", "DEPOIS"])
        self.quick_situacao.currentIndexChanged.connect(self.quick_atualizar_situacao)
        f_layout.addWidget(self.quick_situacao, 1, 1)

        f_layout.addWidget(QLabel("Serviço:"), 1, 2)
        self.quick_servico = QLineEdit()
        self.quick_servico.setPlaceholderText("ex: REGULARIZAÇÃO DE SUBLEITO")
        self.quick_servico.textChanged.connect(self.quick_atualizar_servico)
        f_layout.addWidget(self.quick_servico, 1, 3)

        layout.addWidget(self.form_foto)

        return container

    def criar_barra_rodape(self):
        layout = QHBoxLayout()
        self.lbl_status = QLabel("Pronto para indexar imagens.")
        self.lbl_status.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self.lbl_status)
        layout.addStretch()

        lbl_atalhos = QLabel("⌨️ <i>Navegação: Use as setas <b>▲</b> e <b>▼</b> para ciclar fotos na subpasta.</i>")
        lbl_atalhos.setStyleSheet("color: #7289da; font-size: 11px;")
        layout.addWidget(lbl_atalhos)
        return layout

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """Suporte a atalhos de teclado Up/Down globais para navegação de fotos."""
        # Se o foco atual for um campo de texto, preserva a navegação de texto
        focus_w = QApplication.focusWidget()
        if isinstance(focus_w, QLineEdit):
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_Up:
            self._on_preview_photo_navigated(-1)
            event.accept()
        elif event.key() == Qt.Key.Key_Down:
            self._on_preview_photo_navigated(1)
            event.accept()
        else:
            super().keyPressEvent(event)

    def carregar_dados_iniciais(self):
        total_banco = self.db.total_projetos()
        if total_banco == 0:
            # 1. Carrega dados do XML se existir (como base do primeiro projeto)
            self._importar_dados_xml_ou_padrao()

            # Detecta pasta 'assets' e pastas locais para o FolderManager
            assets_dir = os.path.join(self.diretorio_base, "assets")
            if os.path.isdir(assets_dir):
                self.project.folder_manager.adicionar_pasta_raiz(assets_dir)
                if assets_dir not in self.project.pastas_incluidas:
                    self.project.pastas_incluidas.append(assets_dir)

            for pag in self.project.paginas:
                for s in pag.slots:
                    if s.arquivo and os.path.isfile(s.arquivo):
                        dir_path, idx = self.project.folder_manager.encontrar_pasta_e_indice(s.arquivo)
                        s.subpasta = dir_path or ""
                        s.indice_na_pasta = idx

            # Cria o primeiro projeto no banco
            medicao = self.project.campos.get("medicao", "24ª").strip()
            rodovia = self.project.campos.get("rodovia", "BR-319/AM").strip()
            nome_inicial = f"Projeto Padrão ({rodovia} - Medição {medicao})".strip()
            self.projeto_atual_id = self.db.criar_projeto(
                nome_inicial, "Projeto inicial gerado a partir do modelo padrão", self.project
            )
            self.projeto_atual_nome = nome_inicial
            self.atualizar_todas_as_visoes()
        else:
            # Carrega o projeto mais recentemente modificado no banco
            ultimo_id = self.db.obter_ultimo_projeto_id()
            self._abrir_projeto_por_id(ultimo_id, salvar_atual_antes=False)

        self.atualizar_combo_projetos_ui()
        self.page_editor.selecionar_slot(0)
        self._sincronizar_painel_direito_com_slot(self.page_editor.obter_slot_atual())

    def _importar_dados_xml_ou_padrao(self):
        xml_path = os.path.join(self.diretorio_base, "relatorio_fotografico.xml")
        if os.path.exists(xml_path):
            try:
                raiz = ET.parse(xml_path).getroot()
                dados = raiz.find("dados")
                if dados is not None:
                    for campo in dados.findall("campo"):
                        cid = campo.get("id")
                        if cid in self.inputs:
                            self.inputs[cid].setText(campo.text or "")
                            self.project.campos[cid] = campo.text or ""

                    calc = dados.find("calculo")
                    if calc is not None:
                        expr = calc.get("expressao", "")
                        if "+" in expr:
                            partes = expr.split("+")
                            km_val = partes[-1].strip()
                            self.inputs["km_base"].setText(km_val)
                            self.project.campos["km_base"] = km_val

                    fotos_el = dados.find("fotos")
                    if fotos_el is not None:
                        pag1 = self.project.paginas[0]
                        for i, f in enumerate(fotos_el.findall("foto")):
                            if i >= 6:
                                break
                            arq = f.get("arquivo", "")
                            caminho_abs = os.path.join(self.diretorio_base, arq) if not os.path.isabs(arq) else arq
                            slot = pag1.slots[i]
                            slot.arquivo = caminho_abs
                            slot.estaca = f.get("estaca", "")
                            slot.situacao = f.get("situacao", "DURANTE")
                            slot.servico = f.get("servico", "")
                            slot.ativo = True
            except Exception as e:
                print("Erro ao carregar dados do XML inicial:", e)

        for k, v in VALORES_PADRAO_CAMPOS.items():
            if k in self.inputs and not self.inputs[k].text():
                self.inputs[k].setText(v)
                self.project.campos[k] = v

        logo_atual = self.inputs["logo_path"].text()
        if not os.path.isabs(logo_atual):
            self.inputs["logo_path"].setText(os.path.join(self.diretorio_base, logo_atual))
            self.project.campos["logo_path"] = self.inputs["logo_path"].text()

    def _abrir_projeto_por_id(self, projeto_id: int, salvar_atual_antes: bool = True):
        """Carrega e ativa um projeto do banco de dados na interface."""
        if salvar_atual_antes and self.projeto_atual_id and self.projeto_atual_id != projeto_id:
            self.salvar_progresso_banco(silencioso=True)

        proj, info = self.db.carregar_projeto(projeto_id)
        if not proj:
            QMessageBox.warning(self, "Aviso", f"Não foi possível carregar o projeto ID {projeto_id}.")
            return

        self.project = proj
        self.projeto_atual_id = projeto_id
        self.projeto_atual_nome = info.get("nome", f"Projeto #{projeto_id}")

        # Atualiza campos de entrada do contrato
        for k, edt in self.inputs.items():
            if k in self.project.campos:
                edt.blockSignals(True)
                edt.setText(str(self.project.campos[k]))
                edt.blockSignals(False)

        # Atualiza o FolderManager com as pastas do projeto
        for pasta in self.project.pastas_incluidas:
            if os.path.isdir(pasta):
                self.project.folder_manager.adicionar_pasta_raiz(pasta)

        assets_dir = os.path.join(self.diretorio_base, "assets")
        if os.path.isdir(assets_dir) and assets_dir not in self.project.folder_manager.pastas:
            self.project.folder_manager.adicionar_pasta_raiz(assets_dir)

        for pag in self.project.paginas:
            for s in pag.slots:
                if s.arquivo and os.path.isfile(s.arquivo):
                    dir_path, idx = self.project.folder_manager.encontrar_pasta_e_indice(s.arquivo)
                    if not s.subpasta and dir_path:
                        s.subpasta = dir_path
                    if s.indice_na_pasta < 0:
                        s.indice_na_pasta = idx

        self.page_editor.set_project(self.project)
        self.page_editor.pagina_atual_index = 0
        self.preview_widget.set_folder_manager(self.project.folder_manager)

        self.atualizar_todas_as_visoes()
        self.atualizar_combo_projetos_ui()
        self.page_editor.selecionar_slot(0)
        self._sincronizar_painel_direito_com_slot(self.page_editor.obter_slot_atual())

        self.setWindowTitle(f"Gerador & Indexador de Relatórios (DNIT) - [{self.projeto_atual_nome}]")
        self.lbl_status.setText(f"Projeto ativo: '{self.projeto_atual_nome}'")

    def salvar_progresso_banco(self, silencioso: bool = False):
        """Salva todo o progresso atual (variáveis, páginas, indexações de fotos) no banco de dados SQLite."""
        if not self.projeto_atual_id:
            return

        for k, edt in self.inputs.items():
            self.project.campos[k] = edt.text().strip()

        ok = self.db.salvar_projeto(self.projeto_atual_id, self.project)
        if ok:
            agora = datetime.now().strftime("%H:%M:%S")
            self.lbl_status.setText(f"💾 Progresso do projeto '{self.projeto_atual_nome}' salvo no banco de dados às {agora}!")
            self.atualizar_combo_projetos_ui()
            if not silencioso:
                total_fotos = len(self.project.obter_todas_fotos_ativas())
                total_pags = len(self.project.paginas)
                QMessageBox.information(
                    self, "Progresso Salvo no Banco de Dados",
                    f"O progresso do projeto '{self.projeto_atual_nome}' foi salvo com sucesso no banco de dados local!\n\n"
                    f"• {total_pags} página(s)\n"
                    f"• {total_fotos} foto(s) ativas indexadas\n"
                    f"• Variáveis e parâmetros de cálculo atualizados\n\n"
                    f"Registro gravado às {agora} sem necessidade de gerar PDF."
                )
        else:
            if not silencioso:
                QMessageBox.critical(self, "Erro", "Erro ao gravar dados no banco de dados local.")

    def _ao_selecionar_projeto_combo(self, idx: int):
        if idx < 0:
            return
        pid = self.cmb_projetos.itemData(idx)
        if pid and pid != self.projeto_atual_id:
            self._abrir_projeto_por_id(pid, salvar_atual_antes=True)

    def atualizar_combo_projetos_ui(self):
        if not hasattr(self, 'cmb_projetos'):
            return
        self.cmb_projetos.blockSignals(True)
        self.cmb_projetos.clear()

        projetos = self.db.listar_projetos()
        idx_selecionar = 0

        for i, p in enumerate(projetos):
            texto = f"📁 {p['nome']} ({p['total_paginas']} pág. • {p['total_fotos_ativas']} fotos)"
            self.cmb_projetos.addItem(texto, p["id"])
            if p["id"] == self.projeto_atual_id:
                idx_selecionar = i

        if self.cmb_projetos.count() > 0:
            self.cmb_projetos.setCurrentIndex(idx_selecionar)

        self.cmb_projetos.blockSignals(False)

    def acao_novo_projeto(self):
        nome, ok = QtWidgets.QInputDialog.getText(
            self, "Novo Projeto", "Digite o nome para o novo projeto:",
            text=f"Projeto - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        if not ok or not nome.strip():
            return

        nome = nome.strip()
        try:
            if self.projeto_atual_id:
                self.salvar_progresso_banco(silencioso=True)

            novo_proj = ReportProject()
            novo_id = self.db.criar_projeto(nome, "", novo_proj)
            self._abrir_projeto_por_id(novo_id, salvar_atual_antes=False)
            QMessageBox.information(self, "Projeto Criado", f"Projeto '{nome}' criado e ativado com sucesso!")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível criar o projeto:\n{e}")

    def acao_duplicar_projeto_atual(self):
        if not self.projeto_atual_id:
            return

        sugestao = f"{self.projeto_atual_nome} (Cópia)"
        nome, ok = QtWidgets.QInputDialog.getText(
            self, "Duplicar Projeto", "Nome para a cópia do projeto:",
            text=sugestao
        )
        if not ok or not nome.strip():
            return

        try:
            self.salvar_progresso_banco(silencioso=True)
            novo_id = self.db.duplicar_projeto(self.projeto_atual_id, nome.strip())
            self._abrir_projeto_por_id(novo_id, salvar_atual_antes=False)
            QMessageBox.information(self, "Projeto Duplicado", f"Projeto duplicado com sucesso como '{nome.strip()}'!")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao duplicar projeto:\n{e}")

    def acao_renomear_projeto_atual(self):
        if not self.projeto_atual_id:
            return

        nome, ok = QtWidgets.QInputDialog.getText(
            self, "Renomear Projeto", "Novo nome para o projeto:",
            text=self.projeto_atual_nome
        )
        if not ok or not nome.strip():
            return

        try:
            self.db.renomear_projeto(self.projeto_atual_id, nome.strip())
            self.projeto_atual_nome = nome.strip()
            self.atualizar_combo_projetos_ui()
            self.setWindowTitle(f"Gerador & Indexador de Relatórios (DNIT) - [{self.projeto_atual_nome}]")
            QMessageBox.information(self, "Projeto Renomeado", f"Projeto renomeado para '{self.projeto_atual_nome}' com sucesso!")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao renomear projeto:\n{e}")

    def acao_excluir_projeto_atual(self):
        if not self.projeto_atual_id:
            return

        if self.db.total_projetos() <= 1:
            QMessageBox.warning(
                self, "Aviso",
                "Não é possível excluir o único projeto do banco de dados.\nCrie outro projeto antes de excluir este."
            )
            return

        resp = QMessageBox.question(
            self, "Confirmar Exclusão de Projeto",
            f"Tem certeza que deseja excluir o projeto '{self.projeto_atual_nome}' do banco de dados?\n"
            f"Todas as páginas e indexações deste projeto serão permanentemente apagadas.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            pid = self.projeto_atual_id
            self.db.excluir_projeto(pid)
            outro_id = self.db.obter_ultimo_projeto_id()
            self.projeto_atual_id = None
            self._abrir_projeto_por_id(outro_id, salvar_atual_antes=False)
            QMessageBox.information(self, "Projeto Excluído", "Projeto excluído com sucesso do banco de dados.")

    def acao_abrir_gerenciador_projetos(self):
        dlg = ProjectManagerDialog(self.db, self.projeto_atual_id, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if dlg.projeto_selecionado_id and dlg.projeto_selecionado_id != self.projeto_atual_id:
                self._abrir_projeto_por_id(dlg.projeto_selecionado_id, salvar_atual_antes=True)
            else:
                self.atualizar_combo_projetos_ui()

    def acao_incluir_pastas(self):
        pasta = QFileDialog.getExistingDirectory(self, "Selecionar Pasta Raiz ou Subpasta", self.diretorio_base)
        if not pasta:
            return

        pastas_adicionadas = self.project.incluir_pasta(pasta)
        if not pastas_adicionadas:
            QMessageBox.information(self, "Sem Fotos", "Nenhuma imagem (.jpg, .png, etc.) encontrada na pasta selecionada.")
            return

        self.preview_widget.atualizar_lista_subpastas()
        self.page_editor.carregar_pagina_atual()
        self.atualizar_lista_subpastas_ui()

        total_pastas = len(pastas_adicionadas)
        self.lbl_status.setText(f"{total_pastas} subpasta(s) indexada(s) a partir de '{os.path.basename(pasta)}'.")

    def acao_adicionar_pagina(self):
        self.page_editor.adicionar_pagina()
        self.atualizar_todas_as_visoes()

    def acao_duplicar_pagina(self):
        self.page_editor.duplicar_pagina_atual()
        self.atualizar_todas_as_visoes()

    def acao_remover_pagina(self):
        self.page_editor.remover_pagina_atual()
        self.atualizar_todas_as_visoes()

    def acao_mover_pagina_cima(self):
        idx = self.page_editor.pagina_atual_index
        if idx > 0:
            self.project.mover_pagina(idx, idx - 1)
            self.page_editor.pagina_atual_index = idx - 1
            self.page_editor.carregar_pagina_atual()
            self.atualizar_todas_as_visoes()

    def acao_mover_pagina_baixo(self):
        idx = self.page_editor.pagina_atual_index
        if idx < len(self.project.paginas) - 1:
            self.project.mover_pagina(idx, idx + 1)
            self.page_editor.pagina_atual_index = idx + 1
            self.page_editor.carregar_pagina_atual()
            self.atualizar_todas_as_visoes()

    def _ao_trocar_pagina_lista(self, row: int):
        if 0 <= row < len(self.project.paginas):
            if self.page_editor.pagina_atual_index != row:
                self.page_editor.pagina_atual_index = row
                self.page_editor.carregar_pagina_atual()
                self.page_editor.selecionar_slot(0)
                self._sincronizar_painel_direito_com_slot(self.page_editor.obter_slot_atual())
                self.atualizar_tabela_geral()

    def _ao_pagina_mudou(self, page_idx: int):
        self.atualizar_lista_paginas_ui()
        self._sincronizar_painel_direito_com_slot(self.page_editor.obter_slot_atual())

    def atualizar_lista_paginas_ui(self):
        if not hasattr(self, 'list_paginas'):
            return
        self.list_paginas.blockSignals(True)
        self.list_paginas.clear()
        total_pags = len(self.project.paginas)
        for i, p in enumerate(self.project.paginas):
            total_ativas = p.total_fotos_ativas()
            item = QListWidgetItem(f"📄 {p.titulo} ({total_ativas}/6 fotos)")
            self.list_paginas.addItem(item)

        curr = self.page_editor.pagina_atual_index
        if 0 <= curr < self.list_paginas.count():
            self.list_paginas.setCurrentRow(curr)
        self.lbl_paginas_badge.setText(f"{total_pags} pág.")
        self.list_paginas.blockSignals(False)

    def atualizar_lista_subpastas_ui(self):
        self.list_subpastas.clear()
        for caminho, nome, total in self.project.folder_manager.obter_subpastas():
            item = QListWidgetItem(f"{nome} ({total} fotos)")
            item.setData(Qt.ItemDataRole.UserRole, caminho)
            self.list_subpastas.addItem(item)

    def _criar_pagina_de_subpasta_selecionada(self):
        item = self.list_subpastas.currentItem()
        if not item:
            QMessageBox.information(self, "Aviso", "Selecione uma subpasta na lista.")
            return
        caminho = item.data(Qt.ItemDataRole.UserRole)
        fotos = self.project.folder_manager.obter_fotos(caminho)
        if not fotos:
            return

        # Adiciona nova página e preenche com até 6 fotos
        nova_pag = self.project.adicionar_pagina(f"Página - {os.path.basename(caminho)}")
        for i in range(min(6, len(fotos))):
            slot = nova_pag.slots[i]
            slot.arquivo = fotos[i]
            slot.subpasta = caminho
            slot.indice_na_pasta = i
            slot.ativo = True

        self.page_editor.atualizar_abas_e_pagina()
        self.page_editor.selecionar_slot(0)
        self.atualizar_todas_as_visoes()

    def _ao_alterar_campo_relatorio(self):
        for k, edt in self.inputs.items():
            self.project.campos[k] = edt.text().strip()
        self.page_editor.carregar_pagina_atual()
        self.atualizar_tabela_geral()

    def selecionar_logo(self):
        arq, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Imagem do Logo", self.diretorio_base, "Imagens (*.png *.jpg *.jpeg)"
        )
        if arq:
            self.inputs["logo_path"].setText(arq)
            self.project.campos["logo_path"] = arq

    def _ao_selecionar_slot_da_pagina(self, slot_idx: int):
        slot = self.page_editor.obter_slot_atual()
        self._sincronizar_painel_direito_com_slot(slot)

    def _sincronizar_painel_direito_com_slot(self, slot: Optional[PhotoSlot]):
        self.preview_widget.exibir_slot(slot)

        self.quick_estaca.blockSignals(True)
        self.quick_situacao.blockSignals(True)
        self.quick_servico.blockSignals(True)

        pag_idx = self.page_editor.pagina_atual_index + 1
        slot_idx = self.page_editor.slot_selecionado_index + 1
        self.form_foto.setTitle(f"📝 Edição da Foto Selecionada (Página {pag_idx} • Slot #{slot_idx})")

        if slot:
            self.quick_estaca.setEnabled(True)
            self.quick_situacao.setEnabled(True)
            self.quick_servico.setEnabled(True)

            self.quick_estaca.setText(slot.estaca)
            km_base = self.project.campos.get("km_base", "198.8")
            m_estaca = self.project.campos.get("metros_estaca", "20.0")
            self.quick_km.setText(calcular_km_estaca(slot.estaca, km_base, m_estaca) or "-")

            idx = self.quick_situacao.findText(slot.situacao)
            if idx >= 0:
                self.quick_situacao.setCurrentIndex(idx)
            self.quick_servico.setText(slot.servico)
        else:
            self.quick_estaca.setText("")
            self.quick_km.setText("-")
            self.quick_servico.setText("")
            self.quick_estaca.setEnabled(False)
            self.quick_situacao.setEnabled(False)
            self.quick_servico.setEnabled(False)

        self.quick_estaca.blockSignals(False)
        self.quick_situacao.blockSignals(False)
        self.quick_servico.blockSignals(False)

    def _on_preview_photo_navigated(self, delta: int):
        slot = self.page_editor.obter_slot_atual()
        if not slot:
            return

        # Se o slot não tem subpasta definida, usa a primeira subpasta registrada
        if not slot.subpasta:
            subpastas = self.project.folder_manager.obter_subpastas()
            if subpastas:
                slot.subpasta = subpastas[0][0]
                slot.indice_na_pasta = -1

        if not slot.subpasta:
            QMessageBox.information(
                self, "Subpasta Necessária",
                "Selecione primeiro uma subpasta no topo da prévia ou inclua uma pasta com fotos."
            )
            return

        novo_idx, novo_arq = self.project.folder_manager.navegar_foto(slot.subpasta, slot.indice_na_pasta, delta)
        if novo_arq:
            slot.arquivo = novo_arq
            slot.indice_na_pasta = novo_idx
            slot.ativo = True

            self.page_editor.carregar_pagina_atual()
            self._sincronizar_painel_direito_com_slot(slot)
            self.atualizar_tabela_geral()
            self.atualizar_status_geral()

    def _ao_navegar_foto_slot(self, slot_idx: int, delta: int):
        self._on_preview_photo_navigated(delta)

    def _on_preview_folder_selected(self, caminho_subpasta: str):
        slot = self.page_editor.obter_slot_atual()
        if not slot or not caminho_subpasta:
            return

        slot.subpasta = caminho_subpasta
        fotos = self.project.folder_manager.obter_fotos(caminho_subpasta)
        if fotos:
            slot.arquivo = fotos[0]
            slot.indice_na_pasta = 0
            slot.ativo = True

        self.page_editor.carregar_pagina_atual()
        self._sincronizar_painel_direito_com_slot(slot)
        self.atualizar_tabela_geral()
        self.atualizar_status_geral()

    def _ao_selecionar_subpasta_slot(self, slot_idx: int, caminho_subpasta: str):
        self._on_preview_folder_selected(caminho_subpasta)

    def _on_preview_rotation_changed(self, nova_rot: int):
        slot = self.page_editor.obter_slot_atual()
        if slot:
            slot.rotacao = nova_rot
            self.page_editor.carregar_pagina_atual()

    def _ao_modificar_projeto(self):
        self.atualizar_lista_paginas_ui()
        self.atualizar_tabela_geral()
        self.atualizar_status_geral()

    def _ao_trocar_aba_central(self, index: int):
        if index == 1:
            self.atualizar_tabela_geral()
        elif index == 0:
            self.page_editor.carregar_pagina_atual()

    # ---- Métodos de Edição Rápida da Foto ----
    def quick_atualizar_estaca(self, txt: str):
        slot = self.page_editor.obter_slot_atual()
        if slot:
            slot.estaca = txt.strip()
            km_base = self.project.campos.get("km_base", "198.8")
            m_estaca = self.project.campos.get("metros_estaca", "20.0")
            km_val = calcular_km_estaca(txt, km_base, m_estaca)
            self.quick_km.setText(km_val or "-")
            self._ao_modificar_projeto()

    def quick_atualizar_situacao(self, idx: int):
        slot = self.page_editor.obter_slot_atual()
        if slot:
            slot.situacao = self.quick_situacao.currentText()
            self._ao_modificar_projeto()

    def quick_atualizar_servico(self, txt: str):
        slot = self.page_editor.obter_slot_atual()
        if slot:
            slot.servico = txt.strip()
            self._ao_modificar_projeto()

    # ---- Sincronização com Tabela Geral e Ações em Lote ----
    def _obter_lista_slots_plana(self):
        """Retorna lista de tuplas (pagina_idx, slot_idx, slot)."""
        resultado = []
        for p_idx, pag in enumerate(self.project.paginas):
            for s_idx, slot in enumerate(pag.slots):
                if slot.esta_preenchido():
                    resultado.append((p_idx, s_idx, slot))
        return resultado

    def atualizar_tabela_geral(self):
        self.table.blockSignals(True)
        itens = self._obter_lista_slots_plana()
        self.table.setRowCount(len(itens))

        km_base = self.project.campos.get("km_base", "198.8")
        metros = self.project.campos.get("metros_estaca", "20.0")

        for r, (p_idx, s_idx, slot) in enumerate(itens):
            # Checkbox
            chk = QTableWidgetItem()
            chk.setCheckState(Qt.CheckState.Checked if slot.ativo else Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, (p_idx, s_idx))
            self.table.setItem(r, 0, chk)

            # Página
            it_pag = QTableWidgetItem(f"Pág. {p_idx + 1}")
            it_pag.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_pag.setFlags(it_pag.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 1, it_pag)

            # Slot
            it_slot = QTableWidgetItem(f"#{s_idx + 1}")
            it_slot.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_slot.setFlags(it_slot.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 2, it_slot)

            # Arquivo
            it_arq = QTableWidgetItem(slot.nome)
            it_arq.setToolTip(slot.arquivo)
            it_arq.setFlags(it_arq.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 3, it_arq)

            # Estaca
            it_est = QTableWidgetItem(slot.estaca)
            it_est.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 4, it_est)

            # KM Calc
            km_val = calcular_km_estaca(slot.estaca, km_base, metros)
            it_km = QTableWidgetItem(km_val)
            it_km.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_km.setFlags(it_km.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 5, it_km)

            # Situação
            it_sit = QTableWidgetItem(slot.situacao)
            it_sit.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 6, it_sit)

            # Serviço
            it_serv = QTableWidgetItem(slot.servico)
            self.table.setItem(r, 7, it_serv)

        self.table.blockSignals(False)

    def _ao_selecionar_linha_tabela(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item_chk = self.table.item(row, 0)
        if not item_chk:
            return
        p_idx, s_idx = item_chk.data(Qt.ItemDataRole.UserRole)
        if 0 <= p_idx < len(self.project.paginas):
            self.page_editor.pagina_atual_index = p_idx
            self.page_editor.tab_paginas.setCurrentIndex(p_idx)
            self.page_editor.selecionar_slot(s_idx)
            slot = self.project.paginas[p_idx].obter_slot(s_idx)
            self._sincronizar_painel_direito_com_slot(slot)

    def _ao_alterar_celula_tabela(self, row: int, col: int):
        item_chk = self.table.item(row, 0)
        if not item_chk:
            return
        p_idx, s_idx = item_chk.data(Qt.ItemDataRole.UserRole)
        slot = self.project.paginas[p_idx].obter_slot(s_idx)
        if not slot:
            return

        if col == 0:
            slot.ativo = (item_chk.checkState() == Qt.CheckState.Checked)
        elif col == 4:
            it = self.table.item(row, col)
            slot.estaca = it.text().strip()
            km_base = self.project.campos.get("km_base", "198.8")
            metros = self.project.campos.get("metros_estaca", "20.0")
            km_val = calcular_km_estaca(slot.estaca, km_base, metros)
            self.table.blockSignals(True)
            self.table.item(row, 5).setText(km_val)
            self.table.blockSignals(False)
        elif col == 6:
            it = self.table.item(row, col)
            slot.situacao = it.text().strip().upper()
        elif col == 7:
            it = self.table.item(row, col)
            slot.servico = it.text().strip()

        self.page_editor.carregar_pagina_atual()
        self.atualizar_status_geral()

    def aplicar_servico_em_lote(self):
        serv = self.edt_lote_servico.text().strip()
        if not serv:
            QMessageBox.warning(self, "Aviso", "Digite o nome do serviço a aplicar.")
            return

        linhas = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        if not linhas:
            linhas = list(range(self.table.rowCount()))

        for r in linhas:
            item_chk = self.table.item(r, 0)
            if item_chk:
                p_idx, s_idx = item_chk.data(Qt.ItemDataRole.UserRole)
                slot = self.project.paginas[p_idx].obter_slot(s_idx)
                if slot:
                    slot.servico = serv

        self.atualizar_todas_as_visoes()
        self.lbl_status.setText(f"Serviço '{serv}' aplicado a {len(linhas)} foto(s).")

    def aplicar_situacao_em_lote(self):
        sit = self.cmb_lote_situacao.currentText()
        linhas = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        if not linhas:
            linhas = list(range(self.table.rowCount()))

        for r in linhas:
            item_chk = self.table.item(r, 0)
            if item_chk:
                p_idx, s_idx = item_chk.data(Qt.ItemDataRole.UserRole)
                slot = self.project.paginas[p_idx].obter_slot(s_idx)
                if slot:
                    slot.situacao = sit

        self.atualizar_todas_as_visoes()
        self.lbl_status.setText(f"Situação '{sit}' aplicada a {len(linhas)} foto(s).")

    def aplicar_estacas_em_lote(self):
        txt_ini = self.edt_lote_estaca_ini.text().strip()
        txt_passo = self.edt_lote_estaca_passo.text().strip() or "1"
        try:
            estaca_atual = float(txt_ini.replace(",", "."))
            passo = float(txt_passo.replace(",", "."))
        except ValueError:
            QMessageBox.warning(self, "Aviso", "Informe valores numéricos válidos para Estaca Inicial e Passo.")
            return

        linhas = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        if not linhas:
            linhas = list(range(self.table.rowCount()))

        for r in linhas:
            item_chk = self.table.item(r, 0)
            if item_chk:
                p_idx, s_idx = item_chk.data(Qt.ItemDataRole.UserRole)
                slot = self.project.paginas[p_idx].obter_slot(s_idx)
                if slot:
                    if estaca_atual.is_integer():
                        str_est = str(int(estaca_atual))
                    else:
                        str_est = f"{estaca_atual:.2f}".replace(".", ",")
                    slot.estaca = str_est
                    estaca_atual += passo

        self.atualizar_todas_as_visoes()
        self.lbl_status.setText(f"Estacas em sequência aplicadas a {len(linhas)} foto(s).")

    def atualizar_todas_as_visoes(self):
        self.preview_widget.atualizar_lista_subpastas()
        self.atualizar_lista_subpastas_ui()
        self.page_editor.atualizar_abas_e_pagina()
        self.atualizar_lista_paginas_ui()
        self.atualizar_tabela_geral()
        self.atualizar_status_geral()

    def atualizar_status_geral(self):
        total_pags = len(self.project.paginas)
        fotos_ativas = self.project.obter_todas_fotos_ativas()
        subpastas = len(self.project.folder_manager.pastas)
        self.lbl_status.setText(
            f"Projeto: {total_pags} página(s) | {len(fotos_ativas)} fotos ativas vinculadas | {subpastas} subpasta(s) registradas"
        )

    # ---- Persistência JSON e Geração PDF ----
    def salvar_perfil_json(self):
        caminho, _ = QFileDialog.getSaveFileName(
            self, "Salvar Perfil / Projeto",
            os.path.join(self.diretorio_base, "projeto_relatorio.json"),
            "Arquivos JSON (*.json)"
        )
        if not caminho:
            return

        for k, edt in self.inputs.items():
            self.project.campos[k] = edt.text().strip()

        try:
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(self.project.to_dict(), f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Sucesso", "Projeto e páginas salvos com sucesso!")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar arquivo JSON:\n{e}")

    def carregar_perfil_json(self):
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Carregar Perfil / Projeto", self.diretorio_base, "Arquivos JSON (*.json)"
        )
        if not caminho:
            return

        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)

            self.project.carregar_de_dict(dados)

            # Atualiza inputs
            for k, edt in self.inputs.items():
                if k in self.project.campos:
                    edt.setText(str(self.project.campos[k]))

            self.atualizar_todas_as_visoes()
            self.page_editor.selecionar_slot(0)
            self._sincronizar_painel_direito_com_slot(self.page_editor.obter_slot_atual())

            QMessageBox.information(self, "Sucesso", "Projeto e páginas carregados com sucesso!")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao ler arquivo JSON:\n{e}")

    def gerar_pdf(self):
        fotos_ativas = self.project.obter_todas_fotos_ativas()
        if not fotos_ativas:
            QMessageBox.warning(self, "Aviso", "Nenhuma foto está ativa para o relatório.")
            return

        medicao_limpa = self.project.campos.get("medicao", "").replace("ª", "").strip() or "relatorio"
        sugestao_nome = f"relatorio_medicao_{medicao_limpa}.pdf"
        saida_pdf, _ = QFileDialog.getSaveFileName(
            self, "Salvar Relatório PDF",
            os.path.join(self.diretorio_base, sugestao_nome),
            "Arquivos PDF (*.pdf)"
        )
        if not saida_pdf:
            return

        campos = dict(self.project.campos)
        logo_path = campos.get("logo_path", "")
        if not os.path.isabs(logo_path):
            logo_path = os.path.join(self.diretorio_base, logo_path)

        try:
            # Geração direta respeitando as páginas explícitas do projeto
            total_paginas = generator.gerar_relatorio_paginas_pdf(
                saida_pdf, campos, self.project.paginas, logo_path
            )

            # Exporta também o XML para manter compatibilidade
            saida_xml = os.path.splitext(saida_pdf)[0] + ".xml"
            generator.exportar_xml(saida_xml, campos, fotos_ativas, logo_path)

            msg = QMessageBox(self)
            msg.setWindowTitle("Relatório Gerado com Sucesso")
            msg.setText(
                f"O relatório foi gerado com sucesso!\n\n"
                f"• Folhas/Páginas geradas: {total_paginas}\n"
                f"• Fotos incluídas: {len(fotos_ativas)}\n"
                f"• Arquivo PDF: {os.path.basename(saida_pdf)}\n"
                f"• Arquivo XML: {os.path.basename(saida_xml)}"
            )
            btn_abrir = msg.addButton("Abrir PDF", QMessageBox.ButtonRole.ActionRole)
            btn_ok = msg.addButton(QMessageBox.StandardButton.Ok)
            msg.exec()

            if msg.clickedButton() == btn_abrir:
                os.startfile(saida_pdf)

        except Exception as e:
            QMessageBox.critical(self, "Erro na Geração", f"Ocorreu um erro ao gerar o PDF:\n{e}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Paleta Dark / Clean Profissional
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QColor(34, 36, 40))
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QColor(230, 230, 230))
    palette.setColor(QtGui.QPalette.ColorRole.Base, QColor(24, 25, 28))
    palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QColor(34, 36, 40))
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QColor(230, 230, 230))
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QColor(230, 230, 230))
    palette.setColor(QtGui.QPalette.ColorRole.Text, QColor(230, 230, 230))
    palette.setColor(QtGui.QPalette.ColorRole.Button, QColor(45, 48, 54))
    palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QColor(230, 230, 230))
    palette.setColor(QtGui.QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QtGui.QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QtGui.QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
