import discord
from discord import app_commands
from discord.ext import commands 
import re
import string
import json
import requests
from urllib.parse import quote_plus
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
api_url = "https://deadlock.wiki/api.php"
wiki_url = "https://deadlock.wiki/"
headers = {"User-Agent": AGENT}
WIKI_BOT_KEY = os.getenv("WIKI_BOT_KEY")
if WIKI_BOT_KEY: headers["X-Bot-Key"] = WIKI_BOT_KEY  # lets the wiki's Cloudflare rule recognise this bot
number_of_results = 1
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def exact_title(query):
  # plain title lookup (follows redirects). doesnt use the search backend, so it works when search is broken
  # also tries Title Case so "rusted barrel" finds "Rusted Barrel"
  candidates = list(dict.fromkeys([query, string.capwords(query)]))
  try:
    response = requests.get(api_url, headers=headers, timeout=10, params={"action": "query", "titles": "|".join(candidates), "redirects": 1, "format": "json", "formatversion": 2})
    response.raise_for_status()
    data = response.json()["query"]
  except (requests.RequestException, ValueError, KeyError):
    return None
  # map what we asked for to the final title (normalized -> redirected)
  renames = {r["from"]: r["to"] for r in data.get("normalized", []) + data.get("redirects", [])}
  found = {p["title"] for p in data.get("pages", []) if not p.get("missing") and not p.get("invalid")}
  for title in candidates:
    for _ in range(3):  # normalized -> redirect, capped so a bad response cant loop forever
      if title in found or title not in renames:
        break
      title = renames[title]
    if title in found:
      return title.replace(" ", "_")
  return None

def search_titles(query):
  # returns (list of page keys, failed). failed=True means the wiki errored, not that nothing matched
  try:
    response = requests.get(base_url, headers=headers, timeout=10, params={"q": query, "limit": number_of_results})
    response.raise_for_status()
    pages = response.json().get("pages") or []
  except (requests.RequestException, ValueError) as e:
    print(f"search failed for {query!r}: {e}")
    return [], True
  return [page["key"] for page in pages], False

def lookup(user_queries, no_embed):
  replies = []

  for query in user_queries[:5]:
    exact = exact_title(query)
    if exact:
      keys, failed = [exact], False
    else:
      keys, failed = search_titles(query)

    if keys:
      for key in keys:
        if no_embed:
          result = f"<{wiki_url}{key}>"
        else:
          result = f"{wiki_url}{key}"
        replies.append(result)
    elif failed:
      replies.append(f"wiki search is having issues, try: <{wiki_url}Special:Search?search={quote_plus(query)}>")
    else:
      redlink = f"{wiki_url}{query.replace(' ', '_')}?action=edit&redlink=1"
      replies.append(f"page doesnt exist: <{redlink}>")
  return "\n".join(replies)

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
  
  if not search_queries:
    return
  
  api_query = []
  for term, is_template in search_queries:
    clean_query = term.strip()
    if not clean_query or len(clean_query) > 200:
      continue
    
    prefix = ("Template:" if is_template and not clean_query.lower().startswith("template:")else "")  

    api_query.append(f"{prefix}{clean_query}")

  if not api_query:
    return

  await message.channel.send(lookup(api_query, 1))

# SLASH COMMANDS # SLASH COMMANDS # SLASH COMMANDS # SLASH COMMANDS # SLASH COMMANDS # SLASH COMMANDS # SLASH COMMANDS 

@client.event
async def on_ready():
    guild = discord.Object(id=GUILD)
    synced = await tree.sync(guild=guild)
    print(f"Synced {len(synced)} command(s) to guild {GUILD}. Logged in as {client.user}")

    await client.change_presence(
        status=discord.Status.idle,
        activity=discord.Activity(
            type=discord.ActivityType.competing,
            name="a pillow fight"
        )
    )
        
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