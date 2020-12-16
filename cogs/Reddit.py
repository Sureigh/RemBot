import aiohttp

from config import reddit
import asyncpraw
import asyncprawcore.exceptions
from discord.ext import commands, flags
import discord
import json
import asyncio
import sys
import traceback
import datetime
from urllib.parse import urlparse
import collections

praw = asyncpraw.Reddit(client_id=reddit['id'], client_secret=reddit['secret'], user_agent="RemBot by /u/IBOSSWOLF")


# TODO: Make one FeedHandler object handle multiple channels(?)
class FeedHandler:
    def __init__(self, bot, channel_id, *, sub, current, webhook,
                 upvote_limit=0, image_only=False, attempts=12, keywords=None):
        # Flags default value should be here
        # P.S Argparse bad
        if upvote_limit is None:
            upvote_limit = 0
        if attempts is None:
            attempts = 12
        if keywords is None:
            keywords = []

        self._sub_name = sub
        self.bot = bot
        self.channel_id = channel_id
        self.sub = None
        self.webhook = discord.Webhook.from_url(webhook, adapter=discord.AsyncWebhookAdapter(bot.session))
        self.currently_checking = {}  # type: dict[str, asyncio.Task]
        self.timer = self.loop.create_task(self.auto_handler_task(sub))

        self.flags = {"upvote_limit": upvote_limit,
                      "image_only": image_only,
                      "attempts": attempts,
                      "keywords": keywords}

        for sub in current:
            if upvote_limit == 0:  # 0 = don't bother checking
                self.loop.create_task(self.dispatch(sub))
            else:
                self.currently_checking[sub] = self.loop.create_task(self.check(sub))

    @property
    def upvote_limit(self):
        return self.flags['upvote_limit']

    @property
    def image_only(self):
        return self.flags['image_only']

    @property
    def attempts(self):
        return self.flags['attempts']

    @property
    def keywords(self):
        return self.flags['keywords']

    def __repr__(self):
        return (f"FeedHandler({self.channel.id}, {self.sub}, {self.currently_checking.keys()}"
                f"{self.flags})")

    def __eq__(self, other):
        return all([isinstance(other, self.__class__),
                    self.channel == other.channel,
                    self._sub_name == other._sub_name])

    def image_check(self, submission):
        return self.image_only and not submission.url.endswith((".jpg", ".png", ".jpeg", ".webp", ".webm", ".gif",
                                                                ".gifv"))

    async def auto_handler_task(self, sub):
        self.sub = await praw.subreddit(sub)
        await self.sub.load()
        await self.bot.wait_until_ready()
        print(f"Awaiting submissions in /r/{sub}")

        try:
            # Submission checking
            async for submission in self.sub.stream.submissions(skip_existing=True):
                print(f"Received submission: /r/{sub}/comments/{submission}")
                sub_id = submission.id

                # No NSFW
                if not self.channel.is_nsfw() and submission.over_18:
                    print(f"[NSFW] Skipped NSFW post /r/{sub}/comments/{submission} ({submission.url})")
                    continue
                # Image only
                if self.image_check(submission):
                    print(f"[Image] Skipped non-image post /r/{sub}/comments/{submission} ({submission.url})")
                    continue
                # Keywords
                if self.keywords and not any(word.lower() in submission.name.lower() for word in self.keywords):
                    print(f"[Keyword] Skipped non-relevant post /r/{sub}/comments/{submission} ({submission.url})")
                    continue
                # Upvote limit
                if not self.upvote_limit:
                    await self.dispatch(sub_id)
                else:
                    self.currently_checking[sub_id] = self.loop.create_task(self.check(sub_id))

                await asyncio.sleep(10)
        except asyncprawcore.exceptions.RequestException as e:
            print("Caught exception", e, e.__cause__)
            if isinstance(e.__cause__, asyncio.TimeoutError):
                print("Timed out fetching submissions. Restarting...", file=sys.stderr)
                self.timer = self.loop.create_task(self.auto_handler_task(sub))
            elif isinstance(e.__cause__, aiohttp.ClientOSError) and e.__cause__.errno == 104:
                print("Disconnected while fetching. Restarting...", file=sys.stderr)
                self.timer = self.loop.create_task(self.auto_handler_task(sub))
            else:
                print("Error occurred during automatic handler:", file=sys.stderr)
                traceback.print_exception(type(e), e, e.__traceback__)
        except Exception as e:
            print("Error occurred during automatic handler:", file=sys.stderr)
            traceback.print_exception(type(e), e, e.__traceback__)

    async def check(self, sub_name):
        sub = await praw.submission(id=sub_name)
        if self.image_check(sub):
            print(f"Ignoring non-image submission {sub}")
            return  # skipped!
        await self.bot.wait_until_ready()
        tries = self.attempts
        try:
            while tries:
                await sub.load()
                print(f"Checking if /r/{self.sub.display_name}/comments/{sub} has reached upvote threshold "
                      f"({sub.score}/{self.upvote_limit}) ({tries} attempts remaining)")
                if sub.score >= self.upvote_limit:
                    await self.dispatch(sub)
                    break
                tries -= 1
                await asyncio.sleep(360)
        except Exception as e:
            print("Error occurred during periodic updater:")
            traceback.print_exception(type(e), e, e.__traceback__)
        else:
            print(f"/r/{self.sub.display_name}/comments/{sub} did not reach the upvote threshold. Disposing...")
        finally:
            task = self.currently_checking.pop(sub_name, None)
            if task:
                task.cancel()

    def get_community_icon(self):
        o = urlparse(self.sub.community_icon)
        return f"{o.scheme}://{o.netloc}{o.path}" if o.scheme else ""

    async def dispatch(self, sub):
        print(f"Dispatching /r/{self.sub.display_name}/comments/{sub}")
        submit = await praw.submission(id=sub)
        if len(submit.title) > 250:
            title = submit.title[:250] + '...'
        else:
            title = submit.title
        embed = discord.Embed(colour=discord.Colour.blue(), title=title,
                              url=f"https://reddit.com{submit.permalink}",
                              timestamp=datetime.datetime.utcfromtimestamp(int(submit.created_utc)))
        icon = self.sub.icon_img or self.get_community_icon() or embed.Empty
        embed.set_author(url=f"https://reddit.com/r/{self.sub.display_name}",
                         name=f"/r/{self.sub.display_name}",
                         icon_url=icon)
        embed.set_footer(text=f"/u/{submit.author.name}")
        if submit.url.endswith((".jpg", ".png", ".jpeg", ".webp", ".webm", ".gif", ".gifv")):
            embed.set_image(url=submit.url)
        if submit.selftext:
            if len(submit.selftext) > 2048:
                embed.description = submit.selftext[:2040] + "..."
            else:
                embed.description = submit.selftext
        try:
            await self.webhook.send(embed=embed)
        except discord.NotFound:
            if self.channel is None:
                # TODO: channel was deleted, find a way to remove this feed from the database
                self.timer.cancel()
                return
            try:
                webhook = discord.utils.get(await self.channel.webhooks(), name=f'/r/{self.sub.display_name}')
                if webhook is None:
                    webhook = await self.channel.create_webhook(name=f'/r/{self.sub.display_name}')
                self.webhook = webhook
                await webhook.send(embed=embed)
            except discord.Forbidden:  # no perms to fetch/create a webhook
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
        return {"sub": self.sub.display_name, "upvote_limit": self.upvote_limit,
                "current": [sub for sub in self.currently_checking],
                "webhook": self.webhook.url, "image_only": self.image_only,
                "attempts": self.attempts, "keywords": self.keywords}


class Reddit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.feeds = collections.defaultdict(dict)  # type: dict[int, dict[str, FeedHandler]]
        bot.loop.run_until_complete(self.prepare_auto_feeds())
        # TODO: find a way to allow reloading of this cog (bot.is_ready?)

    async def prepare_auto_feeds(self):
        # TODO: use a database
        with open("feeds.json") as f:
            feeds = json.load(f)
        for i, data in feeds.items():
            for sub in data:
                self.feeds[int(i)][sub] = FeedHandler(self.bot, int(i), **data[sub])

    @commands.group()
    async def reddit(self, ctx):
        """Base cog for auto-reddit feed related commands."""
        pass

    @flags.add_flag("-k", "--keywords", type=lambda x: x.split(", "),
                    help="The keywords required before dispatching.")
    @flags.add_flag("-u", "--upvote-limit", type=int,
                    help="The required amount of upvotes before dispatching.")
    @flags.add_flag('-i', "--image-only", action="store_true",
                    help="Only send image posts.")
    @flags.add_flag('-a', "--attempts", type=int,
                    help="Total attempts to allow when checking for upvotes.")
    @reddit.command(cls=flags.FlagCommand)
    @commands.has_permissions(manage_channels=True, manage_webhooks=True)
    @commands.bot_has_permissions(manage_webhooks=True)
    async def feed(self, ctx, sub: str.lower, **options):
        """Creates a new reddit feed, or modifies an existing one."""
        await ctx.channel.trigger_typing()

        # If the flag value is None (which means, default values), it'll straight up delete the flag lmao
        options = {k: v for k, v in options.items() if v not in [None, False]}

        async with self.bot.session.get(f"https://reddit.com/r/{sub}.json") as f:
            if f.status != 200:
                await ctx.send("Unknown subreddit! :c")
                return

        _sub = await praw.subreddit(sub)
        await _sub.load()

        # NSFW Check: If subreddit is NSFW, you are sent to horny jail
        if not ctx.channel.is_nsfw() and _sub.over18:
            await ctx.send("Error: This subreddit is NSFW! Please make sure this channel is marked as NSFW first.")
            return

        webhook = discord.utils.find(lambda w: w.name.lower() == f'/r/{sub}', await ctx.channel.webhooks())
        if webhook is None:
            print("No webhook found, making new")
            if _sub.icon_img or _sub.community_icon:
                async with self.bot.session.get(_sub.icon_img or _sub.community_icon) as g:
                    img = await g.read()
            else:
                img = None
            webhook = await ctx.channel.create_webhook(name=f'/r/{_sub.display_name}', avatar=img)
            print("Created")

        if sub in self.feeds[ctx.channel.id].keys():
            print(f"Existing feed {_sub.display_name} detected")
            msg = f"A feed for /r/{_sub.display_name} already exists here."
            if options:
                msg += "\nSo, we've updated the feed with the following flags:\n```"
                for k, v in options.items():
                    self.feeds[ctx.channel.id][sub].flags[k] = v
                    msg += f"\n{k}: {v}"
                msg += "```"
            await ctx.send(msg)
            return

        print(f"Creating a new feed {_sub.display_name}")
        feed = FeedHandler(self.bot, ctx.channel.id, sub=sub, current=[], webhook=webhook.url, **options)

        self.feeds[ctx.channel.id][sub] = feed

        msg = f"Done! You should now get express images straight from /r/{_sub.display_name}!~\n"
        if options:
            msg += "With the following flags:\n```"
            for k, v in options.items():
                msg += f"\n{k}: {v}"
            msg += "```"
        await ctx.send(msg)  # maya and sleigh are a big cutie btw uwu

    # TODO: Hey we should clean up webhooks lol
    @reddit.command()
    async def remove(self, ctx, sub: str.lower):
        """Removes an auto-reddit feed."""
        try:
            feed = self.feeds[ctx.channel.id].pop(sub)
        except KeyError:
            await ctx.send("This feed doesn't seem to exist... Are you sure you typed in the right subreddit name?")
            return

        [task.cancel() for task in feed.currently_checking.values()]
        feed.timer.cancel()

        await ctx.send(f"Okay! Removed /r/{sub} from your feeds.")

def setup(bot):
    bot.add_cog(Reddit(bot))
