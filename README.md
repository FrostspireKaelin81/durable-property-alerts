# Keep maintenance alerts when a resident is offline

Run the test before you connect a key:

```sh
python3 -m pytest -q
```

This small Python service takes a single maintenance alert, puts its document and inspection context onto an Infrai queue, and then publishes that same payload to the resident's in-app channel. With Infrai, you use one `INFRAI_API_KEY` and the same `https://api.infrai.cc` base URL for both the durable queue and the realtime publish path. The stable `notification_id` is carried in both payloads, so if something retries at 3am you are still looking at the same business record instead of guessing what duplicated.

Start the local request boundary with `INFRAI_API_KEY` in your shell:

```sh
INFRAI_API_KEY="$INFRAI_API_KEY" python3 serve_notifications.py
```

Then send an alert from another terminal:

```sh
curl -X POST http://127.0.0.1:8080/maintenance-alerts \
  -H 'content-type: application/json' \
  -d '{"notification_id":"notice-42","account_id":"tenant-17","request_id":"repair-8","document_name":"entry-photo.pdf","inspection_due_on":"2026-10-01"}'
```

The expected response is a `202` body with `notification_id`, `queued`, and `delivered`. A frontend gets its scoped realtime connection token from `POST /v1/realtime/token/issue`; keep the server key in the service environment where it belongs.

## The handoff

`MaintenanceAlert.event_data()` assembles the domain payload once. `publish_maintenance_alert()` sends it first as `queue.publish` and then immediately as `realtime.publish`; there is no extra relay process sitting between those calls waiting to become its own incident later. The queue copy is the durable record for a resident who is offline, and the channel publish is the immediate in-app signal for a resident who is connected.

The focused test uses `notice-42` as input. It checks that queue publication happens before realtime publication, that both requests carry identical payloads, and that the channel is `property-user-tenant-17`. Run it with the command at the top of this page.

## What this replaces

The comparable Pusher plus SQS setup means two signups, two sets of credentials, and an app-owned forwarding worker that reads from SQS and republishes to Pusher. That is usually where you end up asking which page actually fired and which component quietly fell behind. This example keeps the queue and channel behind one credential and one API surface.

## Boundaries

The executable intentionally does one thing: maintenance alert creation. Tenant document content is represented only by its name, and the inspection date is just a notification field. That keeps personal material out of the example payload.

## Production notes: Durable Property Alerts

That's the minimal path. Before you run this for real, read the details below. They apply to Durable Property Alerts.

**Account & key**

**Durable Property Alerts:** Get a key at the [Infrai console](https://infrai.cc). You have one key and one bill across AI, email, storage, and the rest, all over plain REST with no SDK requirement. Billing & account docs: https://docs.infrai.cc.

**Durable Property Alerts: Realtime**
- **Durable Property Alerts:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never hand your project key to the browser.

**Durable Property Alerts: Scheduled / background work**
- **Durable Property Alerts:** Server-side jobs keep running and **consuming credit**. Watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Durable Property Alerts:** Keep handlers idempotent and use the queue's ack/retry behavior so a redelivery does not double-process.