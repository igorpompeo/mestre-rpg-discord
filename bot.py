import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
import random
import json
from datetime import datetime

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
    await bot.change_presence(activity=discord.Game(name="!ajuda | Mestre de RPG"))

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

@bot.tree.command(name="ficha", description="Crie seu personagem")
async def ficha(interaction: discord.Interaction, nome: str, classe: str, nivel: int = 1):
    embed = discord.Embed(
        title="📋 Ficha do Personagem",
        description=f"**{nome}**",
        color=discord.Color.purple()
    )
    embed.add_field(name="Classe", value=classe, inline=True)
    embed.add_field(name="Nível", value=nivel, inline=True)
    embed.add_field(name="Jogador", value=interaction.user.mention, inline=True)
    embed.add_field(name="PV", value="10 + modificador", inline=True)
    embed.add_field(name="CA", value="10 + armadura", inline=True)
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)

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
