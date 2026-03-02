# clinician-safety-monitor

This is a service that monitors the real-time locations of phlebotomists and sends an email alert when any of them leave their designated zone.

## Overview

The service polls a clinician status API every 30 seconds for a list of clinician IDs. Each API response returns a GeoJSON FeatureCollection containing the clinician's current position as a Point and their expected zone as a Polygon. I then check whether the clinician's position falls inside the zone (on the boundary counts as outside) and sends an email alert the first time they are detected outside it.

If a clinician is already outside their zone, no repeat emails are sent unless they return to their zone and leave again later.

## Boundary Handling

This is done in two steps:

1. **Boundary check**: for each edge of the polygon, I used a cross product to check if the point is collinear with the edge, and a dot product to check if it falls within the segment's endpoints. If both pass, the point is on the boundary and is said to be outside the zone.

2. **Ray casting**: if the point is not on the boundary, a horizontal ray is cast from the point and the number of polygon edges it crosses is counted. An odd number of crossings means the point is inside, even means outside. Ray casting is necessary because the zone polygons can be any irregular shape.

## Main Loop Logic

The main loop runs indefinitely, getting data from each clinician every 30 seconds. For each clinician, it fetches their current position and zone from the API, checks if they are inside the zone, and sends an alert if they are not.
I noticed that the API was at one point returning more than 1 zone for a clinician, so I added logic to just grab the first polygon it finds and ignore the rest.
An alerted set tracks which clinicians have already triggered an alert. The first time a clinician is detected outside their zone they are added to the set and an email is sent. If they are still outside on the next poll, nothing happens. If they return to their zone they are removed from the set, so a new alert will fire if they leave again later.

## Setup

Install dependencies:

pip install -r requirements.txt

Set environment variables:

export SMTP_USERNAME="your@gmail.com"
export APP_PASSWORD="your_app_password"
export FROM_EMAIL="your@gmail.com"

To run it:

python main.py

## Configuration

- SMTP_USERNAME: Gmail address to send alerts from
- APP_PASSWORD: Gmail app password
- FROM_EMAIL: Sending email address
- TO_EMAIL: Receiving email address (defaults to Sprinter's alert inbox)