# -*- coding: utf-8 -*-

from discord.ext import commands
import discord
import re

class General(commands.Cog):
    """Random commands and stuffs go here, kthx"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def convert(self, ctx, message: discord.Message, unit=None):
        """
        Convert various Imperial units into Metric units, and vice versa.
        Currently only supports temperature.
        By default, will convert F into C.
        """
        # You can tell Sleigh worked on this command...
        # TODO: All messages here should be constructed and sent as an embed. I'm too lazy to do it today. Tomorrow.
        #  Soon. Eventually.

        # TODO: Make this a bot var
        temp_default = True

        # I have no fucking clue how RegEx works
        result = re.search(r"(\d+)(?:[\s*°]?(?:[degrs]?)*)\s?([fc])?", message.content, flags=re.I)

        # No results
        if result is None:
            ctx.send("Error: No match found.")

        # An else *should* be enough here? Because if it doesn't match then it isn't a number idk
        else:
            # Temperature
            # Formula: T(°C) = (T(°F) - 32) / 1.8
            temp = int(result[2])

            # C to F
            if result[2].lower() == "c" or not temp_default:
                ctx.send(f"{temp}°C is roughly {round((temp * 1.8 + 32), 1)}°F.")

            # F to C
            else:
                ctx.send(f"{temp}°F is roughly {round(((temp - 32) / 1.8), 1)}°C.")


def setup(bot):
    bot.add_cog(General(bot))
