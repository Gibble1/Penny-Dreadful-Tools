import inspect
import json
import os
import random
import string
from typing import Any, Dict, List, Optional, Union, overload

from shared.pd_exception import InvalidArgumentException, InvalidDataException

DEFAULTS = {
    # Array of Pricefile URLs (foil, non-foil).  Used by price_grabber and rotation_script
    'cardhoarder_urls': [],
    # Path to TSV list of card nicknames.  Should never be changed.  Used by magic.
    'card_alias_file': './card_aliases.tsv',
    # Path to chart storage directory.  Used by decksite.
    'charts_dir': './images/charts',
    # mysql database name.  Used by decksite.
    'decksite_database': 'decksite',
    # URL for decksite API calls.  Used by discordbot.
    'decksite_hostname': 'pennydreadfulmagic.com',
    'decksite_port': 80,
    'decksite_protocol': 'https',
    # github credentials.  Used for auto-reporting issues.
    'github_password': None,
    'github_user': None,
    # Discord server id.  Used for admin verification.  Used by decksite.
    'guild_id': '207281932214599682',
    'image_dir': './images',
    'legality_dir': '~/legality/Legality Checker/',
    'logsite_database': 'pdlogs',
    'magic_database': 'cards',
    'mtgotraders_url': None,
    'mysql_host': 'localhost',
    'mysql_passwd': '',
    'mysql_port': 3306,
    'mysql_user': 'pennydreadful',
    'not_pd': '',
    'oauth2_client_id': '',
    'oauth2_client_secret': '',
    'otherbot_commands': '!s,!card,!ipg,!mtr,!cr,!define',
    'pdbot_api_token': lambda: ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(32)),
    'prices_database': 'prices',
    'scratch_dir': '.',
    'slow_fetch': 10.0,
    'slow_page': 10.0,
    'slow_query': 5.0,
    'spellfix': './spellfix',
    'test_vcr_record_mode': 'new_episodes', # https://vcrpy.readthedocs.io/en/latest/usage.html#record-modes
    'to_password': '',
    'to_username': '',
    'tournament_channel_id': '207281932214599682',
    'web_cache': '.web_cache',
    'cse_api_key': None,
    'cse_engine_id': None,
    'whoosh_index_dir': 'whoosh_index',
    'poeditor_api_key': None,
    'league_webhook_id': None,
    'league_webhook_token': None,
}

CONFIG: Dict[str, Any] = {}

def get_optional_str(key: str) -> Optional[str]:
    val = get(key)
    if val is None:
        return None
    if isinstance(val, str):
        return val
    raise fail(key, val, str)

def get_str(key: str) -> str:
    val = get_optional_str(key)
    if val is None:
        raise fail(key, val, str)
    return val

def get_int(key: str) -> int:
    val = get(key)
    if isinstance(val, int):
        return val
    raise fail(key, val, int)

def get_float(key: str) -> Optional[float]:
    val = get(key)
    if val is None:
        return None
    if isinstance(val, float):
        return val
    if isinstance(val, int):
        return write(key, float(val))
    raise fail(key, val, float)

def get_list(key: str) -> List[str]:
    val = get(key)
    if val is None:
        return []
    if isinstance(val, list):
        return val
    raise fail(key, val, List[str])

def get(key: str) -> Optional[Union[str, List[str], int, float]]:
    if key in CONFIG:
        return CONFIG[key]
    try:
        cfg = json.load(open('config.json'))
    except FileNotFoundError:
        cfg = {}
    if key in cfg:
        CONFIG.update(cfg)
        return cfg[key]
    elif key in os.environ:
        cfg[key] = os.environ[key]
    elif key in DEFAULTS:
        # Lock in the default value if we use it.
        cfg[key] = DEFAULTS[key]

        if inspect.isfunction(cfg[key]): # If default value is a function, call it.
            cfg[key] = cfg[key]()
    else:
        raise InvalidArgumentException('No default or other configuration value available for {key}'.format(key=key))

    print('CONFIG: {0}={1}'.format(key, cfg[key]))
    fh = open('config.json', 'w')
    fh.write(json.dumps(cfg, indent=4))
    return cfg[key]

# pylint: disable=unused-argument, function-redefined
@overload
def write(key: str, value: str) -> str:
    pass

# pylint: disable=unused-argument, function-redefined
@overload
def write(key: str, value: int) -> int:
    pass

# pylint: disable=unused-argument, function-redefined
@overload
def write(key: str, value: float) -> float:
    pass

def write(key: str, value: Union[str, List[str], int, float]) -> Union[str, List[str], int, float]:
    try:
        cfg = json.load(open('config.json'))
    except FileNotFoundError:
        cfg = {}

    cfg[key] = value

    print('CONFIG: {0}={1}'.format(key, cfg[key]))
    fh = open('config.json', 'w')
    fh.write(json.dumps(cfg, indent=4, sort_keys=True))
    return cfg[key]

def fail(key: str, val: Any, expected_type: type) -> InvalidDataException:
    return InvalidDataException('Expected a {expected_type} for {key}, got `{val}` ({actual_type})'.format(expected_type=expected_type, key=key, val=val, actual_type=type(val)))
