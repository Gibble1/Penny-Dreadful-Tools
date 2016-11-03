from decksite.data import deck

from magic import legality, oracle

def test_legal_formats():
    swamp = oracle.load_card('Swamp')
    think_twice = oracle.load_card('Think Twice')
    fork = oracle.load_card('Fork')

    d = deck.Deck({'id': 0})
    d.maindeck = [{'n': 59, 'card': swamp}]
    d.sideboard = []
    assert len(d.all_cards()) == 59
    formats = legality.legal_formats(d)
    assert len(formats) == 0

    d.maindeck = [{'n': 60, 'card': swamp}]
    formats = legality.legal_formats(d)
    assert 'Penny Dreadful' in formats
    assert 'Legacy' in formats

    d.maindeck = [{'n': 55, 'card': swamp}, {'n': 5, 'card': think_twice}]
    formats = legality.legal_formats(d)
    assert len(d.all_cards()) == 60
    assert len(legality.legal_formats(d)) == 0

    d.maindeck = [{'n': 56, 'card': swamp}, {'n': 4, 'card': think_twice}]
    formats = legality.legal_formats(d)
    assert 'Legacy' in formats
    assert 'Modern' in formats

    d.sideboard = [{'n': 15, 'card': swamp}, {'n': 1, 'card': think_twice}]
    formats = legality.legal_formats(d)
    assert len(legality.legal_formats(d)) == 0

    d.maindeck = [{'n': 56, 'card': swamp}, {'n': 4, 'card': fork}]
    d.sideboard = [{'n': 15, 'card': swamp}]
    formats = legality.legal_formats(d)
    assert 'Legacy' in formats
    assert 'Modern' not in formats
