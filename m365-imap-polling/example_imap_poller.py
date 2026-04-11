"""
M365 IMAP OAuth2 Polling Example (Client Credentials Flow)

Prerequisites:
1. Azure/Entra ID app registration with IMAP.AccessAsApp permission
2. Admin consent granted
3. Service principal registered in Exchange Online (New-ServicePrincipal)
4. FullAccess mailbox permission granted (Add-MailboxPermission)

Install: pip install msal imap-tools
"""

import time
import logging
import email
import imaplib
from dataclasses import dataclass

import msal
from imap_tools import MailBox, AND

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


@dataclass
class M365Config:
    tenant_id: str
    client_id: str
    client_secret: str
    mailbox: str  # email address to poll
    poll_interval: int = 60  # seconds


class M365IMAPPoller:
    """Resilient IMAP poller for M365 with OAuth2 client credentials."""

    AUTHORITY_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}"
    SCOPES = ["https://outlook.office365.com/.default"]
    IMAP_HOST = "outlook.office365.com"
    IMAP_PORT = 993

    def __init__(self, config: M365Config, handler):
        """
        Args:
            config: M365 connection configuration
            handler: callable(msg) invoked for each new message.
                     msg is an imap_tools MailMessage object.
        """
        self.config = config
        self.handler = handler
        self._msal_app = msal.ConfidentialClientApplication(
            config.client_id,
            authority=self.AUTHORITY_TEMPLATE.format(tenant_id=config.tenant_id),
            client_credential=config.client_secret,
        )

    def _get_access_token(self) -> str:
        """Acquire token via client credentials. MSAL caches automatically."""
        result = self._msal_app.acquire_token_for_client(scopes=self.SCOPES)
        if "access_token" in result:
            return result["access_token"]
        error = result.get("error_description", result.get("error", "unknown"))
        raise RuntimeError(f"Token acquisition failed: {error}")

    def _connect_imap_tools(self):
        """Connect using imap_tools with XOAUTH2."""
        token = self._get_access_token()
        mailbox = MailBox(self.IMAP_HOST, self.IMAP_PORT)
        mailbox.xoauth2(self.config.mailbox, token)
        return mailbox

    def _connect_imaplib(self) -> imaplib.IMAP4_SSL:
        """Connect using raw imaplib with XOAUTH2."""
        token = self._get_access_token()
        imap = imaplib.IMAP4_SSL(self.IMAP_HOST, self.IMAP_PORT)
        auth_string = f"user={self.config.mailbox}\x01auth=Bearer {token}\x01\x01"
        imap.authenticate("XOAUTH2", lambda _: auth_string.encode())
        return imap

    def poll_once_imap_tools(self):
        """Single poll cycle using imap_tools (recommended)."""
        token = self._get_access_token()
        with MailBox(self.IMAP_HOST, self.IMAP_PORT).xoauth2(
            self.config.mailbox, token, initial_folder="INBOX"
        ) as mailbox:
            for msg in mailbox.fetch(AND(seen=False), limit=50):
                try:
                    self.handler(msg)
                except Exception:
                    log.exception("Handler error for message %s", msg.uid)

    def poll_once_imaplib(self):
        """Single poll cycle using raw imaplib."""
        imap = self._connect_imaplib()
        try:
            imap.select("INBOX")
            status, data = imap.search(None, "UNSEEN")
            if status != "OK":
                log.warning("IMAP SEARCH failed: %s", status)
                return

            uids = data[0].split()
            if not uids:
                log.debug("No new messages")
                return

            log.info("Found %d unseen message(s)", len(uids))
            for uid in uids:
                status, msg_data = imap.fetch(uid, "(RFC822)")
                if status == "OK":
                    msg = email.message_from_bytes(msg_data[0][1])
                    try:
                        self.handler(msg)
                    except Exception:
                        log.exception("Handler error for UID %s", uid)
        finally:
            try:
                imap.logout()
            except Exception:
                pass

    def run(self, use_imap_tools=True):
        """Run the polling loop with automatic reconnection."""
        poll_fn = self.poll_once_imap_tools if use_imap_tools else self.poll_once_imaplib
        log.info(
            "Starting IMAP poller for %s (interval=%ds)",
            self.config.mailbox,
            self.config.poll_interval,
        )

        while True:
            try:
                poll_fn()
            except KeyboardInterrupt:
                log.info("Shutting down")
                return
            except Exception:
                log.exception("Poll cycle failed; will retry")

            time.sleep(self.config.poll_interval)


# --- Usage example ---

def handle_message(msg):
    """Process a new email. msg is an imap_tools MailMessage."""
    log.info("New email: subject=%r from=%r date=%s", msg.subject, msg.from_, msg.date)
    for att in msg.attachments:
        log.info("  Attachment: %s (%d bytes)", att.filename, len(att.payload))


if __name__ == "__main__":
    config = M365Config(
        tenant_id="YOUR_TENANT_ID",
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
        mailbox="inbox@contoso.com",
        poll_interval=60,
    )
    poller = M365IMAPPoller(config, handler=handle_message)
    poller.run()
