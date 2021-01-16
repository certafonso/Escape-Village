# external libraries
import discord
import asyncio
from dotenv import load_dotenv
import os
import time
import random

class Client(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.running_games = {}

        # self.bg_task = self.loop.create_task(self.check_clock())

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

        # command to start a game
        if message.content.split()[0] == "-start":    
            await self.start_game(message.author, message.content.split())

        # command to end a game
        if message.content.split()[0] == "-end":     
            await self.end_game(message.guild)
        

        # if type(message.channel) == discord.DMChannel:  # received a dm
        #     channel, message.author = self.user_ingame(message.author)
        #     if channel != None:
        #         await self.running_games[channel]["Game"].on_message(message)

        # else:
        #     if message.content == "-wikigames":             # command to start a game
        #         await self.start_game(message.channel, message.author)  

    async def start_game(self, gamemaster, options):
        """ Starts a game with everyone in the voice channel of the gamemaster """

        # create game dictionary
        game = {}
        game["gamemaster"] = gamemaster
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
                "voice": voice
            })

        self.running_games[str(game["guild"].id)] = game

    async def end_game(self, guild):
        """ Deletes every role and channel created """

        for team in self.running_games[str(guild.id)]["teams"]:
            # move players to the default channel
            for player in team["players"]:
                await player.move_to(self.running_games[str(guild.id)]["default_voice"])

            await team["role"].delete()
            await team["text"].delete()
            await team["voice"].delete()

        del self.running_games[str(guild.id)]



if __name__ == "__main__":

    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')

    client = Client()
    client.run(TOKEN)