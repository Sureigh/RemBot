from config import reddit
import asyncpraw
from discord.ext import commands, flags
import discord
import json
import asyncio
import sys
import traceback
import datetime
from urllib.parse import urlparse

praw = asyncpraw.Reddit(client_id=reddit['id'], client_secret=reddit['secret'], user_agent="RemBot by /u/IBOSSWOLF")

class FeedHandler:
    def __init__(self, bot, channel_id, sub, limit, current, webhook):
        self.bot = bot
        self.channel_id = channel_id
        self._sub = sub
        self.sub = None
        self.upvote_limit = limit
        self.webhook = discord.Webhook.from_url(webhook, adapter=discord.AsyncWebhookAdapter(bot.session))
        self.currently_checking = {}  # type: dict[str, asyncio.Task]
        self.timer = self.loop.create_task(self.auto_handler_task())
        for sub in current:
            if self.upvote_limit == 0:  # 0 = don't bother checking
                self.loop.create_task(self.dispatch(sub))
            else:
                self.currently_checking[sub] = self.loop.create_task(self.check(sub))

    def __repr__(self):
        return (f"FeedHandler({self.channel_id}, {self.sub}, {self.upvote_limit}, {self.currently_checking}, "
                f"{self.webhook.url})")

    async def auto_handler_task(self):
        self.sub = await praw.subreddit(self._sub)
        await self.sub.load()
        await self.bot.wait_until_ready()
        try:
            async for submission in self.sub.stream.submissions(skip_existing=True):
                print(f"Received submission: /r/{self._sub}/comments/{submission}")
                sub = submission.id
                if self.upvote_limit == 0:
                    await self.dispatch(sub)
                else:
                    self.currently_checking[sub] = self.loop.create_task(self.check(sub))
                await asyncio.sleep(10)
        except Exception as e:
            print("Error occurred during automatic handler:", file=sys.stderr)
            traceback.print_exception(type(e), e, e.__traceback__)

    async def check(self, subn):
        await self.bot.wait_until_ready()
        tries = 0
        try:
            while True:
                sub = await praw.submission(id=subn)
                await sub.load()
                print(f"Checking if /r/{self._sub}/comments/{subn} has reached upvote threshold "
                      f"({sub.score}/{self.upvote_limit}) ({12-tries} attempts remaining)")
                if sub.score >= self.upvote_limit:
                    await self.dispatch(subn)
                    break
                tries += 1
                if tries >= 12:
                    break
                await asyncio.sleep(360)
        except Exception as e:
            print("Error occurred during periodic updater:")
            traceback.print_exception(type(e), e, e.__traceback__)
        finally:
            task = self.currently_checking.pop(subn, None)
            if task:
                task.cancel()

    def get_community_icon(self):
        o = urlparse(self.sub.community_icon)
        return f"{o.scheme}://{o.netloc}{o.path}"

    async def dispatch(self, sub):
        print(f"Dispatching /r/{self._sub}/comments/{sub}")
        subm = await praw.submission(id=sub)
        embed = discord.Embed(colour=discord.Colour.blue(), title=subm.title, url=f"https://reddit.com{subm.permalink}",
                              timestamp=datetime.datetime.utcfromtimestamp(int(subm.created_utc)))
        icon = self.sub.icon_img or self.get_community_icon()
        embed.set_author(icon_url=icon,
                         url=f"https://reddit.com/r/{self.sub.display_name}",
                         name=f"/r/{self.sub.display_name}")
        embed.set_footer(text=f"/u/{subm.author.name}")
        if subm.url.endswith((".jpg", ".png", ".jpeg", ".webp", ".webm", ".gif", ".gifv")):
            embed.set_image(url=subm.url)
        if subm.selftext:
            embed.description = subm.selftext[:2040] + "..."
        try:
            await self.webhook.send(embed=embed)
        except discord.NotFound:  # webhook was deleted
            if self.channel is None:  # channel was deleted
                self.timer.cancel()
                return
            try:
                self.webhook = await self.channel.create_webhook(name="Auto-reddit by Rem")
                await self.dispatch(sub)
            except discord.Forbidden:  # no perms to make a new webhook
                self.timer.cancel()
                return
        except Exception as e:
            print("Error occurred whilst dispatching", file=sys.stderr)
            traceback.print_exception(type(e), e, e.__traceback__)

    @property
    def loop(self):
        return self.bot.loop

    @property
    def channel(self):
        return self.bot.get_channel(self.channel_id)

    def to_json(self):
        return {"sub": self._sub, "limit": self.upvote_limit,
                "current": [sub for sub in self.currently_checking],
                "webhook": self.webhook.url}

class Reddit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.feeds = {}  # type: dict[int, FeedHandler]
        bot.loop.run_until_complete(self.prepare_auto_feeds())

    async def prepare_auto_feeds(self):
        # TODO: use a database
        with open("feeds.json") as f:
            feeds = json.load(f)
        for i, data in feeds.items():
            self.feeds[int(i)] = FeedHandler(self.bot, int(i), **data)

    @commands.group()
    async def reddit(self, ctx):
        """Base command for auto-reddit feed related commands."""

    @flags.add_flag("-u", "--upvote-limit", type=int,
                    help="The required amount of upvotes before dispatching.", default=0)
    @reddit.command(cls=flags.FlagCommand)
    @commands.has_permissions(manage_channels=True, manage_webhooks=True)
    @commands.bot_has_permissions(manage_webhooks=True)
    async def new(self, ctx, sub, **options):
        """Creates a new reddit feed."""
        if ctx.channel.id in self.feeds:
            await ctx.send("A feed already exists in this channel~")
            return

        async with self.bot.session.get(f"https://reddit.com/r/{sub}.json") as f:
            if f.status != 200:
                await ctx.send("Unknown subreddit! :c")
                return

        try:
            webhook = (await ctx.channel.webhooks())[0]
        except IndexError:
            webhook = await ctx.channel.create_webhook(name="Auto-reddit by Rem")

        self.feeds[ctx.channel.id] = FeedHandler(self.bot, ctx.channel.id, **{"sub": sub,
                                                                              "limit": options['upvote_limit'],
                                                                              "current": [], "webhook": webhook.url})
        await ctx.send("Done! You should now get express images straight from Reddit!~")

def setup(bot):
    bot.add_cog(Reddit(bot))
