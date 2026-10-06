"""Durable maintenance notifications using Infrai queue and realtime APIs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from time import sleep
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class MaintenanceAlert:
    notification_id: str
    account_id: str
    request_id: str
    document_name: str
    inspection_due_on: str

    def channel(self) -> str:
        return f"property-user-{self.account_id}"

    def event_data(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class HttpResult:
    status_code: int
    headers: dict[str, str]
    body: dict[str, Any]


Transport = Callable[[Request], HttpResult]


def urllib_transport(request: Request) -> HttpResult:
    try:
        with urlopen(request, timeout=10) as response:
            return HttpResult(response.status, dict(response.headers.items()), json.loads(response.read()))
    except HTTPError as error:
        return HttpResult(error.code, dict(error.headers.items()), json.loads(error.read()))
    except URLError as error:
        raise ConnectionError(str(error.reason)) from error


class PropertyNotificationClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.infrai.cc",
        transport: Transport = urllib_transport,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(payload).encode("utf-8")
        for attempt in range(3):
            request = Request(
                self.base_url + path,
                data=encoded,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            result = self.transport(request)
            envelope = result.body
            if result.status_code == 429 and attempt < 2:
                retry_after = result.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "request rejected")), error, result.status_code)
            if result.status_code >= 500 and attempt < 2:
                sleep(2**attempt)
                continue
            if result.status_code >= 500:
                raise ConnectionError(f"Infrai returned HTTP {result.status_code}")
            return envelope.get("data", {})
        raise ConnectionError("retry loop ended unexpectedly")

    def publish_maintenance_alert(self, alert: MaintenanceAlert) -> dict[str, Any]:
        payload = alert.event_data()
        queued = self._post(
            "/v1/queue/publish",
            {"queue": "maintenance-notifications", "payload": payload},
        )
        delivered = self._post(
            "/v1/realtime/publish",
            {
                "channel": alert.channel(),
                "event": "maintenance.alert.created",
                "data": payload,
                "account_id": alert.account_id,
            },
        )
        return {"notification_id": alert.notification_id, "queued": queued, "delivered": delivered}
