import datetime
import re

import card
import database
import fetcher

CARD_IDS = {}
FORMAT_IDS = {}
DATABASE = database.DATABASE

def layouts():
    return ['normal', 'meld', 'split', 'phenomenon', 'token', 'vanguard', 'double-faced', 'plane', 'flip', 'scheme', 'leveler']

def initialize():
    current_version = fetcher.version()
    if current_version > DATABASE.version():
        print('Database update required')
        update_database(str(current_version))
    aliases = fetcher.card_aliases()
    if DATABASE.alias_count() != len(aliases):
        print('Card alias update required')
        update_card_aliases(aliases)

def search(query):
    # 260 makes 'Odds/Ends' match 'Odds // Ends' so that's what we're using for our spellfix1 threshold here.
    sql = """
        {base_select}
        HAVING GROUP_CONCAT(face_name, ' // ') IN (SELECT word FROM fuzzy WHERE word MATCH ? AND distance <= 260)
            OR SUM(CASE WHEN face_name IN (SELECT word FROM fuzzy WHERE word MATCH ? AND distance <= 260) THEN 1 ELSE 0 END) > 0
        ORDER BY pd_legal DESC, name
    """.format(base_select=base_select())
    print(sql)
    query = '*{query}*'.format(query=query)
    rs = DATABASE.execute(sql, [query, query])
    return [card.Card(r) for r in rs]

def base_select(where_clause='(1 = 1)'):
    return """SELECT
        id,
        layout,
        CASE WHEN layout = 'meld' OR layout = 'double-faced' THEN
            GROUP_CONCAT(CASE WHEN position = 1 THEN face_name ELSE '' END, '')
        ELSE
            GROUP_CONCAT(face_name , ' // ' )
        END AS name,
        GROUP_CONCAT(face_name, '|') AS names,
        CASE
            WHEN layout IN ('split') AND `text` LIKE '%Fuse (You may cast one or both halves of this card from your hand.)%' THEN
                GROUP_CONCAT(mana_cost, '')
            WHEN layout IN ('split') THEN
                NULL
            ELSE
                GROUP_CONCAT(CASE WHEN position = 1 THEN mana_cost ELSE '' END, '')
        END AS mana_cost,
        SUM(cmc) AS cmc,
        GROUP_CONCAT(CASE WHEN position = 1 THEN power ELSE '' END, '') AS power,
        GROUP_CONCAT(CASE WHEN position = 1 THEN toughness ELSE '' END, '') AS toughness,
        GROUP_CONCAT(CASE WHEN position = 1 THEN loyalty ELSE '' END, '') AS loyalty,
        GROUP_CONCAT(CASE WHEN position = 1 THEN type ELSE '' END, '') AS type,
        GROUP_CONCAT(CASE WHEN position = 1 THEN type ELSE '' END, '') AS type,
        GROUP_CONCAT(`text`, '\n-----\n') AS `text`,
        GROUP_CONCAT(CASE WHEN position = 1 THEN type ELSE '' END, '') AS type,
        GROUP_CONCAT(CASE WHEN position = 1 THEN hand ELSE '' END, '') AS hand,
        GROUP_CONCAT(CASE WHEN position = 1 THEN life ELSE '' END, '') AS life,
        GROUP_CONCAT(CASE WHEN position = 1 THEN starter ELSE '' END, '') AS starter,
        alias
        FROM
            (SELECT c.id, c.pd_legal, {card_props}, {face_props}, f.name AS face_name, f.position, f.name_ascii, ca.alias
            FROM card AS c
            INNER JOIN face AS f ON c.id = f.card_id
            LEFT OUTER JOIN card_alias AS ca ON c.id = ca.card_id
            ORDER BY f.card_id, f.position)
        WHERE id IN (SELECT c.id FROM card AS c INNER JOIN face AS f ON c.id = f.card_id WHERE {where_clause})
        GROUP BY id
        """.format(where_clause=where_clause,
                   card_props=(', '.join(prop for prop in card.card_properties())),
                   face_props=(', '.join(prop for prop in card.face_properties() if prop not in ['name'])))

def get_legal_cards(force=False):
    new_list = ['']
    try:
        new_list = fetcher.legal_cards(force)
    except fetcher.FetchException:
        pass
    if new_list == ['']:
        new_list = [r['name'].lower() for r in DATABASE.execute("SELECT GROUP_CONCAT(name, ' // ') AS name FROM card AS c INNER JOIN face AS f ON c.id = f.card_id WHERE pd_legal = 1 GROUP BY c.id")]
        if len(new_list) == 0:
            new_list = fetcher.legal_cards(force=True)
            DATABASE.execute('UPDATE card SET pd_legal = 0')
            DATABASE.execute('UPDATE card SET pd_legal = 1 WHERE LOWER(name) IN (' + ', '.join(database.escape(name) for name in new_list) + ')')
    else:
        DATABASE.execute('UPDATE card SET pd_legal = 0')
        DATABASE.execute('UPDATE card SET pd_legal = 1 WHERE id IN (SELECT card_id FROM face WHERE LOWER(name) IN (' + ', '.join(database.escape(name) for name in new_list) + '))')
    return new_list

def update_database(new_version):
    DATABASE.execute('BEGIN TRANSACTION')
    DATABASE.execute('DELETE FROM version')
    cards = fetcher.all_cards()
    for _, c in cards.items():
        insert_card(c)
    sets = fetcher.all_sets()
    for _, s in sets.items():
        insert_set(s)
    check_layouts() # Check that the hardcoded list of layouts we're about to use is still valid.
    # mtgjson thinks that lands have a CMC of NULL so we'll work around that here.
    DATABASE.execute("UPDATE face SET cmc = 0 WHERE cmc IS NULL AND card_id IN (SELECT id FROM card WHERE layout IN ('normal', 'double-faced', 'flip', 'leveler', 'token', 'split'))")
    rs = DATABASE.execute('SELECT id, name FROM rarity')
    for row in rs:
        DATABASE.execute('UPDATE printing SET rarity_id = ? WHERE rarity = ?', [row['id'], row['name']])
    update_fuzzy_matching()
    DATABASE.execute('INSERT INTO version (version) VALUES (?)', [new_version])
    DATABASE.execute('COMMIT')

def update_card_aliases(aliases):
    DATABASE.execute('DELETE FROM card_alias', [])
    for alias, name in aliases:
        card_id = DATABASE.value('SELECT card_id FROM face WHERE name = ?', [name])
        if card_id is not None:
            DATABASE.execute('INSERT INTO card_alias (card_id, alias) VALUES (?, ?)', [card_id, alias])
        else:
            print("no card found named " + name + " for alias " + alias)

def update_fuzzy_matching():
    DATABASE.execute('DROP TABLE IF EXISTS fuzzy')
    DATABASE.execute('CREATE VIRTUAL TABLE IF NOT EXISTS fuzzy USING spellfix1')
    # BAKERT this does not order split card names correctly
    DATABASE.execute("""INSERT INTO fuzzy (word, rank)
        SELECT GROUP_CONCAT(name, ' // '), pd_legal
        FROM (SELECT f.name, c.pd_legal, f.card_id FROM card AS c INNER JOIN face AS f ON c.id = f.card_id ORDER BY card_id, position)
        GROUP BY card_id
    """)
    DATABASE.execute('INSERT INTO fuzzy (word, rank) SELECT f.name, c.pd_legal FROM face AS f INNER JOIN card AS c ON f.card_id = c.id WHERE f.name NOT IN (SELECT word FROM fuzzy)')

def insert_card(c):
    name = card_name(c)
    try:
        card_id = CARD_IDS[name]
    except KeyError:
        sql = 'INSERT INTO card ('
        sql += ', '.join(prop for prop in card.card_properties())
        sql += ') VALUES ('
        sql += ', '.join('?' for prop in card.card_properties())
        sql += ')'
        values = [c.get(database2json(prop)) for prop in card.card_properties()]
        # database.execute commits after each statement, which we want to avoid while inserting cards
        DATABASE.database.execute(sql, values)
        card_id = DATABASE.value('SELECT last_insert_rowid()')
        CARD_IDS[name] = card_id
    sql = 'INSERT INTO face ('
    sql += ', '.join(prop for prop in card.face_properties())
    sql += ', name_ascii, card_id, position'
    sql += ') VALUES ('
    sql += ', '.join('?' for prop in card.face_properties())
    sql += ', ?, ?, ?'
    sql += ')'
    position = 1 if not c.get('names') else c.get('names', [c.get('name')]).index(c.get('name')) + 1
    values = [c.get(database2json(prop)) for prop in card.face_properties()] + [database.unaccent(c.get('name')), card_id, position]
    DATABASE.database.execute(sql, values)
    for color in c.get('colors', []):
        color_id = DATABASE.value('SELECT id FROM color WHERE name = ?', [color])
        DATABASE.database.execute('INSERT INTO card_color (card_id, color_id) VALUES (?, ?)', [card_id, color_id])
    for symbol in c.get('colorIdentity', []):
        color_id = DATABASE.value('SELECT id FROM color WHERE symbol = ?', [symbol])
        DATABASE.database.execute('INSERT INTO card_color_identity (card_id, color_id) VALUES (?, ?)', [card_id, color_id])
    for supertype in c.get('supertypes', []):
        DATABASE.database.execute('INSERT INTO card_supertype (card_id, supertype) VALUES (?, ?)', [card_id, supertype])
    for subtype in c.get('subtypes', []):
        DATABASE.database.execute('INSERT INTO card_subtype (card_id, subtype) VALUES (?, ?)', [card_id, subtype])
    for info in c.get('legalities', []):
        format_id = get_format_id(info['format'], True)
        DATABASE.database.execute('INSERT INTO card_legality (card_id, format_id, legality) VALUES (?, ?, ?)', [card_id, format_id, info['legality']])

def insert_set(s) -> None:
    sql = 'INSERT INTO `set` ('
    sql += ', '.join(prop for prop in card.set_properties())
    sql += ') VALUES ('
    sql += ', '.join('?' for prop in card.set_properties())
    sql += ')'
    values = [date2int(s.get(underscore2camel(prop))) for prop in card.set_properties()]
    # database.execute commits after each statement, which we want to
    # avoid while inserting sets
    DATABASE.database.execute(sql, values)
    set_id = DATABASE.value('SELECT last_insert_rowid()')
    for c in s.get('cards', []):
        card_id = CARD_IDS[card_name(c)]
        sql = 'INSERT INTO printing (card_id, set_id, '
        sql += ', '.join(prop for prop in card.printing_properties())
        sql += ') VALUES (?, ?, '
        sql += ', '.join('?' for prop in card.printing_properties())
        sql += ')'
        values = [card_id, set_id] + [c.get(database2json(prop)) for prop in card.printing_properties()]
        DATABASE.database.execute(sql, values)

def get_format_id(name, allow_create=False):
    if len(FORMAT_IDS) == 0:
        rs = DATABASE.execute('SELECT id, name FROM format')
        for row in rs:
            FORMAT_IDS[row['name']] = row['id']
    if name not in FORMAT_IDS.keys() and allow_create:
        DATABASE.execute('INSERT INTO format (name) VALUES (?)', [name])
        FORMAT_IDS[name] = DATABASE.value('SELECT last_insert_rowid()')
    if name not in FORMAT_IDS.keys():
        return None
    return FORMAT_IDS[name]

def check_layouts():
    rs = DATABASE.execute('SELECT DISTINCT layout FROM card')
    if sorted([row['layout'] for row in rs]) != sorted(layouts()):
        print('WARNING. There has been a change in layouts. The update to 0 CMC may no longer be valid.')

def get_printings(generalized_card: card.Card):
    sql = 'SELECT ' + (', '.join(property for property in card.printing_properties())) \
        + ' FROM printing ' \
        + ' WHERE card_id = ? '
    rs = DATABASE.execute(sql, [generalized_card.id])
    return [card.Printing(r) for r in rs]

def database2json(propname: str) -> str:
    if propname == "system_id":
        propname = "id"
    return underscore2camel(propname)

def underscore2camel(s):
    return re.sub(r'(?!^)_([a-zA-Z])', lambda m: m.group(1).upper(), s)

def date2int(s):
    try:
        dt = datetime.datetime.strptime(str(s), '%Y-%m-%d')
        return dt.replace(tzinfo=datetime.timezone.utc).timestamp()
    except ValueError:
        return s

def card_name(c):
    return ' // '.join(c.get('names', [c.get('name')]))

initialize()
