# -*- coding: utf-8 -*-

from discord.ext import commands
import discord
import re
import pint
import itertools
import random


class General(commands.Cog):
    """Random commands and stuffs go here, kthx"""

    def __init__(self, bot):
        self.bot = bot

        # Stuff for list_emotes
        bot.split_animated = False  # TODO: Allow editing this in config
        bot.template = "{emoji} `{emoji.name}`"  # TODO: Allow editing this in config
        bot.debug = False

    @commands.command()
    async def convert(self, ctx, *, args):
        """
        Convert various Imperial units into Metric units, and vice versa.
        Currently only supports temperature.
        By default, will convert F into C.
        """
        # You can tell Sleigh worked on this command...

        # TODO: Make this a bot var
        temp_default = True

        # Process message
        # TODO: There has to be a smarter way; Too bad I'm not smart enough to know what it is lmao
        # If msg
        try:
            msg = await commands.MessageConverter().convert(ctx, args)
            msg = msg.content
        except commands.MessageNotFound:
            # If msg + unit
            # TODO: This command won't work for units w/ spaces in them (e.g Nautical miles); IDK, find a better way
            arg = args.split()
            try:
                msg = await commands.MessageConverter().convert(ctx, arg[-1])
                msg = msg.content
                unit = arg.pop(-1)
            except commands.MessageNotFound:
                # If unit
                # TODO: Either regex/python parse text to check if "unit" here is any specified unit to "msg" convert to
                #  e.g inch, ', c, feet etc, and if it's not any unit assume it's part of msg
                # TODO: Replace "True" with parser
                if arg[-1] == True:
                    unit = arg.pop(-1)
                msg = " ".join(arg)

        # I have no fucking clue how RegEx works
        # TODO: Perhaps this can be less specific, but more diverse in finding what kind of units we're looking for?
        results = re.findall(r"(\d+)(?:[\s*°]?(?:[degrs]?)*)\s?([fc])?", msg, flags=re.I)

        # An error that happens only if there's no results found whatsoever
        if not results:
            embed = discord.Embed(
                description="No match found.",
                color=discord.Color.red()
            ).set_author(name="Error:")
            await ctx.send(embed=embed)
            return

        # TODO: Have a try/except clause here that will handle conversion errors
        # TODO: In the future, make it a list in a dict within a dict, sorted by system->category->list of
        # I mean, I *could* probably write all of this into a dict comprehension with a list comprehension...
        # ...But that's messy and ugly.
        systems = {"Metric": [],
                   "Imperial": []}

        for result in results:
            # Temperature
            # Formula: T(°C) = (T(°F) - 32) / 1.8
            temp = int(result[2])

            # C to F
            if any(["c" in unit, result[2].lower() == "c", not temp_default]):
                systems["Metric"].append(f"{temp}°C => {round((temp * 1.8 + 32), 1)}°F.")

            # F to C
            else:
                systems["Imperial"].append(f"{temp}°F => {round(((temp - 32) / 1.8), 1)}°C.")

        # TODO: In the future, we'll be doing more than just temperature, so use .add_field() instead and separate by
        #  field type, I suppose.
        async def send_embed(sys_name):
            embed = discord.Embed(
                description="\n".join([i for i in systems[sys_name]])
            ).set_author(name=f"{sys_name} units found:")
            await ctx.send(embed=embed)

        for sys in systems:
            await send_embed(sys)

    @commands.command(aliases=["emote_list", "emotes", "emojis", "list_emojis", "emoji_list"])
    async def list_emotes(self, ctx, channel=None):
        """
        Creates an automatically-updated list of emotes in the specified channel.
        By default, sorts animated emotes together with non-animated ones.
        Will paginate automatically.
        """

        try:
            if channel is not None:
                _channel = await commands.TextChannelConverter().convert(ctx, channel)
            else:
                await ctx.send("Which channel would you like to send the emote list to?")
                msg = await self.bot.wait_for("Message", check=lambda msg: all([ctx.author == msg.author,
                                                                                ctx.channel == msg.channel]))
                _channel = await commands.TextChannelConverter().convert(ctx, msg.content)
        except commands.ChannelNotReadable as error:
            await ctx.send(f"Error: Sorry, I don't have the permissions to view {error.argument.mention}...")
            return
        except commands.ChannelNotFound:
            await ctx.send("Error: That channel doesn't seem to exist... maybe it's hidden? u3u'")
            return

        sent = []  # TODO: This should be in DB

        # Creates two separate iterables, one animated, one non-animated emojis.
        emojis = [(False, ctx.guild.emojis)]

        if self.bot.split_animated:
            emoji = set(filter(lambda e: not e.animated, ctx.guild.emojis))
            emojis = [(False, [*emoji]), (True, [*(set(ctx.guild.emojis) - emoji)])]

        template = self.bot.template

        # I can't believe i have to use .format and string concatenation 😔
        for a, e in emojis:
            msg = {False: "__**Emotes list**__",
                   True: "__**Animated Emotes list**__"}[a] + "\n"  # TODO: Allow editing this in config
            for emoji in sorted(e, key=lambda e: e.name.lower()):
                if len(msg) + len(template.format(emoji=emoji)) >= 2000:
                    sent.append(await _channel.send(msg))
                    msg = ""
                msg += template.format(emoji=emoji) + "\n"
            sent.append(await _channel.send(msg))

        if self.bot.debug:
            await _channel.send(f"lmao this is for debug purposes ignore me pls\n{sent}")

        # TODO: Make sure if sent in an empty channel, will remove/send messages as necessary when emojis are
        #  added/removed. See on_guild_emojis_update() for more info

        # TODO: Add a feature where, if the channel where the bot is posting ahead in already is not completely empty,
        #  the bot will "reserve" slots for future use. Of course, reserved message slots will be configurable. Default
        #  should be two slots + actual message.

    @commands.command()
    async def someone(self, ctx):
        await ctx.send(random.choice(ctx.guild.members).mention)
        # TODO: Add ability to exclude admins/moderators?

def setup(bot):
    bot.add_cog(General(bot))
