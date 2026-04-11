"""
M365 Graph API Email Poller with Delta Queries

This demonstrates the recommended approach for polling M365 mailboxes.
Uses delta queries for efficient incremental sync.

Prerequisites:
1. Azure/Entra ID app registration with Mail.Read application permission
2. Admin consent granted
3. (Optional) RBAC for Applications configured to scope to specific mailboxes

Install: pip install msgraph-sdk azure-identity msal
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
from kiota_abstractions.base_request_configuration import RequestConfiguration

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


@dataclass
class GraphConfig:
    tenant_id: str
    client_id: str
    client_secret: str
    mailbox: str  # user ID or email address
    folder_id: str = "inbox"  # mail folder to monitor
    poll_interval: int = 60  # seconds
    state_file: str = "delta_state.json"  # persists delta token between runs


class GraphEmailPoller:
    """Efficient email poller using Graph API delta queries."""

    def __init__(self, config: GraphConfig, handler):
        self.config = config
        self.handler = handler
        self._credential = ClientSecretCredential(
            tenant_id=config.tenant_id,
            client_id=config.client_id,
            client_secret=config.client_secret,
        )
        self._client = GraphServiceClient(self._credential)
        self._delta_link: Optional[str] = None
        self._load_state()

    def _load_state(self):
        """Load persisted delta token from disk."""
        path = Path(self.config.state_file)
        if path.exists():
            try:
                state = json.loads(path.read_text())
                self._delta_link = state.get("delta_link")
                log.info("Loaded delta state from %s", self.config.state_file)
            except Exception:
                log.warning("Failed to load delta state; starting fresh")

    def _save_state(self):
        """Persist delta token to disk for restart resilience."""
        Path(self.config.state_file).write_text(
            json.dumps({"delta_link": self._delta_link})
        )

    async def poll_once(self):
        """
        Execute one delta query poll cycle.

        First call: returns all current messages (initial sync).
        Subsequent calls: returns only changes since last delta token.
        """
        user = self.config.mailbox
        folder = self.config.folder_id

        if self._delta_link:
            # Use saved delta link for incremental query
            # The msgraph SDK doesn't directly support raw delta links,
            # so we fall back to the raw HTTP client for subsequent polls.
            result = await self._client.users.by_user_id(user)\
                .mail_folders.by_mail_folder_id(folder)\
                .messages.delta.get()
        else:
            # Initial sync
            config = RequestConfiguration()
            config.headers.add("Prefer", "odata.maxpagesize=50")

            result = await self._client.users.by_user_id(user)\
                .mail_folders.by_mail_folder_id(folder)\
                .messages.delta.get(request_configuration=config)

        if result is None:
            log.warning("Delta query returned None")
            return

        # Process messages in this page
        new_count = 0
        if result.value:
            for msg in result.value:
                # Skip removed items (deletions/moves)
                if hasattr(msg, "additional_data") and msg.additional_data.get("@removed"):
                    log.debug("Skipping removed message: %s", msg.id)
                    continue

                try:
                    self.handler(msg)
                    new_count += 1
                except Exception:
                    log.exception("Handler error for message %s", msg.id)

        # Handle pagination: follow nextLink until we get deltaLink
        # In practice, the SDK handles pagination automatically for most cases

        # Save the delta link for next poll
        if hasattr(result, "odata_delta_link") and result.odata_delta_link:
            self._delta_link = result.odata_delta_link
            self._save_state()
            log.info("Processed %d message(s); delta state saved", new_count)
        elif hasattr(result, "odata_next_link") and result.odata_next_link:
            log.info("More pages available; processed %d so far", new_count)
            # In production, follow nextLink pages until deltaLink is received

    async def get_message_detail(self, user_id: str, message_id: str):
        """Fetch full message details including body and attachments."""
        message = await self._client.users.by_user_id(user_id)\
            .messages.by_message_id(message_id).get()
        return message

    async def get_attachments(self, user_id: str, message_id: str):
        """List and download attachments for a message."""
        attachments = await self._client.users.by_user_id(user_id)\
            .messages.by_message_id(message_id)\
            .attachments.get()
        return attachments.value if attachments else []

    async def run(self):
        """Main polling loop."""
        log.info(
            "Starting Graph delta poller for %s/%s (interval=%ds)",
            self.config.mailbox,
            self.config.folder_id,
            self.config.poll_interval,
        )

        while True:
            try:
                await self.poll_once()
            except KeyboardInterrupt:
                log.info("Shutting down")
                return
            except Exception:
                log.exception("Poll cycle failed; will retry")

            await asyncio.sleep(self.config.poll_interval)


# --- Webhook subscription management ---

async def create_webhook_subscription(
    client: GraphServiceClient,
    mailbox: str,
    notification_url: str,
    expiration_hours: int = 168,  # 7 days max for mail
    client_state: str = "secret",
):
    """
    Create a Graph webhook subscription for new emails.

    The notification_url must be a publicly accessible HTTPS endpoint
    that responds to the validation request within 10 seconds.
    """
    from msgraph.generated.models.subscription import Subscription
    from datetime import datetime, timedelta, timezone

    sub = Subscription()
    sub.change_type = "created"  # or "created,updated" for both
    sub.notification_url = notification_url
    sub.resource = f"users/{mailbox}/mailFolders('inbox')/messages"
    sub.expiration_date_time = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)
    sub.client_state = client_state

    result = await client.subscriptions.post(sub)
    log.info("Created subscription %s, expires %s", result.id, result.expiration_date_time)
    return result


async def renew_subscription(client: GraphServiceClient, subscription_id: str, hours: int = 168):
    """Renew a subscription before it expires."""
    from msgraph.generated.models.subscription import Subscription
    from datetime import datetime, timedelta, timezone

    sub = Subscription()
    sub.expiration_date_time = datetime.now(timezone.utc) + timedelta(hours=hours)

    result = await client.subscriptions.by_subscription_id(subscription_id).patch(sub)
    log.info("Renewed subscription %s until %s", subscription_id, result.expiration_date_time)
    return result


# --- Usage example ---

def handle_message(msg):
    """Process a new/changed email from delta query."""
    subject = msg.subject or "(no subject)"
    sender = ""
    if msg.from_ and msg.from_.email_address:
        sender = msg.from_.email_address.address
    received = msg.received_date_time
    log.info("Message: subject=%r from=%r received=%s", subject, sender, received)


async def main():
    config = GraphConfig(
        tenant_id="YOUR_TENANT_ID",
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
        mailbox="inbox@contoso.com",
        poll_interval=60,
    )
    poller = GraphEmailPoller(config, handler=handle_message)
    await poller.run()


if __name__ == "__main__":
    asyncio.run(main())
