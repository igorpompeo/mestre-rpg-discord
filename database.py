"""
🗄️ Sistema de Banco de Dados - Mestre RPG
SQLite assíncrono para fichas, sessões e históricos
"""

import aiosqlite
import json
import os
from datetime import datetime

DB_PATH = "rpg_campanhas.db"

class Database:
    """Gerenciador do banco de dados"""

    async def init_db(self):
        """Inicializa todas as tabelas"""
        async with aiosqlite.connect(DB_PATH) as db:
            # Tabela de fichas de personagem
            await db.execute("""
                CREATE TABLE IF NOT EXISTS fichas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jogador_id TEXT NOT NULL,
                    servidor_id TEXT NOT NULL,
                    nome_personagem TEXT NOT NULL,
                    classe TEXT NOT NULL,
                    nivel INTEGER DEFAULT 1,
                    raca TEXT DEFAULT 'Humano',
                    forca INTEGER DEFAULT 10,
                    destreza INTEGER DEFAULT 10,
                    constituicao INTEGER DEFAULT 10,
                    inteligencia INTEGER DEFAULT 10,
                    sabedoria INTEGER DEFAULT 10,
                    carisma INTEGER DEFAULT 10,
                    pv_max INTEGER DEFAULT 10,
                    pv_atual INTEGER DEFAULT 10,
                    experiencia INTEGER DEFAULT 0,
                    moedas TEXT DEFAULT '{"po": 0, "pp": 0, "pe": 0, "pc": 0}',
                    inventario TEXT DEFAULT '[]',
                    anotacoes TEXT DEFAULT '',
                    criado_em TEXT,
                    atualizado_em TEXT
                )
            """)

            # Tabela de sessões/campanhas
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sessao_id TEXT UNIQUE NOT NULL,
                    servidor_id TEXT NOT NULL,
                    canal_id TEXT NOT NULL,
                    mestre_id TEXT NOT NULL,
                    sistema TEXT NOT NULL,
                    nome_campanha TEXT DEFAULT 'Aventura Sem Nome',
                    status TEXT DEFAULT 'ativa',
                    jogadores TEXT DEFAULT '[]',
                    historico TEXT DEFAULT '[]',
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            # Tabela de iniciativa/combate
            await db.execute("""
                CREATE TABLE IF NOT EXISTS combate (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sessao_id TEXT NOT NULL,
                    canal_id TEXT NOT NULL,
                    turno INTEGER DEFAULT 1,
                    rodada INTEGER DEFAULT 1,
                    participante_atual TEXT,
                    participantes TEXT DEFAULT '[]',
                    ativo BOOLEAN DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            await db.commit()
        print("✅ Banco de dados inicializado!")
        return True

    # ========== FICHAS ==========

    async def criar_ficha(self, jogador_id, servidor_id, dados):
        """Cria uma nova ficha de personagem"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                agora = datetime.now().isoformat()

                # Valores padrão
                nome = dados.get('nome', 'Sem Nome')
                classe = dados.get('classe', 'Aventureiro')
                nivel = dados.get('nivel', 1)
                raca = dados.get('raca', 'Humano')

                # Atributos
                forca = dados.get('forca', 10)
                destreza = dados.get('destreza', 10)
                constituicao = dados.get('constituicao', 10)
                inteligencia = dados.get('inteligencia', 10)
                sabedoria = dados.get('sabedoria', 10)
                carisma = dados.get('carisma', 10)

                # PV (simplificado para D&D 5e)
                modificador_con = (constituicao - 10) // 2
                pv_max = dados.get('pv_max', 10 + modificador_con + (nivel - 1) * 6)
                pv_atual = dados.get('pv_atual', pv_max)

                await db.execute("""
                    INSERT INTO fichas (
                        jogador_id, servidor_id, nome_personagem, classe, nivel, raca,
                        forca, destreza, constituicao, inteligencia, sabedoria, carisma,
                        pv_max, pv_atual, criado_em, atualizado_em
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    jogador_id, servidor_id, nome, classe, nivel, raca,
                    forca, destreza, constituicao, inteligencia, sabedoria, carisma,
                    pv_max, pv_atual, agora, agora
                ))
                await db.commit()

                # Pegar o ID criado
                cursor = await db.execute("SELECT last_insert_rowid()")
                row = await cursor.fetchone()
                return row[0]
        except Exception as e:
            print(f"❌ Erro ao criar ficha: {e}")
            return None

    async def buscar_fichas(self, jogador_id, servidor_id, ficha_id=None):
        """Busca fichas de um jogador"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row

                if ficha_id:
                    cursor = await db.execute("""
                        SELECT * FROM fichas
                        WHERE jogador_id = ? AND servidor_id = ? AND id = ?
                    """, (jogador_id, servidor_id, ficha_id))
                else:
                    cursor = await db.execute("""
                        SELECT * FROM fichas
                        WHERE jogador_id = ? AND servidor_id = ?
                        ORDER BY atualizado_em DESC
                    """, (jogador_id, servidor_id))

                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"❌ Erro ao buscar fichas: {e}")
            return []

    async def atualizar_ficha(self, ficha_id, dados):
        """Atualiza uma ficha existente"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                agora = datetime.now().isoformat()

                # Construir query dinamicamente
                sets = []
                params = []
                for key, value in dados.items():
                    if key in ['nome_personagem', 'classe', 'nivel', 'raca',
                              'forca', 'destreza', 'constituicao', 'inteligencia',
                              'sabedoria', 'carisma', 'pv_max', 'pv_atual', 'experiencia']:
                        sets.append(f"{key} = ?")
                        params.append(value)

                if not sets:
                    return False

                sets.append("atualizado_em = ?")
                params.append(agora)
                params.append(ficha_id)

                await db.execute(f"""
                    UPDATE fichas
                    SET {', '.join(sets)}
                    WHERE id = ?
                """, params)
                await db.commit()
                return True
        except Exception as e:
            print(f"❌ Erro ao atualizar ficha: {e}")
            return False

    async def deletar_ficha(self, ficha_id, jogador_id, servidor_id):
        """Deleta uma ficha (apenas se for do jogador)"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("""
                    DELETE FROM fichas
                    WHERE id = ? AND jogador_id = ? AND servidor_id = ?
                """, (ficha_id, jogador_id, servidor_id))
                await db.commit()
                return True
        except Exception as e:
            print(f"❌ Erro ao deletar ficha: {e}")
            return False

    # ========== SESSÕES ==========

    async def criar_sessao(self, sessao_id, servidor_id, canal_id, mestre_id, sistema, nome_campanha=None):
        """Registra uma nova sessão"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                agora = datetime.now().isoformat()
                nome = nome_campanha or f"Sessão {agora[5:16]}"

                await db.execute("""
                    INSERT INTO sessoes (
                        sessao_id, servidor_id, canal_id, mestre_id,
                        sistema, nome_campanha, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (sessao_id, servidor_id, canal_id, mestre_id,
                      sistema, nome, agora, agora))
                await db.commit()
                return True
        except Exception as e:
            print(f"❌ Erro ao criar sessão: {e}")
            return False

    async def get_sessao_ativa(self, canal_id):
        """Busca sessão ativa em um canal"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM sessoes
                    WHERE canal_id = ? AND status = 'ativa'
                    ORDER BY created_at DESC LIMIT 1
                """, (str(canal_id),))
                row = await cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"❌ Erro ao buscar sessão: {e}")
            return None

    async def encerrar_sessao(self, canal_id):
        """Encerra uma sessão"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("""
                    UPDATE sessoes
                    SET status = 'encerrada', updated_at = ?
                    WHERE canal_id = ? AND status = 'ativa'
                """, (datetime.now().isoformat(), str(canal_id)))
                await db.commit()
                return True
        except Exception as e:
            print(f"❌ Erro ao encerrar sessão: {e}")
            return False

# Instância global do banco
db = Database()