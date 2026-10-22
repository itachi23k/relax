#!/usr/bin/env python3
"""
Módulo de Banco de Dados Local (SQLite) para Projetos de Relatórios Fotográficos.
Permite salvar e recuperar o progresso diário de múltiplos projetos distintos
sem a necessidade de gerar arquivos PDF a cada salvamento.
"""
import os
import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager
from typing import List, Dict, Optional, Tuple, Any

from models import ReportProject, ReportPage, PhotoSlot, calcular_km_estaca


class DatabaseManager:
    """Gerenciador do banco de dados SQLite local para múltiplos projetos."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            diretorio_base = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(diretorio_base, "relatorios_projetos.db")
        else:
            self.db_path = os.path.abspath(db_path)

        self.init_db()

    @contextmanager
    def get_connection(self):
        """Retorna conexão configurada e fecha automaticamente ao sair do bloco with."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """Inicializa as tabelas do banco de dados caso não existam."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Tabela de Projetos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projetos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL,
                    descricao TEXT DEFAULT '',
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    campos_json TEXT DEFAULT '{}',
                    pastas_incluidas_json TEXT DEFAULT '[]',
                    dados_completos_json TEXT DEFAULT '{}'
                );
            """)

            # Tabela de Páginas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paginas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    projeto_id INTEGER NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
                    numero INTEGER NOT NULL,
                    titulo TEXT NOT NULL,
                    criado_em TEXT NOT NULL
                );
            """)

            # Tabela de Slots de Fotos (6 por página)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS slots_fotos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pagina_id INTEGER NOT NULL REFERENCES paginas(id) ON DELETE CASCADE,
                    slot_index INTEGER NOT NULL,
                    arquivo TEXT DEFAULT '',
                    estaca TEXT DEFAULT '',
                    km_calculado TEXT DEFAULT '',
                    situacao TEXT DEFAULT 'DURANTE',
                    servico TEXT DEFAULT '',
                    ativo INTEGER DEFAULT 1,
                    subpasta TEXT DEFAULT '',
                    indice_na_pasta INTEGER DEFAULT -1,
                    rotacao INTEGER DEFAULT 0,
                    edicao_meta_json TEXT DEFAULT '{}',
                    atualizado_em TEXT NOT NULL
                );
            """)

            # Índices para alta performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_paginas_projeto ON paginas(projeto_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_slots_pagina ON slots_fotos(pagina_id);")
            conn.commit()

    def listar_projetos(self) -> List[Dict[str, Any]]:
        """
        Retorna a lista de todos os projetos cadastrados com estatísticas resumidas.
        Ordenado pelo mais recentemente atualizado.
        """
        sql = """
            SELECT
                p.id,
                p.nome,
                p.descricao,
                p.criado_em,
                p.atualizado_em,
                COUNT(DISTINCT pg.id) as total_paginas,
                SUM(CASE WHEN sf.ativo = 1 AND sf.arquivo != '' THEN 1 ELSE 0 END) as total_fotos_ativas
            FROM projetos p
            LEFT JOIN paginas pg ON pg.projeto_id = p.id
            LEFT JOIN slots_fotos sf ON sf.pagina_id = pg.id
            GROUP BY p.id
            ORDER BY p.atualizado_em DESC;
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            resultado = []
            for r in rows:
                resultado.append({
                    "id": r["id"],
                    "nome": r["nome"],
                    "descricao": r["descricao"] or "",
                    "criado_em": r["criado_em"],
                    "atualizado_em": r["atualizado_em"],
                    "total_paginas": r["total_paginas"] or 0,
                    "total_fotos_ativas": r["total_fotos_ativas"] or 0
                })
            return resultado

    def criar_projeto(
        self,
        nome: str,
        descricao: str = "",
        projeto_base: Optional[ReportProject] = None
    ) -> int:
        """
        Cria um novo projeto no banco de dados.
        Se projeto_base for fornecido, copia seus dados para o novo projeto.
        """
        nome_limpo = nome.strip()
        if not nome_limpo:
            raise ValueError("O nome do projeto não pode ser vazio.")

        agora = datetime.now().isoformat()
        proj = projeto_base if projeto_base is not None else ReportProject()

        campos_json = json.dumps(proj.campos, ensure_ascii=False)
        pastas_json = json.dumps(proj.pastas_incluidas, ensure_ascii=False)
        completo_json = json.dumps(proj.to_dict(), ensure_ascii=False)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO projetos (nome, descricao, criado_em, atualizado_em, campos_json, pastas_incluidas_json, dados_completos_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (nome_limpo, descricao, agora, agora, campos_json, pastas_json, completo_json))
            projeto_id = cursor.lastrowid

            # Grava páginas e slots relacionais
            self._salvar_paginas_relacionais(cursor, projeto_id, proj, agora)
            conn.commit()

        return projeto_id

    def salvar_projeto(
        self,
        projeto_id: int,
        proj: ReportProject,
        novo_nome: Optional[str] = None,
        nova_descricao: Optional[str] = None
    ) -> bool:
        """
        Salva o progresso completo de um projeto existente no banco de dados.
        Atualiza campos, pastas, páginas e slots de fotos.
        """
        agora = datetime.now().isoformat()
        campos_json = json.dumps(proj.campos, ensure_ascii=False)
        pastas_json = json.dumps(proj.pastas_incluidas, ensure_ascii=False)
        completo_json = json.dumps(proj.to_dict(), ensure_ascii=False)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Atualiza dados do projeto
            if novo_nome is not None and nova_descricao is not None:
                cursor.execute("""
                    UPDATE projetos
                    SET nome = ?, descricao = ?, atualizado_em = ?, campos_json = ?, pastas_incluidas_json = ?, dados_completos_json = ?
                    WHERE id = ?
                """, (novo_nome.strip(), nova_descricao.strip(), agora, campos_json, pastas_json, completo_json, projeto_id))
            elif novo_nome is not None:
                cursor.execute("""
                    UPDATE projetos
                    SET nome = ?, atualizado_em = ?, campos_json = ?, pastas_incluidas_json = ?, dados_completos_json = ?
                    WHERE id = ?
                """, (novo_nome.strip(), agora, campos_json, pastas_json, completo_json, projeto_id))
            else:
                cursor.execute("""
                    UPDATE projetos
                    SET atualizado_em = ?, campos_json = ?, pastas_incluidas_json = ?, dados_completos_json = ?
                    WHERE id = ?
                """, (agora, campos_json, pastas_json, completo_json, projeto_id))

            # Atualiza as páginas e slots relacionais (remove antigas e insere novas)
            cursor.execute("DELETE FROM paginas WHERE projeto_id = ?", (projeto_id,))
            self._salvar_paginas_relacionais(cursor, projeto_id, proj, agora)

            conn.commit()
            return True

    def _salvar_paginas_relacionais(
        self,
        cursor: sqlite3.Cursor,
        projeto_id: int,
        proj: ReportProject,
        timestamp: str
    ):
        """Salva a hierarquia relacional de páginas e slots."""
        km_base = proj.campos.get("km_base", "198.8")
        metros = proj.campos.get("metros_estaca", "20.0")

        for pag in proj.paginas:
            cursor.execute("""
                INSERT INTO paginas (projeto_id, numero, titulo, criado_em)
                VALUES (?, ?, ?, ?)
            """, (projeto_id, pag.numero, pag.titulo, timestamp))
            pagina_id = cursor.lastrowid

            for idx, slot in enumerate(pag.slots):
                km_calc = calcular_km_estaca(slot.estaca, km_base, metros)
                edicao_json = json.dumps(slot.edicao_meta, ensure_ascii=False)
                cursor.execute("""
                    INSERT INTO slots_fotos (
                        pagina_id, slot_index, arquivo, estaca, km_calculado,
                        situacao, servico, ativo, subpasta, indice_na_pasta,
                        rotacao, edicao_meta_json, atualizado_em
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pagina_id, idx, slot.arquivo, slot.estaca, km_calc,
                    slot.situacao, slot.servico, 1 if slot.ativo else 0,
                    slot.subpasta, slot.indice_na_pasta, slot.rotacao,
                    edicao_json, timestamp
                ))

    def carregar_projeto(self, projeto_id: int) -> Tuple[Optional[ReportProject], Dict[str, Any]]:
        """
        Carrega o projeto do banco de dados pelo seu ID.
        Retorna uma instância de ReportProject e o dicionário de metadados do projeto.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, nome, descricao, criado_em, atualizado_em, campos_json, pastas_incluidas_json, dados_completos_json
                FROM projetos
                WHERE id = ?
            """, (projeto_id,))
            row = cursor.fetchone()

            if not row:
                return None, {}

            info = {
                "id": row["id"],
                "nome": row["nome"],
                "descricao": row["descricao"] or "",
                "criado_em": row["criado_em"],
                "atualizado_em": row["atualizado_em"]
            }

            proj = ReportProject()

            # Tenta restaurar do payload JSON completo
            dados_json = row["dados_completos_json"]
            if dados_json:
                try:
                    payload = json.loads(dados_json)
                    proj.carregar_de_dict(payload)
                    return proj, info
                except Exception:
                    pass

            # Caso o JSON falhe, restaura via tabelas relacionais
            if row["campos_json"]:
                try:
                    proj.campos.update(json.loads(row["campos_json"]))
                except Exception:
                    pass

            if row["pastas_incluidas_json"]:
                try:
                    pastas = json.loads(row["pastas_incluidas_json"])
                    for p in pastas:
                        proj.incluir_pasta(p)
                except Exception:
                    pass

            cursor.execute("""
                SELECT id, numero, titulo
                FROM paginas
                WHERE projeto_id = ?
                ORDER BY numero ASC
            """, (projeto_id,))
            pag_rows = cursor.fetchall()

            if pag_rows:
                proj.paginas.clear()
                for pr in pag_rows:
                    cursor.execute("""
                        SELECT slot_index, arquivo, estaca, situacao, servico, ativo, subpasta, indice_na_pasta, rotacao, edicao_meta_json
                        FROM slots_fotos
                        WHERE pagina_id = ?
                        ORDER BY slot_index ASC
                    """, (pr["id"],))
                    slots_rows = cursor.fetchall()
                    slots = []
                    for sr in slots_rows:
                        meta = {}
                        if sr["edicao_meta_json"]:
                            try:
                                meta = json.loads(sr["edicao_meta_json"])
                            except Exception:
                                pass
                        slot = PhotoSlot(
                            arquivo=sr["arquivo"] or "",
                            estaca=sr["estaca"] or "",
                            situacao=sr["situacao"] or "DURANTE",
                            servico=sr["servico"] or "",
                            ativo=bool(sr["ativo"]),
                            subpasta=sr["subpasta"] or "",
                            indice_na_pasta=sr["indice_na_pasta"] if sr["indice_na_pasta"] is not None else -1,
                            rotacao=sr["rotacao"] or 0,
                            edicao_meta=meta
                        )
                        slots.append(slot)

                    pag = ReportPage(numero=pr["numero"], titulo=pr["titulo"], slots=slots)
                    proj.paginas.append(pag)

            return proj, info

    def carregar_projeto_por_nome(self, nome: str) -> Tuple[Optional[ReportProject], Dict[str, Any]]:
        """Carrega projeto buscando pelo nome."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM projetos WHERE nome = ?", (nome.strip(),))
            row = cursor.fetchone()
            if row:
                return self.carregar_projeto(row["id"])
            return None, {}

    def duplicar_projeto(self, projeto_id: int, novo_nome: str) -> int:
        """Duplica um projeto existente criando uma nova cópia independente."""
        proj, info = self.carregar_projeto(projeto_id)
        if not proj:
            raise ValueError(f"Projeto com ID {projeto_id} não encontrado.")

        desc = f"Cópia de '{info.get('nome', '')}'. {info.get('descricao', '')}".strip()
        return self.criar_projeto(novo_nome, desc, proj)

    def renomear_projeto(self, projeto_id: int, novo_nome: str) -> bool:
        """Renomeia um projeto existente."""
        nome_limpo = novo_nome.strip()
        if not nome_limpo:
            raise ValueError("O novo nome não pode ser vazio.")

        agora = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE projetos
                SET nome = ?, atualizado_em = ?
                WHERE id = ?
            """, (nome_limpo, agora, projeto_id))
            conn.commit()
            return cursor.rowcount > 0

    def excluir_projeto(self, projeto_id: int) -> bool:
        """Exclui um projeto e todas as suas páginas/slots associados."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projetos WHERE id = ?", (projeto_id,))
            conn.commit()
            return cursor.rowcount > 0

    def obter_ultimo_projeto_id(self) -> Optional[int]:
        """Retorna o ID do projeto mais recentemente atualizado."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM projetos ORDER BY atualizado_em DESC LIMIT 1")
            row = cursor.fetchone()
            return row["id"] if row else None

    def total_projetos(self) -> int:
        """Retorna a contagem total de projetos no banco."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM projetos")
            row = cursor.fetchone()
            return row["total"] if row else 0
