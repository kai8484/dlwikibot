import discord
from discord import app_commands
import re
import json
from urllib.parse import quote, unquote
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

base_url = "https://deadlock.wiki/api.php"  # rest.php search API was removed from the wiki
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


def split_fragment(query):
  # "Page#Section" -> ("Page", "#Section"), since title search ignores the fragment
  page, sep, fragment = query.partition("#")
  page = page.strip()
  if not page or not fragment.strip():
    return page or query, ""
  return page, f"#{quote(fragment.strip().replace(' ', '_'), safe='_-.')}"


def resolve_section(page_key, fragment):
  # anchors come from the page's real headings, so duplicate headings get a _2 suffix
  want = unquote(fragment.lstrip("#")).replace("_", " ").strip().casefold()
  response = requests.get(api_url, headers=headers, params={
    "action": "parse", "page": page_key, "prop": "tocdata", "format": "json", "formatversion": "2",
  })
  sections = response.json().get("parse", {}).get("tocdata", {}).get("sections", [])
  for section in sections:
    if section.get("line", "").strip().casefold() == want:
      return f"#{section['anchor']}"
  return ""  # no such heading: link the page rather than a dead anchor


def find_page(query):
  # exact title first (redirects included), so [[Gun]] lands on Weapon Damage
  response = requests.get(base_url, headers=headers, params={
    "action": "query", "titles": query, "redirects": 1, "format": "json", "formatversion": "2",
  })
  pages = response.json().get("query", {}).get("pages", [])
  if pages and not pages[0].get("missing") and not pages[0].get("invalid"):
    return pages[0]["title"]

  # fall back to search for typos / near matches
  response = requests.get(base_url, headers=headers, params={
    "action": "query", "list": "search", "srsearch": query,
    "srlimit": number_of_results, "format": "json", "formatversion": "2",
  })
  pages = response.json().get("query", {}).get("search", [])
  return pages[0]["title"] if pages else None


def lookup(user_queries, no_embed):
  replies = []
  
  for query in user_queries[:5]:
    page_query, fragment = split_fragment(query)
    page_title = find_page(page_query)
    
    if page_title:
      title = quote(page_title.replace(" ", "_"), safe="/:")
      anchor = resolve_section(page_title, fragment) if fragment else ""
      if no_embed:
        result = f"<{wiki_url}{title}{anchor}>"
      else:
        result = f"{wiki_url}{title}{anchor}"
      replies.append(result)
    else:
      redlink = f"{wiki_url}{page_query.replace(' ', '_')}?action=edit&redlink=1"
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
  
  if not search_queries:
    return
  
  api_query = []
  for term, is_template in search_queries:
    clean_query = term.strip()
    if not clean_query or len(clean_query) > 200:
      continue
    
    prefix = ("Template:" if is_template and not clean_query.lower().startswith("template:")else "")  

    api_query.append(f"{prefix}{clean_query}")
    
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

client.run(TOKEN)