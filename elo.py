import math

K_FACTOR = 20.
PERFORMANCE_CONSTANT=400.

def calculate_new_rating(team1_rating, team2_rating, team1_score, team2_score):
  if (team1_score > team2_score):
    winner_rating = team1_rating
    loser_rating = team2_rating
  elif (team1_score < team2_score):
    winner_rating = team2_rating
    loser_rating = team1_rating
  else:
    return
    #Tie so use different logic

  #no partial points, winner of the series takes all
  winner_expectation, loser_expectation = expected_score(winner_rating, loser_rating)
  winner_difference = 1.-winner_expectation
  loser_difference = 0.-loser_expectation
  new_winner_rating = round(winner_rating + winner_difference * K_FACTOR)
  new_loser_rating = round(loser_rating + loser_difference * K_FACTOR)
  
  #make sure to return team1's rating first
  if (team1_score > team2_score):
    return new_winner_rating, new_loser_rating
  else:
    return new_loser_rating, new_winner_rating

def expected_score(rating1, rating2):
  QA = pow(10., float(rating1)/PERFORMANCE_CONSTANT)
  QB = pow(10., float(rating2)/PERFORMANCE_CONSTANT)
  expectation = QA/(QA+QB)
  return expectation, 1.-expectation
