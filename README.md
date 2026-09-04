# Wingz Ride API

A Django REST Framework API for managing rides, users, and ride events.

## Setup

```bash
git clone <repo-url> && cd wingz-ride-api
python -m venv .venv        # Windows: py -m venv .venv
source .venv/bin/activate   # Windows: source .venv/Scripts/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo --rides 200
python manage.py runserver
```

For test purposed use the Seeded admin: `admin@wingz.test` / `admin12345`. SQLite by default; Postgres is used
whenever `POSTGRES_DB` is set, which is what `docker compose up --build` does.

Token auth:

```bash
python manage.py drf_create_token admin@wingz.test
curl -H "Authorization: Token <token>" http://localhost:8000/api/rides/
```

## Endpoints

`/api/rides/`, `/api/ride-events/`, `/api/users/` — full CRUD via DRF viewsets.
All require an authenticated user whose `role` is `admin`; unauthenticated requests
get 401, authenticated non-admins get 403.

Ride list parameters: `status`, `rider_email`, `rider_email_contains`, `ordering`
(`pickup_time`, `-pickup_time`, `distance`, `-distance`), `pickup_lat` and
`pickup_lng` (required for distance ordering), `radius_km`, `page`, `page_size`.

```
GET /api/rides/?status=pickup&ordering=distance&pickup_lat=14.5995&pickup_lng=120.9842&radius_km=25
```

## Design decisions

**Three queries.** The ride list runs in three queries at any page size: rides
joined to rider and driver via `select_related`, one `IN` query for ride events via
`Prefetch`, and the paginator's `COUNT`. This is asserted with
`assertNumQueries(3)`, plus a second test that adds twenty rides and confirms the
count does not move. Tests use `force_authenticate`, so real requests add one token
lookup.

`**todays_ride_events`.** The 24-hour filter lives inside the `Prefetch` queryset, so
it becomes part of the SQL and the full event history is never loaded. `to_attr`
puts the result in a plain list, which the serializer reads directly. The two
alternatives both fail the requirement: a `SerializerMethodField` calling
`obj.ride_events.filter(...)` builds a new queryset that bypasses the prefetch cache
and fires once per ride, while a plain `prefetch_related("ride_events")` loads every
event ever recorded before filtering in Python.

**Related events vs the 24-hour set.** The spec asks each ride to include its related
ride events and separately forbids loading the full list. Those pull against each
other, so the list endpoint exposes the 24-hour set, and full history stays available
per ride at `/api/ride-events/?id_ride=<id>`, which is paginated. Happy to change
this if the requirement was meant differently.

**Distance sorting.** Distance is a haversine expression built from Django ORM math
functions, so `ORDER BY` and `LIMIT` both happen in the database. Sorting in Python
would return an arbitrary page correctly sorted among itself, which looks right and
is wrong. `Least(1.0, ...)` guards the `ACOS` domain against float rounding.

A computed expression cannot use an index, so ordering by distance over a large ride
table means a full scan. `radius_km` engages a bounding-box prefilter on the indexed
latitude and longitude columns, narrowing the candidate set before the trigonometry
runs; the box is a superset of the circle, so the exact haversine still decides the
ordering. At real scale the right answer is PostGIS with a GiST index, left out here
because the spec fixes the table structure to plain floats.

**Ordering stability.** Every ordering ends with `id_ride`. Without a unique
tiebreaker, rows sharing a sort value can appear on two pages or on none, since each
paginated request is its own `LIMIT`/`OFFSET` query.

**Schema.** Foreign keys use an explicit `db_column`, otherwise Django would name the
columns `id_rider_id` and the schema would not match the spec. `User` is a custom
`AUTH_USER_MODEL` on `AbstractBaseUser` with `email` as the username field. Indexes
follow the access patterns actually used: `(status, pickup_time)` for filter-plus-sort,
`(id_ride, -created_at)` for the event prefetch, `(description, created_at)` for the
report below.

**Read and write serializers are separate**, so nested rider and driver output does
not require writable nested serializers on input.

## Bonus: SQL report

Trips over one hour, grouped by month and driver (PostgreSQL):

```sql
SELECT
    to_char(pickup.created_at, 'YYYY-MM')       AS "Month",
    d.first_name || ' ' || LEFT(d.last_name, 1) AS "Driver",
    COUNT(*)                                    AS "Count of Trips > 1 hr"
FROM ride r
JOIN ride_event pickup
      ON pickup.id_ride = r.id_ride
     AND pickup.description = 'Status changed to pickup'
JOIN ride_event dropoff
      ON dropoff.id_ride = r.id_ride
     AND dropoff.description = 'Status changed to dropoff'
JOIN "user" d ON d.id_user = r.id_driver
WHERE dropoff.created_at - pickup.created_at > INTERVAL '1 hour'
GROUP BY 1, 2
ORDER BY 1, 2;
```

SQLite equivalent, for anyone running without Postgres: replace `to_char(...)` with
`strftime('%Y-%m', pickup.created_at)`, `LEFT(d.last_name, 1)` with
`substr(d.last_name, 1, 1)`, and the interval comparison with
`(julianday(dropoff.created_at) - julianday(pickup.created_at)) * 24 > 1`.

The two self-joins pair each ride's pickup with its dropoff on one row, so the
duration is a single subtraction rather than a correlated subquery. The month comes
from the pickup timestamp, so a trip crossing midnight counts in the month it
started. Rides missing either event are dropped by the inner joins, which is
intended: an incomplete trip has no measurable duration.

## Tests

```bash
python manage.py test rides
```

**14** tests covering the query budget, role-based access, the 24-hour window,  
filtering, both sort modes, pagination under distance sorting, and input validation.