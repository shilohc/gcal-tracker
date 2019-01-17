import datetime
import udatetime
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from collections import defaultdict

SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'

def mk_service():
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))
    return service

def get_next_ten_events(service, calendarId='primary'):
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    print('Getting the upcoming 10 events')
    events_result = service.events().list(calendarId=calendarId, timeMin=now,
                                        maxResults=10, singleEvents=True,
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])

def get_prev_week_events(service, calendarId):
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    week_ago = week_ago.isoformat() + 'Z'
    events_result = service.events().list(calendarId = calendarId,
                                        timeMin=week_ago, timeMax=now,
                                        orderBy='startTime',
                                        singleEvents=True).execute()
    events = events_result.get('items', [])
    #if not events:
    #    print('No events found in past week.')
    return events

def sum_event_durations(events):
    duration_sum = datetime.timedelta()
    duration_sum_by_name = defaultdict(datetime.timedelta)
    for event in events:
        # TODO: make sure to exclude all-day events
        try:
            event_start = event['start']['dateTime']
            event_end = event['end']['dateTime']
            duration = udatetime.from_string(event_end) - udatetime.from_string(event_start)
        except KeyError:
            # all-day events have no dateTime
            duration = datetime.timedelta()
        duration_sum += duration
        duration_sum_by_name[event['summary']] += duration
        #print(event['summary'], duration)
    #print("Total:", duration_sum)
    #if sum_by_name:
    #    for name, duration in duration_sum_by_name.items():
    #        print("Total for {}:".format(name), duration)
    return duration_sum, duration_sum_by_name

def print_durations(calendar_name, duration_sum, duration_sum_by_name,
        sum_by_name=True, include_empty_calendars=False):
    #print("Total time of events in calendar {}:".format(calendar_name), duration_sum)
    if duration_sum != datetime.timedelta() or include_empty_calendars:
        print("Total time of events in calendar {}:".format(calendar_name), duration_sum)
    if sum_by_name:
        for n, d in duration_sum_by_name.items():
            if d != datetime.timedelta():
                print(" -> Total time spent on {}:".format(n), d)

def get_prev_week_durations(service, calendar_id, calendar_name,
        sum_by_name=True, include_empty_calendars=False):
    events = get_prev_week_events(service, calendarId=calendar_id)
    duration_sum, duration_sum_by_name = sum_event_durations(events)
    if duration_sum != datetime.timedelta() or include_empty_calendars:
        print("Total time of events in calendar {}:".format(calendar_name), duration_sum)
    if sum_by_name:
        for n, d in duration_sum_by_name.items():
            if d != datetime.timedelta():
                print(" -> Total time spent on {}:".format(n), d)

def get_events_for_range(service, calendar_id, start_time, end_time):
    pass

def get_durations_for_range(service, calendars, start_time, end_time,
        sum_by_name=True, include_empty=False):
    for cal_id, cal_name in calendars.items():
        events = get_events_for_range(service, cal_id, start_time, end_time)
        duration_sum, duration_sum_by_name = sum_event_durations(events)
        if duration_sum != datetime.timedelta() or include_empty:
            print("Total time of events in calendar {}: {}".format(
                cal_name, duration_sum))
        if sum_by_name:
            for n, d in duration_sum_by_name.items():
                if d != datetime.timedelta():
                    print(" -> Total time spent on {}: {}".format(n, d))

def list_calendars(service, showHidden=False):
    calendars = {}
    calendar_list_result = service.calendarList().list(showHidden=showHidden).execute()
    calendar_list = calendar_list_result.get('items', [])

    if not calendar_list:
        print('No calendars found.')
    for calendar in calendar_list:
        #print(calendar['summary'], calendar['id']) #, calendar['description'])
        calendars[calendar['id']] = calendar['summary']
    return calendars

if __name__ == '__main__':
    service = mk_service()
    #list_calendars(service)
    #events = get_prev_week_events(service, calendarId='euit0li3phfo3u1njjqqpn4jmo@group.calendar.google.com')
    #sum_event_durations(events)

    calendars = list_calendars(service)
    print("For the past week:")
    for cal_id, cal_name in calendars.items():
        get_prev_week_durations(service, cal_id, cal_name)
