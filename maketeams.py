#! /usr/bin/env python
import random
import json
import re
import time
import math
import sys

# input file is JSON data with the following keys: rating, name, in_slack, account_status, date_created, prefers_alt, friends, has_20_games.
data = sys.argv[1]
infile = open(data,'r')
playerdata = json.load(infile)
print "This data was read from file."
infile.close()

class Player:
    pref_score = 0
    team = None
    board = None
    req_met = False
    def __init__(self, name, rating, friends, date, alt):
        self.name = name
        self.rating = rating 
        self.friends = friends
        self.date = date
        self.alt = alt
    def __repr__(self):
        return str((self.name, self.board, self.rating, self.req_met))
    def setPrefScore(self):
        self.pref_score = 0
        for friend in self.friends:
            if friend in self.team.getBoards():
                self.pref_score += 1
            else:
                self.pref_score -= 1
        #player with more than 5 choices can be <5 preference even if all teammates are preferred
    def setReqMet(self):
        for friend in self.friends:
            if friend in self.team.getBoards():
                self.req_met = True
                friend.req_met = True
            else:
                self.req_met = False
class Team:
    def __init__(self):
        self.boards = [None,None,None,None,None,None]
    def __str__(self):
        return str((self.boards, self.team_pref_score, self.getMean()))
    def __repr__(self):
        return "Team:{0}".format(id(self))
    def changeBoard(self, board, new_player):
        #updates the player on a board and updates that player's team attribute
        if self.boards[board]:
            self.boards[board].team = None
        self.boards[board] = new_player
        if new_player.team:
            new_player.team.boards[board] = None
        new_player.team = self
    def getMean(self):
        ratings = [board.rating for board in self.boards]
        mean = sum(ratings) / len(ratings)
        return mean
    def getBoards(self):
        return self.boards
    def getPlayer(self, board):
        return self.boards[board]
    def setTeamPrefScore(self):
        self.team_pref_score = sum([x.pref_score for x in self.boards])

def updatePref(): #update preference scores
    for player in players:
        player.setPrefScore()
    for team in teams:
        team.setTeamPrefScore()
def updateSort(): #based on preference score high to low
    players.sort(key=lambda player: (player.team.team_pref_score, player.pref_score), reverse = False)
    teams.sort(key=lambda team: team.team_pref_score, reverse = False)
    
# put player data into Player objects
players = []
for player in playerdata:
    if player['has_20_games'] and player['in_slack']:
        players.append(Player(player['name'], player['rating'], player['friends'], player['date_created'], player['prefers_alt']))
    else:
        print "{0} skipped".format(player['name'])
players.sort(key=lambda player: player.rating, reverse=True)

# splits list of Player objects into 6 near equal lists, sectioned by rating
avg = len(players) / 6.0
print len(players)
players_split = []
last = 0.0
while round(last) < len(players):
    players_split.append(players[int(round(last)):int(round(last + avg))])
    last += avg
num_teams = int(math.ceil((len(players_split[0])*0.8)/2.0)*2)

# separate preferred alternates into alternates lists
alts_split = [[] for i in range(6)]
for n, board in enumerate(players_split):
    for player in board:
        if player.alt:
            alts_split[n].append(player)
for n, board in enumerate(alts_split):
    for alt in board:
        players_split[n].remove(alt)

# separate latest joining players into alternate lists as required
for n, board in enumerate(players_split):
    board.sort(key=lambda player: player.date)
    alts = board[num_teams:]
    for p in alts:
        alts_split[n].append(p)
    del board[num_teams:]
    board.sort(key=lambda player: player.rating, reverse=True)

players = sum(players_split,[])
#print len(players)
#print num_teams
#print alts_split

# snake draft players into initial teams and update player and team attributes
for board in players_split[1::2]:
    board.reverse()
for n, board in enumerate(players_split):
    for player in board:
        player.board = n
teams = []
for n in xrange(num_teams):
    teams.append(Team())
for n, board in enumerate(players_split):
    for team, player in enumerate(board):
        teams[team].changeBoard(n, player)

# convert players' friends from name to references of the friend's player object
for player in players:
    if player.friends:
        player.friends = re.split("[^a-zA-Z0-9]+", player.friends)
    else:
        player.friends = []
for player in players:
    temp_friends = []
    for friend in player.friends:
        for potentialfriend in players:
            if friend.lower() == potentialfriend.name.lower() and potentialfriend not in temp_friends: # prevent duplicated friend error
                temp_friends.append(potentialfriend)
    player.friends = temp_friends
for player in players:
    for friend in player.friends:
        if friend.board == player.board:
            player.friends.remove(friend)
updatePref()
updateSort()

def swapPlayers(teama, playera, teamb, playerb, board):
    #swap players between teams - ensure players are same board for input
    teama.changeBoard(board,playerb)
    teamb.changeBoard(board,playera)

def testSwap(teama, playera, teamb, playerb, board):
    #try a swap and return the preference change if this swap was made
    prior_pref = teama.team_pref_score + teamb.team_pref_score
    swapPlayers(teama, playera, teamb, playerb, board) #swap players forwards
    updatePref()
    post_pref = teama.team_pref_score + teamb.team_pref_score
    swapPlayers(teama, playerb, teamb, playera, board) #swap players back
    updatePref()
    return post_pref - prior_pref #more positive = better swap

# take player from least happy team
# calculate the overall preference score if player were to swap to each of the preferences' teams or preference swaps into their team.
# swap player into the team that makes the best change to overall preference
# check if the swap has increased the overall preference rating
# if swap made, resort list by preference score and start at the least happy player again
# if no improving swaps are available, go to the next player
# if end of the list reached with no swaps made: stop

p = 0
while p<len(players):
    player = players[p] #least happy player
    friend_swaps = []
    for friend in player.friends:
        #test both swaps for each friend and whichever is better, add the swap ID and score to temp friends list
        if friend.board != player.board and friend.team != player.team:
            #test swap friend to player team (swap1)
            swap1_ID = (friend.team, friend, player.team, player.team.getPlayer(friend.board), friend.board)
            swap1_score = testSwap(*swap1_ID)
            #test swap player to friend team (swap2)
            swap2_ID = (player.team, player, friend.team, friend.team.getPlayer(player.board), player.board)
            swap2_score = testSwap(*swap2_ID)
            friend_swaps.append(max((swap1_score, swap1_ID),(swap2_score, swap2_ID)))
    friend_swaps.sort()
    if friend_swaps and friend_swaps[-1][0] > 0: # there is a swap to make and it improves the preference score
        swapPlayers(*(friend_swaps[-1][1]))
        print friend_swaps[-1]
        updatePref()
        updateSort()
        p = 0
    else: # go to the next player in the list
        p += 1

for player in players:
    player.setReqMet()

for team in teams:
    print team
print "ALTERNATES"
for board in alts_split:
    print board
