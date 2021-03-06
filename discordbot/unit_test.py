import os

from discordbot import command, emoji
from magic import fetcher_internal, image_fetcher, oracle
from magic.models.card import Card
from shared import configuration


# Check that we can fetch card images.
def test_imagedownload() -> None:
    filepath = '{dir}/{filename}'.format(dir=configuration.get('image_dir'), filename='island.jpg')
    if fetcher_internal.acceptable_file(filepath):
        os.remove(filepath)
    c = [oracle.load_card('Island')]
    assert image_fetcher.download_image(c) is not None

# Check that we can fall back to the Gatherer images if all else fails.
# Note: bluebones doesn't have Nalathni Dragon, while Gatherer does, which makes it useful here.
def test_fallbackimagedownload() -> None:
    filepath = '{dir}/{filename}'.format(dir=configuration.get('image_dir'), filename='nalathni-dragon.jpg')
    if fetcher_internal.acceptable_file(filepath):
        os.remove(filepath)
    c = [oracle.load_card('Nalathni Dragon')]
    assert image_fetcher.download_image(c) is not None

# Check that we can succesfully fail at getting an image.
def test_noimageavailable() -> None:
    c = Card({'name': "Barry's Land", 'id': 0, 'multiverseid': 0, 'names': "Barry's Land"})
    assert image_fetcher.download_image([c]) is None

# Search for a single card via full name,
def test_solo_query() -> None:
    names = command.parse_queries('[Gilder Bairn]')
    assert len(names) == 1
    assert names[0] == 'gilder bairn'
    results = command.results_from_queries(names)
    assert len(results) == 1

# Two cards, via full name
def test_double_query() -> None:
    names = command.parse_queries('[Mother of Runes] [Ghostfire]')
    assert len(names) == 2
    results = command.results_from_queries(names)
    assert len(results) == 2

# The following two sets assume that Ertai is a long dead character, and is getting no new cards.
# If wizards does an Invasion block throwback in some supplemental product, they may start failing.
def test_legend_query() -> None:
    names = command.parse_queries('[Ertai]')
    assert len(names) == 1
    results = command.results_from_queries(names)[0][0]
    assert len(results.get_ambiguous_matches()) == 2

def test_partial_query() -> None:
    names = command.parse_queries("[Ertai's]")
    assert len(names) == 1
    results = command.results_from_queries(names)[0][0]
    assert len(results.get_ambiguous_matches()) == 3

def test_legality_emoji() -> None:
    legal_cards = oracle.legal_cards()
    assert len(legal_cards) > 0
    legal_card = oracle.load_card('island')
    assert emoji.legal_emoji(legal_card) == ':white_check_mark:'
    illegal_card = oracle.load_card('black lotus')
    assert emoji.legal_emoji(illegal_card) == ':no_entry_sign:'
    assert emoji.legal_emoji(illegal_card, True) == ':no_entry_sign: (not legal in PD)'

def test_accents() -> None:
    c = oracle.load_card('Lim-Dûl the Necromancer')
    assert c is not None
    c = oracle.load_card('Séance')
    assert c is not None
    c = oracle.load_card('Lim-Dul the Necromancer')
    assert c is not None
    c = oracle.load_card('Seance')
    assert c is not None

def test_aether() -> None:
    c = oracle.load_card('aether Spellbomb')
    assert c is not None

def test_split_cards() -> None:
    cards = oracle.load_cards(['Armed // Dangerous'])
    assert len(cards) == 1
    assert image_fetcher.download_image(cards) is not None
    names = command.parse_queries('[Toil // Trouble]')
    assert len(names) == 1
    results = command.results_from_queries(names)
    assert len(results) == 1
