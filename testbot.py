import discord
import re
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

AGENT = os.getenv("USER_AGENT")
if not AGENT:
    raise ValueError(
        "Missing USER_AGENT. Ensure it is defined in your .env file."
    )

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise ValueError(
        "Missing DISCORD_BOT_TOKEN. Ensure it is defined in your .env file."
    )

# Configure intents
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# Matches text inside [[ and ]], non-greedy
WIKI_PATTERN = re.compile(r'\[\[(.*?)\]\]')
TEMPLATE_WIKI_PATTERN = re.compile(r'\{\{(.*?)\}\}')


@client.event
async def on_message(message):
  if message.author.bot:
    return
  
  page_matches = [(term, False) for term in WIKI_PATTERN.findall(message.content)]
  template_matches = [(term, True) for term in TEMPLATE_WIKI_PATTERN.findall(message.content)]
  search_queries = (page_matches + template_matches)[:5]
  base_url = "https://deadlock.wiki/rest.php/v1/search/page"
  wiki_url = "https://deadlock.wiki/"
  headers = {"User-Agent": AGENT}
  number_of_results = 1
  replies = []

  if not search_queries:
    return
  
  print(search_queries)
  
  for term, is_template in search_queries:
    clean_query = term.strip()
    if not clean_query or len(clean_query) > 200:
      continue
    
    prefix = (
      "Template:"
      if is_template 
      and not clean_query.lower().startswith("template:")
      else ""
    )
    
    api_query = f"{prefix}{clean_query}"
       
    response = requests.get(base_url, headers=headers, params={"q": api_query, "limit": number_of_results})
    data = response.json()

    if data.get("pages"):
        for page in data["pages"]:
          result = f"<{wiki_url}{page['key']}>"
          replies.append(result)
    else:
      redlink = f"{wiki_url}{clean_query.replace(' ', '_')}?action=edit&redlink=1"
      redlink_output = (f"page doesnt exist: <{redlink}>")
      replies.append(redlink_output)
    
  output = "\n".join(replies)
  if len(output) <= 2000:
    await message.channel.send(output)
  
client.run(TOKEN)