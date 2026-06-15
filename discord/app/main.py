import discord
from discord.ext import commands
import aiohttp
import asyncio
import os
import redis
import json
import logging
import sys
import io

# 1. Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("DiscordBot")

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ORCHESTRATOR_API_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8001/v1/chat")
r = redis.from_url(REDIS_URL, decode_responses=True)


class DiscordLLMBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        commands = await self.tree.sync()
        logger.info(f"Synced {len(commands)} slash commands.")

    async def on_ready(self):
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

            # Trigger typing indicator so users know the Orchestrator/LLM is working
            async with message.channel.typing():
                response = await fetch_llm_response(message.author.id, clean_prompt)

                # Discord character limit handling
                if len(response) > 2000:
                    text_stream = io.StringIO(response)
                    response_file = discord.File(
                        fp=text_stream, filename="full_response.txt"
                    )
                    await message.reply(
                        content=response[:1990] + "...", file=response_file
                    )
                else:
                    await message.reply(response)


bot = DiscordLLMBot()


# Helper functions for Redis and LLM
def get_history(user_id):
    history_json = r.get(f"session:{user_id}")
    return json.loads(history_json) if history_json else []


def save_history(user_id, history):
    r.setex(f"session:{user_id}", 3600, json.dumps(history[-10:]))


async def fetch_llm_response(user_id, prompt):
    # Get context history from Redis cache layer
    history = get_history(user_id)

    # { "message": "...", "history": [{"role": "...", "content": "..."}] }
    payload = {"message": prompt, "history": history}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                ORCHESTRATOR_API_URL, json=payload, timeout=240
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"Orchestrator response data: {data}")

                    ai_content = data["response"].get(
                        "content", "Error: No response message parsed."
                    )

                    # Update history array and save back down to your Redis cache
                    history.append({"role": "user", "content": prompt})
                    history.append({"role": "assistant", "content": ai_content})
                    save_history(user_id, history)

                    logger.info("Successfully processed response from Orchestrator")
                    return ai_content

                error_detail = await resp.text()
                logger.error(
                    f"Orchestrator response error: {resp.status} - {error_detail}"
                )
                return f"Orchestrator Error: Status code {resp.status}. 🚨 The request responded with an error. Somebody check the logs."

    except asyncio.TimeoutError:
        logger.error("Orchestrator request timed out")
        return (
            "⚠️ **Timeout**: The orchestrator took too long processing tools or models."
        )
    except Exception as e:
        logger.exception(f"Unexpected orchestration connection error: {str(e)}")
        return "🚨 **Connection Error**: Please reach out to the devs!"


# Slash Command for clearing history
@bot.tree.command(name="clear", description="Clear your chat session history")
async def clear_command(interaction: discord.Interaction):
    r.delete(f"session:{interaction.user.id}")
    logger.info("Chat session data cleared from Redis")
    await interaction.response.send_message("Session cleared!", ephemeral=True)


# Slash command for getting session history
@bot.tree.command(name="get_history", description="Obtain your conversation history")
async def get_history_command(interaction: discord.Interaction):
    history = get_history(interaction.user.id)
    if not history:
        await interaction.response.send_message(
            "You don't have an active session history", ephemeral=True
        )
        return

    formatted_transcript = ""
    for turn in history:
        formatted_transcript += f"[{turn['role'].upper()}]: {turn['content']}\n\n"

    text_stream = io.StringIO(formatted_transcript)
    response_file = discord.File(fp=text_stream, filename="session_transcript.txt")

    logger.info("User requested chat history.")
    await interaction.response.send_message(
        content="Your requested session history is attached.",
        file=response_file,
        ephemeral=True,  # Keeps it private to the user
    )


if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"), log_handler=None)
