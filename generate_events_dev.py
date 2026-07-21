import datetime
import html
import json
import re
import urllib.request
from collections import OrderedDict

API_URL = (
    "https://events.cornell.edu/api/2/events"
    "?type=5167"
    "&days=31"
    "&pp=50"
    "&for=widget"
)

OUTPUT_FILE = "dev.html"
MAX_EVENTS = 8
MAX_BLURB_LENGTH = 150


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


def strip_html(value):
    if not value:
        return ""

    text = re.sub(r"<[^>]+>", " ", str(value))
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def truncate(value, limit):
    value = value.strip()
    if len(value) <= limit:
        return value

    shortened = value[: limit + 1].rsplit(" ", 1)[0]
    return shortened.rstrip(".,;:") + "…"


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
    except (TypeError, ValueError):
        return None


def format_time(event):
    start = parse_start(event)
    if start:
        return start.strftime("%-I:%M %p")

    return strip_html(event.get("date_time_description"))


def get_location(event):
    room = strip_html(event.get("room_number"))
    venue = strip_html(event.get("venue_name"))
    location = strip_html(event.get("location_name"))

    if venue and room:
        return venue + ", " + room
    if room:
        return room
    if venue:
        return venue
    return location


def get_tag(event):
    candidates = []

    for key in ("event_types", "departments", "groups"):
        value = event.get(key)
        if isinstance(value, list):
            candidates.extend(value)

    filters = event.get("filters")
    if isinstance(filters, dict):
        for value in filters.values():
            if isinstance(value, list):
                candidates.extend(value)

    for candidate in candidates:
        if isinstance(candidate, dict):
            name = candidate.get("name") or candidate.get("title")
        else:
            name = candidate

        if name:
            cleaned = strip_html(name)
            if cleaned and cleaned.lower() != "cornell university college of veterinary medicine":
                return cleaned

    return ""


def get_blurb(event):
    value = (
        event.get("description_text")
        or event.get("description")
        or event.get("summary")
        or ""
    )
    return truncate(strip_html(value), MAX_BLURB_LENGTH)


def tag_class(tag):
    lowered = tag.lower()

    if "seminar" in lowered or "lecture" in lowered:
        return "ef-tag ef-tag--seminar"
    if "ceremony" in lowered or "reception" in lowered:
        return "ef-tag ef-tag--ceremony"
    return "ef-tag"


CLOCK_ICON = """
<svg class="ef-meta__icon" viewBox="0 0 24 24" aria-hidden="true">
  <circle cx="12" cy="12" r="10"></circle>
  <polyline points="12 6 12 12 16 14"></polyline>
</svg>
"""

PIN_ICON = """
<svg class="ef-meta__icon" viewBox="0 0 24 24" aria-hidden="true">
  <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"></path>
  <circle cx="12" cy="10" r="3"></circle>
</svg>
"""


def build_event_row(event):
    start = parse_start(event)

    month = start.strftime("%b").upper() if start else ""
    day = start.strftime("%-d") if start else ""
    weekday = start.strftime("%a") if start else ""

    title = safe_text(event.get("title"), "Untitled event")
    time_text = safe_text(format_time(event))
    location = safe_text(get_location(event))
    tag = get_tag(event)
    blurb = get_blurb(event)

    event_url = safe_text(
        event.get("localist_url")
        or event.get("url"),
        "https://events.cornell.edu/"
    )

    tag_html = ""
    if tag:
        tag_html = f'<div class="{tag_class(tag)}">{safe_text(tag)}</div>'

    blurb_html = ""
    if blurb:
        blurb_html = f'<p class="ef-event__blurb">{safe_text(blurb)}</p>'

    time_html = ""
    if time_text:
        time_html = (
            '<span class="ef-meta__item">'
            + CLOCK_ICON
            + time_text
            + "</span>"
        )

    location_html = ""
    if location:
        location_html = (
            '<span class="ef-meta__item">'
            + PIN_ICON
            + location
            + "</span>"
        )

    return f"""
      <article class="ef-event">
        <div class="ef-date">
          <div class="ef-date__month">{safe_text(month)}</div>
          <div class="ef-date__day">{safe_text(day)}</div>
          <div class="ef-date__weekday">{safe_text(weekday)}</div>
        </div>

        <div class="ef-event__body">
          {tag_html}

          <h3 class="ef-event__title">
            <a href="{event_url}" target="_blank" rel="noopener">{title}</a>
          </h3>

          {blurb_html}

          <div class="ef-meta">
            {time_html}
            {location_html}
          </div>
        </div>
      </article>
    """


def group_events_by_month(events):
    grouped = OrderedDict()

    for event in events:
        start = parse_start(event)
        month_key = start.strftime("%Y-%m") if start else "unknown"
        month_name = start.strftime("%B %Y") if start else "Upcoming"

        if month_key not in grouped:
            grouped[month_key] = {"name": month_name, "events": []}

        grouped[month_key]["events"].append(event)

    return list(grouped.values())


def build_month_section(month):
    events = month["events"]
    count = len(events)
    count_label = f"{count} event" if count == 1 else f"{count} events"
    rows = "\n".join(build_event_row(event) for event in events)

    return f"""
    <section class="ef-month">
      <header class="ef-month__header">
        <h2 class="ef-month__name">{safe_text(month["name"])}</h2>
        <div class="ef-month__rule"></div>
        <span class="ef-month__count">{count_label}</span>
      </header>

      <div class="ef-list ef-list--compact">
        {rows}
      </div>
    </section>
    """


def build_page(events):
    visible_events = events[:MAX_EVENTS]
    months = group_events_by_month(visible_events)
    sections = "\n".join(build_month_section(month) for month in months)

    if not sections:
        sections = """
        <div class="ef-empty">
          No upcoming events are currently available.
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="1800">
  <title>Cornell CVM Events — Development</title>

  <style>
    :root {{
      --cvm-carnelian: #B31B1B;
      --cvm-black: #222222;
      --cvm-white: #FFFFFF;
      --cvm-blue: #32658A;
      --cvm-gray-700: #303030;
      --cvm-gray-500: #5f5f5f;
      --cvm-gray-300: #969696;
      --cvm-gray-100: #E5E5E5;
      --cvm-gray-50: #F5F5F4;

      --fg-1: var(--cvm-black);
      --fg-2: var(--cvm-gray-700);
      --fg-3: var(--cvm-gray-500);
      --fg-muted: var(--cvm-gray-300);
      --bg-1: var(--cvm-white);
      --bg-2: var(--cvm-gray-50);
      --border-1: var(--cvm-gray-100);

      --font-display: "Montserrat", "Helvetica Neue", Arial, sans-serif;
      --font-body: "Source Sans 3", "Helvetica Neue", Arial, sans-serif;
    }}

    * {{ box-sizing: border-box; }}

    html,
    body {{
      width: 100%;
      min-height: 100%;
      margin: 0;
      padding: 0;
      background: var(--bg-2);
      color: var(--fg-1);
      font-family: var(--font-body);
      -webkit-font-smoothing: antialiased;
      text-rendering: optimizeLegibility;
    }}

    body {{ padding: 18px 14px; }}

    .ef-feed {{
      width: 100%;
      margin: 0 auto;
    }}

    .ef-month {{ margin-bottom: 18px; }}
    .ef-month:last-child {{ margin-bottom: 0; }}

    .ef-month__header {{
      display: flex;
      align-items: baseline;
      gap: 9px;
      margin-bottom: 7px;
    }}

    .ef-month__name {{
      margin: 0;
      font-family: var(--font-display);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      line-height: 1.2;
      text-transform: uppercase;
      color: var(--fg-1);
      white-space: nowrap;
    }}

    .ef-month__rule {{
      flex: 1;
      height: 1px;
      background: var(--border-1);
    }}

    .ef-month__count {{
      font-size: 10px;
      color: var(--fg-3);
      white-space: nowrap;
    }}

    .ef-list {{
      overflow: hidden;
      background: var(--bg-1);
      border: 1px solid var(--border-1);
      border-radius: 4px;
    }}

    .ef-event {{
      display: flex;
      gap: 12px;
      align-items: flex-start;
      padding: 12px;
    }}

    .ef-event + .ef-event {{
      border-top: 1px solid var(--border-1);
    }}

    .ef-date {{
      flex: 0 0 53px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1px;
      padding: 1px 12px 0 0;
      border-right: 1px solid var(--border-1);
      align-self: stretch;
    }}

    .ef-date__month {{
      font-family: var(--font-display);
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.1em;
      line-height: 1.1;
      text-transform: uppercase;
      color: var(--cvm-carnelian);
    }}

    .ef-date__day {{
      font-family: var(--font-display);
      font-size: 24px;
      font-weight: 800;
      line-height: 1;
      letter-spacing: -0.02em;
      color: var(--fg-1);
    }}

    .ef-date__weekday {{
      font-size: 9px;
      line-height: 1.1;
      color: var(--fg-muted);
    }}

    .ef-event__body {{
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 0;
    }}

    .ef-tag {{
      font-family: var(--font-display);
      font-size: 8px;
      font-weight: 700;
      letter-spacing: 0.08em;
      line-height: 1.1;
      text-transform: uppercase;
      color: var(--cvm-carnelian);
    }}

    .ef-tag--seminar {{ color: var(--cvm-blue); }}
    .ef-tag--ceremony {{ color: #8a6210; }}

    .ef-event__title {{
      margin: 0;
      font-family: var(--font-display);
      font-size: 15px;
      font-weight: 700;
      letter-spacing: -0.01em;
      line-height: 1.17;
      color: var(--fg-1);
    }}

    .ef-event__title a {{
      color: inherit;
      text-decoration: none;
    }}

    .ef-event__blurb {{
      margin: 0;
      font-size: 11px;
      line-height: 1.3;
      color: var(--fg-2);
    }}

    .ef-meta {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 2px;
    }}

    .ef-meta__item {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 10px;
      line-height: 1.2;
      color: var(--fg-3);
    }}

    .ef-meta__icon {{
      width: 11px;
      height: 11px;
      flex: 0 0 11px;
      stroke: currentColor;
      fill: none;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}

    .ef-empty {{
      padding: 20px;
      background: var(--bg-1);
      border: 1px solid var(--border-1);
      font-size: 16px;
    }}

    @media (max-height: 760px) {{
      body {{
        padding-top: 10px;
        padding-bottom: 10px;
      }}

      .ef-month {{ margin-bottom: 12px; }}

      .ef-event {{
        padding-top: 9px;
        padding-bottom: 9px;
      }}

      .ef-event__blurb {{ display: none; }}
    }}
  </style>
</head>

<body>
  <main class="ef-feed">
    {sections}
  </main>
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

    events.sort(key=lambda event: parse_start(event) or datetime.datetime.max)
    page = build_page(events)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as output:
        output.write(page)

    print(
        "Created "
        + OUTPUT_FILE
        + " with "
        + str(min(len(events), MAX_EVENTS))
        + " events."
    )


if __name__ == "__main__":
    main()
