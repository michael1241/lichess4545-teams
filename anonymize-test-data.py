import click
import random
import json



@click.command()
@click.option('--players', help='the json file containing the players.', required=True)
def run(players):

    with open(players,'r') as infile:
        players = json.load(infile)

    names = [p['name'] for p in players]

    for i, name in enumerate(names):
        for player in players:
            replaceName = 'p{}'.format(i)
            if player['name'] == name:
                player['name'] = replaceName
            player['friends'] = player['friends'].replace(name, replaceName)

    ratings = [player['rating'] for player in players]
    random.shuffle(ratings)
    for player, rating in zip(players, ratings):
        player['rating'] = rating

    print(json.dumps(players))


if __name__ == "__main__":
    run()
