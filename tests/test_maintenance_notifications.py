import json

from maintenance_notifications import HttpResult, MaintenanceAlert, PropertyNotificationClient


def test_alert_is_queued_before_its_realtime_delivery() -> None:
    requests = []

    def transport(request):
        requests.append((request.full_url, json.loads(request.data)))
        return HttpResult(200, {}, {"ok": True, "data": {"accepted": True}})

    alert = MaintenanceAlert(
        notification_id="notice-42",
        account_id="tenant-17",
        request_id="repair-8",
        document_name="entry-photo.pdf",
        inspection_due_on="2026-10-01",
    )
    result = PropertyNotificationClient(api_key="test-key", transport=transport).publish_maintenance_alert(alert)

    assert [url.rsplit("/", 2)[-2:] for url, _ in requests] == [
        ["queue", "publish"],
        ["realtime", "publish"],
    ]
    assert requests[0][1]["payload"] == requests[1][1]["data"]
    assert requests[1][1]["channel"] == "property-user-tenant-17"
    assert result["notification_id"] == "notice-42"
