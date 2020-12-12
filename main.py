import discord
from discord.ext import commands
import glob
import config
import os, os.path
import sys
import traceback
import aiohttp
import json

if not os.path.isfile("feeds.json"):
	with open("feeds.json", "w") as f:
		f.write("{}")

class Rem(commands.Bot):
	def __init__(self):
		super().__init__(
			commands.when_mentioned,
			intents=discord.Intents(guilds=True, messages=True, members=True, reactions=True),
			owner_ids={155159390637260800, 455289384187592704},
			activity=discord.Game("with your feelings 💙 | @ me for help!")
		)
		self.session = None

		async def set_the_fucking_session():
			self.session = aiohttp.ClientSession()
		self.loop.create_task(set_the_fucking_session())

		try:
			self.load_extension('jishaku')
			print("Found and loaded Jishaku")
		except commands.ExtensionError:
			pass

		for file in glob.glob("cogs/*.py"):
			fname = file.replace(os.sep, '.')[:-3]
			try:
				self.load_extension(fname)
				print("Found and loaded", fname)
			except commands.ExtensionError as e:
				print("Failed to load", fname, file=sys.stderr)
				traceback.print_exc()

	async def on_ready(self):
		print("Ready!", self.user.name, self.user.id)

	async def close(self):
		cog = self.get_cog("Reddit")
		with open("feeds.json", "w") as f:
			json.dump({
				i: s.to_json()
				for i, s in cog.feeds.items()
			}, f, indent=2, sort_keys=True)

		if self.session:
			await self.session.close()
			self.session = None
		return await super().close()

Rem().run(config.token)
