"""Run a narrow HTTP boundary for property-maintenance alerts."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from maintenance_notifications import InfraiError, MaintenanceAlert, PropertyNotificationClient


class NotificationHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/maintenance-alerts":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            alert = MaintenanceAlert(**json.loads(self.rfile.read(size)))
            result = PropertyNotificationClient().publish_maintenance_alert(alert)
            self._send(202, result)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            self._send(400, {"error": str(error)})
        except InfraiError as error:
            self._send(error.status_code, {"error": error.code})

    def _send(self, status: int, body: dict[str, object]) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8080), NotificationHandler).serve_forever()
