import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configura o logging para podermos ver o que o bot está a fazer (útil para depuração)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CARREGAR OS SEGREDOS DO AMBIENTE ---
# O Render irá fornecer estes valores a partir das "Environment Variables" que vamos configurar mais tarde
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
THE_SPORTS_DB_API_KEY = os.environ.get("THE_SPORTS_DB_API_KEY")

# --- FUNÇÕES DO BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia uma mensagem de boas-vindas quando o comando /start é executado."""
    user = update.effective_user
    mensagem = (
        f"Olá, {user.first_name}!\n\n"
        "Eu sou o seu Bot de Desporto. Use os comandos abaixo para começar:\n\n"
        "⚽ `/proximos_jogos <nome da equipa>`\n"
        "   Exemplo: `/proximos_jogos Real Madrid`\n\n"
        "📅 `/ultimos_jogos <nome da equipa>`\n"
        "   Exemplo: `/ultimos_jogos Porto`\n\n"
        "Use `/ajuda` para ver esta mensagem novamente."
    )
    await update.message.reply_html(mensagem)

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia a mensagem de ajuda."""
    mensagem = (
        "Comandos disponíveis:\n\n"
        "⚽ `/proximos_jogos <nome da equipa>`\n"
        "   Mostra os próximos 5 jogos da equipa.\n\n"
        "📅 `/ultimos_jogos <nome da equipa>`\n"
        "   Mostra os últimos 5 resultados da equipa."
    )
    await update.message.reply_html(mensagem)

async def buscar_jogos(update: Update, context: ContextTypes.DEFAULT_TYPE, tipo: str) -> None:
    """Função principal que busca os jogos (próximos ou últimos)."""
    nome_equipa = " ".join(context.args)
    if not nome_equipa:
        await update.message.reply_text(f"Por favor, insira o nome de uma equipa. Ex: `/{tipo}_jogos Real Madrid`")
        return

    await update.message.reply_text(f"🔍 A procurar por '{nome_equipa}'...")

    # 1. Encontrar o ID da equipa
    try:
        url_busca = f"https://www.thesportsdb.com/api/v1/json/{THE_SPORTS_DB_API_KEY}/searchteams.php?t={nome_equipa}"
        response = requests.get(url_busca)
        response.raise_for_status()
        data = response.json()
        
        if not data or not data.get('teams'):
            await update.message.reply_text(f"Não consegui encontrar a equipa '{nome_equipa}'. Tente verificar o nome.")
            return
        
        id_equipa = data['teams'][0]['idTeam']
        nome_oficial = data['teams'][0]['strTeam']

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao buscar ID da equipa: {e}")
        await update.message.reply_text("Ocorreu um erro de rede. Tente novamente mais tarde.")
        return

    # 2. Buscar os jogos com o ID da equipa
    try:
        if tipo == 'proximos':
            url_jogos = f"https://www.thesportsdb.com/api/v1/json/{THE_SPORTS_DB_API_KEY}/eventsnext.php?id={id_equipa}"
            header = f"📅 Próximos 5 jogos de *{nome_oficial}*:\n\n"
        else: # ultimos
            url_jogos = f"https://www.thesportsdb.com/api/v1/json/{THE_SPORTS_DB_API_KEY}/eventslast.php?id={id_equipa}"
            header = f"✅ Últimos 5 resultados de *{nome_oficial}*:\n\n"

        response = requests.get(url_jogos)
        response.raise_for_status()
        data_jogos = response.json()

        if not data_jogos or not (data_jogos.get('events') or data_jogos.get('results')):
            await update.message.reply_text(f"Não encontrei jogos para '{nome_oficial}'.")
            return
            
        jogos = data_jogos.get('events') or data_jogos.get('results')
        
        # Formatar a mensagem de resposta
        mensagem_final = [header]
        for jogo in jogos:
            casa = jogo.get('strHomeTeam', 'N/A')
            fora = jogo.get('strAwayTeam', 'N/A')
            score_casa = jogo.get('intHomeScore', '')
            score_fora = jogo.get('intAwayScore', '')
            data_jogo = jogo.get('dateEvent', '')
            
            if tipo == 'ultimos' and score_casa is not None:
                resultado = f"*{score_casa} x {score_fora}*"
                linha = f"⚽ {casa} {resultado} {fora} ({data_jogo})"
            else:
                linha = f"⚽ {casa} vs {fora} ({data_jogo})"
            mensagem_final.append(linha)
            
        await update.message.reply_markdown("\n".join(mensagem_final))

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao buscar jogos da equipa: {e}")
        await update.message.reply_text("Ocorreu um erro de rede ao buscar os jogos. Tente novamente.")

async def proximos_jogos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para o comando /proximos_jogos."""
    await buscar_jogos(update, context, tipo='proximos')

async def ultimos_jogos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para o comando /ultimos_jogos."""
    await buscar_jogos(update, context, tipo='ultimos')


def main() -> None:
    """Inicia e corre o bot."""
    logger.info("A iniciar a aplicação do bot...")
    
    # Validação dos tokens
    if not TELEGRAM_TOKEN or not THE_SPORTS_DB_API_KEY:
        logger.error("ERRO CRÍTICO: As variáveis de ambiente TELEGRAM_TOKEN ou THE_SPORTS_DB_API_KEY não foram definidas.")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Adicionar os handlers de comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ajuda", ajuda))
    application.add_handler(CommandHandler("proximos_jogos", proximos_jogos))
    application.add_handler(CommandHandler("ultimos_jogos", ultimos_jogos))

    logger.info("Bot configurado. A iniciar o polling...")
    # Corre o bot até que o utilizador pressione Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
