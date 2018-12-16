import click
import random
import json
import re
from functools import partial


@click.command()
@click.option('--players', help='the json file containing the players.', required=True)
def run(players):

    with open(players,'r') as infile:
        players = json.load(infile)

    names = [p['name'] for p in players]
    for i, name in enumerate(names):
        replaceName = 'p{}'.format(i)
        replaceNameInString = partial(re.sub,
                                      r"\b{}\b".format(name),
                                      replaceName)
        for player in players:
            if player['name'] == name:
                player['name'] = replaceName
            player['friends'] = replaceNameInString(player['friends'])
            player['avoid'] = replaceNameInString(player['avoid'])

    ratings = [player['rating'] for player in players]
    random.shuffle(ratings)
    for player, rating in zip(players, ratings):
        player['rating'] = rating

    print(json.dumps(players, indent=4))


if __name__ == "__main__":
    run()
