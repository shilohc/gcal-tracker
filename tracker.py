import datetime
import udatetime
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from collections import defaultdict
import readline

SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'

def mk_service():
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))
    return service

def get_prev_week_events(service, calendarId):
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    week_ago = week_ago.isoformat() + 'Z'
    events_result = service.events().list(calendarId = calendarId,
                                        timeMin=week_ago, timeMax=now,
                                        orderBy='startTime',
                                        singleEvents=True).execute()
    events = events_result.get('items', [])
    return events

def get_events_for_range(service, calendar_id, start_time, end_time):
    # start_time and end_time are rfc3339 compliant strings
    events_result = service.events().list(calendarId = calendar_id,
            timeMin=start_time, timeMax=end_time, orderBy='startTime',
            singleEvents=True).execute()
    events = events_result.get('items', [])
    return events

def sum_event_durations(events):
    duration_sum = datetime.timedelta()
    duration_sum_by_name = defaultdict(datetime.timedelta)
    for event in events:
        try:
            event_start = event['start']['dateTime']
            event_end = event['end']['dateTime']
            duration = udatetime.from_string(event_end) - udatetime.from_string(event_start)
        except KeyError:
            # all-day events have no dateTime
            duration = datetime.timedelta()
        duration_sum += duration
        duration_sum_by_name[event['summary']] += duration
    return duration_sum, duration_sum_by_name

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

def get_durations_for_range(service, start_time, end_time,
        sum_by_name=True, include_empty=False):
    print("From {} to {}:".format(start_time[:10], end_time[:10]))
    calendars = list_calendars(service)
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

def get_simple_time_range(range_name="past_week"):
    start_time = udatetime.utcnow()
    end_time = udatetime.utcnow()
    if range_name == "past_week":
        start_time -= datetime.timedelta(days=7)
    elif range_name == "next_week":
        end_time += datetime.timedelta(days=7)
    else:
        print('Range "{}" unsupported'.format(range_name))

    return udatetime.to_string(start_time), udatetime.to_string(end_time)

def ask_for_date(date_name):
    valid_date = False
    while not valid_date:
        print("Please enter a {} in the format YYYY-MM-DD".format(date_name))
        date_text = input("{}: ".format(date_name))
        try:
            datetime.datetime.strptime(date_text, "%Y-%m-%d")
        except ValueError:
            print("Sorry, that date wasn't in the correct format.")
        else:
            valid_date = True
    return date_text 

def ask_for_range():
    print("Over what range do you want to compute time spent?")
    print("p: The past week")
    print("n: The next week")
    print("anything else: Custom range")
    rangeid = input("range: ")
    if rangeid == 'p':
        return get_simple_time_range("past_week")
    if rangeid == 'n':
        return get_simple_time_range("next_week")
    tzinfo = udatetime.now_to_string()[-6:]
    start_time = ask_for_date("start date") + "T00:00:00.0" + tzinfo
    end_time = ask_for_date("end date") + "T23:59:58.0" + tzinfo
    return start_time, end_time
    # TODO: fix this so i'm not dealing with dates by munging strings
    # around manually!

if __name__ == '__main__':
    service = mk_service()

    #calendars = list_calendars(service)
    #print("For the past week:")
    #for cal_id, cal_name in calendars.items():
    #    get_prev_week_durations(service, cal_id, cal_name)

    start_time, end_time = ask_for_range()
    get_durations_for_range(service, start_time, end_time)
