# -*- coding: utf-8 -*-

from discord.ext import commands, flags
import discord
import re

class General(commands.Cog):
    """Random commands and stuffs go here, kthx"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def convert(self, ctx, msg: discord.Message, unit=None):
        """
        Convert various Imperial units into Metric units, and vice versa.
        Currently only supports temperature.
        By default, will convert F into C.
        """
        # You can tell Sleigh worked on this command...

        # TODO: Make this a bot var
        temp_default = True

        # I have no fucking clue how RegEx works
        results = re.findall(r"(\d+)(?:[\s*°]?(?:[degrs]?)*)\s?([fc])?", msg.content, flags=re.I)

        # An error that happens only if there's no results found whatsoever
        if not results:
            embed = discord.Embed(
                description="No match found.",
                color=discord.Color.red()
            ).set_author(name="Error:")
            await ctx.send(embed=embed)
            return

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

    # TODO: nargs will probably split anything longer than one word into multiple args, find out how to fix that
    # TODO: Write format for each command
    # Embed management
    @flags.add_flag("--channel", "--c",
                    type=discord.TextChannel,
                    help="Sets the channel for the complete embed to be sent to.")
    @flags.add_flag("--send", "--s",
                    action="store_true",
                    help="Sends the completed embed to the set channel.")
    @flags.add_flag("--reset", "--r",
                    action="store_true",
                    help="Reset and clear the embed.")
    # Author
    @flags.add_flag("--author_set", "--as",
                    type=discord.User,
                    help="Set avatar + name of the embed to a user.")
    @flags.add_flag("--author", "--a",
                    nargs="*",
                    help="Author: [user] [name] [URL] [icon URL]")
    @flags.add_flag("--author_clear", "--acl",
                    action="store_true",
                    help="Clears embed’s author information.")
    @flags.add_flag("-author_name", "-an",
                    help="The name of the author.")
    @flags.add_flag("-author_url", "-au",
                    help="The URL for the author.")
    @flags.add_flag("-author_icon", "-ai",
                    help="The URL of the author icon. Only HTTP(S) is supported.")
    # Embed info
    @flags.add_flag("--embed", "--e",
                    nargs="*",
                    help="Embed: [title] [desc] [URL]")
    @flags.add_flag("--embed_clear", "--ecl",
                    action="store_true",
                    help="Clears embed's information.")
    @flags.add_flag("-embed_title", "-et",
                    default="Placeholder",
                    help="The title of the embed.")
    @flags.add_flag("-embed_desc", "-ed",
                    default="Placeholder",
                    help="The description of the embed.")
    @flags.add_flag("-embed_url", "-eu",
                    help="The URL of the embed. ")
    # Embed info - optional
    @flags.add_flag("--embed_optional", "--eo",
                    nargs="*",
                    help="Embed optionals: [color] [image URL] [footer text] [footer URL] [timestamp]")
    @flags.add_flag("--embed_optional_clear", "--eocl",
                    action="store_true",
                    help="Clears embed's optional information.")
    @flags.add_flag("-embed_color", "-embed_colour", "-ec",
                    help="The color code of the embed.")
    @flags.add_flag("-embed_image", "-ei",
                    help="The image for the embed content.")
    @flags.add_flag("-embed_footer", "-ef",
                    help="The footer text.")
    @flags.add_flag("-embed_footer_url", "-efu",
                    help="The URL of the footer icon.")
    @flags.add_flag("-embed_timestamp", "-ets",
                    help="The timestamp of the embed content.")
    # Embed fields
    @flags.add_flag("-field_name", "-fn",
                    nargs=2,
                    help="The name of the field."
                         "Format: `-fn [field number] [field name]`")
    @flags.add_flag("-field_value", "-fv",
                    nargs=2,
                    help="The value of the field."
                         "Format: `-fn [field number] [field value]`")
    @flags.add_flag("-field_inline", "-fi",
                    nargs=2,
                    choices=["true", "false", "t", "f", "yes", "no", "y", "n"],
                    help="Whether the field should be displayed inline."
                         "Format: `-fn [field number] [true/false]`")
    @flags.command(aliases=["embed"])
    async def create_embed(self, ctx, **args):
        """
        Allows the bot to create an embed message via user input.
        Can be worked on over time and directed to send the completed embed to a specified channel on completion.
        """
        pass

def setup(bot):
    bot.add_cog(General(bot))
