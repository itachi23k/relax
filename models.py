#!/usr/bin/env python3
"""
Módulo de Modelos de Dados e Gerenciamento de Pastas/Páginas.
Desenvolvido com foco em escalabilidade para o Gerador de Relatórios Fotográficos DNIT.
"""
import os
import copy
from typing import List, Dict, Optional, Tuple

EXTENSOES_FOTO = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

VALORES_PADRAO_CAMPOS = {
    "orgao": "DEPARTAMENTO NACIONAL DE INFRAESTRUTURA DE TRANSPORTES",
    "regional": "SUPERINTENDÊNCIA REGIONAL NO ESTADO DO AMAZONAS - SR/AM",
    "titulo": "REGISTRO FOTOGRÁFICO DOS SERVIÇOS EXECUTADOS",
    "empresa": "LCM CONSTRUÇÃO E COMERCIO S/A",
    "contrato": "SR-00 00563/2024",
    "medicao": "24ª",
    "servicos_ate": "31/08/2026",
    "periodo_inicio": "01/08/2026",
    "periodo_fim": "31/08/2026",
    "rodovia": "BR-319/AM",
    "supervisora": "PROSUL - Projetos, Supervisão e Planejamento Ltda",
    "fiscal": "Engº Isaias Reis Pinheiro",
    "km_base": "198.8",
    "metros_estaca": "20.0",
    "logo_path": "assets/logo_dnit.png"
}


def calcular_km_estaca(estaca_val: str, km_base: str = "198.8", metros_estaca: str = "20.0") -> str:
    """Calcula o KM formatado a partir da estaca e parâmetros."""
    try:
        txt = str(estaca_val).strip()
        if not txt:
            return ""
        estaca = float(txt.replace(",", "."))
        km = (estaca * float(str(metros_estaca).replace(",", ".")) / 1000.0) + float(str(km_base).replace(",", "."))
        return f"{km:.2f}".replace(".", ",")
    except Exception:
        return ""


class FolderManager:
    """Gerencia pastas e subpastas indexadas, mantendo cache ordenado de fotos."""
    def __init__(self):
        # Mapeamento: dir_path -> lista de caminhos absolutos de fotos
        self.pastas: Dict[str, List[str]] = {}
        # Mapeamento: dir_path -> nome amigável para exibição
        self.nomes_exibicao: Dict[str, str] = {}

    def adicionar_pasta_raiz(self, pasta_raiz: str) -> List[str]:
        """
        Escaneia recursivamente uma pasta raiz e registra ela e todas as subpastas
        que contenham fotos. Retorna a lista de diretórios registrados.
        """
        pasta_raiz = os.path.abspath(pasta_raiz)
        pastas_adicionadas = []

        # Primeiro verifica a própria pasta raiz
        fotos_raiz = self._escanear_diretorio_direto(pasta_raiz)
        if fotos_raiz:
            self.pastas[pasta_raiz] = sorted(fotos_raiz)
            self.nomes_exibicao[pasta_raiz] = f"📁 {os.path.basename(pasta_raiz)} (Raiz)"
            pastas_adicionadas.append(pasta_raiz)

        # Em seguida verifica todas as subpastas
        for raiz, dirs, _ in os.walk(pasta_raiz):
            dirs.sort()
            for d in dirs:
                caminho_sub = os.path.join(raiz, d)
                fotos_sub = self._escanear_diretorio_direto(caminho_sub)
                if fotos_sub:
                    self.pastas[caminho_sub] = sorted(fotos_sub)
                    rel = os.path.relpath(caminho_sub, os.path.dirname(pasta_raiz))
                    self.nomes_exibicao[caminho_sub] = f"📁 {rel}"
                    pastas_adicionadas.append(caminho_sub)

        return pastas_adicionadas

    def adicionar_pasta_direta(self, pasta: str, nome_exibicao: Optional[str] = None) -> bool:
        """Registra diretamente um único diretório com suas fotos."""
        pasta = os.path.abspath(pasta)
        fotos = self._escanear_diretorio_direto(pasta)
        if fotos:
            self.pastas[pasta] = sorted(fotos)
            self.nomes_exibicao[pasta] = nome_exibicao or f"📁 {os.path.basename(pasta)}"
            return True
        return False

    def _escanear_diretorio_direto(self, diretorio: str) -> List[str]:
        fotos = []
        try:
            if os.path.isdir(diretorio):
                for item in os.listdir(diretorio):
                    caminho = os.path.join(diretorio, item)
                    if os.path.isfile(caminho) and item.lower().endswith(EXTENSOES_FOTO):
                        fotos.append(caminho)
        except Exception:
            pass
        return fotos

    def obter_subpastas(self) -> List[Tuple[str, str, int]]:
        """Retorna lista de tuplas (caminho_dir, nome_exibicao, total_fotos)."""
        resultado = []
        for d, fotos in self.pastas.items():
            nome = self.nomes_exibicao.get(d, os.path.basename(d))
            resultado.append((d, nome, len(fotos)))
        return resultado

    def obter_fotos(self, dir_path: str) -> List[str]:
        """Retorna a lista de arquivos de fotos daquela subpasta."""
        dir_path = os.path.abspath(dir_path)
        return self.pastas.get(dir_path, [])

    def encontrar_pasta_e_indice(self, arquivo_path: str) -> Tuple[Optional[str], int]:
        """
        Dado um arquivo de foto, localiza qual subpasta o contém e seu índice.
        Se a pasta do arquivo ainda não estiver registrada, registra-a automaticamente.
        """
        if not arquivo_path:
            return None, -1
        arquivo_abs = os.path.abspath(arquivo_path)
        dir_pai = os.path.dirname(arquivo_abs)

        if dir_pai not in self.pastas:
            self.adicionar_pasta_direta(dir_pai)

        fotos = self.pastas.get(dir_pai, [])
        try:
            idx = fotos.index(arquivo_abs)
            return dir_pai, idx
        except ValueError:
            # Tenta comparar por nome de arquivo se o caminho diferir
            nome = os.path.basename(arquivo_abs)
            for i, f in enumerate(fotos):
                if os.path.basename(f) == nome:
                    return dir_pai, i
            return dir_pai, -1

    def navegar_foto(self, dir_path: str, indice_atual: int, delta: int) -> Tuple[int, Optional[str]]:
        """
        Avança (+1) ou retrocede (-1) na lista de fotos da subpasta.
        Retorna (novo_indice, caminho_arquivo). Suporta ciclagem circular.
        """
        fotos = self.obter_fotos(dir_path)
        if not fotos:
            return -1, None
        total = len(fotos)
        if indice_atual < 0:
            novo_indice = 0
        else:
            novo_indice = (indice_atual + delta) % total
        return novo_indice, fotos[novo_indice]


class PhotoSlot:
    """Representa um slot de foto dentro de uma página."""
    def __init__(
        self,
        arquivo: str = "",
        estaca: str = "",
        situacao: str = "DURANTE",
        servico: str = "",
        ativo: bool = True,
        subpasta: str = "",
        indice_na_pasta: int = -1,
        rotacao: int = 0,
        edicao_meta: Optional[Dict] = None
    ):
        self.arquivo = arquivo
        self.estaca = str(estaca)
        self.situacao = situacao.upper() if situacao else "DURANTE"
        self.servico = servico
        self.ativo = ativo
        self.subpasta = subpasta
        self.indice_na_pasta = indice_na_pasta
        self.rotacao = rotacao  # 0, 90, 180, 270 (preparado para edição/rotação)
        self.edicao_meta = edicao_meta or {}  # Escalabilidade: crop, filtros, anotações

    @property
    def nome(self) -> str:
        return os.path.basename(self.arquivo) if self.arquivo else ""

    def esta_preenchido(self) -> bool:
        return bool(self.arquivo and os.path.isfile(self.arquivo))

    def to_dict(self) -> Dict:
        return {
            "arquivo": self.arquivo,
            "estaca": self.estaca,
            "situacao": self.situacao,
            "servico": self.servico,
            "ativo": self.ativo,
            "subpasta": self.subpasta,
            "indice_na_pasta": self.indice_na_pasta,
            "rotacao": self.rotacao,
            "edicao_meta": copy.deepcopy(self.edicao_meta)
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PhotoSlot":
        return cls(
            arquivo=data.get("arquivo", ""),
            estaca=str(data.get("estaca", "")),
            situacao=data.get("situacao", "DURANTE"),
            servico=data.get("servico", ""),
            ativo=data.get("ativo", True),
            subpasta=data.get("subpasta", ""),
            indice_na_pasta=data.get("indice_na_pasta", -1),
            rotacao=data.get("rotacao", 0),
            edicao_meta=data.get("edicao_meta", {})
        )


class ReportPage:
    """Representa uma folha/página do relatório (contém até 6 slots DNIT)."""
    MAX_SLOTS = 6

    def __init__(self, numero: int = 1, titulo: str = "", slots: Optional[List[PhotoSlot]] = None):
        self.numero = numero
        self.titulo = titulo or f"Página {numero}"
        if slots is not None:
            self.slots = slots[:self.MAX_SLOTS]
            while len(self.slots) < self.MAX_SLOTS:
                self.slots.append(PhotoSlot())
        else:
            self.slots = [PhotoSlot() for _ in range(self.MAX_SLOTS)]

    def obter_slot(self, index: int) -> Optional[PhotoSlot]:
        if 0 <= index < len(self.slots):
            return self.slots[index]
        return None

    def total_fotos_ativas(self) -> int:
        return sum(1 for s in self.slots if s.ativo and s.esta_preenchido())

    def to_dict(self) -> Dict:
        return {
            "numero": self.numero,
            "titulo": self.titulo,
            "slots": [s.to_dict() for s in self.slots]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ReportPage":
        slots_data = data.get("slots", [])
        slots = [PhotoSlot.from_dict(s) for s in slots_data]
        return cls(
            numero=data.get("numero", 1),
            titulo=data.get("titulo", ""),
            slots=slots
        )


class ReportProject:
    """Projeto global do relatório: metadados, pastas incluídas e lista de páginas."""
    def __init__(self):
        self.campos: Dict[str, str] = dict(VALORES_PADRAO_CAMPOS)
        self.paginas: List[ReportPage] = []
        self.pastas_incluidas: List[str] = []
        self.folder_manager = FolderManager()

        # Inicia com pelo menos 1 página
        self.adicionar_pagina()

    def adicionar_pagina(self, titulo: Optional[str] = None) -> ReportPage:
        num = len(self.paginas) + 1
        tit = titulo or f"Página {num}"
        nova_pag = ReportPage(numero=num, titulo=tit)
        self.paginas.append(nova_pag)
        self._renumerar_paginas()
        return nova_pag

    def remover_pagina(self, index: int) -> bool:
        if len(self.paginas) <= 1:
            return False  # Mantém ao menos uma página
        if 0 <= index < len(self.paginas):
            del self.paginas[index]
            self._renumerar_paginas()
            return True
        return False

    def duplicar_pagina(self, index: int) -> Optional[ReportPage]:
        if 0 <= index < len(self.paginas):
            orig = self.paginas[index]
            novos_slots = [PhotoSlot.from_dict(s.to_dict()) for s in orig.slots]
            num = len(self.paginas) + 1
            nova = ReportPage(numero=num, titulo=f"Página {num}", slots=novos_slots)
            self.paginas.insert(index + 1, nova)
            self._renumerar_paginas()
            return nova
        return None

    def mover_pagina(self, index_origem: int, index_destino: int) -> bool:
        if 0 <= index_origem < len(self.paginas) and 0 <= index_destino < len(self.paginas):
            pag = self.paginas.pop(index_origem)
            self.paginas.insert(index_destino, pag)
            self._renumerar_paginas()
            return True
        return False

    def _renumerar_paginas(self):
        import re
        for i, p in enumerate(self.paginas, 1):
            p.numero = i
            if not p.titulo or re.match(r"^Página \d+$", p.titulo):
                p.titulo = f"Página {i}"

    def incluir_pasta(self, pasta_caminho: str) -> List[str]:
        pasta_caminho = os.path.abspath(pasta_caminho)
        if pasta_caminho not in self.pastas_incluidas:
            self.pastas_incluidas.append(pasta_caminho)
        return self.folder_manager.adicionar_pasta_raiz(pasta_caminho)

    def obter_todas_fotos_ativas(self) -> List[Dict]:
        """
        Retorna lista plana de todas as fotos ativas e válidas com KM calculado.
        Compatível com as rotinas de geração do PDF e XML.
        """
        km_base = self.campos.get("km_base", "198.8")
        metros = self.campos.get("metros_estaca", "20.0")
        fotos = []

        for pag in self.paginas:
            for s in pag.slots:
                if s.ativo and s.esta_preenchido():
                    km_val = calcular_km_estaca(s.estaca, km_base, metros)
                    fotos.append({
                        "arquivo": s.arquivo,
                        "nome": s.nome,
                        "estaca": s.estaca,
                        "km": km_val,
                        "situacao": s.situacao,
                        "servico": s.servico,
                        "rotacao": s.rotacao,
                        "pagina": pag.numero
                    })
        return fotos

    def to_dict(self) -> Dict:
        return {
            "versao": "2.0",
            "campos": self.campos,
            "pastas_incluidas": self.pastas_incluidas,
            "paginas": [p.to_dict() for p in self.paginas]
        }

    def carregar_de_dict(self, data: Dict):
        """Carrega projeto com suporte a versão 1.0 (fotos planas) e 2.0 (páginas)."""
        if "campos" in data:
            self.campos.update(data["campos"])

        if "pastas_incluidas" in data:
            self.pastas_incluidas = data["pastas_incluidas"]
            for p in self.pastas_incluidas:
                if os.path.isdir(p):
                    self.folder_manager.adicionar_pasta_raiz(p)

        if "paginas" in data and data["paginas"]:
            self.paginas = [ReportPage.from_dict(p) for p in data["paginas"]]
            self._renumerar_paginas()
        elif "fotos" in data:
            # Compatibilidade com v1.0: agrupa fotos em blocos de 6 por página
            self.paginas.clear()
            fotos = data["fotos"]
            chunk_size = 6
            for chunk_idx, i in enumerate(range(0, len(fotos), chunk_size), 1):
                chunk = fotos[i:i + chunk_size]
                slots = []
                for f in chunk:
                    slot = PhotoSlot(
                        arquivo=f.get("arquivo", ""),
                        estaca=f.get("estaca", ""),
                        situacao=f.get("situacao", "DURANTE"),
                        servico=f.get("servico", ""),
                        ativo=f.get("ativo", True)
                    )
                    slots.append(slot)
                pag = ReportPage(numero=chunk_idx, titulo=f"Página {chunk_idx}", slots=slots)
                self.paginas.append(pag)

            if not self.paginas:
                self.adicionar_pagina()

        # Atualiza o FolderManager com as fotos existentes
        for pag in self.paginas:
            for s in pag.slots:
                if s.arquivo and os.path.isfile(s.arquivo):
                    dir_path, idx = self.folder_manager.encontrar_pasta_e_indice(s.arquivo)
                    if not s.subpasta and dir_path:
                        s.subpasta = dir_path
                    if s.indice_na_pasta < 0:
                        s.indice_na_pasta = idx
