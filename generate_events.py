import datetime
import html
import json
import urllib.request

API_URL = (
    "https://events.cornell.edu/api/2/events"
    "?type=5167"
    "&days=31"
    "&pp=4"
)

OUTPUT_FILE = "index.html"


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


def get_start_date(event):
    instances = event.get("event_instances", [])
    if not instances:
        return None

    instance_wrapper = instances[0]
    instance = instance_wrapper.get("event_instance", instance_wrapper)
    return instance.get("start")


def format_date(date_value):
    if not date_value:
        return ""

    try:
        cleaned = date_value.replace("Z", "+00:00")
        parsed = datetime.datetime.fromisoformat(cleaned)

        # Linux runner supports %-d and %-I.
        return parsed.strftime("%A, %B %-d, %Y · %-I:%M %p")
    except Exception:
        return str(date_value)


def build_event_card(event):
    title = safe_text(event.get("title"), "Untitled event")

    location = safe_text(
        event.get("location_name")
        or event.get("venue_name")
        or event.get("room_number"),
        ""
    )

    date_text = safe_text(
        event.get("date_time_description")
        or format_date(get_start_date(event)),
        ""
    )

    event_url = safe_text(
        event.get("localist_url")
        or event.get("url"),
        "https://events.cornell.edu/"
    )

    location_html = ""
    if location:
        location_html = (
            '<div class="event-location">'
            + location
            + "</div>"
        )

    return f"""
    <article class="event">
        <div class="event-date">{date_text}</div>

        <h2 class="event-title">
            <a href="{event_url}" target="_blank" rel="noopener">
                {title}
            </a>
        </h2>

        {location_html}
    </article>
    """


def build_page(events):
    cards = "\n".join(build_event_card(event) for event in events)

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

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <meta
        http-equiv="refresh"
        content="1800"
    >

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
            color: #222222;
            font-family: Arial, Helvetica, sans-serif;
        }}

        body {{
            padding: 32px 42px;
        }}

        .events {{
            width: 100%;
        }}

        .event {{
            margin: 0;
            padding: 22px 0;
            border-bottom: 2px solid #dddddd;
        }}

        .event:first-child {{
            padding-top: 0;
        }}

        .event:last-child {{
            border-bottom: 0;
        }}

        .event-date {{
            margin-bottom: 8px;
            color: #666666;
            font-size: 22px;
            font-weight: bold;
            line-height: 1.25;
        }}

        .event-title {{
            margin: 0 0 8px;
            font-size: 34px;
            line-height: 1.15;
        }}

        .event-title a {{
            color: #b31b1b;
            text-decoration: none;
        }}

        .event-location {{
            color: #333333;
            font-size: 23px;
            line-height: 1.3;
        }}

        .empty-message {{
            padding: 40px 0;
            font-size: 30px;
        }}

        .updated {{
            margin-top: 24px;
            color: #777777;
            font-size: 15px;
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

    page = build_page(events[:4])

    with open(OUTPUT_FILE, "w", encoding="utf-8") as output:
        output.write(page)

    print(
        "Created "
        + OUTPUT_FILE
        + " with "
        + str(len(events[:4]))
        + " events."
    )


if __name__ == "__main__":
    main()
