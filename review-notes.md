## app/schema/trip.py
- [TripCreate.include_home_city](app/schema/trip.py) is not used consistently in trip creation, so we should either remove it 
- [TripCreate.stops](app/schema/trip.py) should be removed if trips are not meant to accept stops at creation time, because the router currently turns this field into `Stop` rows.
- [TripOut](app/schema/trip.py) duplicates [TripBaseOut](app/schema/trip.py); keep one response schema to avoid repetition.
- If the intent is to store the user's home city, rename [Trip.city_id](app/models/trip.py) to `home_city_id` everywhere instead of using a generic `city_id`.

## app/router/trip.py
- The `Trip(...)` constructor in [create_trip](app/router/trip.py) does not consistently reflect the trip-city relationship, so the field used here should match the model rename or be removed.
- The block that builds `stops_to_create` in [create_trip](app/router/trip.py) is where route input is normalized into stop rows.
- The loop in [create_trip](app/router/trip.py) creates a brand new `City` for every stop on every trip, which will duplicate the same real-world city data many times; prefer reusing an existing city record by lookup, or store route points in a separate table instead of inserting into `City` here, or delate the city tables intirelly a we have stops
- If trip creation should not create stops yet, remove the `for stop_input in stops_to_create:` block from [create_trip](app/router/trip.py) and keep stop creation in a separate endpoint.
- The `get_my_trips` empty branch is broken because the `return` exits before `TripBaseOut(...)`, so the endpoint can return `None` instead of the declared `TripsOut` shape.
- Stop ordering is inconsistent across endpoints: trip creation hardcodes `0`/`1`, `add_stop` starts new stops at `1`, and `reorder_stops` rewrites from `0`, so the API should use one ordering rule everywhere.

## app/models/trip.py
- Add cascade behavior to [Trip.stops](app/models/trip.py) so deleting a trip also deletes its stops.





