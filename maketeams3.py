import click
import random
import json
import re
import time
import math
import sys

class Player:
    pref_score = 0
    team = None
    board = None
    req_met = False
    def __init__(self, name, rating, friends, avoid, date, alt, previous_season_alt):
        self.name = name
        self.rating = rating
        self.friends = friends
        self.avoid = avoid
        self.date = date
        self.alt = alt
        self.previous_season_alt = previous_season_alt

    @classmethod
    def player_from_json(cls, player):
        return cls(
            player['name'],
            player['rating'],
            player['friends'],
            player['avoid'],
            player['date_created'],
            player['prefers_alt'],
            player['previous_season_alternate'] == 'alternate'
        )

    def __repr__(self):
        return str((self.name, self.board, self.rating, self.req_met))
    def __lt__(self, other):
        return True
    def setPrefScore(self):
        self.pref_score = 0
        for friend in self.friends:
            if friend in self.team.getBoards():
                self.pref_score += 1
            else:
                self.pref_score -= 1
        for avoid in self.avoid:
            if avoid in self.team.getBoards():
                self.pref_score -= 1
        #player with more than 5 choices can be <5 preference even if all teammates are preferred
    def setReqMet(self):
        self.req_met = False
        if not self.friends:
            self.req_met = None
        for friend in self.friends:
            if friend in self.team.getBoards():
                self.req_met = True

class Team:
    def __init__(self):
        self.boards = [None,None,None,None,None,None]
    def __str__(self):
        return str((self.boards, self.team_pref_score, self.getMean()))
    def __repr__(self):
        return "Team:{0}".format(id(self))
    def __lt__(self, other):
        return True
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

def updatePref(players, teams): #update preference scores
    for player in players:
        player.setPrefScore()
    for team in teams:
        team.setTeamPrefScore()

def updateSort(players, teams): #based on preference score high to low
    players.sort(key=lambda player: (player.team.team_pref_score, player.pref_score), reverse = False)
    teams.sort(key=lambda team: team.team_pref_score, reverse = False)

@click.command()
@click.option('--output', default="readable", type=click.Choice(['json', 'readable']))
@click.option('--players', help='the json file containing the players.', required=True)
def make_teams(players, output):
    # input file is JSON data with the following keys: rating, name, in_slack, account_status, date_created, prefers_alt, friends, avoid, has_20_games.
    with open(players,'r') as infile:
        playerdata = json.load(infile)
    print("This data was read from file.")

    # put player data into Player objects
    players = []
    for player in playerdata:
        if player['has_20_games'] and player['in_slack']:
            players.append(Player.player_from_json(player))
        else:
            print("{0} skipped".format(player['name']))
    players.sort(key=lambda player: player.rating, reverse=True)

    # Split into those that want to be alternates vs those that do not.
    alternates = [p for p in players if p.alt]
    players = [p for p in players if not p.alt]

    # splits list of Player objects into 6 near equal lists, sectioned by rating
    avg = len(players) / 6.0
    players_split = []
    last = 0.0
    while round(last) < len(players):
        players_split.append(players[int(round(last)):int(round(last + avg))])
        last += avg


    min_ratings = [min([p.rating for p in board]) for board in players_split]
    max_ratings = [max([p.rating for p in board]) for board in players_split]
    min_ratings[-1] = 0
    max_ratings[0] = 5000
    board_bounds = list(zip(min_ratings, max_ratings))

    num_teams = int(math.ceil((len(players_split[0])*0.8)/2.0)*2)
    print(f"Targetting {num_teams} teams")

    # separate latest joining players into alternate lists as required
    alts_split = [[] for x in players_split]
    for n, board in enumerate(players_split):
        board.sort(key=lambda player: (0 if player.previous_season_alt else 1, player.date))
        alts_split[n].extend(board[num_teams:])
        del board[num_teams:]
        board.sort(key=lambda player: player.rating, reverse=True)
    for n, (min_rating, max_rating) in enumerate(board_bounds):
        alts_split[n].extend([p for p in alternates if p.rating >= min_rating and p.rating < max_rating])

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
    for n in range(num_teams):
        teams.append(Team())
    for n, board in enumerate(players_split):
        for team, player in enumerate(board):
            teams[team].changeBoard(n, player)

    # convert players' friends and avoid from name to references of the friend's/avoid's player object
    for player in players:
        if player.friends or player.avoid:
            player.friends = re.split("[^-_a-zA-Z0-9]+", player.friends) # separate friends requests into individual usernames - split on any number of non-(alphanumeric, hyphen or underscore)
            player.avoid = re.split("[^-_a-zA-Z0-9]+", player.avoid) # separate avoid requests into individual usernames - split on any number of non-(alphanumeric, hyphen or underscore)
        else:
            player.friends = []
            player.avoid = []
    for player in players:
        temp_friends = []
        for friend in player.friends:
            for potentialfriend in players:
                if friend.lower() == potentialfriend.name.lower() and potentialfriend not in temp_friends: # prevent duplicated friend error
                    temp_friends.append(potentialfriend)
        player.friends = temp_friends

        temp_avoid = []
        for avoid in player.avoid:
            for potentialavoid in players:
                if avoid.lower() == potentialavoid.name.lower() and potentialavoid not in temp_avoid: # prevent duplicated friend error
                    temp_avoid.append(potentialavoid)
        player.avoid = temp_avoid

    #remove friend requests for same board
    for player in players:
        for friend in player.friends:
            if friend.board == player.board:
                player.friends.remove(friend)
    updatePref(players, teams)
    updateSort(players, teams)

    def swapPlayers(teama, playera, teamb, playerb, board):
        #swap players between teams - ensure players are same board for input
        teama.changeBoard(board,playerb)
        teamb.changeBoard(board,playera)

    def testSwap(teama, playera, teamb, playerb, board):
        #try a swap and return the preference change if this swap was made
        prior_pref = teama.team_pref_score + teamb.team_pref_score
        swapPlayers(teama, playera, teamb, playerb, board) #swap players forwards
        updatePref(players, teams)
        post_pref = teama.team_pref_score + teamb.team_pref_score
        swapPlayers(teama, playerb, teamb, playera, board) #swap players back
        updatePref(players, teams)
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
        swaps = []
        for friend in player.friends:
            #test both direction swaps for each friend and whichever is better, add the swap ID and score to temp friends list
            if friend.board != player.board and friend.team != player.team: #board check is redundant due to earlier removal of same board requests
                #test swap friend to player team (swap1)
                swap1_ID = (friend.team, friend, player.team, player.team.getPlayer(friend.board), friend.board)
                swap1_score = testSwap(*swap1_ID)
                #test swap player to friend team (swap2)
                swap2_ID = (player.team, player, friend.team, friend.team.getPlayer(player.board), player.board)
                swap2_score = testSwap(*swap2_ID)
                swaps.append(max((swap1_score, swap1_ID),(swap2_score, swap2_ID)))
        for avoid in player.avoid:
            #test moving player to be avoided to the best preferred team
            if player.team == avoid.team: #otherwise irrelevant
                for swap_team in teams:
                    swap_ID = (avoid.team, avoid, swap_team, swap_team.getPlayer(avoid.board), avoid.board)
                    swap_score = testSwap(*swap_ID)
                    swaps.append((swap_score,swap_ID))
        swaps.sort()
        if swaps and swaps[-1][0] > 0: # there is a swap to make and it improves the preference score
            swapPlayers(*(swaps[-1][1]))
            print(swaps[-1])
            updatePref(players, teams)
            updateSort(players, teams)
            p = 0
        else: # go to the next player in the list
            p += 1

    for player in players:
        player.setReqMet()

    #WIP for upload format for heltour
    jsonoutput = []
    #[{"action":"change-member","team_number":1,"board_number":1,"player":{"name":"lemonworld","is_captain":false,"is_vice_captain":false}}]
    for t, team in enumerate(teams):
        for b, board in enumerate(team.boards):
            pp = {"action":"change-member","team_number":t+1,"board_number":b+1,"player":{"name":board.name,"is_captain":False,"is_vice_captain":False}}
            jsonoutput.append(pp)
    for b, board in enumerate(alts_split):
        print(board)
        for _, pp in enumerate(board):
            pp = {"action":"create-alternate","board_number":b+1,"player_name":pp.name}
            jsonoutput.append(pp)

    if output == "readable":
        print("-{0: <5}--".format("-"*5), end='')
        for x in range(6):
            print("-{0: <27}--".format("-"*27), end='')
        print()
        print(f"Using: {len(players)} players and {len(alternates)} alternates")
        for i, (n, x) in enumerate(reversed(board_bounds)):
            print(f"Board #{i+1} rating range: [{n}, {x})")
        print("TEAMS")
        print(" {0: <5} |".format("Team #"), end='')
        for x in range(6):
            print(" {0: <27} |".format(f"Board #{x+1}"), end='')
        print()
        print("-{0: <5}--".format("-"*5), end='')
        for x in range(6):
            print("-{0: <27}--".format("-"*27), end='')
        print()
        for team_i in range(num_teams):
            print(f" #{team_i+1: <5} |", end='')
            for board_i in range(6):
                team = teams[team_i]
                player = team.boards[board_i]
                short_name = player.name[:20]
                player_name = f"{short_name} ({player.rating})"

                print(f" {player_name: <27} |", end='')
            print()
        print()
        print("ALTERNATES")
        for i in range(6):
            n,x = board_bounds[i]
            print(" {0: <27} |".format(f"Board #{i+1} [{n},{x})"), end='')
        print()
        for x in range(6):
            print("-{0: <27}--".format("-"*27), end='')
        print()
        for player_i in range(max([len(a) for a in alts_split])):
            for board_i in range(6):
                board = alts_split[board_i]
                player_name = ""
                if player_i < len(board):
                    player = board[player_i]
                    short_name = player.name
                    if player.alt:
                        short_name = "*" + player.name[:19]
                    else:
                        short_name = player.name[:20]
                    player_name = f"{short_name} ({player.rating})"
                print(f" {player_name: <27} |", end='')
            print()
    elif output == "json":
        print(json.dumps(jsonoutput))

if __name__ == "__main__":
    make_teams()
