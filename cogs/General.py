# -*- coding: utf-8 -*-

from discord.ext import commands
import discord
import re
import pint


class General(commands.Cog):
    """Random commands and stuffs go here, kthx"""

    def __init__(self, bot):
        self.bot = bot

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

    @commands.command()
    async def list_emotes(self, ctx, channel=None):
        """
        Creates an automatically-updated list of emotes in the specified channel.
        By default, sorts animated emotes together with non-animated ones.
        Will paginate automatically.
        """

        emoji_list = False  # TODO: Make this a bot var

        if channel is not None:
            try:
                _channel = await commands.TextChannelConverter().convert(ctx, channel)
            except commands.ChannelNotReadable as error:
                await ctx.send(f"Error: Sorry, I don't have the permissions to view {error.argument.mention}...")
                return
            except commands.ChannelNotFound:
                await ctx.send("Error: That channel doesn't seem to exist. Maybe it's hidden? u3u'")
                return
        else:
            ctx.send("Which channel would you like to send the emote list to?")
            # TODO: Add a wait_for("message") here which will retrieve and convert a message to a channel

            _channel = """this is a placeholder to make my linter shut up"""

        msg = "__**Emotes list**__\n"
        template = ["{emoji} `{emoji}`\n", "`{emoji}` {emoji}\n"][emoji_list]  # Code golfing lmao

        # TODO: Split animated and non-animated emotes
        # I can't believe i have to use .format 😔
        for emoji in sorted([emoji.name for emoji in ctx.guild.emojis]):
            if len(msg) + len(template.format(emoji=emoji)) >= 2000:
                _channel.send(msg)
                msg = ""
                # TODO: Add a check to properly add spacing between animated and non-animated emotes
            msg += template.format(emoji=emoji)

def setup(bot):
    bot.add_cog(General(bot))
