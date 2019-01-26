import click
import random
import json
import re


@click.command()
@click.option('--players', help='the json file containing the players.', required=True)
def run(players):

    with open(players,'r') as infile:
        players = json.load(infile)

    names = [p['name'] for p in players]
    for player in players:
        player['new_friends'] = ''
        player['new_avoid'] = ''

    for i, name in enumerate(names):
        replaceName = 'p{}'.format(i)
        boundary = r"[^-_a-zA-Z0-9]"
        pattern = r"({1}|^){0}({1}|$)".format(name, boundary)

        for player in players:
            if player['name'] == name:
                player['name'] = replaceName
            if re.search(pattern, player['friends'], re.I):
                player['new_friends'] = player['new_friends'] + " " + replaceName
            if re.search(pattern, player['avoid'], re.I):
                player['new_avoid'] = player['new_avoid'] + " " + replaceName

    for player in players:
        player['friends'] = player.pop('new_friends').strip()
        player['avoid'] = player.pop('new_avoid').strip()

    ratings = [player['rating'] for player in players]
    random.shuffle(ratings)
    for player, rating in zip(players, ratings):
        player['rating'] = rating

    print(json.dumps(players, indent=4))


if __name__ == "__main__":
    run()
