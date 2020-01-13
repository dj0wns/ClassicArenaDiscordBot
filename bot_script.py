import discord
import asyncio
import random
import os
import datetime
import re

import elo
import sqldb

fpath=os.path.realpath(__file__)
path=os.path.dirname(fpath)
DB_PATH=path+"/local.db"
datetime_format = '%Y-%m-%d %H:%M:%S'
time_conversion_delta = datetime.timedelta(hours=3) #server is 3 hours behind east coast time - our server time
BOT_LEADING_CHAR='$'
MATCHES_TO_DISPLAY=20

def autoUpdateTasks():
  None

async def checkArguments(channel, argsExpected, commandText, tokens):
  if len(tokens) < argsExpected:
    await channel.send(commandText + " requires at least " + str(argsExpected) + " argument" + ("s." if argsExpected > 1 else "."))  
    return False
  else:
    return True

def mention_to_id(channel, client, text):
  #if text is null, then return
  if len(text) == 0:
    return None

  mention_id = re.search('\<\@[^0-9]*([^<>@!]+)\>', text)
  #invalid user
  if mention_id is None:
    return None

  disc_id = mention_id.group(1)
  if client.get_user(int(disc_id)) is None:
    return None
  else:
    return int(disc_id)

async def commands(channel, author, client):
  message=(
           " - " + BOT_LEADING_CHAR + "help - displays this helpful help dialogue\n"
           " - " + BOT_LEADING_CHAR + "register [class] [OPTIONAL character_name] - Adds you as a user, if a character name is not supplied it uses your discord name\n"
           " - " + BOT_LEADING_CHAR + "createteam [@Second Player] [name - only 1 word!] - Creates a two's team named [name] with the person who runs the command and the second player mentioned\n"
           " - " + BOT_LEADING_CHAR + "reportmatch [team 1] [team 2] [team 1 score] [team 2 score] - Reports a match between the two teams where the first team won and the second team lost. You must be a member of one of the teams to report a match.\n"
           " - " + BOT_LEADING_CHAR + "matches [OPTIONAL team name] - Displays the last " + str(MATCHES_TO_DISPLAY) + " matches played by a specific team or all matches.\n"
           " - " + BOT_LEADING_CHAR + "teams - Displays all teams and some details about them.\n"
          )
  embedMessage = discord.Embed()
  embedMessage.add_field(name="Commands", value=message)
  await channel.send(embed=embedMessage)

async def register(channel, author, client, tokens):
  #check if player already exists
  player = sqldb.get_player(author.id)
  if player is not None:
    await channel.send(author.display_name + " is already registed as a " + sqldb.get_class_name(player[2]) + " named " + player[1] + ".")
    return False
  #Check is class name is valid
  class_id = sqldb.get_class_id(tokens[0])
  if class_id is None:
    await channel.send(tokens[0] + " is not a valid class name.")
    return False
  #Check if name is given as an argument
  if len(tokens) > 1:
    name = tokens[1]
  else:
    name = author.display_name
  #Add player to db
  sqldb.add_player(author.id, name, class_id)
  await channel.send(name + " has been added to the database as a " + tokens[0] + ".")
  return True

async def create_twos_team(channel, author, client, tokens):
  #Check if second player is valid
  second_id = mention_to_id(channel, client, tokens[0])
  if second_id is None:
    await channel.send("The second user provided for this team is not a valid user")
    return False

  #Check if both players are registered
  player = sqldb.get_player(author.id)
  if player is None:
    await channel.send(author.display_name + " has not yet registered.")
    return False

  player = sqldb.get_player(second_id)
  if player is None:
    await channel.send(tokens[0] + " has not yet registered.")
    return False

  #Check if team already exists
  team = sqldb.get_twos_team_from_players(author.id, second_id)
  if team is not None:
    await channel.send("A team containing " + author.display_name  + " and " + tokens[0] + " already exists." )
    return False

  #Check if name is too long
  if len(tokens) > 2:
    await channel.send("The supplied name is too long, one word only please")
    return False
    
  #Create team
  name = tokens[1]
  sqldb.add_twos_team(author.id, second_id, name)
  await channel.send("The team '" + name + "' has been created!")
 
async def print_teams(channel, client):
  teams = sqldb.get_twos_teams_data()
  if len(teams) == 0:
    await channel.send("The are no teams currently registered.")
    return True

  message = ""
  for team in teams:
    rating = str(team[0])
    name = str(team[1])
    player1 = team[2]
    player2 = team[3]
    class1 = team[4]
    class2 = team[5]
    message += name
    message += " -- "
    message += player1
    message += "("
    message += class1
    message += ") -- " 
    message += player2
    message += "("
    message += class2
    message += ") -- Rating:  " 
    message += rating
    message += "\n" 
  
  embedMessage = discord.Embed()
  embedMessage.add_field(name="Teams", value=message)
  await channel.send(embed=embedMessage)

async def report_twos_match(channel, author, client, tokens):
  team1_name = tokens[0]
  team2_name = tokens[1]
  team1_score = tokens[2]
  team2_score = tokens[3]

  #Check if team1 exists
  team1 = sqldb.get_twos_team(team1_name)
  if team1 is None:
    await channel.send(team1_name + " is not a valid team name!")
    return False
  
  #Check if team2 exists
  team2 = sqldb.get_twos_team(team2_name)
  if team2 is None:
    await channel.send(team2_name + " is not a valid team name!")
    return False
  
  #check if reporter is on any of the teams they are reporting for
  if author.id != team1[1] and author.id != team1[2] and author.id != team2[1] and author.id != team2[2]:
    await channel.send(author.display_name + " is not a member of any of the teams they are reporting on!")
    return False
   
  #calculate new elos
  team1_new_elo, team2_new_elo = elo.calculate_new_rating(team1[3], team2[3], team1_score, team2_score)

  #Create match
  match_id = sqldb.add_twos_match(team1[0], team2[0])
  if match_id is None:
    await channel.send("Match could not be added for an unknown reason!")
    return False
    
  #Create results
  sqldb.add_twos_match_result(match_id, team1_score, team2_score, team1_new_elo, team2_new_elo, team1_new_elo - team1[3], team2_new_elo - team2[3])

  #update ratings
  sqldb.set_twos_rating(team1_name, team1_new_elo)
  sqldb.set_twos_rating(team2_name, team2_new_elo)
  
  await channel.send("Match has been recorded and " + team1_name + "'s new rating is " + str(team1_new_elo) + " and " + team2_name + "'s new rating is " + str(team2_new_elo) + "!")
    

async def print_matches(channel, client, tokens):
  matches = sqldb.get_twos_matches()
  if len(matches) == 0:
    await channel.send("The are no matches in the database.")
    return True

  message = ""
  for match in matches:
    match_id = str(match[0])
    league_id = str(match[1])
    round_number = str(match[2])
    name1 = str(match[3])
    name2 = str(match[4])
    score1 = str(match[5])
    score2 = str(match[6])
    rating1 = str(match[7])
    rating2 = str(match[8])
    rating_delta1 = match[9]
    rating_delta2 = match[10]
    match_time = str(match[11])
    verified = str(match[12])
    message += "["
    message += match_id
    message += "] - "
    message += name1
    message += "("
    message += rating1
    message += "("
    if (rating_delta1 > 0):
      message += "+"
    message += str(rating_delta1)
    message += ")" 
    message += ") vs " 
    message += name2
    message += "("
    message += rating2
    message += "("
    if (rating_delta2 > 0):
      message += "+"
    message += str(rating_delta2)
    message += ")" 
    message += ") -  " 
    message += score1
    message += "/" 
    message += score2
    message += " - " 
    message += verified
    message += match_time
    message += "\n" 
  
  embedMessage = discord.Embed()
  embedMessage.add_field(name="Teams", value=message)
  await channel.send(embed=embedMessage)

# user response functions
async def parse_command(client, channel, author, name, content):
  if not content[0] == BOT_LEADING_CHAR: #Not using the bot prefix therefore we dont care
    return False
  #remove leading char
  message = content[1:]
  tokens = message.split()
  operation = tokens[0].lower()
  tokens = tokens[1:] #remove the command from tokens for easier access
  print(operation)
  if operation == "commands" or operation=="help":
    await commands(channel, author, client)
  elif operation == "register" and await checkArguments(channel, 1, operation, tokens):
    await register(channel, author, client, tokens)
  elif operation == "createteam" and await checkArguments(channel, 2, operation, tokens):
    await create_twos_team(channel, author, client, tokens)
  elif operation == "reportmatch" and await checkArguments(channel, 4, operation, tokens):
    await report_twos_match(channel, author, client, tokens)
  elif operation == "matches":
    await print_matches(channel, client, tokens)
  elif operation == "teams":
    await print_teams(channel, client)

#execute script
sqldb.init_db()
token = open(path+"/token", "r").readline()
client = discord.Client()

@client.event
async def on_ready(): #Runs on connection
  print(f'We have logged in as {client.user}')
  await client.change_presence(activity=discord.Game(name="Quack"))

  while True:
    autoUpdateTasks()

    await asyncio.sleep(60) #wait 60 seconds between rechecking

@client.event
async def on_message(message):
  #Don't respond to self
  if not message.author == client.user:
    try:
      if len(message.content) > 0:
        await parse_command(client, message.channel, message.author, message.author.display_name, message.content)
    except Exception as e:
      print(e)
      await message.channel.send("Exception raised: '" + str(e) + "'\n - Pester Duckie that his bot is broken")
  print(f"{message.channel}: {message.author}: {message.author.name}: {message.content}")

client.run(token.strip())
