#!/usr/bin/env python3
"""Exports the dashboard saved objects to an .ndjson import file (with references)."""
import json
import urllib.request

DASH = "http://localhost:5601"
AUTH = "Basic YWRtaW46YWRtaW4="

OBJECTS = [
    ("index-pattern", "factory-log-all"),
    ("index-pattern", "factory-log-tanks"),
    ("index-pattern", "factory-log-valves"),
    ("visualization", "factory-health"),
    ("visualization", "tank-state"),
    ("visualization", "temp-by-tank"),
    ("visualization", "capacity-by-tank"),
    ("visualization", "pressure-by-tank"),
    ("visualization", "heat-cool"),
    ("visualization", "events-over-time"),
    ("visualization", "volume-by-sim"),
    ("visualization", "valve-status"),
    ("visualization", "valve-open-rate"),
    ("dashboard", "virtual-factory-overview"),
]

INDEX_BY_VIZ = {
    "factory-health": "factory-log-all",
    "tank-state": "factory-log-tanks",
    "temp-by-tank": "factory-log-tanks",
    "capacity-by-tank": "factory-log-tanks",
    "pressure-by-tank": "factory-log-tanks",
    "heat-cool": "factory-log-tanks",
    "events-over-time": "factory-log-all",
    "volume-by-sim": "factory-log-all",
    "valve-status": "factory-log-valves",
    "valve-open-rate": "factory-log-valves",
}


def get(path):
    req = urllib.request.Request(DASH + path)
    req.add_header("Authorization", AUTH)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


lines = []
for type_, oid in OBJECTS:
    obj = get(f"/api/saved_objects/{type_}/{oid}")
    attrs = obj["attributes"]
    refs = []
    if type_ == "visualization":
        refs.append({
            "name": "kibanaSavedObjectMeta.searchSourceJSON.index",
            "type": "index-pattern",
            "id": INDEX_BY_VIZ[oid],
        })
    if type_ == "dashboard":
        for panel in json.loads(attrs["panelsJSON"]):
            refs.append({"name": f"panel_{panel['panelIndex']}", "type": "visualization", "id": panel["id"]})
    lines.append({
        "id": oid,
        "type": type_,
        "attributes": attrs,
        "references": refs,
        "migrationVersion": {},
        "updated_at": obj.get("updated_at", ""),
        "version": obj.get("version"),
    })

with open("opensearch/virtual-factory.ndjson", "w") as f:
    for line in lines:
        f.write(json.dumps(line) + "\n")
print(f"wrote {len(lines)} objects to opensearch/virtual-factory.ndjson")
