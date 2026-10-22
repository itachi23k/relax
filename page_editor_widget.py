#!/usr/bin/env python3
"""
Widget do Editor Visual de Páginas e Slots (Padrão DNIT).
Gerencia a criação e navegação de páginas e a visualização dos 6 slots por folha.
"""
import os
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QFrame,
    QTabWidget, QTabBar, QMessageBox, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QFont, QColor, QTransform

from typing import Optional, List, Dict, Tuple
from models import ReportProject, ReportPage, PhotoSlot, FolderManager, calcular_km_estaca


class SlotCardWidget(QFrame):
    """Card individual para cada um dos 6 slots de uma página."""
    slot_selected = pyqtSignal(int)
    photo_navigated = pyqtSignal(int, int)  # (slot_index, delta)
    subfolder_changed = pyqtSignal(int, str)  # (slot_index, subfolder_path)
    metadata_changed = pyqtSignal(int)  # slot_index

    def __init__(self, slot_index: int, parent=None):
        super().__init__(parent)
        self.slot_index = slot_index
        self.slot_data: Optional[PhotoSlot] = None
        self.is_selected = False
        self.folder_manager: Optional[FolderManager] = None
        self.km_base = "198.8"
        self.metros_estaca = "20.0"

        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.atualizar_estilo()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Cabeçalho do Slot
        header_layout = QHBoxLayout()
        posicoes = [
            "1 (Topo-Esq)", "2 (Topo-Dir)",
            "3 (Meio-Esq)", "4 (Meio-Dir)",
            "5 (Fundo-Esq)", "6 (Fundo-Dir)"
        ]
        pos_txt = posicoes[self.slot_index] if self.slot_index < len(posicoes) else str(self.slot_index + 1)
        self.lbl_titulo = QLabel(f"<b>Foto #{pos_txt}</b>")
        self.lbl_titulo.setFont(QFont("Segoe UI", 8))
        header_layout.addWidget(self.lbl_titulo)

        header_layout.addStretch()

        self.chk_ativo = QCheckBox("Incluir")
        self.chk_ativo.setChecked(True)
        self.chk_ativo.toggled.connect(self._on_chk_toggled)
        header_layout.addWidget(self.chk_ativo)

        self.btn_limpar = QPushButton("✕")
        self.btn_limpar.setToolTip("Limpar foto deste slot")
        self.btn_limpar.setMaximumWidth(22)
        self.btn_limpar.clicked.connect(self._limpar_slot)
        header_layout.addWidget(self.btn_limpar)

        layout.addLayout(header_layout)

        # Miniatura Clicável (Expandida)
        self.lbl_thumb = QLabel("Slot Vazio\n(Clique para selecionar)")
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thumb.setMinimumHeight(140)
        self.lbl_thumb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.lbl_thumb.setStyleSheet("""
            QLabel {
                background-color: #1e2023;
                border: 1px dashed #3f434a;
                border-radius: 4px;
                color: #888;
                font-size: 11px;
            }
            QLabel:hover {
                border-color: #4da3ff;
                background-color: #24272c;
            }
        """)
        self.lbl_thumb.mousePressEvent = self._on_thumb_clicked
        layout.addWidget(self.lbl_thumb)

        # Linha de Navegação: Subpasta e Botões UP / DOWN
        nav_layout = QHBoxLayout()
        self.btn_up = QPushButton("▲")
        self.btn_up.setToolTip("Foto anterior na subpasta [Up]")
        self.btn_up.setMaximumWidth(26)
        self.btn_up.clicked.connect(lambda: self.photo_navigated.emit(self.slot_index, -1))
        nav_layout.addWidget(self.btn_up)

        self.cmb_subpasta = QComboBox()
        self.cmb_subpasta.setToolTip("Escolha a subpasta para esta foto")
        self.cmb_subpasta.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cmb_subpasta.currentIndexChanged.connect(self._on_subpasta_combo_changed)
        nav_layout.addWidget(self.cmb_subpasta, 1)

        self.btn_down = QPushButton("▼")
        self.btn_down.setToolTip("Próxima foto na subpasta [Down]")
        self.btn_down.setMaximumWidth(26)
        self.btn_down.clicked.connect(lambda: self.photo_navigated.emit(self.slot_index, 1))
        nav_layout.addWidget(self.btn_down)

        layout.addLayout(nav_layout)

        # Contador e Nome da foto no slot
        self.lbl_foto_info = QLabel("Nenhuma foto")
        self.lbl_foto_info.setStyleSheet("color: #7289da; font-size: 10px; font-weight: bold;")
        self.lbl_foto_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_foto_info)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.slot_selected.emit(self.slot_index)

    def _on_thumb_clicked(self, event):
        self.slot_selected.emit(self.slot_index)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.atualizar_estilo()

    def atualizar_estilo(self):
        if self.is_selected:
            self.setStyleSheet("""
                SlotCardWidget {
                    background-color: #2b3038;
                    border: 2px solid #2a82da;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                SlotCardWidget {
                    background-color: #24262a;
                    border: 1px solid #36393f;
                    border-radius: 6px;
                }
            """)

    def set_folder_manager(self, fm: FolderManager):
        self.folder_manager = fm
        self.atualizar_combo_subpastas()

    def set_km_params(self, km_base: str, metros_estaca: str):
        self.km_base = km_base
        self.metros_estaca = metros_estaca

    def atualizar_combo_subpastas(self):
        if not self.folder_manager:
            return
        self.cmb_subpasta.blockSignals(True)
        caminho_atual = self.cmb_subpasta.currentData()
        self.cmb_subpasta.clear()
        self.cmb_subpasta.addItem("-- Subpasta --", "")

        for caminho, nome, total in self.folder_manager.obter_subpastas():
            self.cmb_subpasta.addItem(f"{nome} ({total})", caminho)

        # Restaura seleção se válida
        if caminho_atual:
            for i in range(self.cmb_subpasta.count()):
                if self.cmb_subpasta.itemData(i) == caminho_atual:
                    self.cmb_subpasta.setCurrentIndex(i)
                    break
        self.cmb_subpasta.blockSignals(False)

    def carregar_slot(self, slot: PhotoSlot):
        self.slot_data = slot
        self.blockSignals(True)

        self.chk_ativo.setChecked(slot.ativo)

        # Seleciona subpasta no combo
        self.cmb_subpasta.blockSignals(True)
        if slot.subpasta:
            norm = os.path.abspath(slot.subpasta)
            for i in range(self.cmb_subpasta.count()):
                if self.cmb_subpasta.itemData(i) == norm:
                    self.cmb_subpasta.setCurrentIndex(i)
                    break
        else:
            self.cmb_subpasta.setCurrentIndex(0)
        self.cmb_subpasta.blockSignals(False)

        self._atualizar_miniatura()
        self._atualizar_info_texto()

        self.blockSignals(False)

    def _atualizar_miniatura(self):
        if self.slot_data and self.slot_data.esta_preenchido():
            try:
                pix = QPixmap(self.slot_data.arquivo)
                if not pix.isNull():
                    if self.slot_data.rotacao != 0:
                        transform = QTransform().rotate(self.slot_data.rotacao)
                        pix = pix.transformed(transform, Qt.TransformationMode.SmoothTransformation)
                    scaled = pix.scaled(
                        240, 150,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.lbl_thumb.setPixmap(scaled)
                    return
            except Exception:
                pass
        self.lbl_thumb.clear()
        self.lbl_thumb.setText("Slot Vazio\n(Clique para selecionar)")

    def _atualizar_info_texto(self):
        if not self.slot_data or not self.slot_data.esta_preenchido():
            self.lbl_foto_info.setText("Nenhuma foto vinculada")
            return

        nome = self.slot_data.nome
        if self.folder_manager and self.slot_data.subpasta:
            fotos = self.folder_manager.obter_fotos(self.slot_data.subpasta)
            total = len(fotos)
            idx = self.slot_data.indice_na_pasta
            pos = (idx + 1) if idx >= 0 else 1
            self.lbl_foto_info.setText(f"Foto {pos}/{total}: {nome}")
        else:
            self.lbl_foto_info.setText(nome)

    def _on_chk_toggled(self, checked: bool):
        if self.slot_data:
            self.slot_data.ativo = checked
            self.metadata_changed.emit(self.slot_index)

    def _limpar_slot(self):
        if self.slot_data:
            self.slot_data.arquivo = ""
            self.slot_data.subpasta = ""
            self.slot_data.indice_na_pasta = -1
            self.carregar_slot(self.slot_data)
            self.metadata_changed.emit(self.slot_index)
            self.slot_selected.emit(self.slot_index)

    def _on_subpasta_combo_changed(self, idx: int):
        caminho = self.cmb_subpasta.itemData(idx)
        if caminho:
            self.subfolder_changed.emit(self.slot_index, caminho)


class PageEditorWidget(QWidget):
    """
    Editor de Páginas com abas para cada Página do relatório e grid DNIT de 6 slots.
    """
    slot_selected = pyqtSignal(int)  # slot_index selecionado na página atual
    page_changed = pyqtSignal(int)  # page_index
    photo_navigated = pyqtSignal(int, int)  # (slot_index, delta)
    subfolder_selected = pyqtSignal(int, str)  # (slot_index, subfolder)
    project_modified = pyqtSignal()

    def __init__(self, project: ReportProject, parent=None):
        super().__init__(parent)
        self.project = project
        self.pagina_atual_index = 0
        self.slot_selecionado_index = 0
        self.slot_cards: List[SlotCardWidget] = []

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)

        # Barra de Ações Rápidas da Página Ativa
        sub_page_bar = QHBoxLayout()
        self.lbl_status_pagina = QLabel("Página 1 de 1")
        self.lbl_status_pagina.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_status_pagina.setStyleSheet("color: #4da3ff;")
        sub_page_bar.addWidget(self.lbl_status_pagina)

        sub_page_bar.addSpacing(15)

        btn_preencher_subpasta = QPushButton("⚡ Preencher Página com Subpasta...")
        btn_preencher_subpasta.setToolTip("Preenche os slots vazios desta página com as fotos da subpasta escolhida")
        btn_preencher_subpasta.clicked.connect(self._preencher_pagina_com_subpasta)
        sub_page_bar.addWidget(btn_preencher_subpasta)

        sub_page_bar.addStretch()
        main_layout.addLayout(sub_page_bar)

        # Scroll Area para o Grid de 6 slots
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setContentsMargins(4, 4, 4, 4)
        grid_layout.setSpacing(8)

        # Cria os 6 Slot Cards (2 colunas x 3 linhas)
        self.slot_cards.clear()
        for i in range(6):
            card = SlotCardWidget(slot_index=i)
            card.slot_selected.connect(self._on_slot_selected)
            card.photo_navigated.connect(self._on_photo_navigated)
            card.subfolder_changed.connect(self._on_subfolder_changed)
            card.metadata_changed.connect(self._on_metadata_changed)
            self.slot_cards.append(card)

            row = i // 2
            col = i % 2
            grid_layout.addWidget(card, row, col)

        scroll.setWidget(grid_container)
        main_layout.addWidget(scroll, 1)

        self.atualizar_abas_e_pagina()

    def set_project(self, project: ReportProject):
        self.project = project
        self.atualizar_abas_e_pagina()

    def atualizar_abas_e_pagina(self):
        qtd_paginas = len(self.project.paginas)
        if self.pagina_atual_index >= qtd_paginas:
            self.pagina_atual_index = max(0, qtd_paginas - 1)
        self.carregar_pagina_atual()

    def carregar_pagina_atual(self):
        if not self.project.paginas:
            return

        idx = self.pagina_atual_index
        if idx >= len(self.project.paginas):
            idx = 0
            self.pagina_atual_index = idx

        pagina = self.project.paginas[idx]
        total_ativas = pagina.total_fotos_ativas()
        total_pags = len(self.project.paginas)
        self.lbl_status_pagina.setText(f"Página {idx + 1} de {total_pags} | {total_ativas}/6 fotos ativas")

        km_base = self.project.campos.get("km_base", "198.8")
        metros = self.project.campos.get("metros_estaca", "20.0")

        # Atualiza os 6 cards
        for i, card in enumerate(self.slot_cards):
            card.set_folder_manager(self.project.folder_manager)
            card.set_km_params(km_base, metros)
            slot = pagina.obter_slot(i)
            if slot:
                card.carregar_slot(slot)
            card.set_selected(i == self.slot_selecionado_index)

    def selecionar_slot(self, slot_idx: int):
        if 0 <= slot_idx < len(self.slot_cards):
            self.slot_selecionado_index = slot_idx
            for i, card in enumerate(self.slot_cards):
                card.set_selected(i == slot_idx)
            self.slot_selected.emit(slot_idx)

    def obter_slot_atual(self) -> Optional[PhotoSlot]:
        if 0 <= self.pagina_atual_index < len(self.project.paginas):
            pag = self.project.paginas[self.pagina_atual_index]
            return pag.obter_slot(self.slot_selecionado_index)
        return None

    def adicionar_pagina(self):
        nova_pag = self.project.adicionar_pagina()
        self.pagina_atual_index = len(self.project.paginas) - 1
        self.slot_selecionado_index = 0
        self.atualizar_abas_e_pagina()
        self.selecionar_slot(0)
        self.page_changed.emit(self.pagina_atual_index)
        self.project_modified.emit()

    def remover_pagina_atual(self):
        if len(self.project.paginas) <= 1:
            QMessageBox.information(self, "Aviso", "O relatório deve conter pelo menos uma página.")
            return

        resp = QMessageBox.question(
            self, "Confirmar Exclusão",
            f"Deseja excluir a Página {self.pagina_atual_index + 1} e suas fotos associadas?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.project.remover_pagina(self.pagina_atual_index)
            self.pagina_atual_index = max(0, self.pagina_atual_index - 1)
            self.slot_selecionado_index = 0
            self.atualizar_abas_e_pagina()
            self.selecionar_slot(0)
            self.page_changed.emit(self.pagina_atual_index)
            self.project_modified.emit()

    def duplicar_pagina_atual(self):
        self.project.duplicar_pagina(self.pagina_atual_index)
        self.pagina_atual_index += 1
        self.atualizar_abas_e_pagina()
        self.selecionar_slot(self.slot_selecionado_index)
        self.page_changed.emit(self.pagina_atual_index)
        self.project_modified.emit()

    def _on_slot_selected(self, slot_idx: int):
        self.selecionar_slot(slot_idx)

    def _on_photo_navigated(self, slot_idx: int, delta: int):
        self.selecionar_slot(slot_idx)
        self.photo_navigated.emit(slot_idx, delta)

    def _on_subfolder_changed(self, slot_idx: int, caminho_subpasta: str):
        self.selecionar_slot(slot_idx)
        self.subfolder_selected.emit(slot_idx, caminho_subpasta)

    def _on_metadata_changed(self, slot_idx: int):
        if 0 <= self.pagina_atual_index < len(self.project.paginas):
            pag = self.project.paginas[self.pagina_atual_index]
            total_ativas = pag.total_fotos_ativas()
            self.lbl_status_pagina.setText(
                f"Página {self.pagina_atual_index + 1} de {len(self.project.paginas)} | {total_ativas}/6 fotos ativas"
            )
        self.project_modified.emit()

    def _preencher_pagina_com_subpasta(self):
        subpastas = self.project.folder_manager.obter_subpastas()
        if not subpastas:
            QMessageBox.information(
                self, "Nenhuma Subpasta",
                "Inclua primeiro uma pasta de fotos usando o botão '📂 Incluir Pastas / Subpastas'."
            )
            return

        itens = [f"{nome} ({tot} fotos)" for _, nome, tot in subpastas]
        escolha, ok = QtWidgets.QInputDialog.getItem(
            self, "Preencher Página", "Selecione a subpasta:", itens, 0, False
        )
        if not ok or not escolha:
            return

        idx_escolhido = itens.index(escolha)
        caminho_dir = subpastas[idx_escolhido][0]
        fotos = self.project.folder_manager.obter_fotos(caminho_dir)

        if not fotos:
            QMessageBox.information(self, "Vazia", "A subpasta selecionada não contém imagens.")
            return

        pag = self.project.paginas[self.pagina_atual_index]
        for i in range(min(6, len(fotos))):
            slot = pag.slots[i]
            slot.arquivo = fotos[i]
            slot.subpasta = caminho_dir
            slot.indice_na_pasta = i
            slot.ativo = True

        self.carregar_pagina_atual()
        self.selecionar_slot(0)
        self.project_modified.emit()
