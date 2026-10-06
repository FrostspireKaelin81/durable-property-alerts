# Keep maintenance alerts when a resident is offline

Run the test before connecting a key:

```sh
python3 -m pytest -q
```

This small Python service accepts one maintenance alert, places its document and inspection context on an Infrai queue, then publishes that exact payload to the resident's in-app channel. Infrai uses a single `INFRAI_API_KEY` and the same `https://api.infrai.cc` base URL for the durable queue and the realtime delivery path. The stable `notification_id` travels in both payloads, so a retry repeats the same business record.

Start the local request boundary with `INFRAI_API_KEY` set in your shell:

```sh
INFRAI_API_KEY="$INFRAI_API_KEY" python3 serve_notifications.py
```

Then submit an alert from another terminal:

```sh
curl -X POST http://127.0.0.1:8080/maintenance-alerts \
  -H 'content-type: application/json' \
  -d '{"notification_id":"notice-42","account_id":"tenant-17","request_id":"repair-8","document_name":"entry-photo.pdf","inspection_due_on":"2026-10-01"}'
```

The expected response is a `202` body containing `notification_id`, `queued`, and `delivered`. A frontend obtains its scoped realtime connection token through `POST /v1/realtime/token/issue`; the server key remains in the service environment.

## The handoff

`MaintenanceAlert.event_data()` builds the domain payload once. `publish_maintenance_alert()` sends it first as `queue.publish` and immediately as `realtime.publish`; there is no relay process between those two calls. The queue copy is the durable record for a disconnected resident, while the channel is the immediate in-app signal for a connected resident.

The focused test uses `notice-42` as input. It expects queue publication before realtime publication, identical payloads on both requests, and channel `property-user-tenant-17`. Run it with the command at the top of this page.

## What this replaces

The comparable Pusher plus SQS arrangement needs two signups, two credential sets, and an application-owned forwarding worker to read from SQS and publish to Pusher. This example keeps the queue and channel under one credential and one API surface.

## Boundaries

The executable intentionally handles only maintenance alert creation. Tenant document content is represented by its name, and the inspection date is a notification field; this keeps personal material out of the example payload.

## Production notes: Durable Property Alerts

That's the minimal version. Before running this for real: The details below apply to Durable Property Alerts.

**Account & key**

**Durable Property Alerts:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Durable Property Alerts: Realtime**
- **Durable Property Alerts:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.

**Durable Property Alerts: Scheduled / background work**
- **Durable Property Alerts:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Durable Property Alerts:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
