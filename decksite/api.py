from flask import Response, request, session, url_for

from decksite import APP, auth, league
from decksite.data import card as cs
from decksite.data import competition as comp
from decksite.data import deck, guarantee, match
from decksite.data import person as ps
from magic import oracle, rotation
from shared import dtutil
from shared.pd_exception import DoesNotExistException, TooManyItemsException
from shared_web.api import (generate_error, process_github_webhook,
                            return_json, validate_api_key)


@APP.route('/api/decks/<deck_id>/')
def deck_api(deck_id):
    blob = deck.load_deck(deck_id)
    return return_json(blob)

@APP.route('/api/competitions/<competition_id>/')
def competition_api(competition_id):
    return return_json(comp.load_competition(competition_id))

@APP.route('/api/league/')
def league_api():
    return return_json(league.active_league())

@APP.route('/api/person/<person>/')
def person_api(person):
    try:
        p = ps.load_person(person)
        p.decks = url_for('person_decks_api', person=person)
        p.head_to_head = url_for('person_h2h_api', person=person)
        return return_json(p)
    except DoesNotExistException:
        return return_json(generate_error('NOTFOUND', 'Person does not exist'))

@APP.route('/api/person/<person>/decks/')
def person_decks_api(person):
    p = ps.load_person(person)
    return return_json(p.decks)

@APP.route('/api/person/<person>/h2h/')
def person_h2h_api(person):
    p = ps.load_person(person)
    return return_json(p.head_to_head)

@APP.route('/api/league/run/<person>')
def league_run_api(person):
    decks = league.active_decks_by(person)
    if len(decks) == 0:
        return return_json(None)

    run = guarantee_at_most_one_or_retire(decks)

    decks = league.active_decks()
    already_played = [m.opponent_deck_id for m in match.get_matches(run)]
    run.can_play = [d.person for d in decks if d.person != person and d.id not in already_played]

    return return_json(run)

@APP.route('/api/league/drop/<person>', methods=['POST'])
def drop(person):
    error = validate_api_key()
    if error:
        return error

    decks = league.active_decks_by(person)
    if len(decks) == 0:
        return return_json(generate_error('NO_ACTIVE_RUN', 'That person does not have an active run'))

    run = guarantee.exactly_one(decks)

    league.retire_deck(run)
    result = {'success':True}
    return return_json(result)

@APP.route('/api/rotation/')
def rotation_api():
    now = dtutil.now()
    diff = rotation.next_rotation() - now
    result = {
        'last': rotation.last_rotation_ex(),
        'next': rotation.next_rotation_ex(),
        'diff': diff.total_seconds(),
        'friendly_diff': dtutil.display_time(diff.total_seconds())
    }
    return return_json(result)

@APP.route('/api/cards/')
def cards_api():
    return return_json(cs.played_cards())

@APP.route('/api/card/<card>/')
def card_api(card):
    return return_json(oracle.load_card(card))

@APP.route('/api/sitemap/')
def sitemap():
    urls = [url_for(rule.endpoint) for rule in APP.url_map.iter_rules() if 'GET' in rule.methods and len(rule.arguments) == 0]
    return return_json(urls)

@APP.route('/api/admin/')
def admin():
    return return_json(session.get('admin'))

@APP.route('/api/intro/')
def intro():
    return return_json(not request.cookies.get('hide_intro', False) and not auth.hide_intro())

@APP.route('/api/intro/', methods=['POST'])
def hide_intro():
    r = Response(response='')
    r.set_cookie('hide_intro', value=str(True), expires=dtutil.dt2ts(dtutil.now()) + 60 *  60 * 24 * 365 * 10)
    return r

@APP.route('/api/gitpull', methods=['POST'])
def gitpull():
    return process_github_webhook()

@APP.route('/api/status/')
@auth.load_person
def person_status():
    r = {
        'mtgo_username': auth.mtgo_username(),
        'discord_id': auth.discord_id(),
        'admin': session.get('admin', False)
        }
    if auth.mtgo_username():
        d = guarantee_at_most_one_or_retire(league.active_decks_by(auth.mtgo_username()))
        if d is not None:
            r['deck'] = {'name': d.name, 'url': url_for('deck', deck_id=d.id), 'wins': d.get('wins', 0), 'losses': d.get('losses', 0)}
    return return_json(r)

def guarantee_at_most_one_or_retire(decks):
    try:
        run = guarantee.at_most_one(decks)
    except TooManyItemsException:
        league.retire_deck(decks[0])
        run = decks[1]
    return run
