# external libraries
import discord
import asyncio
from dotenv import load_dotenv
import os
import time
import random
import json
from math import asin, sin, cos, radians, sqrt

class Client(discord.Client):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.running_games = {}
		
		with open("EscapeVillage.json", "r") as json_file:
			self.game = json.load(json_file)

	async def on_ready(self):
		print('Logged in as')
		print(self.user.name)
		print(self.user.id)
		print('------')

	async def on_guild_join(self, guild):
		print("Entered")
		print(guild.name)

	async def on_message(self, message):
		"""Handles messages"""

		if message.author == client.user:
			return

		print(message.attachments)

		if type(message.channel) == discord.DMChannel:  # received a dm
			guild = self.get_guild(message.author)
			if guild != None:

				# command to broadcast
				if message.content.split()[0] == "-say":
					await self.broadcast(guild, " ".join(message.content.split()[1:]))

				# command to end a game
				elif message.content.split()[0] == "-end":	 
					await self.end_game(guild)

		else:
			# command to start a game
			if message.content.split()[0] == "-start":	
				await self.start_game(message.author, message.content.split())

			team = self.check_game_channel(message.channel)

			if team != None:

				# command to submit
				if message.content.split()[0] == "-submit":
					await self.task_submission(message.guild, team, message)

			

	def get_guild(self, gamemaster):
		""" Checks if a user is the gamemaster of some guild, returns the guild."""

		for guild in self.running_games:
			if self.running_games[guild]["gamemaster"] == gamemaster:
				return self.running_games[guild]["guild"]

		return None

	def check_game_channel(self, channel):
		""" Checks if a channel is a game channel"""
		
		try:
			for team in self.running_games[str(channel.guild.id)]["teams"]:
				if team["text"] == channel:
					return team

			return None

		except KeyError:
			return None

	async def start_game(self, gamemaster, options):
		""" Starts a game with everyone in the voice channel of the gamemaster """

		# create game dictionary
		game = {}
		game["gamemaster"] = gamemaster
		await game["gamemaster"].create_dm()
		game["teams"] = []

		# parse options and stuff
		game["n_teams"] = int(options[1])
		game["guild"] = gamemaster.guild

		# get members of the gamemaster voice channel	 
		game["default_voice"] = gamemaster.voice.channel
		players = game["default_voice"].members
		players.remove(gamemaster)

		# split into teams
		random.shuffle(players)
		teams = [players[i::game["n_teams"]] for i in range(game["n_teams"])]

		for i in range(len(teams)):
			# create the role and the channels
			role = await game["guild"].create_role(name=f"Team {i}", mentionable=True)

			overwrites = {
				game["guild"].default_role: discord.PermissionOverwrite(read_messages=False),
				role: discord.PermissionOverwrite(read_messages=True)
			}
			text = await game["guild"].create_text_channel(f"Team {i}", overwrites=overwrites)
			voice = await game["guild"].create_voice_channel(f"Team {i}", overwrites=overwrites)
			
			# add the roles and move players
			await gamemaster.add_roles(role)
			for player in teams[i]:
				await player.add_roles(role)
				await player.move_to(voice)

			# append team to the game
			game["teams"].append({
				"players": teams[i],
				"role": role,
				"text": text,
				"voice": voice,
				"current_stage": 0,
				"current_task": 0,
				"extras_done": []
			})

		self.running_games[str(game["guild"].id)] = game

		for team in game["teams"]:
			await self.send_task(game["guild"], team)

	async def end_game(self, guild):
		""" Deletes every role and channel created """

		await self.broadcast(guild, "The game ended, wait until you are moved again")

		for team in self.running_games[str(guild.id)]["teams"]:
			# move players to the default channel
			for player in team["voice"].members:
				await player.move_to(self.running_games[str(guild.id)]["default_voice"])

			await team["role"].delete()
			await team["text"].delete()
			await team["voice"].delete()

		del self.running_games[str(guild.id)]

	async def broadcast(self, guild, message):
		""" Broadcasts a message to all team text channels"""

		for team in self.running_games[str(guild.id)]["teams"]:
			await team["text"].send(message)

	async def send_task(self, guild, team):
		"""Sends the next task to a team"""

		task = self.game[team["current_stage"]]["tasks"][team["current_task"]]

		message = task["text"]

		# add help text
		if task["type"] == "photo":
			message += "\nDevem submeter uma imagem usando `-submit`"
		elif task["type"] == "int":
			message += "\nDevem submeter um numero inteiro usando `-submit XXX`"
		elif task["type"] == "string":
			message += "\nDevem submeter texto **em minusculas** usando `-submit XXX`"
		elif task["type"] == "location":
			message += "\nDevem submeter as coordenadas do local usando `-submit XX.XXXXX, XX.XXXXX`"

		await team["text"].send(message)

	async def task_submission(self, guild, team, submission):
		"""Handles the submission o a task"""

		current_stage = team["current_stage"]
		current_task = team["current_task"]

		task = self.game[current_stage]["tasks"][current_task]

		accepted = False

		message = ""

		gamemaster = self.running_games[str(guild.id)]["gamemaster"].dm_channel

		# handle the correct type of task
		if task["type"] == "photo":

			await gamemaster.send(f"Submission for task {current_task} of stage {current_stage} from {submission.channel.name}\n" + submission.attachments[0].url)

			accepted = True

			message += "A vossa foto foi aceite."

		elif task["type"] == "int":

			try:
				error = abs(int(submission.content.split()[1]) - task["answer"])
				tolerance = task["tolerance"] 
				
				if error <= tolerance:
					accepted = True
					message += "Resposta aceite!"

				else:
					message += "Resposta errada."
				
				await gamemaster.send(f"Submission for task {current_task} of stage {current_stage} from {submission.channel.name}:\n `{submission.content.split()[1]}` Error: `{error}` Tolerance: `{tolerance}` Accepted: {accepted}")

			except ValueError:
				message += f"{submission.content.split()[1]} não é um numero."
			
		elif task["type"] == "string":
			
			answer = task["answer"]
			guess = " ".join(submission.content.split()[1:])

			if guess == answer:
				accepted = True
				message += "Resposta aceite!"

			else:
				message += "Resposta errada."
			
			await gamemaster.send(f"Submission for task {current_task} of stage {current_stage} from {submission.channel.name}:\n Answer: `{guess}` Correct Answer: `{answer}` Accepted: `{accepted}`")
		
		elif task["type"] == "location":

			guess = " ".join(submission.content.split()[1:])

			coords = guess.split(", ")

			coords = [float(coords[i]) for i in range(2)]

			error = Haversine(coords[0], coords[1], task["lat"], task["lon"])

			tolerance = task["tolerance"]

			if error <= tolerance:
				accepted = True
				message += "Resposta aceite!"

			else:
				message += "Resposta errada."
			
			await gamemaster.send(f"Submission for task {current_task} of stage {current_stage} from {submission.channel.name}:\n Answer: `{guess}` Error: `{error}` Tolerance: `{tolerance}` Accepted: `{accepted}`")

		if accepted:		
			message += "\n A enviar o próximo desafio..."
			team["current_task"] += 1
			
			if team["current_task"] >= len(self.game[team["current_stage"]]["tasks"]):
				team["current_task"] = 0
				team["current_stage"] += 1

		await team["text"].send(message)

		if accepted:
			await self.send_task(guild, team)

def Haversine(lat1, lon1, lat2, lon2):
	""" Calculates the distance in meters between 2 coords """

	earth_radius = 6371000

	lat1 = radians(lat1)
	lat2 = radians(lat2)

	lon1 = radians(lon1)
	lon2 = radians(lon2)

	return 2 * earth_radius * asin(sqrt(sin((lat2 - lat1) / 2)**2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2)**2))

if __name__ == "__main__":

	load_dotenv()
	TOKEN = os.getenv('DISCORD_TOKEN')

	client = Client()
	client.run(TOKEN)