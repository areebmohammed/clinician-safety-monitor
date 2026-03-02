import os
import time
import smtplib
from email.message import EmailMessage
import requests

CLINICIAN_STATUS_API = "https://3qbqr98twd.execute-api.us-west-2.amazonaws.com/test"
CLINICIAN_IDS = [1, 2, 3, 4, 5, 6, 7]
INTERVAL = 30

HOST = "smtp.gmail.com"
PORT = 587
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "")
TO_EMAIL = os.getenv("TO_EMAIL", "coding-challenges+clin-alerts@sprinterhealth.com")

# checks if the given point lies on the boundary of the zone polygon for each edge
# uses cross product to see if it's collinear and dot product to see if its within the segment
# returns True if it is within the small buffer to account for floating precision errors, otherwise False
def on_edge(point, polygon):
    x, y = point
    for i in range(len(polygon) - 1):
        x1, y1 = polygon[i]
        x2, y2 = polygon[i + 1]

        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        dot = (x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)

        if abs(cross) <= 1e-12 and dot >= -1e-12 and dot - ((x2 - x1) ** 2 + (y2 - y1) ** 2) <= 1e-12:
            return True
    return False

# checks if the point is inside the zone boundary
# uses ray casting to account for the possibility that the zone may not be a rectangle (blobs, circles, etc.)
#    if the ray crosses at odd boundaries it's inside and otherwise it's outside
# on the boundary counts as outside
# returns True if the point is strictly inside the polygon and False otherwise
def in_zone(point, polygon):
    if on_edge(point, polygon):
        return False

    x, y = point
    inside = False

    for i in range(len(polygon) - 1):
        x1, y1 = polygon[i]
        x2, y2 = polygon[i + 1]

        if (y1 > y) != (y2 > y):
            if x1 + (y - y1) * (x2 - x1) / (y2 - y1) > x:
                inside = not inside

    return inside

# sends an email alert that the clinician ID is out of the zone
def alert(clinician_id):
    msg = EmailMessage()
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    msg["Subject"] = f"[Clinician Safety Alert] Clinician {clinician_id} out of zone"
    msg.set_content(f"Clinician ID {clinician_id} is out of the designated safety zone.")

    with smtplib.SMTP(HOST, PORT, timeout=10) as server:
        server.starttls()
        if SMTP_USERNAME and APP_PASSWORD:
            server.login(SMTP_USERNAME, APP_PASSWORD)
        server.send_message(msg)

# calls the API to get the current geolocation of a clinician
# returns the response as a dictionary or None if the request fails
def get_clinician(clinician_id):
    try:
        r = requests.get(f"{CLINICIAN_STATUS_API}/clinicianstatus/{clinician_id}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

# polls the API every 30 seconds for each clinician ID
# sends an email alert the first time they are detected outside their zone (sends only once until they get back and leave again)
# boundary counts as outside per requirements
def main():
    alerted = set()

    while True:
        for clinician in CLINICIAN_IDS:
            data = get_clinician(clinician)
            if not data:
                continue

            try:
                features = data["features"]
                coordinates = None
                polygon = None
                for f in features:
                    if f["geometry"]["type"] == "Point" and coordinates is None:
                        coordinates = f["geometry"]["coordinates"]
                    if f["geometry"]["type"] == "Polygon" and polygon is None:
                        polygon = f["geometry"]["coordinates"][0]
                if not coordinates or not polygon:
                    continue
                point = (coordinates[0], coordinates[1])
                zone = [(p[0], p[1]) for p in polygon]
                if zone[0] != zone[-1]:
                    zone.append(zone[0])
            except Exception:
                continue

            if not in_zone(point, zone):
                if clinician not in alerted:
                    alerted.add(clinician)
                    alert(clinician)
            else:
                if clinician in alerted:
                    alerted.discard(clinician)

        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()