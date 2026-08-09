#!/usr/bin/env python3
"""
Creates a "Virtual Factory Overview" dashboard in OpenSearch Dashboards via the
saved-objects API. Idempotent: overwrites existing objects with the same ids.
"""
import json
import urllib.request
import urllib.error

DASH = "http://localhost:5601"
AUTH = "Basic YWRtaW46YWRtaW4="  # admin:admin

INDEX_PATTERNS = {
    "factory-log-all": "factory-log-*",
    "factory-log-tanks": "factory-log-tank1-*,factory-log-tank2-*,factory-log-recolector-*",
    "factory-log-valves": "factory-log-*valve-*",
}


def request(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(DASH + path, data=data, method=method)
    req.add_header("Authorization", AUTH)
    req.add_header("Content-Type", "application/json")
    req.add_header("osd-xsrf", "true")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def upsert(type_, obj_id, attrs):
    code, resp = request("DELETE", f"/api/saved_objects/{type_}/{obj_id}")
    print(f"  delete {type_}/{obj_id}: {code}")
    code, resp = request("POST", f"/api/saved_objects/{type_}/{obj_id}", {"attributes": attrs})
    print(f"  create {type_}/{obj_id}: {code}")
    if code >= 400:
        print("    ERROR:", json.dumps(resp, indent=2))
    return code


def search_source(index_id, query=""):
    return json.dumps({
        "index": index_id,
        "query": {"language": "lucene", "query": query},
        "filter": [],
    })


def vis_obj(title, vis_state, index_id, query=""):
    return {
        "title": title,
        "visState": json.dumps(vis_state),
        "kibanaSavedObjectMeta": {"searchSourceJSON": search_source(index_id, query)},
    }


def line_chart(title, index_id, metric_field, metric_label):
    return {
        "title": title,
        "type": "line",
        "aggs": [
            {"id": "1", "type": "avg", "schema": "metric",
             "params": {"field": metric_field, "customLabel": metric_label}},
            {"id": "2", "type": "date_histogram", "schema": "segment",
             "params": {"field": "timestamp", "interval": "auto", "min_doc_count": 1, "extended_bounds": {}}},
            {"id": "3", "type": "terms", "schema": "group",
             "params": {"field": "name.keyword", "size": 5, "order": "desc", "orderBy": "1"}},
        ],
        "params": {
            "type": "line", "grid": {"categoryLines": False},
            "categoryAxes": [{"id": "CategoryAxis-1", "type": "category", "position": "bottom",
                              "show": True, "style": {}, "scale": {"type": "linear"},
                              "labels": {"show": True}, "title": {}}],
            "valueAxes": [{"id": "ValueAxis-1", "type": "value", "position": "left", "show": True,
                           "style": {}, "scale": {"type": "linear", "mode": "normal"},
                           "labels": {"show": True}, "title": {"text": metric_label}}],
            "seriesParams": [{"show": True, "type": "line", "mode": "normal",
                              "data": {"label": metric_label, "id": "1"},
                              "valueAxis": "ValueAxis-1", "drawLinesBetweenPoints": True, "showCircles": True}],
            "addTooltip": True, "addLegend": True, "legendPosition": "right", "timeseries": [],
            "addTimeMarker": False,
            "thresholdLine": {"show": False, "value": 10, "width": 1, "style": "dashed", "color": "#E7664C"},
            "labels": {},
        },
    }


def main():
    print("== index patterns ==")
    for idx_id, title in INDEX_PATTERNS.items():
        upsert("index-pattern", idx_id, {"title": title, "timeFieldName": "timestamp"})

    print("\n== visualizations ==")
    vizzes = {}

    vizzes["factory-health"] = vis_obj(
        "Factory health",
        {
            "title": "Factory health", "type": "metric",
            "aggs": [
                {"id": "1", "type": "count", "schema": "metric", "params": {"customLabel": "Events"}},
                {"id": "2", "type": "filter", "schema": "metric",
                 "params": {"customLabel": "Active bugs", "filter": {"query_string": {"query": "bug_active:true"}}}},
                {"id": "3", "type": "filter", "schema": "metric",
                 "params": {"customLabel": "Running bugs", "filter": {"query_string": {"query": "running_bugs:true"}}}},
            ],
            "params": {"fontSize": 22, "handleNoResults": True},
        },
        "factory-log-all")

    vizzes["tank-state"] = vis_obj(
        "Tank state",
        {
            "title": "Tank state", "type": "metric",
            "aggs": [
                {"id": "1", "type": "avg", "schema": "metric", "params": {"field": "temp", "customLabel": "Avg Temp (°C)"}},
                {"id": "2", "type": "avg", "schema": "metric", "params": {"field": "capacity", "customLabel": "Avg Capacity"}},
                {"id": "3", "type": "avg", "schema": "metric", "params": {"field": "pressure", "customLabel": "Avg Pressure"}},
            ],
            "params": {"fontSize": 20, "handleNoResults": True},
        },
        "factory-log-tanks")

    vizzes["temp-by-tank"] = vis_obj(
        "Temperature by tank (°C)",
        line_chart("Temperature by tank (°C)", "factory-log-tanks", "temp", "Temperature (°C)"),
        "factory-log-tanks")

    vizzes["capacity-by-tank"] = vis_obj(
        "Capacity by tank",
        line_chart("Capacity by tank", "factory-log-tanks", "capacity", "Capacity"),
        "factory-log-tanks")

    vizzes["pressure-by-tank"] = vis_obj(
        "Pressure by tank",
        line_chart("Pressure by tank", "factory-log-tanks", "pressure", "Pressure"),
        "factory-log-tanks")

    vizzes["heat-cool"] = vis_obj(
        "Heat/Cool level",
        {
            "title": "Heat/Cool level", "type": "histogram",
            "aggs": [
                {"id": "1", "type": "count", "schema": "metric", "params": {}},
                {"id": "2", "type": "terms", "schema": "segment",
                 "params": {"field": "heat_cool_level", "size": 5, "order": "desc", "orderBy": "1"}},
            ],
            "params": {
                "type": "histogram", "grid": {"categoryLines": False},
                "categoryAxes": [{"id": "CategoryAxis-1", "type": "category", "position": "bottom",
                                  "show": True, "style": {}, "scale": {"type": "linear"},
                                  "labels": {"show": True}, "title": {}}],
                "valueAxes": [{"id": "ValueAxis-1", "type": "value", "position": "left", "show": True,
                               "style": {}, "scale": {"type": "linear", "mode": "normal"},
                               "labels": {"show": True}, "title": {"text": "Count"}}],
                "seriesParams": [{"show": True, "type": "histogram", "mode": "stacked",
                                  "data": {"label": "Count", "id": "1"}, "valueAxis": "ValueAxis-1",
                                  "drawLinesBetweenPoints": True, "showCircles": True}],
                "addTooltip": True, "addLegend": True, "legendPosition": "right", "timeseries": [],
                "labels": {"show": False},
                "thresholdLine": {"show": False, "value": 10, "width": 1, "style": "dashed", "color": "#E7664C"},
            },
        },
        "factory-log-tanks")

    vizzes["events-over-time"] = vis_obj(
        "Events over time",
        {
            "title": "Events over time", "type": "line",
            "aggs": [
                {"id": "1", "type": "count", "schema": "metric", "params": {}},
                {"id": "2", "type": "date_histogram", "schema": "segment",
                 "params": {"field": "timestamp", "interval": "auto", "min_doc_count": 1, "extended_bounds": {}}},
            ],
            "params": {
                "type": "line", "grid": {"categoryLines": False},
                "categoryAxes": [{"id": "CategoryAxis-1", "type": "category", "position": "bottom",
                                  "show": True, "style": {}, "scale": {"type": "linear"},
                                  "labels": {"show": True}, "title": {}}],
                "valueAxes": [{"id": "ValueAxis-1", "type": "value", "position": "left", "show": True,
                               "style": {}, "scale": {"type": "linear", "mode": "normal"},
                               "labels": {"show": True}, "title": {"text": "Count"}}],
                "seriesParams": [{"show": True, "type": "line", "mode": "normal",
                                  "data": {"label": "Count", "id": "1"}, "valueAxis": "ValueAxis-1",
                                  "drawLinesBetweenPoints": True, "showCircles": True}],
                "addTooltip": True, "addLegend": True, "legendPosition": "right", "timeseries": [],
                "addTimeMarker": False,
                "thresholdLine": {"show": False, "value": 10, "width": 1, "style": "dashed", "color": "#E7664C"},
                "labels": {},
            },
        },
        "factory-log-all")

    vizzes["volume-by-sim"] = vis_obj(
        "Log volume by simulator",
        {
            "title": "Log volume by simulator", "type": "pie",
            "aggs": [
                {"id": "1", "type": "count", "schema": "metric", "params": {}},
                {"id": "2", "type": "terms", "schema": "segment",
                 "params": {"field": "name.keyword", "size": 10, "order": "desc", "orderBy": "1"}},
            ],
            "params": {"type": "pie", "addTooltip": True, "addLegend": True, "legendPosition": "right",
                       "isDonut": True, "labels": {"show": False, "values": False, "last_level": False, "truncate": 100}},
        },
        "factory-log-all")

    vizzes["valve-status"] = vis_obj(
        "Valve open/closed",
        {
            "title": "Valve open/closed", "type": "metric",
            "aggs": [
                {"id": "1", "type": "filter", "schema": "metric",
                 "params": {"customLabel": "Open valves", "filter": {"query_string": {"query": "open:true"}}}},
                {"id": "2", "type": "filter", "schema": "metric",
                 "params": {"customLabel": "Closed valves", "filter": {"query_string": {"query": "open:false"}}}},
            ],
            "params": {"fontSize": 22, "handleNoResults": True},
        },
        "factory-log-valves")

    vizzes["valve-open-rate"] = vis_obj(
        "Open valves by name",
        {
            "title": "Open valves by name", "type": "horizontal_bar",
            "aggs": [
                {"id": "1", "type": "count", "schema": "metric", "params": {"customLabel": "Open count"}},
                {"id": "2", "type": "terms", "schema": "segment",
                 "params": {"field": "name.keyword", "size": 10, "order": "desc", "orderBy": "1"}},
            ],
            "params": {
                "type": "histogram", "grid": {"categoryLines": False},
                "categoryAxes": [{"id": "CategoryAxis-1", "type": "category", "position": "left",
                                  "show": True, "style": {}, "scale": {"type": "linear"},
                                  "labels": {"show": True}, "title": {}}],
                "valueAxes": [{"id": "ValueAxis-1", "type": "value", "position": "top", "show": True,
                               "style": {}, "scale": {"type": "linear", "mode": "normal"},
                               "labels": {"show": True}, "title": {"text": "Open count"}}],
                "seriesParams": [{"show": True, "type": "histogram", "mode": "stacked",
                                  "data": {"label": "Open count", "id": "1"}, "valueAxis": "ValueAxis-1",
                                  "drawLinesBetweenPoints": True, "showCircles": True}],
                "addTooltip": True, "addLegend": True, "legendPosition": "right", "timeseries": [],
                "labels": {"show": False},
                "thresholdLine": {"show": False, "value": 10, "width": 1, "style": "dashed", "color": "#E7664C"},
            },
        },
        "factory-log-valves",
        query="open:true")

    for vid, vobj in vizzes.items():
        upsert("visualization", vid, vobj)

    print("\n== dashboard ==")
    panels = [
        {"id": "factory-health", "type": "visualization", "panelIndex": "1", "size_x": 3, "size_y": 4, "col": 1, "row": 1},
        {"id": "tank-state", "type": "visualization", "panelIndex": "2", "size_x": 3, "size_y": 4, "col": 4, "row": 1},
        {"id": "valve-status", "type": "visualization", "panelIndex": "3", "size_x": 3, "size_y": 4, "col": 7, "row": 1},
        {"id": "volume-by-sim", "type": "visualization", "panelIndex": "4", "size_x": 3, "size_y": 4, "col": 10, "row": 1},
        {"id": "temp-by-tank", "type": "visualization", "panelIndex": "5", "size_x": 6, "size_y": 4, "col": 1, "row": 5},
        {"id": "capacity-by-tank", "type": "visualization", "panelIndex": "6", "size_x": 6, "size_y": 4, "col": 7, "row": 5},
        {"id": "pressure-by-tank", "type": "visualization", "panelIndex": "7", "size_x": 6, "size_y": 4, "col": 1, "row": 9},
        {"id": "valve-open-rate", "type": "visualization", "panelIndex": "8", "size_x": 6, "size_y": 4, "col": 7, "row": 9},
        {"id": "events-over-time", "type": "visualization", "panelIndex": "9", "size_x": 6, "size_y": 4, "col": 1, "row": 13},
        {"id": "heat-cool", "type": "visualization", "panelIndex": "10", "size_x": 6, "size_y": 4, "col": 7, "row": 13},
    ]
    dash_attrs = {
        "title": "Virtual Factory Overview",
        "description": "Factory telemetry: tanks, valves and alarm state.",
        "version": 1,
        "hits": 0,
        "panelsJSON": json.dumps(panels),
        "optionsJSON": json.dumps({"useMargins": True, "hidePanelTitles": False}),
        "timeRestore": True,
        "timeFrom": "now-24h",
        "timeTo": "now",
    }
    upsert("dashboard", "virtual-factory-overview", dash_attrs)


if __name__ == "__main__":
    main()
