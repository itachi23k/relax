#!/usr/bin/env python3
"""
Widget de Prévia de Alta Resolução e Navegação Rápida (Up/Down) por Subpastas.
Projetado para grande área de visualização e escalabilidade para futuras ferramentas de edição embutidas.
"""
import os
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QScrollArea, QDialog, QSizePolicy, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor, QTransform

from typing import Optional, List, Dict, Tuple
from models import PhotoSlot, FolderManager


class ScalableImageLabel(QLabel):
    """Label que redimensiona a imagem dinamicamente mantendo proporção e qualidade."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.original_pixmap: Optional[QPixmap] = None
        self.current_rotation: int = 0
        self.setStyleSheet("""
            QLabel {
                background-color: #18191b;
                border: 1px solid #33363b;
                border-radius: 6px;
            }
        """)

    def set_image(self, pixmap: Optional[QPixmap], rotation: int = 0):
        self.original_pixmap = pixmap
        self.current_rotation = rotation
        self.update_display()

    def update_display(self):
        if not self.original_pixmap or self.original_pixmap.isNull():
            self.clear()
            self.setText(
                "<div style='text-align: center; color: #777;'>"
                "<b>Nenhuma foto selecionada</b><br><br>"
                "<small>Selecione um slot ou use as teclas <b>↑ (Cima)</b> e <b>↓ (Baixo)</b><br>"
                "para navegar pelas fotos da subpasta.</small>"
                "</div>"
            )
            return

        # Aplica rotação se houver
        pix = self.original_pixmap
        if self.current_rotation != 0:
            transform = QTransform().rotate(self.current_rotation)
            pix = pix.transformed(transform, Qt.TransformationMode.SmoothTransformation)

        # Escala respeitando o tamanho atual do widget
        w = max(100, self.width() - 12)
        h = max(100, self.height() - 12)
        scaled = pix.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        super().setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.original_pixmap and not self.original_pixmap.isNull():
            self.update_display()


class FullscreenPreviewDialog(QDialog):
    """Diálogo modal para visualizar a imagem em tela cheia / alta resolução."""
    def __init__(self, pixmap: QPixmap, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Visualizador em Tela Cheia - {title}")
        self.resize(1024, 768)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        img_label = ScalableImageLabel()
        img_label.set_image(pixmap)
        layout.addWidget(img_label)

        btn_fechar = QPushButton("Fechar Visualizador (ESC)")
        btn_fechar.clicked.connect(self.accept)
        layout.addWidget(btn_fechar, alignment=Qt.AlignmentFlag.AlignCenter)


class LargeImagePreviewWidget(QWidget):
    """
    Painel de Prévia Ampliada com:
    - Barra de ferramentas com Up/Down para troca rápida de fotos da subpasta
    - Suporte a rotação de 90°
    - Pronta para extensões futuras de edição de imagens embutidas
    """
    photo_navigated = pyqtSignal(int)  # delta (-1 para up, +1 para down)
    folder_selected = pyqtSignal(str)  # nova subpasta selecionada
    rotation_changed = pyqtSignal(int)  # nova rotação

    def __init__(self, parent=None):
        super().__init__(parent)
        self.slot_atual: Optional[PhotoSlot] = None
        self.folder_manager: Optional[FolderManager] = None
        self.current_pixmap: Optional[QPixmap] = None

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)

        # 1. Barra de Navegação Superior (Subpasta e Botões UP / DOWN)
        nav_box = QFrame()
        nav_box.setStyleSheet("""
            QFrame {
                background-color: #27292d;
                border: 1px solid #3d4148;
                border-radius: 5px;
                padding: 4px;
            }
        """)
        nav_layout = QVBoxLayout(nav_box)
        nav_layout.setContentsMargins(6, 6, 6, 6)
        nav_layout.setSpacing(4)

        # Linha 1: Seletor de Subpasta
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("<b>Subpasta:</b>"))
        self.cmb_subpastas = QComboBox()
        self.cmb_subpastas.setToolTip("Selecione a subpasta de onde esta foto será escolhida")
        self.cmb_subpastas.currentIndexChanged.connect(self._on_subpasta_changed)
        row1.addWidget(self.cmb_subpastas, 1)
        nav_layout.addLayout(row1)

        # Linha 2: Botões UP / DOWN e Contador
        row2 = QHBoxLayout()
        self.btn_up = QPushButton("▲ Foto Anterior (Up)")
        self.btn_up.setToolTip("Selecionar foto anterior na subpasta [Tecla ↑ ou W]")
        self.btn_up.clicked.connect(lambda: self.photo_navigated.emit(-1))
        row2.addWidget(self.btn_up)

        self.lbl_contador = QLabel("Foto - / -")
        self.lbl_contador.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_contador.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_contador.setStyleSheet("color: #4da3ff;")
        row2.addWidget(self.lbl_contador, 1)

        self.btn_down = QPushButton("▼ Próxima Foto (Down)")
        self.btn_down.setToolTip("Selecionar próxima foto na subpasta [Tecla ↓ ou S]")
        self.btn_down.clicked.connect(lambda: self.photo_navigated.emit(1))
        row2.addWidget(self.btn_down)

        nav_layout.addLayout(row2)
        main_layout.addWidget(nav_box)

        # 2. Barra de Ferramentas de Imagem (Girar, Zoom, Expandir + Espaço para Futura Edição)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)

        self.btn_girar = QPushButton("🔄 Girar 90°")
        self.btn_girar.setToolTip("Girar imagem 90 graus no sentido horário")
        self.btn_girar.clicked.connect(self._girar_imagem)
        toolbar.addWidget(self.btn_girar)

        self.btn_fullscreen = QPushButton("🗖 Expandir")
        self.btn_fullscreen.setToolTip("Visualizar em alta resolução / tela inteira")
        self.btn_fullscreen.clicked.connect(self._abrir_fullscreen)
        toolbar.addWidget(self.btn_fullscreen)

        toolbar.addSpacing(8)

        # Placeholder / Prateleira para futuras edições embutidas (Escalabilidade)
        lbl_edicao = QLabel("<i>Edição:</i>")
        lbl_edicao.setStyleSheet("color: #888;")
        toolbar.addWidget(lbl_edicao)

        self.btn_crop = QPushButton("✂️")
        self.btn_crop.setEnabled(False)
        self.btn_crop.setToolTip("Recortar Imagem (Em breve: Edição Embutida)")
        self.btn_crop.setMaximumWidth(32)
        toolbar.addWidget(self.btn_crop)

        self.btn_draw = QPushButton("✏️")
        self.btn_draw.setEnabled(False)
        self.btn_draw.setToolTip("Desenhar Setas / Destaques (Em breve: Edição Embutida)")
        self.btn_draw.setMaximumWidth(32)
        toolbar.addWidget(self.btn_draw)

        self.btn_ajustes = QPushButton("☀️")
        self.btn_ajustes.setEnabled(False)
        self.btn_ajustes.setToolTip("Ajustar Brilho / Contraste (Em breve: Edição Embutida)")
        self.btn_ajustes.setMaximumWidth(32)
        toolbar.addWidget(self.btn_ajustes)

        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # 3. Área Central da Imagem Grande
        self.image_canvas = ScalableImageLabel()
        main_layout.addWidget(self.image_canvas, 1)

        # 4. Rodapé Informativo (Metadados e Dica de Teclado)
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #212326;
                border-top: 1px solid #33363b;
                padding: 4px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(4, 4, 4, 4)
        info_layout.setSpacing(2)

        self.lbl_nome_arquivo = QLabel("Nenhum arquivo ativo")
        self.lbl_nome_arquivo.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_nome_arquivo.setWordWrap(True)
        info_layout.addWidget(self.lbl_nome_arquivo)

        self.lbl_dimensoes = QLabel("-")
        self.lbl_dimensoes.setStyleSheet("color: #aaa; font-size: 11px;")
        info_layout.addWidget(self.lbl_dimensoes)

        lbl_dica = QLabel("💡 <i>Dica: Navegue com as setas <b>↑</b> e <b>↓</b> do teclado para alternar fotos rapidamente.</i>")
        lbl_dica.setStyleSheet("color: #7289da; font-size: 10px;")
        info_layout.addWidget(lbl_dica)

        main_layout.addWidget(info_frame)

    def set_folder_manager(self, folder_manager: FolderManager):
        self.folder_manager = folder_manager
        self.atualizar_lista_subpastas()

    def atualizar_lista_subpastas(self):
        if not self.folder_manager:
            return
        subpastas = self.folder_manager.obter_subpastas()
        self.cmb_subpastas.blockSignals(True)
        self.cmb_subpastas.clear()
        self.cmb_subpastas.addItem("--- Selecionar Subpasta ---", "")

        for caminho, nome, total in subpastas:
            texto = f"{nome} ({total} fotos)"
            self.cmb_subpastas.addItem(texto, caminho)

        self.cmb_subpastas.blockSignals(False)

    def exibir_slot(self, slot: Optional[PhotoSlot]):
        self.slot_atual = slot

        if not slot or not slot.arquivo or not os.path.isfile(slot.arquivo):
            self.current_pixmap = None
            self.image_canvas.set_image(None)
            self.lbl_nome_arquivo.setText("Slot Vazio / Nenhuma foto selecionada")
            self.lbl_dimensoes.setText("Clique em uma subpasta ou navegue com ▲ / ▼")
            self.lbl_contador.setText("Foto 0 / 0")
            self._sincronizar_subpasta_combo(slot.subpasta if slot else "")
            return

        # Carrega a foto em alta qualidade
        try:
            pix = QPixmap(slot.arquivo)
            if not pix.isNull():
                self.current_pixmap = pix
                self.image_canvas.set_image(pix, slot.rotacao)
                tamanho_kb = os.path.getsize(slot.arquivo) / 1024
                self.lbl_nome_arquivo.setText(f"📄 {slot.nome}")
                self.lbl_dimensoes.setText(
                    f"{pix.width()} × {pix.height()} px | {tamanho_kb:.1f} KB | "
                    f"Rotação: {slot.rotacao}°"
                )
            else:
                self.current_pixmap = None
                self.image_canvas.set_image(None)
                self.lbl_nome_arquivo.setText(f"Erro ao carregar: {slot.nome}")
                self.lbl_dimensoes.setText("Formato inválido ou corrompido")
        except Exception as e:
            self.current_pixmap = None
            self.image_canvas.set_image(None)
            self.lbl_nome_arquivo.setText(f"Erro: {e}")

        # Sincroniza contador e subpasta
        self._sincronizar_subpasta_combo(slot.subpasta)
        self._atualizar_contador_slot(slot)

    def _sincronizar_subpasta_combo(self, subpasta_path: str):
        self.cmb_subpastas.blockSignals(True)
        idx = -1
        if subpasta_path:
            norm = os.path.abspath(subpasta_path)
            for i in range(self.cmb_subpastas.count()):
                if self.cmb_subpastas.itemData(i) == norm:
                    idx = i
                    break
        if idx >= 0:
            self.cmb_subpastas.setCurrentIndex(idx)
        else:
            self.cmb_subpastas.setCurrentIndex(0)
        self.cmb_subpastas.blockSignals(False)

    def _atualizar_contador_slot(self, slot: PhotoSlot):
        if not self.folder_manager or not slot.subpasta:
            self.lbl_contador.setText("Foto 1 / 1" if slot.esta_preenchido() else "Foto 0 / 0")
            return

        fotos = self.folder_manager.obter_fotos(slot.subpasta)
        total = len(fotos)
        if total > 0:
            idx = slot.indice_na_pasta
            if idx < 0 and slot.arquivo:
                _, idx = self.folder_manager.encontrar_pasta_e_indice(slot.arquivo)
                slot.indice_na_pasta = idx
            pos = (idx + 1) if idx >= 0 else 1
            self.lbl_contador.setText(f"Foto {pos} de {total}")
        else:
            self.lbl_contador.setText("0 fotos na pasta")

    def _on_subpasta_changed(self, index: int):
        caminho = self.cmb_subpastas.itemData(index)
        if caminho:
            self.folder_selected.emit(caminho)

    def _girar_imagem(self):
        if not self.slot_atual:
            return
        nova_rot = (self.slot_atual.rotacao + 90) % 360
        self.slot_atual.rotacao = nova_rot
        self.image_canvas.set_image(self.current_pixmap, nova_rot)
        if self.current_pixmap:
            tamanho_kb = os.path.getsize(self.slot_atual.arquivo) / 1024 if os.path.isfile(self.slot_atual.arquivo) else 0
            self.lbl_dimensoes.setText(
                f"{self.current_pixmap.width()} × {self.current_pixmap.height()} px | "
                f"{tamanho_kb:.1f} KB | Rotação: {nova_rot}°"
            )
        self.rotation_changed.emit(nova_rot)

    def _abrir_fullscreen(self):
        if self.current_pixmap and not self.current_pixmap.isNull():
            pix = self.current_pixmap
            if self.slot_atual and self.slot_atual.rotacao != 0:
                transform = QTransform().rotate(self.slot_atual.rotacao)
                pix = pix.transformed(transform, Qt.TransformationMode.SmoothTransformation)
            nome = self.slot_atual.nome if self.slot_atual else "Visualização"
            dlg = FullscreenPreviewDialog(pix, nome, self)
            dlg.exec()
