import discord
from discord import app_commands
import aiohttp
import os
import redis
import json
import logging
import sys
from dotenv import load_dotenv

# 1. Structured Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("DiscordBot")

load_dotenv()

# Redis Configuration with logging
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()  # Verify connection on startup
    logger.info(f"Connected to Redis at {REDIS_URL.split('@')[-1]}")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    sys.exit(1)


class DiscordLLMBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        logger.info("Syncing slash commands...")
        await self.tree.sync()
        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")


bot = DiscordLLMBot()


def get_history(user_id):
    try:
        history_json = r.get(f"session:{user_id}")
        if history_json:
            history = json.loads(history_json)
            logger.debug(
                f"Retrieved history for user {user_id} ({len(history)} messages)"
            )
            return history
        return []
    except Exception as e:
        logger.warning(f"Error reading history for {user_id}: {e}")
        return []


def save_history(user_id, history):
    try:
        # Store history for 1 hour (3600 seconds)
        r.setex(f"session:{user_id}", 3600, json.dumps(history[-10:]))
        logger.debug(f"Saved history for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to save history for {user_id}: {e}")


async def fetch_llm_response(user_id, prompt):
    url = f"{os.getenv('OPEN_WEBUI_URL')}/chat/completions"
    headers = {"Authorization": f"Bearer {os.getenv('OPEN_WEBUI_KEY')}"}
    model = os.getenv("MODEL_ID")

    history = get_history(user_id)
    history.append({"role": "user", "content": prompt})

    payload = {"model": model, "messages": history}

    logger.info(f"Sending request to LLM ({model}) for user {user_id}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers, timeout=60
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ai_content = data["choices"][0]["message"]["content"]

                    history.append({"role": "assistant", "content": ai_content})
                    save_history(user_id, history)

                    logger.info(f"Successfully received response for user {user_id}")
                    return ai_content

                logger.error(
                    f"LLM API Error: Status {resp.status} | Body: {await resp.text()}"
                )
                return f"API Error: {resp.status}"
    except Exception as e:
        logger.exception(f"Exception during LLM request for {user_id}: {e}")
        return f"Connection Error: {str(e)}"


@bot.tree.command(name="ask", description="Send a query to the LLM (Open WebUI)")
async def ask(interaction: discord.Interaction, prompt: str):
    user_info = f"{interaction.user} ({interaction.user.id})"
    logger.info(f"Command /ask received from {user_info}")

    await interaction.response.defer()
    response = await fetch_llm_response(interaction.user.id, prompt)

    if len(response) > 2000:
        logger.warning(
            f"Response for {interaction.user.id} exceeds 2000 chars; truncating."
        )
        await interaction.followup.send(response[:1990] + "...")
    else:
        await interaction.followup.send(response)


@bot.tree.command(name="clear", description="Clear your chat session")
async def clear(interaction: discord.Interaction):
    logger.info(f"Session clear requested by {interaction.user.id}")
    r.delete(f"session:{interaction.user.id}")
    await interaction.response.send_message("Session cleared!", ephemeral=True)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.critical("DISCORD_TOKEN not found in environment variables!")
        sys.exit(1)

    bot.run(token, log_handler=None)  # Disable discord.py default handler to use ours
