"""
Graph Webhook Notification Handler (Flask)

Receives push notifications from Microsoft Graph when new emails arrive.
Pair with example_graph_poller.py's create_webhook_subscription() to set up.

Install: pip install flask msgraph-sdk azure-identity cryptography
"""

import json
import logging
import hmac
import hashlib
from datetime import datetime, timedelta, timezone

from flask import Flask, request, jsonify, Response

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

# Must match the clientState you used when creating the subscription
EXPECTED_CLIENT_STATE = "secret-validation-token"


@app.route("/api/webhook", methods=["POST"])
def handle_notification():
    """
    Handle Graph change notifications.

    Two scenarios:
    1. Subscription validation: Graph sends a validationToken query param.
       We must echo it back with 200 within 10 seconds.
    2. Actual notification: Graph POSTs a JSON payload with change data.
    """

    # --- Scenario 1: Subscription Validation ---
    validation_token = request.args.get("validationToken")
    if validation_token:
        log.info("Subscription validation request received")
        # Must return the token as plain text with 200
        return Response(validation_token, status=200, content_type="text/plain")

    # --- Scenario 2: Change Notification ---
    try:
        body = request.get_json()
    except Exception:
        log.error("Failed to parse notification body")
        return jsonify({"error": "Invalid JSON"}), 400

    if not body or "value" not in body:
        log.warning("Unexpected notification format")
        return jsonify({"error": "Missing value"}), 400

    for notification in body["value"]:
        # Validate clientState to ensure notification is authentic
        client_state = notification.get("clientState")
        if client_state != EXPECTED_CLIENT_STATE:
            log.warning("Invalid clientState: %s", client_state)
            continue

        change_type = notification.get("changeType")
        resource = notification.get("resource")
        tenant_id = notification.get("tenantId")
        subscription_id = notification.get("subscriptionId")

        log.info(
            "Notification: change=%s resource=%s tenant=%s subscription=%s",
            change_type,
            resource,
            tenant_id,
            subscription_id,
        )

        # Resource data (if rich notification with includeResourceData=true)
        encrypted_content = notification.get("encryptedContent")
        if encrypted_content:
            # In production, decrypt using your private key
            log.info("Rich notification with encrypted content received")
            # See: https://learn.microsoft.com/en-us/graph/change-notifications-with-resource-data
            # decrypt_resource_data(encrypted_content)
        else:
            # Basic notification: fetch the full message via Graph API
            resource_data = notification.get("resourceData", {})
            message_id = resource_data.get("id")
            odata_id = resource_data.get("@odata.id")

            if message_id:
                log.info("New message ID: %s - fetching full content", message_id)
                # In production, enqueue this for async processing:
                # fetch_and_process_message(odata_id, message_id)

    # Must return 2xx within 3 seconds or Graph will retry
    return jsonify({"status": "ok"}), 202


@app.route("/api/lifecycle", methods=["POST"])
def handle_lifecycle():
    """
    Handle lifecycle notifications.

    These inform you about subscription problems:
    - subscriptionRemoved: subscription was removed (re-create it)
    - reauthorizationRequired: need to reauthorize
    - missed: some notifications were missed (do a delta query)
    """
    validation_token = request.args.get("validationToken")
    if validation_token:
        return Response(validation_token, status=200, content_type="text/plain")

    body = request.get_json()
    if body and "value" in body:
        for notification in body["value"]:
            lifecycle_event = notification.get("lifecycleEvent")
            subscription_id = notification.get("subscriptionId")
            log.warning(
                "Lifecycle event: %s for subscription %s",
                lifecycle_event,
                subscription_id,
            )

            if lifecycle_event == "subscriptionRemoved":
                log.error("Subscription %s was removed! Re-create it.", subscription_id)
                # trigger_subscription_recreation(subscription_id)

            elif lifecycle_event == "reauthorizationRequired":
                log.warning("Reauthorization needed for %s", subscription_id)
                # reauthorize_subscription(subscription_id)

            elif lifecycle_event == "missed":
                log.warning("Missed notifications for %s; running delta query", subscription_id)
                # trigger_delta_query_catchup()

    return jsonify({"status": "ok"}), 202


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()})


if __name__ == "__main__":
    # In production, use a proper WSGI server (gunicorn, uvicorn)
    # and ensure HTTPS with TLS 1.2+
    app.run(host="0.0.0.0", port=8443, debug=True)
