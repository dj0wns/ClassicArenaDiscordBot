import sqlite3
import discord
import asyncio
import random
import os

fpath=os.path.realpath(__file__)
path=os.path.dirname(fpath)
DB_FILE=path+"/local.db"

#Initializes tables and some data in the database if they don't Exist
def init_db():
  sql_commands =[]
  sql_commands.append("PRAGMA foreign_keys = ON;")
  sql_commands.append(""" CREATE TABLE IF NOT EXISTS classes (
                            id integer NOT NULL PRIMARY KEY,
                            name text NOT NULL,
                            color text NOT NULL
                          ); """)
  sql_commands.append(""" INSERT OR IGNORE INTO classes (id, name, color) VALUES
                            (0, "None", "#000000"),
                            (1, "Druid", "#000000"),
                            (2, "Hunter", "#000000"),
                            (3, "Mage", "#000000"),
                            (4, "Priest", "#000000"),
                            (5, "Paladin", "#000000"),
                            (6, "Rogue", "#000000"),
                            (7, "Shaman", "#000000"),
                            (8, "Warlock", "#000000"),
                            (9, "Warrior", "#000000");
                           """ )
  sql_commands.append(""" CREATE TABLE IF NOT EXISTS players (
                            discord_id integer NOT NULL PRIMARY KEY,
                            character_name text UNIQUE DEFAULT NULL,
                            class int NOT NULL DEFAULT 0,
                            joined_at datetime DEFAULT CURRENT_TIMESTAMP,
                            CONSTRAINT fk_class FOREIGN KEY(class) REFERENCES classes(id) ON DELETE SET DEFAULT
                            ) WITHOUT ROWID;""")
  sql_commands.append(""" CREATE TABLE IF NOT EXISTS two_player_teams (
                            id integer NOT NULL PRIMARY KEY,
                            player1 integer NOT NULL,
                            player2 integer NOT NULL,
                            rating integer NOT NULL DEFAULT 1600,
                            team_name text UNIQUE DEFAULT NULL,
                            created_at datetime DEFAULT CURRENT_TIMESTAMP,
                            CONSTRAINT fk_player1 FOREIGN KEY(player1) REFERENCES players(discord_id) ON DELETE CASCADE,
                            CONSTRAINT fk_player2 FOREIGN KEY(player2) REFERENCES players(discord_id) ON DELETE CASCADE,
                            UNIQUE(player1, player2)
                            ); """)
  # Stores information for auto executing leagues
  sql_commands.append(""" CREATE TABLE IF NOT EXISTS two_player_leagues (
                            id integer NOT NULL PRIMARY KEY,
                            has_announced boolean DEFAULT FALSE,
                            has_started boolean DEFAULT FALSE,
                            has_finished boolean DEFAULT FALSE,
                            started_at datetime DEFAULT CURRENT_TIMESTAMP
                            ); """)
  
  # Stores information about the rounds in a league
  sql_commands.append(""" CREATE TABLE IF NOT EXISTS two_player_league_rounds (
                            id integer NOT NULL PRIMARY KEY,
                            league integer NOT NULL,
                            has_started boolean NOT NULL DEFAULT FALSE,
                            start_time datetime NOT NULL,
                            end_time datetime NOT NULL,
                            previous_round integer DEFAULT NULL,
                            next_round integer DEFAULT NULL,
                            CONSTRAINT fk_league FOREIGN KEY(league) REFERENCES two_player_leagues(id) ON DELETE CASCADE,
                            CONSTRAINT fk_previous_round FOREIGN KEY(previous_round) REFERENCES two_player_league_rounds(id) ON DELETE CASCADE,
                            CONSTRAINT fk_next_round FOREIGN KEY(next_round) REFERENCES two_player_league_rounds(id) ON DELETE CASCADE
                            ); """)
  
  # Stores information about the teams entered into a league
  sql_commands.append(""" CREATE TABLE IF NOT EXISTS two_player_league_teams (
                            id integer NOT NULL PRIMARY KEY,
                            league integer NOT NULL,
                            team integer NOT NULL,
                            dropped boolean NOT NULL DEFAULT FALSE,
                            CONSTRAINT fk_league FOREIGN KEY(league) REFERENCES two_player_leagues(id) ON DELETE CASCADE
                            ); """)

  # Stores information about matches, results stored in another table
  sql_commands.append(""" CREATE TABLE IF NOT EXISTS two_player_matches (
                            id integer NOT NULL PRIMARY KEY,
                            team1 integer NOT NULL,
                            team2 integer NOT NULL,
                            league integer DEFAULT NULL,
                            round integer DEFAULT NULL,
                            CONSTRAINT fk_team1 FOREIGN KEY(team1) REFERENCES two_player_teams(id) ON DELETE SET NULL,
                            CONSTRAINT fk_team2 FOREIGN KEY(team2) REFERENCES two_player_teams(id) ON DELETE SET NULL,
                            CONSTRAINT fk_league FOREIGN KEY(league) REFERENCES two_player_leagues(id) ON DELETE SET NULL,
                            CONSTRAINT fk_round FOREIGN KEY(round) REFERENCES two_player_league_rounds(id) ON DELETE SET NULL
                            ); """)

  # Stores results of matches played
  sql_commands.append(""" CREATE TABLE IF NOT EXISTS two_player_match_results (
                            id integer NOT NULL PRIMARY KEY,
                            team1_score integer NOT NULL,
                            team2_score integer NOT NULL,
                            team1_rating integer NOT NULL,
                            team2_rating integer NOT NULL,
                            team1_rating_change integer NOT NULL,
                            team2_rating_change integer NOT NULL,
                            verified text CHECK(verified in("unverified", "rejected", "verified")) DEFAULT "unverified",
                            played_at datetime DEFAULT CURRENT_TIMESTAMP,
                            CONSTRAINT fk_id FOREIGN KEY(id) REFERENCES two_player_matches(id) ON DELETE SET NULL
                            ) WITHOUT ROWID; """)


  try:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for sql_command in sql_commands:
      c.execute(sql_command)
    conn.commit()
  except Exception as e:
    print(e)
  finally:
    conn.close()

### UNIVERSAL SQL FUNCTIONS ###
def connect_and_modify(statement):
  try:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(statement)
    conn.commit()
  except Exception as e:
    print(e)
  finally:
    conn.close()

def connect_and_modify(statement, args):
  try:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(statement, args)
    conn.commit()
  except Exception as e:
    print(e)
  finally:
    conn.close()

def connect_and_return(statement, args):
  try:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if args is None:
      c.execute(statement)
    else:
      c.execute(statement, args)
    return c.fetchall()
  except Exception as e:
    print(e)
  finally:
    conn.close()

### CLASS SQL FUNCTIONS ###
#Returns class id or None if doesnt exist
def get_class_id(class_name):
  class_id = connect_and_return("SELECT id FROM classes WHERE LOWER(name)=LOWER(?)", (class_name,))
  if len(class_id) == 0:
    return None
  return class_id[0][0]

def get_class_name(class_id):
  class_name = connect_and_return("SELECT name FROM classes WHERE id=?", (class_id,))
  if len(class_name) == 0:
    return None
  return class_name[0][0]

### PLAYER SQL FUNCTIONS ###
def add_player(discord_id, character_name, class_id):
  connect_and_modify("INSERT OR IGNORE INTO players(discord_id, character_name, class) VALUES(?,?,?)", (discord_id, character_name, class_id,))

def get_player(discord_id):
  player = connect_and_return("SELECT * FROM players WHERE discord_id=?", (discord_id,))
  if len(player) == 0:
    return None
  return player[0]

def get_players():
  players = connect_and_return("SELECT * FROM players", None)
  if len(players) == 0:
    return None
  return players

def get_player_name(discord_id):
  player = connect_and_return("SELECT character_name FROM players WHERE discord_id=?", (discord_id,))
  if len(player) == 0:
    return None
  return player[0][0]

def set_player_name(discord_id, character_name):
  connect_and_modify("UPDATE players SET character_name = ? WHERE discord_id = ?", (character_name, discord_id,))

def set_player_class(discord_id, character_class):
  class_id = get_class_id(character_class)
  connect_and_modify("UPDATE players SET class = ? WHERE discord_id = ?", (class_id, discord_id,))

### TWO_PLAYER_TEAMS SQL FUNCTIONS ###

def add_twos_team(player1_id, player2_id, name):
  #order id's properly
  if player1_id < player2_id:
    id1 = player1_id
    id2 = player2_id
  else:
    id1 = player2_id
    id2 = player1_id
  connect_and_modify("INSERT OR IGNORE INTO two_player_teams(player1, player2, team_name) VALUES(?,?,?)", (id1, id2, name,))

def set_twos_rating(name,elo):
  return connect_and_modify("UPDATE two_player_teams SET rating=? WHERE LOWER(team_name)=LOWER(?)", (elo,name,))

def get_twos_team(name):
  team = connect_and_return("SELECT * FROM two_player_teams WHERE LOWER(team_name)=LOWER(?)", (name,))
  if len(team) == 0:
    return None
  return team[0]

def get_twos_teams_data():
  return connect_and_return("""SELECT 
                                  a.rating, a.team_name,
                                  b.character_name, c.character_name,
                                  d.name, e.name
                               FROM two_player_teams a
                               JOIN players b ON a.player1 = b.discord_id
                               JOIN players c ON a.player2 = c.discord_id
                               JOIN classes d ON b.class = d.id
                               JOIN classes e ON c.class = e.id
                               GROUP BY a.id
                               ORDER BY a.rating DESC
                               """, None)

def get_twos_teams():
  return connect_and_return("SELECT * FROM two_player_teams ORDER BY rating", None)

def get_twos_team_from_players(player1_id, player2_id):
  #order id's properly
  if player1_id < player2_id:
    id1 = player1_id
    id2 = player2_id
  else:
    id1 = player2_id
    id2 = player1_id
    
  team = connect_and_return("SELECT * FROM two_player_teams WHERE player1=? AND player2=?", (id1, id2,))
  if len(team) == 0:
    return None
  return team[0]

def get_twos_rating(name):
  return connect_and_return("SELECT rating FROM two_player_teams WHERE LOWER(team_name)=LOWER(?)", (name,))[0]

def get_twos_players(name):
  return connect_and_return("SELECT player1,player2 FROM two_player_teams WHERE LOWER(team_name)=LOWER(?)", (name,))[0]

### TWO_PLAYER_MATCHES SQL FUNCTIONS ###
def add_twos_match(team1, team2):
  try:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(" INSERT OR IGNORE INTO two_player_matches(team1, team2) VALUES(?,?)", (team1, team2,))
    c.execute(" SELECT id FROM two_player_matches ORDER BY id DESC LIMIT 1")
    conn.commit()
    match_id = c.fetchone()
    if len(match_id) == 0:
      return None
    return match_id[0]
  except Exception as e:
    print(e)
  finally:
    conn.close()

def get_twos_matches():
  return connect_and_return("""SELECT
                                  a.id, a.league, a.round,
                                  c.team_name, d.team_name,
                                  b.team1_score, b.team2_score,
                                  b.team1_rating, b.team2_rating,
                                  b.team1_rating_change, b.team2_rating_change,
                                  b.played_at, b.verified
                               FROM two_player_matches a
                               JOIN two_player_match_results b ON a.id = b.id
                               JOIN two_player_teams c ON a.team1 = c.id
                               JOIN two_player_teams d ON a.team2 = d.id
                               GROUP BY a.id
                               ORDER BY b.played_at DESC
                               LIMIT 20
                               """, None)

### TWO_PLAYER_MATCH_RESULTS SQL FUNCTIONS ###
def add_twos_match_result(match_id, team1_score, team2_score, team1_rating, team2_rating, team1_rating_change, team2_rating_change):
  connect_and_modify("""
      INSERT OR IGNORE INTO two_player_match_results(
          id, 
          team1_score, 
          team2_score, 
          team1_rating, 
          team2_rating, 
          team1_rating_change, 
          team2_rating_change)
      VALUES(?,?,?,?,?,?,?) """, 
      (match_id, team1_score, team2_score, team1_rating, team2_rating, team1_rating_change, team2_rating_change))


### TWO_PLAYER_LEAGUE SQL FUNCTIONS ###

def create_leauge_and_rounds(sign_ups_close, number_of_rounds, round_duration):
  try:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(" INSERT OR IGNORE INTO two_player_leagues(has_announced) VALUES(FALSE)")
    c.execute(" SELECT id FROM two_player_leagues ORDER BY id DESC LIMIT 1")
    league_id = c.fetchone()
    #TODO Create and link rounds
    conn.commit()
  except Exception as e:
    print(e)
  finally:
    conn.close()
  
  None

def get_next_unstarted_rounds():
  return connect_and_return(""" SELECT * FROM two_player_league_rounds
                                WHERE has_started IS FALSE
                                  AND start_time < CURRENT_TIMESTAMP
                            """, None)
