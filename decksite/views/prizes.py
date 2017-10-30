import datetime
from dateutil.relativedelta import relativedelta, FR

from magic import tournaments
from shared.container import Container
from shared import dtutil

from decksite.view import View

# pylint: disable=no-self-use
class Prizes(View):
    def __init__(self, competitions):
        self.weeks = []
        weeks = split_by_week(competitions)
        for week in weeks:
            prizes = {}
            if week.end_date > dtutil.now(dtutil.WOTC_TZ):
                pass
            for c in week.competitions:
                for d in c.decks:
                    prizes[d.person] = prizes.get(d.person, 0) + tournaments.prize(d)
            subject = 'Penny Dreadful Prizes for Week Ending {date}'.format(date=week.end_date.strftime('%b %-d'))
            body = '\n'.join(['{username} {prize}'.format(username=k, prize=prizes[k]) for k in sorted(prizes) if prizes[k] > 0])
            self.weeks.append({'subject': subject, 'body': body, 'n': len(week.competitions)})

    def subtitle(self):
        'Weekly Prizes'

def split_by_week(competitions):
    dt = (dtutil.now(dtutil.WOTC_TZ) + relativedelta(weekday=FR(-1))).replace(hour=0, minute=0, second=0)
    weeks = []
    while True:
        week = Container()
        week.start_date = dt
        week.end_date = dt + datetime.timedelta(weeks=1)
        week.competitions = []
        while len(competitions) > 0 and competitions[0].start_date > dt:
            week.competitions = week.competitions + [competitions.pop(0)]
        weeks.append(week)
        dt = dt - datetime.timedelta(weeks=1)
        if len(competitions) == 0:
            break
    return weeks