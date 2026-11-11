"""
Road Trip Planner

Step 1: The user sets a home point and adds stops (latitude and longitude).
The site tries every possible visiting order (brute-force Traveling Salesman)
and shows the shortest round trip: home -> stops -> home.

Step 2: The user enters trip details (mileage, days, travelers, food and
housing expense levels, tolls) and the site estimates the cost of the whole
trip, broken down into fuel, tolls, parking, food and housing, plus per person.

UI: A dark "night drive" look made with CSS, an animated route map drawn
as an SVG, and a color-coded cost bar.
"""
from dataclasses import dataclass
# ADVANCED TECHNIQUE (not covered in class): the math module. We use
# radians() to convert degrees to radians and cos() to shrink east-west
# distances as you move away from the equator (see distance below).
from math import cos, radians
# ADVANCED TECHNIQUE (not covered in class): html.escape turns characters like
# "<" into "&lt;" so a stop name typed by a user can never inject HTML into
# the map drawing (see route_svg below).
from html import escape

# NOTE: Drafter also exports its own class named "Location", so we import
# only the pieces we need instead of using "from drafter import *".
from drafter import (
    route, start_server, Page, Button, TextBox, SelectBox, CheckBox, Table,
    Argument, Header, Div, Span, Link, RawHTML, Details, NumberedList,
    add_website_css, add_website_header, set_website_title,
    set_website_framed, set_website_style, set_page_transition,
    set_state_display, assert_equal, set_site_information, hide_debug_information
)

set_website_title("Road Trip Planner")
set_site_information(
    author="Souritra Bhattacharjee",
    description="Plan efficient road trips and estimate costs.",
    sources="Thanks to the Drafter library and Claude.",
    planning = "Brainstorm and design documents in repository",
    links=["https://github.com/SouritraBhattacharjee/road_trip_planner"]
)
hide_debug_information()
set_website_framed(False)
# ---------------------------------------------------------------------------
# Global CONSTANTS (allowed; never reassigned)
# ---------------------------------------------------------------------------
MIN_STOPS = 1
GOOGLE_MAPS_URL = "https://www.google.com/maps"
DECIMALS = 1  # decimal places shown when displaying distances
MILES_PER_DEGREE = 69.0  # miles per degree of latitude (and of longitude
                         # at the equator)

# ---- Fuel ----
GAS_PRICE = 4.01              # AAA U.S. average, regular, Nov 2026
DEFAULT_MPG = 25.0            # prefilled value in the mileage TextBox
ROAD_FACTOR = 1.25            # driving miles per straight-line mile

# ---- Tolls ----
TOLL_RATE_PER_MILE = 0.10     # typical $/mile on a toll road
TOLL_ROAD_SHARE = 0.25        # share of the trip assumed to be on toll roads

# ---- Parking ----
PARKING_PER_DAY = 20.0        # per vehicle, per trip day

# ---- Food (per person, per day; index 0 = level 1) ----
FOOD_PER_PERSON_DAY = (20.0, 35.0, 55.0, 80.0, 120.0)

# ---- Housing (per room, per night; index 0 = level 1) ----
HOUSING_PER_ROOM_NIGHT = (50.0, 80.0, 120.0, 250.0, 400.0)
PEOPLE_PER_ROOM = 2

# ---- Levels and input validation ----
LEVEL_LABELS = ("Budget", "Economy", "Standard", "Comfort", "Luxury")
MIN_LEVEL = 1
MAX_LEVEL = 5
DEFAULT_LEVEL = 3
DEFAULT_TRIP_DAYS = 3
DEFAULT_TRAVELERS = 2
MAX_TRIP_DAYS = 60
MAX_TRAVELERS = 20
COST_DECIMALS = 2             # decimal places when showing dollars

# ---- Look and feel ----
STEP_NAMES = ("Stops", "Route", "Details", "Costs")
CATEGORY_ICONS = ("⛽", "🛣️", "🅿️", "🍽️", "🏨")
CATEGORY_COLORS = ("#fb923c", "#a78bfa", "#22d3ee", "#f472b6", "#34d399")
MAP_WIDTH = 640               # size of the route map drawing, in pixels
MAP_HEIGHT = 380
MAP_PADDING = 70              # empty border so labels are not cut off
MAP_LABEL_LIMIT = 14          # longest stop name drawn on the map
GOOGLE_FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=Outfit:'
    'wght@400;600;800&display=swap" rel="stylesheet">'
)

# The whole site design. This is plain CSS text that Drafter adds to the page (Advanced coding technique used by LLM)
THEME_CSS = """
:root { --cyan:#22d3ee; --violet:#8b5cf6; --pink:#f472b6; --green:#34d399;
  --text:#e9edfb; --muted:#9aa5c8; --glass:rgba(255,255,255,.06);
  --line:rgba(255,255,255,.12); }
html, body { margin:0; padding:0; background:#080c1c; color:var(--text);
  font-family:'Outfit', system-ui, -apple-system, 'Segoe UI', sans-serif;
  line-height:1.5; }
body::before { content:''; position:fixed; inset:0; z-index:0;
  background:radial-gradient(900px 500px at 10% -10%, rgba(139,92,246,.35), transparent 60%),
    radial-gradient(800px 500px at 100% 10%, rgba(34,211,238,.22), transparent 60%),
    radial-gradient(700px 500px at 50% 120%, rgba(244,114,182,.22), transparent 60%);
  animation:glow 12s ease-in-out infinite alternate; }
#drafter-root--, .drafter-body-- { max-width:none; padding:0; margin:0; background:transparent; }
.app { position:relative; z-index:1; max-width:1080px; margin:0 auto; padding:24px 20px 70px; }
a { color:#67e8f9; }
h1, h2, h3 { margin:0; font-weight:800; letter-spacing:-.01em; }

.topbar { display:flex; align-items:center; justify-content:space-between;
  gap:16px; flex-wrap:wrap; margin-bottom:26px; }
a.brand { font-size:1.35rem; font-weight:800; text-decoration:none; color:#fff; }
a.brand::after { content:''; display:inline-block; width:9px; height:9px; margin-left:7px;
  border-radius:50%; background:linear-gradient(135deg,var(--cyan),var(--pink));
  box-shadow:0 0 12px var(--cyan); }
.stepper { display:flex; gap:8px; flex-wrap:wrap; }
.step { display:flex; align-items:center; gap:8px; padding:6px 14px 6px 6px;
  border-radius:999px; background:var(--glass); border:1px solid transparent;
  color:var(--muted); font-size:.9rem; transition:all .3s; }
.step .dot { width:24px; height:24px; border-radius:50%; display:grid;
  place-items:center; background:rgba(255,255,255,.1); font-size:.75rem; font-weight:800; }
.step.active { color:#fff; border-color:rgba(34,211,238,.6);
  background:linear-gradient(90deg,rgba(34,211,238,.22),rgba(139,92,246,.22)); }
.step.active .dot { background:var(--cyan); color:#021018; }
.step.done { color:#c9f7e6; }
.step.done .dot { background:var(--green); color:#03241a; }

.hero { display:grid; grid-template-columns:1.1fr .9fr; gap:30px; align-items:center; padding:30px 0 10px; }
.title { font-size:clamp(2.4rem,6vw,4.2rem); line-height:1.05;
  background:linear-gradient(90deg,#fff 0%,var(--cyan) 45%,var(--pink) 100%);
  -webkit-background-clip:text; background-clip:text; color:transparent; }
.lead { color:var(--muted); font-size:1.15rem; margin:16px 0 26px; max-width:34rem; }
.page-title { font-size:clamp(1.8rem,4vw,2.6rem); }
.sub { color:var(--muted); margin:6px 0 22px; }
.hero-art { filter:drop-shadow(0 0 30px rgba(34,211,238,.25)); }
.road-glow { fill:none; stroke:rgba(34,211,238,.25); stroke-width:16; stroke-linecap:round; }
.road { fill:none; stroke:#1b2347; stroke-width:12; stroke-linecap:round; }
.road-dash { fill:none; stroke:#fff; stroke-width:2.5; stroke-linecap:round;
  stroke-dasharray:3 14; animation:dashmove 1s linear infinite; }
.pin { animation:pulse 2.4s ease-in-out infinite; transform-box:fill-box; transform-origin:center; }
.features { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-top:34px; }
.feature .icon { font-size:2rem; }
.feature h3 { font-size:1.1rem; margin:8px 0 4px; }
.feature p { margin:0; color:var(--muted); font-size:.95rem; }

.card { background:var(--glass); border:1px solid var(--line); border-radius:22px;
  padding:22px; backdrop-filter:blur(14px); box-shadow:0 12px 40px rgba(0,0,0,.35);
  margin-bottom:20px; animation:rise .5s ease both; }
.feature { transition:transform .25s, border-color .25s; margin-bottom:0; }
.feature:hover { transform:translateY(-6px); border-color:rgba(34,211,238,.6); }
.card h2 { font-size:1.2rem; margin-bottom:14px; }
.grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
.grid-2 .card { margin-bottom:0; }
.grid-2 { margin-bottom:20px; }

.field { display:flex; flex-direction:column; gap:6px; margin-bottom:14px; }
.lbl { font-size:.78rem; color:var(--muted); font-weight:600; letter-spacing:.08em; text-transform:uppercase; }
input[type=text], select { width:100%; box-sizing:border-box; background:rgba(6,9,24,.75);
  border:1px solid rgba(255,255,255,.16); border-radius:12px; padding:12px 14px;
  color:#fff; font:inherit; outline:none; transition:border-color .2s, box-shadow .2s; }
input[type=text]:focus, select:focus { border-color:var(--cyan); box-shadow:0 0 0 4px rgba(34,211,238,.18); }
input::placeholder { color:#5d688d; }
select option { background:#10162f; }
input[type=checkbox] { accent-color:var(--cyan); width:20px; height:20px; margin:0; }
.check-row { display:flex; align-items:center; gap:10px; padding:10px 0; }

button { font:inherit; font-weight:700; cursor:pointer; color:#fff; border-radius:999px;
  padding:12px 22px; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.22);
  transition:transform .15s, box-shadow .2s, background .2s, filter .2s; }
button:hover { transform:translateY(-2px); background:rgba(255,255,255,.16); }
button:active { transform:translateY(0) scale(.98); }
button.primary { border:0; background:linear-gradient(90deg,var(--cyan),var(--violet) 60%,var(--pink));
  box-shadow:0 8px 28px rgba(139,92,246,.45); }
button.primary:hover { filter:brightness(1.12); box-shadow:0 12px 36px rgba(34,211,238,.45); }
button.big { padding:16px 34px; font-size:1.1rem; }
button.icon-btn { width:36px; height:36px; padding:0; flex:none; }
button.icon-btn:hover { background:rgba(244,63,94,.35); border-color:rgba(244,63,94,.7); }
.linkbtn { display:inline-block; padding:9px 18px; border-radius:999px; text-decoration:none;
  font-weight:700; border:1px solid rgba(34,211,238,.6); color:#a5f3fc; transition:all .2s; }
.linkbtn:hover { background:rgba(34,211,238,.18); transform:translateY(-2px); }

.alert { background:rgba(244,63,94,.14); border:1px solid rgba(244,63,94,.6); color:#fecdd3;
  border-radius:14px; padding:12px 16px; margin-bottom:18px; font-weight:600;
  animation:shake .4s ease; }
.ok-note { background:rgba(52,211,153,.14); border:1px solid rgba(52,211,153,.55); color:#a7f3d0;
  border-radius:12px; padding:10px 14px; margin-top:12px; font-weight:600; animation:rise .4s ease; }
.chip { display:inline-block; padding:5px 12px; border-radius:999px; font-size:.85rem; font-weight:600;
  background:rgba(255,255,255,.08); border:1px solid var(--line); margin:0 6px 6px 0; }
.chip.good { color:#a7f3d0; border-color:rgba(52,211,153,.5); }
.chip.warn { color:#fde68a; border-color:rgba(251,191,36,.5); }

.stop-item { display:flex; align-items:center; gap:14px; padding:12px 14px; border-radius:16px;
  background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08);
  margin-bottom:10px; animation:slide .35s ease both; }
.badge { width:34px; height:34px; border-radius:50%; display:grid; place-items:center; flex:none;
  font-weight:800; background:linear-gradient(135deg,var(--cyan),var(--violet)); }
.stop-info { flex:1; min-width:0; }
.stop-name { display:block; font-weight:700; }
.stop-coords { display:block; color:var(--muted); font-size:.85rem; }
.empty { color:var(--muted); text-align:center; padding:26px; border:1.5px dashed rgba(255,255,255,.22);
  border-radius:16px; margin-bottom:12px; }
.actions { display:flex; gap:12px; flex-wrap:wrap; align-items:center; margin-top:22px; }

.stats { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-bottom:20px; }
.stats .card { margin-bottom:0; text-align:center; }
.value { font-size:2.3rem; font-weight:800; background:linear-gradient(90deg,var(--cyan),var(--pink));
  -webkit-background-clip:text; background-clip:text; color:transparent; }
.caption { color:var(--muted); font-size:.85rem; text-transform:uppercase; letter-spacing:.08em; }
.map-card { padding:10px; }
svg.map { width:100%; height:auto; display:block; border-radius:16px; background:rgba(4,7,20,.6); }
.map .grid { stroke:rgba(255,255,255,.06); stroke-width:1; fill:none; }
.map .route-glow { fill:none; stroke:rgba(34,211,238,.28); stroke-width:10; stroke-linejoin:round; }
.map .route-line { fill:none; stroke:url(#rg); stroke-width:3.5; stroke-linejoin:round;
  stroke-dasharray:1; stroke-dashoffset:1; animation:draw 2.6s ease forwards; }
.map .marker { animation:pop .5s ease both; transform-box:fill-box; transform-origin:center; }
.map .num { fill:#021018; font-weight:800; font-size:14px; text-anchor:middle; }
.map .name { fill:#e9edfb; font-size:13px; font-weight:600; text-anchor:middle;
  paint-order:stroke; stroke:#050816; stroke-width:5px; stroke-linejoin:round; }
.leg { display:flex; align-items:center; gap:12px; padding:12px 4px; border-bottom:1px solid rgba(255,255,255,.08); }
.leg:last-child { border-bottom:0; }
.leg .miles { margin-left:auto; font-weight:800; color:#67e8f9; white-space:nowrap; }
.leg .arrow { color:var(--muted); }

.total-hero { display:grid; grid-template-columns:1fr 1fr; gap:20px; text-align:center; }
.big-money { font-size:clamp(2.3rem,6vw,3.8rem); font-weight:800; line-height:1.1;
  background:linear-gradient(90deg,var(--cyan),var(--pink)); -webkit-background-clip:text;
  background-clip:text; color:transparent; }
.bar { display:flex; height:24px; border-radius:999px; overflow:hidden; background:rgba(255,255,255,.08); }
.bar div { height:100%; transition:width .6s ease; animation:grow 1s ease both; transform-origin:left; }
.legend { display:flex; flex-wrap:wrap; gap:6px 16px; margin-top:12px; font-size:.9rem; color:var(--muted); }
.cat-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:14px; margin-bottom:20px; }
.cat { background:var(--glass); border:1px solid var(--line); border-radius:18px; padding:16px;
  transition:transform .25s; animation:rise .6s ease both; }
.cat:hover { transform:translateY(-5px); }
.cat .ico { font-size:1.7rem; }
.cat .name { color:var(--muted); font-size:.85rem; text-transform:uppercase; letter-spacing:.08em; }
.cat .amount { font-size:1.6rem; font-weight:800; }
.cat .each { color:var(--muted); font-size:.9rem; }
table { width:100%; border-collapse:collapse; }
th, td { text-align:left; padding:10px 8px; border-bottom:1px solid rgba(255,255,255,.08); }
th { color:var(--muted); font-size:.8rem; text-transform:uppercase; letter-spacing:.08em; }
details { margin-bottom:16px; }
summary { cursor:pointer; font-weight:700; color:#a5f3fc; margin-bottom:10px; }
ol { color:var(--muted); padding-left:22px; }
.footer { text-align:center; color:#6c779c; font-size:.85rem; margin-top:34px; }

@keyframes draw { to { stroke-dashoffset:0; } }
@keyframes dashmove { to { stroke-dashoffset:-34; } }
@keyframes pop { from { opacity:0; transform:scale(.2); } to { opacity:1; transform:scale(1); } }
@keyframes pulse { 0%,100% { transform:scale(1); } 50% { transform:scale(1.25); } }
@keyframes rise { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:none; } }
@keyframes slide { from { opacity:0; transform:translateX(-18px); } to { opacity:1; transform:none; } }
@keyframes grow { from { transform:scaleX(0); } to { transform:scaleX(1); } }
@keyframes shake { 25% { transform:translateX(-6px); } 75% { transform:translateX(6px); } }
@keyframes glow { from { opacity:.75; } to { opacity:1; } }
@media (max-width:800px) {
  .hero, .grid-2, .features, .stats, .total-hero { grid-template-columns:1fr; }
  .step .label { display:none; }
  .step.active .label { display:inline; }
  .cat-grid { grid-template-columns:1fr 1fr; }
}
@media (prefers-reduced-motion:reduce) { * { animation:none !important; } }
"""

# Decorative drawing for the welcome page: a glowing road with two pins and
# a headlight that drives along it (animateMotion moves the dot on the path).
HERO_SVG = """
<svg class="hero-art" viewBox="0 0 420 320" role="img" aria-label="A winding road">
  <path class="road-glow" d="M30 270 C 110 270, 120 150, 210 160 S 330 250, 392 70"/>
  <path class="road" d="M30 270 C 110 270, 120 150, 210 160 S 330 250, 392 70"/>
  <path class="road-dash" d="M30 270 C 110 270, 120 150, 210 160 S 330 250, 392 70"/>
  <circle class="pin" cx="30" cy="270" r="11" fill="#fbbf24"/>
  <circle class="pin" cx="210" cy="160" r="9" fill="#f472b6"/>
  <circle class="pin" cx="392" cy="70" r="11" fill="#22d3ee"/>
  <circle r="7" fill="#fff">
    <animateMotion dur="7s" repeatCount="indefinite"
      path="M30 270 C 110 270, 120 150, 210 160 S 330 250, 392 70"/>
  </circle>
</svg>
"""


@dataclass
class Location:
    """A named point on the map. Never modified after creation."""
    name: str
    x: float  # latitude in degrees
    y: float  # longitude in degrees


@dataclass
class State:
    """Everything that must persist across the whole website."""
    home: Location
    stops: list[Location]
    best_route: list[Location]
    best_distance: float  # straight-line round trip, in miles
    message: str  # error text, shown in red
    home_notice: str  # shown in green below the home form
    stop_notice: str  # shown in green below the add-stop form
    mileage: float  # miles per gallon of the vehicle
    trip_days: int
    travelers: int
    food_expense_level: int  # 1 (budget) to 5 (luxury)
    housing_expense_level: int  # 1 (budget) to 5 (luxury)
    include_tolls: bool


@dataclass
class TripCosts:
    """The dollar cost of each part of the trip (for the whole group)."""
    fuel: float
    tolls: float
    parking: float
    food: float
    housing: float


def new_state() -> State:
    """Build the starting State: no stops, default trip settings."""
    return State(Location("Home", 0.0, 0.0), [], [], 0.0, "", "", "",
                 DEFAULT_MPG, DEFAULT_TRIP_DAYS, DEFAULT_TRAVELERS,
                 DEFAULT_LEVEL, DEFAULT_LEVEL, False)


# ---------------------------------------------------------------------------
# Helper functions: route finding (pure logic, no Drafter) - unit tested
# ---------------------------------------------------------------------------

def parse_number(text: str) -> float | None:
    """
    Convert user text into a float, or return None if it isn't a number.

    Uses try/except, which handles the error Python raises when float()
    gets text like "abc". Without it, bad input would crash the site.

    Args:
        text: The raw text from a TextBox.
    Returns:
        The number as a float, or None if the text is not a valid number.
    """
    try:
        return float(text.strip())
    except ValueError:
        return None


def parse_int(text: str) -> int | None:
    """
    Convert user text into an int, or return None if it isn't a whole number.

    Args:
        text: The raw text from a TextBox.
    Returns:
        The number as an int, or None if the text is not a whole number.
    """
    try:
        return int(text.strip())
    except ValueError:
        return None


def distance(first: Location, second: Location) -> float:
    """
    Approximate straight-line distance in miles between two locations.

    Latitude (x) and longitude (y) are in degrees. A degree of latitude is
    always about MILES_PER_DEGREE miles. A degree of longitude gets shorter
    farther from the equator, so we multiply it by cos(average latitude).
    Then the Pythagorean theorem combines the north-south and east-west legs.

    Args:
        first: The starting location.
        second: The ending location.
    Returns:
        The distance in miles.
    """
    mid_lat = radians((first.x + second.x) / 2)
    north = (first.x - second.x) * MILES_PER_DEGREE
    east_miles = ((first.y - second.y) * MILES_PER_DEGREE
                  * cos(mid_lat))
    return (north ** 2 + east_miles ** 2) ** 0.5


def route_length(home: Location, stops: list[Location]) -> float:
    """
    Total length of a round trip: home -> each stop in order -> home.

    Args:
        home: Where the trip starts and ends.
        stops: The stops, in the order they are visited.
    Returns:
        The total round-trip distance in miles.
    """
    total = 0.0
    previous = home
    for stop in stops:
        total += distance(previous, stop)
        previous = stop
    return total + distance(previous, home)


def name_is_taken(stops: list[Location], name: str) -> bool:
    """
    Check whether a stop with this name already exists (ignoring case).

    Args:
        stops: The current list of stops.
        name: The proposed new stop name.
    Returns:
        True if a stop already uses that name, otherwise False.
    """
    for stop in stops:
        if stop.name.lower() == name.lower():
            return True
    return False


def all_orderings(stops: list[Location]) -> list[list[Location]]:
    """
    Build every possible visiting order (permutation) of the stops.

    Written with recursion instead of itertools.permutations: pick each stop
    to go first, then recursively order the remaining stops.

    Args:
        stops: The stops to arrange.
    Returns:
        A list containing every ordering, each ordering a list of stops.
    """
    if len(stops) <= 1:
        return [list(stops)]
    orderings = []
    for index, first_stop in enumerate(stops):
        remaining = stops[:index] + stops[index + 1:]
        for rest in all_orderings(remaining):
            orderings.append([first_stop] + rest)
    return orderings


def find_best_route(home: Location,
                    stops: list[Location]) -> tuple[list[Location], float]:
    """
    Brute-force search: try every ordering and keep the shortest round trip.

    Args:
        home: Where the trip starts and ends.
        stops: The stops that must all be visited.
    Returns:
        A tuple of (best ordering of the stops, its round-trip distance).
    """
    best_order = list(stops)
    best_length = route_length(home, best_order)
    for ordering in all_orderings(stops):
        length = route_length(home, ordering)
        if length < best_length:
            best_order = ordering
            best_length = length
    return best_order, best_length


def leg_distances(home: Location, route_stops: list[Location]) -> list[float]:
    """
    Distance of each leg of a round trip (including the return home).

    Args:
        home: Where the trip starts and ends.
        route_stops: The stops in visiting order.
    Returns:
        One distance per leg; there is one more leg than there are stops.
    """
    legs = []
    previous = home
    for stop in route_stops:
        legs.append(distance(previous, stop))
        previous = stop
    legs.append(distance(previous, home))
    return legs


def describe_stop(stop: Location) -> str:
    """
    Format a stop as text, e.g. "Dover (39.16, -75.52)".

    Args:
        stop: The location to describe.
    Returns:
        A short display string with the name and coordinates.
    """
    return f"{stop.name} ({stop.x}, {stop.y})"


# ---------------------------------------------------------------------------
# Helper functions: cost estimation (pure logic, no Drafter) - unit tested
# ---------------------------------------------------------------------------

def level_option(level: int) -> str:
    """
    Make the SelectBox text for a level, e.g. 3 -> "3 - Standard".

    Args:
        level: A level from MIN_LEVEL to MAX_LEVEL.
    Returns:
        The text shown in the SelectBox for that level.
    """
    return f"{level} - {LEVEL_LABELS[level - 1]}"


def level_options() -> list[str]:
    """
    Build the SelectBox choices for every level.

    Returns:
        One option text per level, from MIN_LEVEL to MAX_LEVEL.
    """
    options = []
    for level in range(MIN_LEVEL, MAX_LEVEL + 1):
        options.append(level_option(level))
    return options


def parse_level(option: str) -> int:
    """
    Read the level number back out of SelectBox text like "3 - Standard".

    Args:
        option: The text chosen in a level SelectBox.
    Returns:
        The level number, or DEFAULT_LEVEL if the text is not recognized.
    """
    first = option.strip()[:1]
    if first.isdigit():
        level = int(first)
        if MIN_LEVEL <= level <= MAX_LEVEL:
            return level
    return DEFAULT_LEVEL


def driving_miles(miles: float) -> float:
    """
    Convert straight-line miles to estimated driving miles.

    Roads are not straight, so driving is longer than the straight line.

    Args:
        miles: The straight-line round-trip distance.
    Returns:
        The estimated driving distance in miles.
    """
    return miles * ROAD_FACTOR


def fuel_cost(miles: float, mileage: float) -> float:
    """
    Cost of gas for the trip.

    Args:
        miles: Total driving miles.
        mileage: The vehicle's miles per gallon (must be positive).
    Returns:
        The fuel cost in dollars.
    """
    return miles / mileage * GAS_PRICE


def toll_cost(miles: float, include_tolls: bool) -> float:
    """
    Estimated tolls: only part of the trip is on toll roads.

    Args:
        miles: Total driving miles.
        include_tolls: Whether the user wants tolls counted.
    Returns:
        The toll cost in dollars (0.0 if tolls are not included).
    """
    if include_tolls:
        return miles * TOLL_ROAD_SHARE * TOLL_RATE_PER_MILE
    return 0.0


def parking_cost(trip_days: int) -> float:
    """
    Parking for one vehicle for every day of the trip.

    Args:
        trip_days: The number of days of the trip.
    Returns:
        The parking cost in dollars.
    """
    return trip_days * PARKING_PER_DAY


def food_cost(trip_days: int, travelers: int, level: int) -> float:
    """
    Food for every traveler for every day, at the chosen level.

    Args:
        trip_days: The number of days of the trip.
        travelers: The number of people.
        level: The food expense level, MIN_LEVEL to MAX_LEVEL.
    Returns:
        The food cost in dollars.
    """
    return trip_days * travelers * FOOD_PER_PERSON_DAY[level - 1]


def rooms_needed(travelers: int) -> int:
    """
    Number of rooms needed, rounding up (3 people at 2 per room = 2 rooms).

    Args:
        travelers: The number of people.
    Returns:
        The number of rooms.
    """
    return (travelers + PEOPLE_PER_ROOM - 1) // PEOPLE_PER_ROOM


def housing_cost(trip_days: int, travelers: int, level: int) -> float:
    """
    Lodging cost: one room-night for each night of the trip.

    A trip of N days has N - 1 nights (a one-day trip needs no lodging).

    Args:
        trip_days: The number of days of the trip.
        travelers: The number of people.
        level: The housing expense level, MIN_LEVEL to MAX_LEVEL.
    Returns:
        The housing cost in dollars.
    """
    nights = 0
    if trip_days > 1:
        nights = trip_days - 1
    room_rate = HOUSING_PER_ROOM_NIGHT[level - 1]
    return nights * rooms_needed(travelers) * room_rate


def estimate_costs(state: State) -> TripCosts:
    """
    Estimate every cost category for the trip in the State.

    Args:
        state: The State with a calculated route and trip settings.
    Returns:
        A TripCosts with the dollar cost of each category.
    """
    miles = driving_miles(state.best_distance)
    food_level = state.food_expense_level
    housing_level = state.housing_expense_level
    return TripCosts(
        fuel_cost(miles, state.mileage),
        toll_cost(miles, state.include_tolls),
        parking_cost(state.trip_days),
        food_cost(state.trip_days, state.travelers, food_level),
        housing_cost(state.trip_days, state.travelers, housing_level),
    )


def total_cost(costs: TripCosts) -> float:
    """
    Add up every cost category.

    Args:
        costs: The costs to add.
    Returns:
        The total trip cost in dollars.
    """
    return costs.fuel + costs.tolls + costs.parking + costs.food + costs.housing


def money(amount: float) -> str:
    """
    Format dollars for display, e.g. 20.05 -> "$20.05".

    Args:
        amount: The dollar amount.
    Returns:
        The amount as text with a dollar sign.
    """
    return f"${amount:,.{COST_DECIMALS}f}"


def category_list(costs: TripCosts) -> list[tuple[str, float]]:
    """
    List every cost category with its amount, in a fixed display order.

    The order matches CATEGORY_ICONS and CATEGORY_COLORS.

    Args:
        costs: The costs for each category.
    Returns:
        A list of (category name, dollars) pairs.
    """
    return [
        ("Fuel", costs.fuel), ("Tolls", costs.tolls),
        ("Parking", costs.parking), ("Food", costs.food),
        ("Housing", costs.housing),
    ]


def cost_shares(costs: TripCosts) -> list[float]:
    """
    Each category's share of the total, as a percent (0 to 100).

    Args:
        costs: The costs for each category.
    Returns:
        One percent per category, in category_list order (all 0 if free).
    """
    total = total_cost(costs)
    shares = []
    for label, amount in category_list(costs):
        if total > 0:
            shares.append(amount / total * 100)
        else:
            shares.append(0.0)
    return shares


def cost_rows(costs: TripCosts, travelers: int) -> list[list[str]]:
    """
    Build the cost breakdown table rows (categories, then the total).

    Args:
        costs: The costs for each category.
        travelers: The number of people, used for the per-person column.
    Returns:
        A list of table rows, each a list of display strings.
    """
    rows = []
    for label, amount in category_list(costs):
        rows.append([label, money(amount), money(amount / travelers)])
    total = total_cost(costs)
    rows.append(["Total", money(total), money(total / travelers)])
    return rows


def level_guide_rows() -> list[list[str]]:
    """
    Build the table that explains what each expense level costs.

    Returns:
        One row per level: [label, food $/person/day, housing $/room/night].
    """
    rows = []
    for level in range(MIN_LEVEL, MAX_LEVEL + 1):
        rows.append([level_option(level),
                     money(FOOD_PER_PERSON_DAY[level - 1]),
                     money(HOUSING_PER_ROOM_NIGHT[level - 1])])
    return rows


# ---------------------------------------------------------------------------
# Helper functions: look and feel (pure logic, no Drafter) - unit tested
# ---------------------------------------------------------------------------

def step_class(number: int, current: int) -> str:
    """
    Decide how one step of the progress bar should look.

    Args:
        number: This step's number (1 for the first step).
        current: The step the user is on.
    Returns:
        "done" for earlier steps, "active" for this one, else "todo".
    """
    if number < current:
        return "done"
    if number == current:
        return "active"
    return "todo"


def short_name(name: str, limit: int) -> str:
    """
    Shorten a long name so it fits on the map, adding "..." if cut.

    Args:
        name: The full name.
        limit: The most characters to keep.
    Returns:
        The name, or its first characters followed by "...".
    """
    if len(name) > limit:
        return name[:limit - 1] + "..."
    return name


def project_points(points: list[Location], width: float, height: float,
                   pad: float) -> list[tuple[float, float]]:
    """
    Turn latitude/longitude points into x/y pixel positions for drawing.

    North is up. Longitude is shrunk by cos(latitude) so the shape of the
    route looks right. The whole drawing is scaled to fit and centered.

    Args:
        points: The locations to place on the map.
        width: Drawing width in pixels.
        height: Drawing height in pixels.
        pad: Empty border, in pixels, kept on every side.
    Returns:
        One (pixel x, pixel y) pair per point, in the same order.
    """
    lats = [point.x for point in points]
    lons = [point.y for point in points]
    shrink = cos(radians((min(lats) + max(lats)) / 2))
    span_x = (max(lons) - min(lons)) * shrink
    span_y = max(lats) - min(lats)
    scale = 0.0
    if span_x > 0 and span_y > 0:
        scale = min((width - 2 * pad) / span_x, (height - 2 * pad) / span_y)
    elif span_x > 0:
        scale = (width - 2 * pad) / span_x
    elif span_y > 0:
        scale = (height - 2 * pad) / span_y
    left = (width - span_x * scale) / 2
    top = (height - span_y * scale) / 2
    pixels = []
    for point in points:
        pixel_x = left + (point.y - min(lons)) * shrink * scale
        pixel_y = top + (max(lats) - point.x) * scale
        pixels.append((pixel_x, pixel_y))
    return pixels


def marker_svg(label: str, name: str, pixel_x: float, pixel_y: float,
               is_home: bool, delay: float) -> str:
    """
    Draw one numbered pin and its name on the route map.

    Args:
        label: The text inside the pin (a stop number, or "H" for home).
        name: The place name, which is HTML-escaped before drawing.
        pixel_x: The pin's x position.
        pixel_y: The pin's y position.
        is_home: True for the home pin (drawn gold instead of cyan).
        delay: Seconds to wait before the pin pops in.
    Returns:
        SVG text for the pin.
    """
    color = "#fbbf24" if is_home else "#22d3ee"
    name_y = pixel_y + 34  # put the name on the outer side of the map
    if pixel_y <= MAP_HEIGHT / 2:
        name_y = pixel_y - 24
    safe_name = escape(short_name(name, MAP_LABEL_LIMIT))
    return (
        f'<g class="marker" style="animation-delay:{delay:.2f}s">'
        f'<circle cx="{pixel_x:.1f}" cy="{pixel_y:.1f}" r="16" fill="{color}" '
        f'fill-opacity="0.25"/>'
        f'<circle cx="{pixel_x:.1f}" cy="{pixel_y:.1f}" r="12" fill="{color}"/>'
        f'<text class="num" x="{pixel_x:.1f}" y="{pixel_y + 5:.1f}">'
        f'{escape(label)}</text>'
        f'<text class="name" x="{pixel_x:.1f}" y="{name_y:.1f}">'
        f'{safe_name}</text></g>'
    )


def route_svg(home: Location, route_stops: list[Location]) -> str:
    """
    Draw the whole round trip as an animated SVG map.

    The route line "draws itself" using CSS (see THEME_CSS) and the pins pop
    in one after another. Place names are escaped so they can't inject HTML.

    Args:
        home: Where the trip starts and ends.
        route_stops: The stops, in visiting order.
    Returns:
        SVG text, ready to give to RawHTML.
    """
    places = [home] + route_stops
    pixels = project_points(places, MAP_WIDTH, MAP_HEIGHT, MAP_PADDING)
    loop = pixels + [pixels[0]]
    line_points = " ".join(f"{px:.1f},{py:.1f}" for px, py in loop)
    grid = ""
    for edge in range(0, MAP_WIDTH + 1, 40):
        grid += f"M{edge} 0V{MAP_HEIGHT}"
    for edge in range(0, MAP_HEIGHT + 1, 40):
        grid += f"M0 {edge}H{MAP_WIDTH}"
    pins = ""
    for number, place in enumerate(places):
        label = "H" if number == 0 else str(number)
        pixel_x, pixel_y = pixels[number]
        pins += marker_svg(label, place.name, pixel_x, pixel_y,
                           number == 0, 0.5 + number * 0.25)
    return (
        f'<svg class="map" viewBox="0 0 {MAP_WIDTH} {MAP_HEIGHT}" '
        f'role="img" aria-label="Map of your route">'
        f'<defs><linearGradient id="rg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#22d3ee"/>'
        f'<stop offset="1" stop-color="#f472b6"/></linearGradient></defs>'
        f'<path class="grid" d="{grid}"/>'
        f'<polyline class="route-glow" points="{line_points}"/>'
        f'<polyline class="route-line" pathLength="1" points="{line_points}"/>'
        f'{pins}</svg>'
    )


# ---------------------------------------------------------------------------
# Page-building helpers (these build Drafter components)
# ---------------------------------------------------------------------------

def step_bar(current: int) -> Div:
    """
    Build the progress bar shown at the top of every planning page.

    Args:
        current: The step the user is on (1 to 4).
    Returns:
        A Div holding one pill per step.
    """
    pills = []
    for number, name in enumerate(STEP_NAMES, start=1):
        kind = step_class(number, current)
        mark = "✓" if kind == "done" else str(number)
        pills.append(Div(Span(mark, classes="dot"),
                         Span(name, classes="label"),
                         classes=f"step {kind}"))
    return Div(*pills, classes="stepper")


def shell(state: State, step: int, content: list) -> Page:
    """
    Wrap page content in the site's common layout (top bar and footer).

    Args:
        state: The current State.
        step: The progress step to highlight, or 0 for no progress bar.
        content: The components that make up the page itself.
    Returns:
        The finished Page.
    """
    top_bar = [Link("Road Trip Planner", index, classes="brand")]
    if step > 0:
        top_bar.append(step_bar(step))
    return Page(state, [Div(
        Div(*top_bar, classes="topbar"),
        Div(*content),
        Div("Estimates use average U.S. prices. Safe travels! 🚗",
            classes="footer"),
        classes="app",
    )])


def field(label: str, box: TextBox | SelectBox) -> Div:
    """
    Put a small label above an input box.

    Args:
        label: The label text.
        box: The input component.
    Returns:
        A Div containing the label and the input.
    """
    return Div(Span(label, classes="lbl"), box, classes="field")


def error_banner(message: str) -> list[Div]:
    """
    Build the red error banner, or nothing if there is no error.

    Args:
        message: The error text (empty means no error).
    Returns:
        A list with one banner Div, or an empty list.
    """
    if message != "":
        return [Div("⚠️ " + message, classes="alert")]
    return []


def success_note(message: str) -> list[Div]:
    """
    Build the green success note, or nothing if there is no message.

    Args:
        message: The success text (empty means nothing to show).
    Returns:
        A list with one note Div, or an empty list.
    """
    if message != "":
        return [Div("✅ " + message, classes="ok-note")]
    return []


def stop_card(number: int, stop: Location) -> Div:
    """
    Build the card for one stop, with a remove button.

    Args:
        number: The stop's position in the list (1 for the first).
        stop: The stop to show.
    Returns:
        A Div showing the stop's number, name, coordinates and a button.
    """
    return Div(
        Span(str(number), classes="badge"),
        Div(Span(stop.name, classes="stop-name"),
            Span(f"lat {stop.x}, lon {stop.y}", classes="stop-coords"),
            classes="stop-info"),
        Button("✕", remove_stop, [Argument("stop_name", stop.name)],
               classes="icon-btn"),
        classes="stop-item",
    )


def stops_list(stops: list[Location]) -> list[Div]:
    """
    Build the "Your stops" list, or a friendly empty message.

    Args:
        stops: The current stops.
    Returns:
        A list of stop cards (or one empty-state Div).
    """
    if len(stops) == 0:
        return [Div("🗺️ No stops yet. Add your first destination above!",
                    classes="empty")]
    cards = []
    for number, stop in enumerate(stops, start=1):
        cards.append(stop_card(number, stop))
    return cards


def readiness_chip(stop_count: int) -> Span:
    """
    Build a chip telling the user if they have enough stops.

    Args:
        stop_count: How many stops have been added.
    Returns:
        A green "ready" chip, or an amber chip saying how many are missing.
    """
    missing = MIN_STOPS - stop_count
    if missing > 0:
        return Span(f"Add {missing} more to plan a route", classes="chip warn")
    return Span("Ready to plan your route!", classes="chip good")


def stat_card(value: str, caption: str) -> Div:
    """
    Build one big-number card for the results page.

    Args:
        value: The big number text.
        caption: The small caption underneath.
    Returns:
        A card Div.
    """
    return Div(Div(value, classes="value"), Div(caption, classes="caption"),
               classes="card")


def leg_row(number: int, start: str, end: str, miles: float) -> Div:
    """
    Build one row of the trip legs list.

    Args:
        number: The leg number (1 for the first).
        start: The name where the leg starts.
        end: The name where the leg ends.
        miles: The leg's length in miles.
    Returns:
        A Div with the leg's number, places and distance.
    """
    return Div(Span(str(number), classes="badge"),
               Span(start), Span("→", classes="arrow"), Span(end),
               Span(f"{round(miles, DECIMALS)} mi", classes="miles"),
               classes="leg")


def cost_bar(costs: TripCosts) -> list[Div]:
    """
    Build the colored bar showing each category's share, plus its legend.

    Args:
        costs: The costs for each category.
    Returns:
        A list with the bar Div and the legend Div.
    """
    segments = []
    legend = []
    shares = cost_shares(costs)
    for index_number, (label, amount) in enumerate(category_list(costs)):
        color = CATEGORY_COLORS[index_number]
        segments.append(Div(style_width=f"{shares[index_number]:.2f}%",
                            style_background_color=color, title=label))
        legend.append(Span(
            Span(style_background_color=color, style_display="inline-block",
                 style_width="10px", style_height="10px",
                 style_border_radius="50%", style_margin_right="6px"),
            f"{label} {round(shares[index_number])}%"))
    return [Div(*segments, classes="bar"), Div(*legend, classes="legend")]


def category_card(index_number: int, label: str, amount: float,
                  travelers: int) -> Div:
    """
    Build the card for one cost category.

    Args:
        index_number: Which category this is (0 for fuel, 1 for tolls...).
        label: The category name.
        amount: Its whole-trip cost in dollars.
        travelers: The number of people, for the per-person line.
    Returns:
        A card Div with an icon, name, total and per-person cost.
    """
    return Div(
        Div(CATEGORY_ICONS[index_number], classes="ico"),
        Div(label, classes="name"),
        Div(money(amount), classes="amount"),
        Div(f"{money(amount / travelers)} each", classes="each"),
        classes="cat",
        style_border_top=f"4px solid {CATEGORY_COLORS[index_number]}",
        style_animation_delay=f"{index_number * 0.08:.2f}s",
    )


def category_cards(costs: TripCosts, travelers: int) -> Div:
    """
    Build the grid of cost category cards.

    Args:
        costs: The costs for each category.
        travelers: The number of people.
    Returns:
        A Div containing one card per category.
    """
    cards = []
    for index_number, (label, amount) in enumerate(category_list(costs)):
        cards.append(category_card(index_number, label, amount, travelers))
    return Div(*cards, classes="cat-grid")


def apply_theme() -> None:
    """Give the whole website its look: fonts, colors, animations, title."""
    set_website_style(None)  # turn off Drafter's built-in theme
    set_website_framed(False)
    set_state_display(False)
    set_website_title("Roadtrip Planner")
    set_page_transition("fade", 0.35)
    add_website_header(GOOGLE_FONT_LINK)
    add_website_css(THEME_CSS)


# ---------------------------------------------------------------------------
# Routes (pages and actions)
# ---------------------------------------------------------------------------

@route
def index(state: State) -> Page:
    """Welcome page that explains the site."""
    features = [
        ("🧠", "Smartest route", "Tries every possible order of your stops "
         "and picks the shortest round trip."),
        ("💸", "Real cost estimate", "Fuel, tolls, parking, food and housing, "
         "all in one place."),
        ("👥", "Split it fairly", "See the total and what each traveler "
         "pays."),
    ]
    cards = []
    for icon, title, text in features:
        cards.append(Div(Div(icon, classes="icon"), Header(title, 3),
                         Div(text, classes="feature-text"),
                         classes="card feature"))
    return shell(state, 0, [
        Div(
            Div(Header("Plan your next road trip.", 1, classes="title"),
                Div("Add your home and destinations. We find the most "
                    "efficient route and tell you exactly what the trip will "
                    "cost.", classes="lead"),
                Button("Start planning →", stops_page, classes="primary big")),
            RawHTML(HERO_SVG),
            classes="hero",
        ),
        Div(*cards, classes="features"),
    ])


@route
def stops_page(state: State) -> Page:
    """Page to set home, add stops, and review/remove the current stops."""
    help_box = Details(
        "🧭 How do I find coordinates?",
        NumberedList([
            "Open Google Maps and right-click your location.",
            "Click the latitude, longitude numbers to copy them.",
            "Latitude is x and longitude is y. Use decimals, for example "
            "39.16 and -75.52.",
            "Repeat for every stop.",
        ]),
        RawHTML(f'<a class="linkbtn" href="{GOOGLE_MAPS_URL}" '
                f'target="_blank" rel="noopener">Open Google Maps ↗</a>'),
        open=len(state.stops) == 0,
    )
    home_card = Div(
        Header("🏠 Home base", 2),
        field("Name", TextBox("home_name", state.home.name)),
        field("Latitude (x)", TextBox("home_x", str(state.home.x))),
        field("Longitude (y)", TextBox("home_y", str(state.home.y))),
        Button("Set home", set_home),
        *success_note(state.home_notice),
        classes="card",
    )
    stop_card_form = Div(
        Header("📍 Add a stop", 2),
        field("Name", TextBox("stop_name", placeholder="e.g. Dover")),
        field("Latitude (x)", TextBox("x_text", placeholder="e.g. 39.16")),
        field("Longitude (y)", TextBox("y_text", placeholder="e.g. -75.52")),
        Button("Add stop", add_stop),
        *success_note(state.stop_notice),
        classes="card",
    )
    return shell(state, 1, [
        Header("Where are we going?", 1, classes="page-title"),
        Div("Set your starting point, then add every place you want to "
            "visit.", classes="sub"),
        *error_banner(state.message),
        help_box,
        Div(home_card, stop_card_form, classes="grid-2"),
        Div(
            Header(f"🗺️ Your stops ({len(state.stops)})", 2),
            *stops_list(state.stops),
            readiness_chip(len(state.stops)),
            Div(Button("Find best route →", calculate_route,
                       classes="primary big"),
                Button("Reset everything", reset),
                classes="actions"),
            classes="card",
        ),
    ])


@route
def set_home(state: State, home_name: str, home_x: str, home_y: str) -> Page:
    """Validate and save the home location."""
    x_value = parse_number(home_x)
    y_value = parse_number(home_y)
    state.home_notice = ""
    state.stop_notice = ""
    if home_name.strip() == "":
        state.message = "Home needs a name."
    elif x_value is None or y_value is None:
        state.message = "Home coordinates must be numbers."
    else:
        state.home = Location(home_name.strip(), x_value, y_value)
        state.best_route = []  # old result no longer matches this home
        state.best_distance = 0.0
        state.message = ""
        state.home_notice = f"Home is set to {describe_stop(state.home)}."
    return stops_page(state)


@route
def add_stop(state: State, stop_name: str, x_text: str,
             y_text: str) -> Page:
    """Validate a new stop and add it to the list."""
    name = stop_name.strip()
    x_value = parse_number(x_text)
    y_value = parse_number(y_text)
    state.home_notice = ""
    state.stop_notice = ""
    if name == "":
        state.message = "A stop needs a name."
    elif x_value is None or y_value is None:
        state.message = "Coordinates must be numbers."
    elif name_is_taken(state.stops, name):
        state.message = f"A stop named '{name}' already exists."
    else:
        state.stops.append(Location(name, x_value, y_value))
        state.best_route = []  # old result no longer matches these stops
        state.best_distance = 0.0
        state.message = ""
        state.stop_notice = f"Added {describe_stop(state.stops[-1])}."
    return stops_page(state)


@route
def remove_stop(state: State, stop_name: str) -> Page:
    """Remove the stop with the given name."""
    for stop in state.stops:
        if stop.name == stop_name:
            state.stops.remove(stop)
            break
    state.best_route = []
    state.best_distance = 0.0
    state.message = ""
    state.home_notice = ""
    state.stop_notice = ""
    return stops_page(state)


@route
def calculate_route(state: State) -> Page:
    """Run the brute-force search and go to the results page."""
    if len(state.stops) < MIN_STOPS:
        state.message = f"Add at least {MIN_STOPS} stop(s) first."
        return stops_page(state)
    state.best_route, state.best_distance = find_best_route(
        state.home, state.stops)
    state.message = ""
    return results(state)


@route
def results(state: State) -> Page:
    """Show the best route on a map, with each leg's distance."""
    if len(state.best_route) == 0:
        state.message = "Calculate a route first."
        return stops_page(state)

    legs = leg_distances(state.home, state.best_route)
    names = [state.home.name]
    for stop in state.best_route:
        names.append(stop.name)
    names.append(state.home.name)

    leg_rows = []
    for number, leg in enumerate(legs):
        leg_rows.append(leg_row(number + 1, names[number],
                                names[number + 1], leg))

    return shell(state, 2, [
        Header("Your best route", 1, classes="page-title"),
        Div("The shortest round trip that visits every stop.", classes="sub"),
        Div(
            stat_card(f"{round(state.best_distance, DECIMALS)} mi",
                      "Straight-line distance"),
            stat_card(str(len(state.best_route)), "Stops"),
            stat_card(f"{round(driving_miles(state.best_distance), DECIMALS)}"
                      " mi", "Estimated driving"),
            classes="stats",
        ),
        Div(RawHTML(route_svg(state.home, state.best_route)),
            classes="card map-card"),
        Div(Header("🛣️ Leg by leg", 2), *leg_rows, classes="card"),
        Div(Button("Estimate trip costs →", trip_settings,
                   classes="primary big"),
            Button("Edit stops", stops_page),
            Button("Start over", reset),
            classes="actions"),
    ])


@route
def trip_settings(state: State) -> Page:
    """Page where the user enters trip details used for the cost estimate."""
    if len(state.best_route) == 0:
        state.message = "Calculate a route first."
        return stops_page(state)

    trip_card = Div(
        Header("🚗 Your trip", 2),
        field("Vehicle mileage (miles per gallon)",
              TextBox("mpg_text", str(state.mileage))),
        field(f"Trip length (days, 1-{MAX_TRIP_DAYS})",
              TextBox("days_text", str(state.trip_days))),
        field(f"Travelers (1-{MAX_TRAVELERS})",
              TextBox("people_text", str(state.travelers))),
        Div(CheckBox("tolls_on", state.include_tolls),
            Span("Include estimated tolls"), classes="check-row"),
        classes="card",
    )
    level_card = Div(
        Header("✨ Comfort levels", 2),
        field("Food expense level",
              SelectBox("food_pick", level_options(),
                        level_option(state.food_expense_level))),
        field("Housing expense level",
              SelectBox("housing_pick", level_options(),
                        level_option(state.housing_expense_level))),
        Details("What do the levels cost?",
                Table(level_guide_rows(),
                      header=["Level", "Food / person / day",
                              "Housing / room / night"])),
        classes="card",
    )
    return shell(state, 3, [
        Header("Tell us about the trip", 1, classes="page-title"),
        Div("A few details and we'll price out the whole adventure.",
            classes="sub"),
        *error_banner(state.message),
        Div(trip_card, level_card, classes="grid-2"),
        Div(Button("Calculate cost →", save_settings, classes="primary big"),
            Button("Back to route", results), classes="actions"),
    ])


@route
def save_settings(state: State, mpg_text: str, days_text: str,
                  people_text: str, food_pick: str,
                  housing_pick: str, tolls_on: bool) -> Page:
    """Validate the trip details, save them, and show the cost breakdown."""
    mileage = parse_number(mpg_text)
    days = parse_int(days_text)
    travelers = parse_int(people_text)
    if mileage is None or mileage <= 0:
        state.message = "Mileage must be a number greater than 0."
    elif days is None or days < 1 or days > MAX_TRIP_DAYS:
        state.message = f"Days must be a whole number from 1 to {MAX_TRIP_DAYS}."
    elif travelers is None or travelers < 1 or travelers > MAX_TRAVELERS:
        state.message = (f"Travelers must be a whole number from 1 to "
                         f"{MAX_TRAVELERS}.")
    else:
        state.mileage = mileage
        state.trip_days = days
        state.travelers = travelers
        state.food_expense_level = parse_level(food_pick)
        state.housing_expense_level = parse_level(housing_pick)
        state.include_tolls = tolls_on
        state.message = ""
        return cost_breakdown(state)
    return trip_settings(state)


@route
def cost_breakdown(state: State) -> Page:
    """Show the trip cost by category, for the whole trip and per person."""
    if len(state.best_route) == 0:
        state.message = "Calculate a route first."
        return stops_page(state)

    costs = estimate_costs(state)
    total = total_cost(costs)
    miles = driving_miles(state.best_distance)
    toll_chip = "🛣️ Tolls included" if state.include_tolls else "🛣️ No tolls"
    food_label = LEVEL_LABELS[state.food_expense_level - 1]
    housing_label = LEVEL_LABELS[state.housing_expense_level - 1]
    chips = [
        f"📅 {state.trip_days} days", f"👥 {state.travelers} travelers",
        f"🚗 {round(miles, DECIMALS)} driving mi", f"⛽ {state.mileage} mpg",
        toll_chip, f"🍽️ Food: {food_label}", f"🏨 Housing: {housing_label}",
    ]
    chip_spans = []
    for text in chips:
        chip_spans.append(Span(text, classes="chip"))

    return shell(state, 4, [
        Header("Your trip budget", 1, classes="page-title"),
        Div(*chip_spans, classes="sub"),
        Div(
            Div(Div("Whole trip", classes="caption"),
                Div(money(total), classes="big-money")),
            Div(Div("Per person", classes="caption"),
                Div(money(total / state.travelers), classes="big-money")),
            classes="card total-hero",
        ),
        Div(Header("Where the money goes", 2), *cost_bar(costs),
            classes="card"),
        category_cards(costs, state.travelers),
        Details("See the full table",
                Table(cost_rows(costs, state.travelers),
                      header=["Category", "Whole trip", "Per person"])),
        Div(Button("Change trip details", trip_settings),
            Button("Back to route", results),
            Button("Plan another trip", reset, classes="primary"),
            classes="actions"),
    ])


@route
def reset(state: State) -> Page:
    """Clear all trip data and return to the welcome page."""
    fresh = new_state()
    state.home = fresh.home
    state.stops = fresh.stops
    state.best_route = fresh.best_route
    state.best_distance = fresh.best_distance
    state.message = ""
    state.home_notice = ""
    state.stop_notice = ""
    state.mileage = fresh.mileage
    state.trip_days = fresh.trip_days
    state.travelers = fresh.travelers
    state.food_expense_level = fresh.food_expense_level
    state.housing_expense_level = fresh.housing_expense_level
    state.include_tolls = fresh.include_tolls
    return index(state)


# ---------------------------------------------------------------------------
# Unit tests (run by "python road_trip_planner.py" before the site starts)
# Routes that only build a page (index, stops_page, results, trip_settings,
# cost_breakdown) can't be meaningfully compared, so their logic lives in
# helper functions that are tested instead; the pages themselves are checked
# by running the site and clicking through it. The Drafter component builders
# (shell, step_bar, stop_card, cost_bar...) only assemble components, so they
# are checked the same way.
# ---------------------------------------------------------------------------

def test_route_finding() -> None:
    """Unit tests for the Step 1 helper functions."""
    home = Location("Home", 0.0, 0.0)
    east = Location("East", 0.0, 1.0)    # 1 degree of longitude at equator
    north = Location("North", 1.0, 0.0)  # 1 degree of latitude
    corner = Location("Corner", 1.0, 1.0)

    # parse_number / parse_int
    assert_equal(parse_number(" 3.5 "), 3.5)
    assert_equal(parse_number("-2"), -2.0)
    assert_equal(parse_number("abc"), None)
    assert_equal(parse_number(""), None)
    assert_equal(parse_int(" 4 "), 4)
    assert_equal(parse_int("2.5"), None)
    assert_equal(parse_int("x"), None)

    # distance (degrees -> miles)
    assert_equal(distance(home, east), 69.0)
    assert_equal(distance(home, north), 69.0)
    assert_equal(distance(east, east), 0.0)
    assert_equal(distance(east, home), distance(home, east))

    # route_length: around the square is about 4 * 69 miles
    assert_equal(round(route_length(home, [east, corner, north])), 276)
    assert_equal(route_length(home, [east]), 138.0)
    assert_equal(route_length(home, []), 0.0)

    # name_is_taken
    assert_equal(name_is_taken([east, north], "east"), True)
    assert_equal(name_is_taken([east, north], "Z"), False)
    assert_equal(name_is_taken([], "A"), False)

    # all_orderings
    assert_equal(len(all_orderings([east, north, corner])), 6)
    assert_equal(all_orderings([east]), [[east]])
    assert_equal(all_orderings([east, north]),
                 [[east, north], [north, east]])

    # find_best_route: going around the square beats zig-zagging
    best_order, best_length = find_best_route(home, [east, north, corner])
    assert_equal(round(best_length), 276)
    assert_equal(corner in best_order, True)
    assert_equal(len(best_order), 3)

    # find_best_route with one stop: the trip is Home -> stop -> Home
    assert_equal(find_best_route(home, [east]), ([east], 138.0))

    # leg_distances: one more leg than stops
    legs = leg_distances(home, [east, corner, north])
    assert_equal(len(legs), 4)
    assert_equal(legs[0], 69.0)

    # describe_stop
    assert_equal(describe_stop(east), "East (0.0, 1.0)")


def test_cost_helpers() -> None:
    """Unit tests for the Step 2 cost helper functions."""
    assert_equal(level_option(3), "3 - Standard")
    assert_equal(len(level_options()), 5)
    assert_equal(parse_level("5 - Luxury"), 5)
    assert_equal(parse_level("nonsense"), DEFAULT_LEVEL)
    assert_equal(parse_level("9 - Fake"), DEFAULT_LEVEL)

    assert_equal(driving_miles(100.0), 125.0)
    assert_equal(round(fuel_cost(125.0, 25.0), 2), 20.05)
    assert_equal(round(toll_cost(125.0, True), 2), 3.12)
    assert_equal(toll_cost(125.0, False), 0.0)
    assert_equal(parking_cost(3), 60.0)
    assert_equal(food_cost(3, 2, 3), 330.0)
    assert_equal(food_cost(1, 1, 1), 20.0)
    assert_equal(rooms_needed(1), 1)
    assert_equal(rooms_needed(2), 1)
    assert_equal(rooms_needed(3), 2)
    assert_equal(housing_cost(3, 2, 3), 240.0)   # 2 nights x 1 room x $120
    assert_equal(housing_cost(1, 4, 5), 0.0)     # one day: no nights
    assert_equal(housing_cost(2, 3, 1), 100.0)   # 1 night x 2 rooms x $50

    assert_equal(money(20.05), "$20.05")
    assert_equal(money(1234.5), "$1,234.50")


def test_estimates() -> None:
    """Unit tests for estimate_costs, total_cost and cost_rows."""
    state = new_state()
    state.best_route = [Location("A", 0.0, 1.0)]
    state.best_distance = 100.0
    state.include_tolls = True
    costs = estimate_costs(state)  # defaults: 25 mpg, 3 days, 2 people
    assert_equal(round(costs.fuel, 2), 20.05)
    assert_equal(round(costs.tolls, 2), 3.12)
    assert_equal(costs.parking, 60.0)
    assert_equal(costs.food, 330.0)
    assert_equal(costs.housing, 240.0)
    assert_equal(round(total_cost(costs)), 653)

    rows = cost_rows(costs, 2)
    assert_equal(len(rows), 6)
    assert_equal(rows[0][:2], ["Fuel", "$20.05"])
    assert_equal(rows[2], ["Parking", "$60.00", "$30.00"])
    assert_equal(rows[-1][0], "Total")

    # category_list and cost_shares
    assert_equal(len(category_list(costs)), 5)
    assert_equal(category_list(costs)[2], ("Parking", 60.0))
    simple = TripCosts(25.0, 25.0, 50.0, 0.0, 0.0)
    assert_equal(cost_shares(simple), [25.0, 25.0, 50.0, 0.0, 0.0])
    assert_equal(cost_shares(TripCosts(0.0, 0.0, 0.0, 0.0, 0.0)),
                 [0.0, 0.0, 0.0, 0.0, 0.0])

    # level_guide_rows
    guide = level_guide_rows()
    assert_equal(len(guide), 5)
    assert_equal(guide[0], ["1 - Budget", "$20.00", "$50.00"])


def test_look_and_feel() -> None:
    """Unit tests for the helpers behind the progress bar and route map."""
    # step_class
    assert_equal(step_class(1, 3), "done")
    assert_equal(step_class(3, 3), "active")
    assert_equal(step_class(4, 3), "todo")

    # short_name
    assert_equal(short_name("Dover", 14), "Dover")
    assert_equal(short_name("Philadelphia International", 8), "Philade...")

    # project_points: two points on the equator fill the drawing width
    two = [Location("a", 0.0, 0.0), Location("b", 0.0, 2.0)]
    assert_equal(project_points(two, 100.0, 100.0, 10.0),
                 [(10.0, 50.0), (90.0, 50.0)])
    # a single point is centered
    assert_equal(project_points([Location("a", 5.0, 5.0)], 100.0, 60.0, 10.0),
                 [(50.0, 30.0)])
    # north is up: the northern point has the smaller pixel y
    tall = [Location("s", 0.0, 0.0), Location("n", 2.0, 0.0)]
    pixels = project_points(tall, 100.0, 100.0, 10.0)
    assert_equal(pixels[1][1] < pixels[0][1], True)

    # route_svg: draws the places and escapes dangerous names
    svg = route_svg(Location("Home", 0.0, 0.0),
                    [Location("<b>Hi</b>", 1.0, 1.0)])
    assert_equal(svg.startswith("<svg"), True)
    assert_equal("<b>" in svg, False)
    assert_equal("&lt;b&gt;" in svg, True)
    assert_equal("polyline" in svg, True)


def test_routes() -> None:
    """Unit tests for the routes that change the State."""
    # add_stop (valid and each invalid case)
    state = new_state()
    add_stop(state, "Dover", "39.16", "-75.52")
    assert_equal(state.stops, [Location("Dover", 39.16, -75.52)])
    add_stop(state, "", "1", "1")
    assert_equal(state.message, "A stop needs a name.")
    add_stop(state, "X", "one", "1")
    assert_equal(state.message, "Coordinates must be numbers.")
    add_stop(state, "dover", "1", "1")
    assert_equal(len(state.stops), 1)

    # no upper limit on the number of stops
    many = new_state()
    for number in range(12):
        add_stop(many, f"S{number}", str(number), "0")
    assert_equal(len(many.stops), 12)

    # remove_stop
    remove_stop(state, "Dover")
    assert_equal(state.stops, [])

    # set_home
    set_home(state, "Newark", "39.68", "-75.75")
    assert_equal(state.home, Location("Newark", 39.68, -75.75))
    assert_equal(state.home_notice, "Home is set to Newark (39.68, -75.75).")
    set_home(state, "Bad", "x", "3")
    assert_equal(state.home, Location("Newark", 39.68, -75.75))

    # calculate_route: no stops fails, one stop works (Home -> stop -> Home)
    state = new_state()
    calculate_route(state)
    assert_equal(state.best_route, [])
    assert_equal(state.message, "Add at least 1 stop(s) first.")
    add_stop(state, "A", "0", "1")
    calculate_route(state)
    assert_equal(len(state.best_route), 1)
    assert_equal(state.best_distance, 138.0)

    # two stops also work
    add_stop(state, "B", "1", "0")
    calculate_route(state)
    assert_equal(len(state.best_route), 2)
    assert_equal(state.best_distance > 200.0, True)

    # save_settings: valid input updates every setting
    save_settings(state, "30", "4", "3", "4 - Comfort", "2 - Economy", True)
    assert_equal(state.mileage, 30.0)
    assert_equal(state.trip_days, 4)
    assert_equal(state.travelers, 3)
    assert_equal(state.food_expense_level, 4)
    assert_equal(state.housing_expense_level, 2)
    assert_equal(state.include_tolls, True)
    assert_equal(state.message, "")

    # save_settings: invalid input is rejected and old values are kept
    save_settings(state, "0", "4", "3", "1 - Budget", "1 - Budget", False)
    assert_equal(state.mileage, 30.0)
    assert_equal(state.message, "Mileage must be a number greater than 0.")
    save_settings(state, "30", "2.5", "3", "1 - Budget", "1 - Budget", False)
    assert_equal(state.trip_days, 4)
    save_settings(state, "30", "99", "3", "1 - Budget", "1 - Budget", False)
    assert_equal(state.trip_days, 4)
    save_settings(state, "30", "4", "0", "1 - Budget", "1 - Budget", False)
    assert_equal(state.travelers, 3)
    assert_equal(state.food_expense_level, 4)

    # reset puts everything back to the defaults
    reset(state)
    assert_equal(state.stops, [])
    assert_equal(state.best_distance, 0.0)
    assert_equal(state.mileage, DEFAULT_MPG)
    assert_equal(state.trip_days, DEFAULT_TRIP_DAYS)
    assert_equal(state.include_tolls, False)


def run_tests() -> None:
    """Run every group of unit tests."""
    test_route_finding()
    test_cost_helpers()
    test_estimates()
    test_look_and_feel()
    test_routes()


if __name__ == "__main__":
    run_tests()
    apply_theme()
    start_server(new_state(), in_debug_mode=False)
