import caldav
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import dateparser
import re
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--url', type=str, help="CalDAV url", required=True)
parser.add_argument('--username', type=str, help="login", required=True)
parser.add_argument('--password', type=str, help="password", required=True)
parser.add_argument('--davname', type=str, help="CalDAV name", default='ici-grenoble')
args = parser.parse_args()

def get_description(url):

    if not url or url == "":
        return ""

    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        return ""

    print(f'Fetching: {url}')

    soup = BeautifulSoup(r.content, 'html5lib')
    div = soup.find('div', attrs = {'class':'contenu'})
    desc = div.get_text(" ", strip=True)

    return desc


def get_events():

    events = []

    for i in range(1,10):
        url = f"https://www.ici-grenoble.org/agenda?page={i}"
        r = requests.get(url)

        if r.status_code != requests.codes.ok:
            break

        soup = BeautifulSoup(r.content, 'html5lib')
        evt_div = soup.find('div', attrs = {'class':'events-list is-all-events'})

        for p_date in evt_div.findAll('p', attrs = {'class':'mt-3 mb-1 date'}):
            day,month,year,hour,minute,summ,desc,stime,sdate = [None]*9
            sdate = p_date.string.strip()
            
            for p_evt in p_date.find_all_next('p'):
                if ' '.join(p_evt['class']) != 'mt-2 mb-2':
                    break

                s = ''.join(p_evt.strings).strip().split(':')
                m = re.match(r'(\d+h\d+)', s[0])
                if m :
                    stime = m.group(1).strip()
                
                summ = s[1].strip()

                if stime:
                    s = stime.split('h')
                    hour, minute = int(s[0]), int(s[1])

                dt = dateparser.parse(' '.join(sdate.split(' ')[1:])).date()
                day, month, year = dt.day, dt.month, dt.year
                curl = f'https://www.ici-grenoble.org{p_evt.a["href"].strip()}'
                desc = get_description(curl)

                events.append((day,month,year,hour,minute,summ,desc))

    return events

# --------------------------------------------------------------------------------------------------

with caldav.DAVClient(url=args.url, username=args.username, password=args.password) as client:
    p = client.principal()

    try:
        c = p.calendar(args.davname)
        c.delete()
    finally:
        c = p.make_calendar(args.davname)
    
    for day,month,year,hour,minute,summ,desc in get_events():
        print(f'Adding: {summ}')
        if hour:
            c.save_event(dtstart=datetime(year=year,month=month,day=day,hour=hour,minute=minute),
                         dtend=datetime(year=year,month=month,day=day,hour=hour+1,minute=minute),
                         summary=summ, description=desc)
        else:
            c.save_event(dtstart=datetime(year=year,month=month,day=day),
                         dtend=datetime(year=year,month=month,day=day),
                         summary=summ,description=desc)