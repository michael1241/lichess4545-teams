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
        boundary = r"[^-_a-zA-Z0-9]"
        replaceNameInString = partial(re.sub,
                                      r"((?<={1})|^){0}((?={1})|$)".format(name, boundary),
                                      replaceName)
        for player in players:
            if player['name'] == name:
                player['name'] = replaceName
            player['friends'] = replaceNameInString(player['friends'])
            player['avoid'] = replaceNameInString(player['avoid'])

    def removeJunk(s):
        pattern = r".*?(p\d+)"
        s = re.sub(pattern, r" \1", s)
        s = re.sub(r"\D+$", '', s)
        s = re.sub(r"^[^p]+", '', s)
        return s

    for player in players:
        player['friends'] = removeJunk(player['friends'])
        player['avoid'] = removeJunk(player['avoid'])

    ratings = [player['rating'] for player in players]
    random.shuffle(ratings)
    for player, rating in zip(players, ratings):
        player['rating'] = rating

    print(players)
    print(json.dumps(players, indent=4))


if __name__ == "__main__":
    run()
