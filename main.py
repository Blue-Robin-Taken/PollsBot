# Import libraries:
import discord
from discord.ui import Button, View
from PIL import ImageColor
import datetime
import calendar
import pymongo
import os

bot = discord.Bot()

client = pymongo.MongoClient(os.getenv('MONGODB'))
db = client.fun
coll = db.polls


@bot.listen()
async def on_connect():
    print('Connected!')


@bot.event
async def on_ready():
    for message in coll.find({}):
        if message['ExpiryDate'].isoformat() < datetime.datetime.now().utcnow().isoformat():  # https://stackoverflow.com/questions/8142364/how-to-compare-two-dates
            # https://stackoverflow.com/questions/9433851/converting-utc-time-string-to-datetime-object
            coll.delete_one(message)
            print("deleted one")
    print("ready!")


@bot.listen()
async def on_raw_reaction_add(payload):
    message_id = payload.message_id
    message = coll.find_one({'_id': message_id})
    if message is not None:
        if message['ExpiryDate'].isoformat() < datetime.datetime.now().utcnow().isoformat():  # https://stackoverflow.com/questions/8142364/how-to-compare-two-dates
            # https://stackoverflow.com/questions/9433851/converting-utc-time-string-to-datetime-object
            coll.delete_one({'_id': message_id})
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(message_id)
        embed = message.embeds[0]
        # https://chat.openai.com/share/7684565a-1f29-4c54-9d2f-502e051aef19
        upvotes = discord.utils.get(message.reactions, emoji="🔼").count - 1
        downvotes = discord.utils.get(message.reactions, emoji="🔽").count - 1
        bar = ""
        try:
            percent1 = (upvotes / (upvotes + downvotes)) * 10
            percent2 = (downvotes / (downvotes + upvotes)) * 10
            bar = f"Upvotes: {percent1*10}% {int(percent1) * '😀'} {int(percent2) * '😢'} Downvotes: {percent2*10}"


        except ZeroDivisionError:
            pass
        embed.set_footer(text=bar)
        await message.edit(embed=embed)


def hex_to_rgb(hex):  # https://stackoverflow.com/questions/29643352/converting-hex-to-rgb-value-in-python
    return ImageColor.getcolor(hex, 'RGB')


@bot.slash_command(title='send_poll', description="send a poll", guild_ids=[1044711937956651089])
@discord.option(name='title', type=str)
@discord.option(name='channel', type=discord.TextChannel, channel_types=[discord.ChannelType.text,
                                                                         discord.ChannelType.news,
                                                                         discord.ChannelType.news_thread,
                                                                         discord.ChannelType.public_thread,
                                                                         discord.ChannelType.private_thread])
@discord.option(name='minutes', type=int, min_value=0, max_value=99999)
@discord.option(name='description', type=str, required=False)
@discord.option(name='img', type=discord.Attachment, required=False)
@discord.option(name='r', type=int, max_value=250, min_value=0, required=False)
@discord.option(name='g', type=int, max_value=250, min_value=0, required=False)
@discord.option(name='b', type=int, max_value=250, min_value=0, required=False)
@discord.option(name='hex_code', type=str, required=False)
async def send_poll(ctx, title, channel, minutes, description, img, r, g, b, hex_code):
    if ctx.user.guild_permissions.manage_guild:
        if description is None:
            description = ""
        color = discord.Color.random()
        if hex_code is not None:
            color = hex_to_rgb(hex_code)
            color = discord.Color.from_rgb(color[0], color[1], color[2])
        if (r is not None) and (g is not None) and (b is not None):
            color = discord.Color.from_rgb(r, g, b)
        expiry_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
        embed = discord.Embed(
            title=title,
            description=description + f"\n \n <t:{calendar.timegm(expiry_time.timetuple())}>",
            # https://www.geeksforgeeks.org/convert-python-datetime-to-epoch/
            color=color
        )
        embed.set_footer(text="Upvotes 0% ⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛ Downvotes 0%")
        if img is not None:
            embed.set_image(url=img.url)
        m = await channel.send(embed=embed)

        await m.add_reaction("🔼")
        await m.add_reaction("🔽")
        coll.insert_one({'_id': m.id, 'ExpiryDate': expiry_time})
        await ctx.respond('Sent message', ephemeral=True)


bot.run(os.getenv('TOKEN'))
