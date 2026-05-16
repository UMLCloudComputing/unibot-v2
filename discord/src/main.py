import discord
from discord import app_commands
import aiohttp
import asyncio
import os
import redis
import json
import logging
import sys
from dotenv import load_dotenv

# 1. Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("DiscordBot")

load_dotenv()

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)


class DiscordLLMBot(discord.Client):
    def __init__(self):
        # IMPORTANT: Enable message_content intent to read pings
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        logger.info(f"Bot logged in as {self.user}")

    # Event listener for every message sent
    async def on_message(self, message):
        # 1. Ignore messages sent by the bot itself
        if message.author == self.user:
            return

        # 2. Check if the bot was mentioned (@pinged)
        if self.user.mentioned_in(message):
            # Clean the message to remove the <@ID> mention string
            clean_prompt = (
                message.content.replace(f"<@!{self.user.id}>", "")
                .replace(f"<@{self.user.id}>", "")
                .strip()
            )

            if not clean_prompt:
                await message.reply(
                    "You mentioned me, but didn't provide a prompt! How can I help?"
                )
                logger.info(f"Mention received from {message.author}: No prompt")
                return

            logger.info(f"Mention received from {message.author}: {clean_prompt}")

            # Trigger typing indicator so users know the LLM is working
            async with message.channel.typing():
                response = await fetch_llm_response(message.author.id, clean_prompt)

                # Discord character limit handling
                if len(response) > 2000:
                    await message.reply(response[:1990] + "...")
                else:
                    await message.reply(response)


bot = DiscordLLMBot()


# Helper functions for Redis and LLM (Logic remains the same)
def get_history(user_id):
    history_json = r.get(f"session:{user_id}")
    return json.loads(history_json) if history_json else []


def save_history(user_id, history):
    r.setex(f"session:{user_id}", 3600, json.dumps(history[-10:]))


async def fetch_llm_response(user_id, prompt):
    url = f"{os.getenv('OPEN_WEBUI_URL')}/api/chat/completions"
    headers = {"Authorization": f"Bearer {os.getenv('OPEN_WEBUI_KEY')}"}

    history = get_history(user_id)
    history.append({"role": "user", "content": prompt})

    payload = {"model": os.getenv("MODEL_ID"), "messages": history, "stream": False}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers, timeout=90
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"API call response: {data}")
                    # Obtain model response
                    ai_content = data["choices"][0]["message"]["content"]

                    # Update history
                    history.append({"role": "assistant", "content": ai_content})
                    save_history(user_id, history)

                    logger.info("Successfully processed response")
                    return ai_content

                error_detail = await resp.text()
                logger.error(f"Model response error: {resp.status} - {error_detail}")
                return f"Model Response Error: status code: {resp.status}. 🚨 Somebody call tech support!"
    except asyncio.TimeoutError:
        logger.error("Request timed out")
        return "⚠️ **Timeout**: The LLM took too long to respond. This can happen during heavy RAG document indexing."
    except Exception as e:
        logger.exception(f"Unexpected connection error: {str(e)}")
        return f"🚨 **Connection Error**: `{str(e)}`"


# Slash Command for clearing history
@bot.tree.command(name="clear", description="Clear your chat session")
async def clear(interaction: discord.Interaction):
    r.delete(f"session:{interaction.user.id}")
    await interaction.response.send_message("Session cleared!", ephemeral=True)


if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"), log_handler=None)
