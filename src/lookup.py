import discord
from discord import app_commands
from discord.ext import commands 
import re
import json
import requests
import os
from dotenv import load_dotenv 
load_dotenv()

AGENT = os.getenv("USER_AGENT")
if not AGENT: raise ValueError("Missing USER_AGENT. Ensure it is defined in your .env file.")
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN: raise ValueError("Missing DISCORD_BOT_TOKEN. Ensure it is defined in your .env file.")
GUILD = int(os.environ["GUILD_ID"])
if not GUILD:raise ValueError("Missing GUILD_ID. Ensure it is defined in your .env file.")

base_url = "https://deadlock.wiki/rest.php/v1/search/title"
wiki_url = "https://deadlock.wiki/"
headers = {"User-Agent": AGENT}
number_of_results = 1
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def lookup(user_queries, no_embed):
  replies = []
  
  for query in user_queries[:5]:
    response = requests.get(base_url, headers=headers, params={"q": query, "limit": number_of_results})
    data = response.json()
    
    if data.get("pages"):
      for page in data["pages"]:
        if no_embed:
          result = f"<{wiki_url}{page['key']}>"
        else:
          result = f"{wiki_url}{page['key']}"
        replies.append(result)
    else:
      redlink = f"{wiki_url}{query.replace(' ', '_')}?action=edit&redlink=1"
      replies.append(f"page doesnt exist: <{redlink}>")
    output = "\n".join(replies)
  return output

# NORMAL COMMANDS # NORMAL COMMANDS # NORMAL COMMANDS # NORMAL COMMANDS # NORMAL COMMANDS

@client.event
async def on_message(message):
  if message.author.bot:
    return # do nothing if a bot sent the message
  
  if message.content.strip() == "!wiki":
    await message.channel.send(f"<{wiki_url}>")  # if message is !wiki send the url
    return

  PATTERN = re.compile(r'\[\[(.*?)\]\]|\{\{(.*?)\}\}')
  
  search_queries = []
  for match in PATTERN.finditer(message.content):
    if match.group(1) is not None:
      search_queries.append((match.group(1), False))  # [[...]] match
    else:
      search_queries.append((match.group(2), True))   # {{...}} match

  print(search_queries)
  
  if not search_queries:
    return
  
  api_query = []
  for term, is_template in search_queries:
    clean_query = term.strip()
    if not clean_query or len(clean_query) > 200:
      continue
    
    prefix = ("Template:" if is_template and not clean_query.lower().startswith("template:")else "")  

    api_query.append(f"{prefix}{clean_query}")
  print(api_query)
    
  await message.channel.send(lookup(api_query, 1))

# SLASH COMMANDS # SLASH COMMANDS # SLASH COMMANDS # SLASH COMMANDS # SLASH COMMANDS # SLASH COMMANDS # SLASH COMMANDS 

@client.event
async def on_ready():
    guild = discord.Object(id=GUILD)
    synced = await tree.sync(guild=guild)
    print(f"Synced {len(synced)} command(s) to guild {GUILD}. Logged in as {client.user}")
        
@tree.command(name="wiki", description="Look up a wiki article", guild=discord.Object(id=GUILD))
@app_commands.describe(article="The name of the article to look up")
async def first_command(interaction: discord.Interaction, article: str):
    output = lookup([article], False)
    await interaction.response.send_message(output or "error 3")
    
bot = commands.Bot(command_prefix="!", intents=intents)
@bot.command(name="wiki")
async def input_cmd(ctx):
    await ctx.reply(f"{wiki_url}")
  
client.run(TOKEN)