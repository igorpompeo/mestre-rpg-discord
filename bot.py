import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
import random
import json
from datetime import datetime
from database import db
import aiosqlite

# Carregar token secreto
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Configurar bot com intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MestreRPGBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.sessoes_ativas = {}

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Comandos sincronizados!")

bot = MestreRPGBot()

@bot.event
async def on_ready():
    print(f'🎲 {bot.user} está online e pronto para mestrar!')
    print(f'📚 Estou em {len(bot.guilds)} servidores!')

    # Inicializar banco de dados
    try:
        await db.init_db()
        print("💾 Banco de dados carregado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao carregar banco de dados: {e}")

    await bot.change_presence(activity=discord.Game(name="/ajuda | Mestre de RPG"))

@bot.tree.command(name="rolar", description="Role dados! Ex: /rolar 2d20+5")
async def rolar(interaction: discord.Interaction, dados: str):
    try:
        if '+' in dados:
            parte_dado, modificador = dados.split('+')
            modificador = int(modificador)
        else:
            parte_dado = dados
            modificador = 0

        quantidade, faces = parte_dado.split('d')
        quantidade = int(quantidade)
        faces = int(faces)

        resultados = []
        for _ in range(quantidade):
            resultado = random.randint(1, faces)
            resultados.append(resultado)

        total = sum(resultados) + modificador

        embed = discord.Embed(
            title="🎲 Rolagem de Dados",
            description=f"{interaction.user.mention} rolou **{dados}**",
            color=discord.Color.blue()
        )
        embed.add_field(name="Resultados", value=str(resultados), inline=False)
        embed.add_field(name="Modificador", value=f"+{modificador}" if modificador > 0 else "0", inline=True)
        embed.add_field(name="Total", value=f"**{total}**", inline=True)
        embed.set_footer(text="Que os dados sejam favoráveis!")

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"❌ Formato inválido! Use: 1d20, 2d6+3, etc.")

@bot.tree.command(name="ajuda", description="Receba ajuda sobre regras")
async def ajuda(interaction: discord.Interaction, topico: str = None):
    if topico is None:
        embed = discord.Embed(
            title="📚 Ajuda do Mestre RPG",
            description="Comandos disponíveis:",
            color=discord.Color.green()
        )
        embed.add_field(name="/rolar [dados]", value="Ex: /rolar 2d20+5", inline=False)
        embed.add_field(name="/criar_sessão", value="Inicie uma nova aventura", inline=False)
        embed.add_field(name="/ficha", value="Crie seu personagem", inline=False)
        embed.add_field(name="/ajuda [tópico]", value="Ex: /ajuda combate", inline=False)
        await interaction.response.send_message(embed=embed)
    else:
        # Dicionário de tópicos de ajuda
        topicos = {
            "combate": "⚔️ **Combate**: Ação, movimento, ataque. Role iniciativa com /rolar 1d20+destreza",
            "magias": "🔮 **Magias**: Cada classe tem seu próprio livro de magias. Mago usa inteligência, Clérigo usa sabedoria.",
            "dados": "🎲 **Dados**: Use /rolar XdY+Z. Ex: 1d20, 2d6+3, 1d8+2",
            "classe": "📖 **Classes**: Guerreiro, Mago, Clérigo, Ladino, Bárbaro, etc.",
            "d&d": "🐉 **D&D 5e**: Sistema principal. Força, Destreza, Constituição, Inteligência, Sabedoria, Carisma"
        }
        resposta = topicos.get(topico.lower(), f"📖 Tópico '{topico}' em desenvolvimento!")
        await interaction.response.send_message(resposta)

@bot.tree.command(name="criar_sessão", description="Inicie uma nova campanha de RPG")
async def criar_sessao(interaction: discord.Interaction, sistema: str = "D&D 5e"):
    sessao_id = f"{interaction.channel.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    bot.sessoes_ativas[sessao_id] = {
        "mestre": interaction.user.id,
        "canal": interaction.channel.id,
        "sistema": sistema,
        "jogadores": [],
        "inicio": datetime.now().isoformat()
    }

    embed = discord.Embed(
        title="🏰 Nova Sessão de RPG!",
        description=f"Sistema: **{sistema}**",
        color=discord.Color.gold()
    )
    embed.add_field(name="Mestre", value=interaction.user.mention, inline=True)
    embed.add_field(name="Status", value="🟢 Preparado para aventura!", inline=True)
    embed.add_field(name="ID Sessão", value=sessao_id[:8], inline=True)
    embed.set_footer(text="Use /ficha para criar seu personagem!")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ficha", description="Crie seu personagem (salvo permanentemente!)")
async def ficha(interaction: discord.Interaction,
                nome: str,
                classe: str,
                nivel: int = 1,
                raca: str = "Humano",
                forca: int = 10,
                destreza: int = 10,
                constituicao: int = 10,
                inteligencia: int = 10,
                sabedoria: int = 10,
                carisma: int = 10):

    await interaction.response.defer()

    try:
        # Preparar dados da ficha
        dados_ficha = {
            'nome': nome,
            'classe': classe,
            'nivel': nivel,
            'raca': raca,
            'forca': forca,
            'destreza': destreza,
            'constituicao': constituicao,
            'inteligencia': inteligencia,
            'sabedoria': sabedoria,
            'carisma': carisma,
        }

        # Salvar no banco
        ficha_id = await db.criar_ficha(
            str(interaction.user.id),
            str(interaction.guild_id),
            dados_ficha
        )

        if ficha_id:
            # Calcular modificadores
            mod_for = (forca - 10) // 2
            mod_des = (destreza - 10) // 2
            mod_con = (constituicao - 10) // 2

            # PV base (D&D 5e simplificado)
            pv_max = 10 + mod_con + (nivel - 1) * 6

            # Criar embed bonito
            embed = discord.Embed(
                title="📋 Ficha Salva com Sucesso!",
                description=f"**{nome}** - {raca} {classe} Nvl.{nivel}",
                color=discord.Color.green()
            )

            # Atributos
            atributos = f"💪 For:{forca} ({mod_for:+d})  🏹 Des:{destreza} ({mod_des:+d})  ❤️ Con:{constituicao} ({mod_con:+d})"
            embed.add_field(name="Atributos Físicos", value=atributos, inline=False)

            atributos2 = f"📘 Int:{inteligencia}  🧠 Sab:{sabedoria}  💬 Car:{carisma}"
            embed.add_field(name="Atributos Mentais", value=atributos2, inline=False)

            # Combate
            embed.add_field(name="❤️ PV Máximo", value=pv_max, inline=True)
            embed.add_field(name="🛡️ CA", value="10 + " + str(mod_des), inline=True)
            embed.add_field(name="🎲 ID", value=f"`{ficha_id}`", inline=True)

            embed.set_footer(text="✅ Salvo no banco de dados! Use /ficha_ver para consultar")
            embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)

            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Erro ao criar ficha. Tente novamente.")

    except Exception as e:
        print(f"❌ Erro no comando ficha: {e}")
        await interaction.followup.send("❌ Erro ao criar ficha. Verifique os dados e tente novamente.")

@bot.tree.command(name="fichas", description="Lista todas as suas fichas de personagem")
async def listar_fichas(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        # Buscar fichas do jogador
        fichas = await db.buscar_fichas(
            str(interaction.user.id),
            str(interaction.guild_id)
        )

        if not fichas:
            embed = discord.Embed(
                title="📭 Nenhuma Ficha Encontrada",
                description="Você ainda não tem personagens! Crie um com `/ficha`",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title=f"📚 Suas Fichas de Personagem ({len(fichas)})",
            color=discord.Color.blue()
        )

        for ficha in fichas[:5]:  # Mostrar até 5 fichas
            nome = ficha['nome_personagem']
            classe = ficha['classe']
            nivel = ficha['nivel']
            raca = ficha['raca']
            pv = ficha['pv_atual']
            pv_max = ficha['pv_max']

            # Barra de vida visual
            vida_porcentagem = (pv / pv_max) * 10
            barra_vida = "🟩" * int(vida_porcentagem) + "⬜" * (10 - int(vida_porcentagem))

            embed.add_field(
                name=f"**{nome}** (ID: `{ficha['id']}`)",
                value=f"🎭 {raca} {classe} Nvl.{nivel}\n❤️ {pv}/{pv_max} PV {barra_vida}",
                inline=False
            )

        if len(fichas) > 5:
            embed.set_footer(text=f"E mais {len(fichas) - 5} personagens...")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"❌ Erro ao listar fichas: {e}")
        await interaction.followup.send("❌ Erro ao buscar fichas. Tente novamente.")

@bot.tree.command(name="ficha_ver", description="Mostra os detalhes de uma ficha específica")
async def ver_ficha(interaction: discord.Interaction, id: int):
    await interaction.response.defer()

    try:
        fichas = await db.buscar_fichas(
            str(interaction.user.id),
            str(interaction.guild_id),
            id
        )

        if not fichas:
            await interaction.followup.send(f"❌ Ficha com ID `{id}` não encontrada!")
            return

        ficha = fichas[0]

        # Calcular modificadores
        mod_for = (ficha['forca'] - 10) // 2
        mod_des = (ficha['destreza'] - 10) // 2
        mod_con = (ficha['constituicao'] - 10) // 2
        mod_int = (ficha['inteligencia'] - 10) // 2
        mod_sab = (ficha['sabedoria'] - 10) // 2
        mod_car = (ficha['carisma'] - 10) // 2

        embed = discord.Embed(
            title=f"📖 {ficha['nome_personagem']}",
            description=f"{ficha['raca']} {ficha['classe']} • Nível {ficha['nivel']}",
            color=discord.Color.purple()
        )

        # Atributos
        embed.add_field(
            name="💪 Força",
            value=f"{ficha['forca']} ({mod_for:+d})",
            inline=True
        )
        embed.add_field(
            name="🏹 Destreza",
            value=f"{ficha['destreza']} ({mod_des:+d})",
            inline=True
        )
        embed.add_field(
            name="❤️ Constituição",
            value=f"{ficha['constituicao']} ({mod_con:+d})",
            inline=True
        )
        embed.add_field(
            name="📘 Inteligência",
            value=f"{ficha['inteligencia']} ({mod_int:+d})",
            inline=True
        )
        embed.add_field(
            name="🧠 Sabedoria",
            value=f"{ficha['sabedoria']} ({mod_sab:+d})",
            inline=True
        )
        embed.add_field(
            name="💬 Carisma",
            value=f"{ficha['carisma']} ({mod_car:+d})",
            inline=True
        )

        # Combate
        ca_base = 10 + mod_des
        embed.add_field(name="🛡️ Classe de Armadura", value=ca_base, inline=True)
        embed.add_field(name="❤️ Pontos de Vida", value=f"{ficha['pv_atual']}/{ficha['pv_max']}", inline=True)
        embed.add_field(name="⚔️ Bônus de Proficiência", value=f"+{2 + (ficha['nivel'] - 1) // 4}", inline=True)

        embed.set_footer(text=f"ID: {ficha['id']} • Criado em {ficha['criado_em'][:10]}")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"❌ Erro ao ver ficha: {e}")
        await interaction.followup.send("❌ Erro ao buscar ficha. Verifique o ID e tente novamente.")

@bot.tree.command(name="iniciativa", description="Role iniciativa para combate")
async def iniciativa(interaction: discord.Interaction, modificador: int = 0):
    """Rola 1d20 + modificador para iniciativa"""
    rolagem = random.randint(1, 20)
    total = rolagem + modificador

    embed = discord.Embed(
        title="⚔️ Iniciativa!",
        description=f"{interaction.user.mention} age com **{total}**",
        color=discord.Color.orange()
    )
    embed.add_field(name="🎲 Rolagem", value=f"1d20: {rolagem}", inline=True)
    embed.add_field(name="➕ Mod", value=modificador, inline=True)
    embed.add_field(name="🏁 Total", value=f"**{total}**", inline=True)

    # Mensagem dramática baseada no resultado
    if total >= 20:
        embed.set_footer(text="⚡ Você age antes que todos percebam o movimento!")
    elif total <= 5:
        embed.set_footer(text="😴 Você estava distraído... age por último.")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="atacar", description="Role um ataque contra um alvo")
async def atacar(interaction: discord.Interaction,
                 alvo: str,
                 modificador_forca: int = 0,
                 modificador_proficiencia: int = 2):

    # Rolagem de ataque
    ataque = random.randint(1, 20)
    bonus_ataque = modificador_forca + modificador_proficiencia
    total_ataque = ataque + bonus_ataque

    # Rolar dano (1d8 para arma simples)
    dano = random.randint(1, 8)
    total_dano = dano + modificador_forca

    embed = discord.Embed(
        title="⚔️ Ataque!",
        description=f"{interaction.user.mention} ataca **{alvo}**!",
        color=discord.Color.red()
    )

    # Resultado do ataque
    if ataque == 20:
        resultado = "🎯 **CRÍTICO!**"
        total_dano *= 2  # Dano dobrado no crítico
        cor = discord.Color.gold()
    elif total_ataque >= 15:  # CA média
        resultado = "✅ **Acertou!**"
        cor = discord.Color.green()
    else:
        resultado = "❌ **Errou!**"
        cor = discord.Color.dark_gray()

    embed.color = cor
    embed.add_field(name="🎲 Ataque", value=f"1d20: {ataque} + {bonus_ataque} = **{total_ataque}**", inline=False)
    embed.add_field(name="💥 Dano", value=f"1d8: {dano} + {modificador_forca} = **{total_dano}**", inline=False)
    embed.add_field(name="📊 Resultado", value=resultado, inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="dano", description="Aplique dano a um personagem")
async def causar_dano(interaction: discord.Interaction,
                      ficha_id: int,
                      dano: int,
                      tipo: str = "perfurante"):

    # Buscar ficha
    fichas = await db.buscar_fichas(
        str(interaction.user.id),
        str(interaction.guild_id),
        ficha_id
    )

    if not fichas:
        await interaction.response.send_message(f"❌ Ficha com ID `{ficha_id}` não encontrada!")
        return

    ficha = fichas[0]
    pv_atual = ficha['pv_atual']
    pv_max = ficha['pv_max']

    # Aplicar dano
    novo_pv = max(0, pv_atual - dano)

    # Atualizar no banco
    await db.atualizar_ficha(ficha_id, {'pv_atual': novo_pv})

    # Calcular porcentagem de vida
    porcentagem = (novo_pv / pv_max) * 100

    # Criar barra de vida visual
    barras = 10
    vida_barras = int((novo_pv / pv_max) * barras)
    barra_vida = "🟩" * vida_barras + "⬜" * (barras - vida_barras)

    embed = discord.Embed(
        title="💥 Dano Recebido!",
        description=f"**{ficha['nome_personagem']}** sofreu {dano} de dano {tipo}!",
        color=discord.Color.red()
    )

    embed.add_field(name="❤️ Vida",
                   value=f"{novo_pv}/{pv_max} PV\n{barra_vida} {porcentagem:.0f}%",
                   inline=False)

    if novo_pv == 0:
        embed.add_field(name="💀 Status", value="**Inconsciente!**", inline=False)
    elif novo_pv <= pv_max * 0.25:
        embed.add_field(name="⚠️ Alerta", value="**Ferido gravemente!**", inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="curar", description="Cure um personagem")
async def curar(interaction: discord.Interaction,
                ficha_id: int,
                cura: int):

    # Buscar ficha
    fichas = await db.buscar_fichas(
        str(interaction.user.id),
        str(interaction.guild_id),
        ficha_id
    )

    if not fichas:
        await interaction.response.send_message(f"❌ Ficha com ID `{ficha_id}` não encontrada!")
        return

    ficha = fichas[0]
    pv_atual = ficha['pv_atual']
    pv_max = ficha['pv_max']

    # Aplicar cura (não ultrapassar o máximo)
    novo_pv = min(pv_max, pv_atual + cura)

    # Atualizar no banco
    await db.atualizar_ficha(ficha_id, {'pv_atual': novo_pv})

    porcentagem = (novo_pv / pv_max) * 100
    barras = 10
    vida_barras = int((novo_pv / pv_max) * barras)
    barra_vida = "🟩" * vida_barras + "⬜" * (barras - vida_barras)

    embed = discord.Embed(
        title="✨ Cura Recebida!",
        description=f"**{ficha['nome_personagem']}** recuperou {cura} pontos de vida!",
        color=discord.Color.green()
    )

    embed.add_field(name="❤️ Vida",
                   value=f"{novo_pv}/{pv_max} PV\n{barra_vida} {porcentagem:.0f}%",
                   inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="narrar", description="Peça para o mestre narrar uma ação")
async def narrar(interaction: discord.Interaction, acao: str):
    respostas = [
        "Você avança corajosamente...",
        "Ao realizar esta ação, você percebe que...",
        "Os dados revelam que...",
        "Uma aura misteriosa envolve seus movimentos...",
        "O destino parece estar ao seu favor..."
    ]

    embed = discord.Embed(
        title="🎭 Ação do Jogador",
        description=f"*{acao}*",
        color=discord.Color.orange()
    )
    embed.add_field(name="Narração", value=random.choice(respostas), inline=False)
    embed.set_footer(text="Mestre IA • Use /rolar para determinar o resultado")

    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERRO: Token não encontrado! Verifique seu arquivo .env")
    else:
        print("✅ Bot configurado! Conectando ao Discord...")
        bot.run(TOKEN)
