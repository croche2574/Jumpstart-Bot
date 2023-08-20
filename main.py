import os
from src import JumpStartManagerBot, Pack
from dotenv import load_dotenv
import discord
from discord import option
import json

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


bot = JumpStartManagerBot()

@bot.slash_command(
    name="start_draft",
    description="Starts a draft. Parameters are draft timer in minutes and number of people (max 16).")
@option(
    "draft_timer",
    description="Duration of draft in minutes.",
    min_value=1,
    max_value=30,
    default=10
)
@option(
    "num_players",
    description="Max number of players in the draft.",
    min_value=2,
    max_value=16,
    default=8
)
async def start_draft(ctx, draft_timer: int, num_players: int):
    await bot.start_draft(ctx, draft_timer, num_players)

@bot.slash_command(
    name="load_packs",
    description="Submit a CSV file of packs for drafting, or leave blank to attempt to load from disk.",
)
@option(
    "attachment",
    discord.Attachment,
    description="Packs to load",
    required=False
)
async def load_packs(ctx: discord.ApplicationContext, attachment: discord.Attachment ):
    #print(attachment)
    if attachment:
        csv = await attachment.read()
        csv = csv.decode('utf-8').splitlines()
        #print(csv)
        await bot.load_packs(ctx, csv)
        await ctx.respond("Successfully added " + str(len(bot.pack_list)) + " packs!")
    else:
        try:
            pack_list = []
            with open('packs.json', 'r') as openfile:
                # Reading from json file
                for json_obj in openfile:
                    json_object = json.loads(json_obj, object_hook=Pack.from_json)
                    pack_list.append(json_object)
                    print(pack_list[0])
                    bot.pack_list = pack_list[0]
                    await ctx.respond("Successfully loaded " + str(len(bot.pack_list)) + " packs from disk!")
        except EnvironmentError:
            await ctx.respond("Failed to load packs from disk, please load CSV.")

bot.run(TOKEN)