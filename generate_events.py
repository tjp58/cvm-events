import datetime
import html
import json
import urllib.request

API_URL = (
    "https://events.cornell.edu/api/2/events"
    "?days=31"
    "&pp=50"
    "&experience=inperson"
)

OUTPUT_FILE = "index.html"
MAX_EVENTS = 6


def get_event_data():
    request = urllib.request.Request(
        API_URL,
        headers={
            "User-Agent": "Cornell-CVM-Digital-Signage/1.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def safe_text(value, fallback=""):
    if value is None:
        return fallback
    return html.escape(str(value), quote=True)


def get_instance(event):
    instances = event.get("event_instances", [])
    if not instances:
        return {}

    wrapper = instances[0]
    return wrapper.get("event_instance", wrapper)


def parse_start(event):
    start = get_instance(event).get("start")
    if not start:
        return None

    try:
        return datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
    except Exception:
        return None


def format_time(event):
    date_text = event.get("date_time_description")
    if date_text:
        return safe_text(date_text)

    start = parse_start(event)
    if not start:
        return ""

    return safe_text(start.strftime("%-I:%M %p"))


def build_event_card(event):
    start = parse_start(event)

    month = start.strftime("%b") if start else ""
    day = start.strftime("%-d") if start else ""

    title = safe_text(event.get("title"), "Untitled event")

    location = safe_text(
        event.get("location_name")
        or event.get("venue_name")
        or event.get("room_number"),
        ""
    )

    time_text = format_time(event)

    event_url = safe_text(
        event.get("localist_url")
        or event.get("url"),
        "https://events.cornell.edu/"
    )

    location_html = ""
    if location:
        location_html = f'<div class="event-location">{location}</div>'

    return f"""
    <article class="event">
        <div class="date-block">
            <div class="month">{safe_text(month)}</div>
            <div class="day">{safe_text(day)}</div>
        </div>

        <div class="event-copy">
            <h2 class="event-title">
                <a href="{event_url}" target="_blank" rel="noopener">{title}</a>
            </h2>

            <div class="event-time">{time_text}</div>
            {location_html}
        </div>
    </article>
    """


def build_page(events):
    cards = "\n".join(build_event_card(event) for event in events[:MAX_EVENTS])

    if not cards:
        cards = """
        <div class="empty-message">
            No upcoming events are currently available.
        </div>
        """

    updated = datetime.datetime.now().strftime("%B %-d, %Y at %-I:%M %p")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="1800">

    <title>Cornell CVM Events</title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        html,
        body {{
            width: 100%;
            min-height: 100%;
            margin: 0;
            padding: 0;
            background: #ffffff;
            color: #111111;
            font-family: Arial, Helvetica, sans-serif;
        }}

        body {{
            padding: 18px 22px 12px;
        }}

        .events {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 0;
            width: 100%;
        }}

        .event {{
            display: grid;
            grid-template-columns: 58px minmax(0, 1fr);
            gap: 12px;
            align-items: start;
            padding: 14px 0;
            border-bottom: 1px solid #d7d7d7;
        }}

        .event:first-child {{
            padding-top: 0;
        }}

        .event:last-child {{
            border-bottom: 0;
        }}

        .date-block {{
            text-align: center;
            line-height: 1;
        }}

        .month {{
            margin-bottom: 2px;
            color: #666666;
            font-size: 14px;
            text-transform: uppercase;
        }}

        .day {{
            font-size: 32px;
            font-weight: 400;
        }}

        .event-copy {{
            min-width: 0;
        }}

        .event-title {{
            margin: 0 0 4px;
            font-size: 22px;
            line-height: 1.08;
        }}

        .event-title a {{
            color: #006699;
            text-decoration: none;
        }}

        .event-time,
        .event-location {{
            font-size: 15px;
            line-height: 1.25;
        }}

        .event-time {{
            margin-bottom: 2px;
            font-weight: 700;
        }}

        .event-location {{
            color: #333333;
        }}

        .empty-message {{
            padding: 24px 0;
            font-size: 24px;
        }}

        .updated {{
            margin-top: 10px;
            color: #777777;
            font-size: 11px;
            text-align: right;
        }}

        @media (min-width: 900px) {{
            .events {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
                column-gap: 34px;
            }}

            .event:nth-last-child(-n + 2) {{
                border-bottom: 0;
            }}
        }}
    </style>
</head>

<body>
    <main class="events">
        {cards}
    </main>

    <div class="updated">
        Updated {safe_text(updated)}
    </div>
</body>
</html>
"""


def main():
    data = get_event_data()
    event_wrappers = data.get("events", [])
    events = []

    for wrapper in event_wrappers:
        event = wrapper.get("event", wrapper)
        if isinstance(event, dict):
            events.append(event)

    page = build_page(events)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as output:
        output.write(page)

    print("Created " + OUTPUT_FILE + " with " + str(min(len(events), MAX_EVENTS)) + " events.")


if __name__ == "__main__":
    main()
