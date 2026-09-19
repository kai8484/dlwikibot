import discord
from discord import app_commands
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

base_url = "https://deadlock.wiki/rest.php/v1/search/page"
wiki_url = "https://deadlock.wiki/"
headers = {"User-Agent": AGENT}
number_of_results = 1
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def lookup(user_query, no_embed):
  
  replies = []
  
  response = requests.get(base_url, headers=headers, params={"q": user_query, "limit": number_of_results})
  data = response.json()

  if data.get("pages"):
      for page in data["pages"]:
        if no_embed:
          result = f"<{wiki_url}{page['key']}>"
        else:
          result = f"{wiki_url}{page['key']}"
        replies.append(result)
  else:
    redlink = f"{wiki_url}{user_query.replace(' ', '_')}?action=edit&redlink=1"
    redlink_output = (f"page doesnt exist: <{redlink}>")
    replies.append(redlink_output)
    # print(replies)
  output = "\n".join(replies)
  if not output:
          return "No results found."
  if len(output) <= 2000:
      return output
  else:
      return "Result is too long to send on Discord (>2000 characters)."

# NORMAL COMMANDS # NORMAL COMMANDS # NORMAL COMMANDS # NORMAL COMMANDS # NORMAL COMMANDS

@client.event
async def on_message(message):
  if message.author.bot:
    return # do nothing if a bot sent the message

  WIKI_PATTERN = re.compile(r'\[\[(.*?)\]\]')
  TEMPLATE_WIKI_PATTERN = re.compile(r'\{\{(.*?)\}\}')

  page_matches = [(term, False) for term in WIKI_PATTERN.findall(message.content)] # all queries matching regex WIKI_PATTERN
  template_matches = [(term, True) for term in TEMPLATE_WIKI_PATTERN.findall(message.content)] # all queries matching regex TEMPLATE_WIKI_PATTERN
  search_queries = (page_matches + template_matches)[:5] # total queries in a list, max 5

  if not search_queries:
    return

  for term, is_template in search_queries:
    clean_query = term.strip()
    if not clean_query or len(clean_query) > 200:
      continue
    
    prefix = ("Template:" if is_template and not clean_query.lower().startswith("template:")else "")  
    
    api_query = f"{prefix}{clean_query}"
    
    output = lookup(api_query, True)
    if output:
      await message.channel.send(output)
    else:
      await message.channel.send("error 2")
      
# SLASH COMMANDS # SLASH COMMANDS # SLASH COMMANDS # SLASH COMMANDS # SLASH COMMANDS # SLASH COMMANDS # SLASH COMMANDS 

@client.event
async def on_ready():
    guild = discord.Object(id=GUILD)
    synced = await tree.sync(guild=guild)
    print(f"Synced {len(synced)} command(s) to guild {GUILD}. Logged in as {client.user}")
        
@tree.command(name="wiki", description="Look up a wiki article", guild=discord.Object(id=GUILD))
@app_commands.describe(article="The name of the article to look up")
async def first_command(interaction: discord.Interaction, article: str):
    output = lookup(article, False)
    await interaction.response.send_message(output or "error 3")

client.run(TOKEN)