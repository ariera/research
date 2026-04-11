# Research Notes: M365 IMAP Polling / Email Reaction System

## Research Process

### Sources Consulted
- Microsoft Learn: Official docs for IMAP OAuth, Graph API change notifications, subscriptions, throttling
- GitHub: python-o365, M365-IMAP, msgraph-sdk-python, email-oauth2-proxy repos
- PyPI: exchangelib, o365, msgraph-sdk packages
- Microsoft Q&A forums: practical issues with OAuth2 IMAP, shared mailbox access
- Community blogs: Limilabs, Codewrecks, practical365, Voitanos

### Key Findings

1. **IMAP OAuth2 with client credentials flow IS possible** but requires a non-obvious Exchange Online PowerShell step (New-ServicePrincipal + Add-MailboxPermission) that many people miss
2. **The permission is IMAP.AccessAsApp** (application-level), NOT IMAP.AccessAsUser.All (delegated) for daemon services
3. **Scope for token acquisition is `https://outlook.office365.com/.default`** - this trips people up; it's NOT the individual permission scope
4. **Graph API is almost certainly better than IMAP** for new greenfield projects:
   - Webhooks provide near-real-time notification (avg <1 min latency for mail)
   - Delta queries provide efficient polling
   - RBAC for Applications provides granular mailbox scoping (replaces Application Access Policies)
   - No connection management headaches
5. **Graph subscription max lifetime for mail: 7 days** (10,080 min) for basic notifications, **1 day** (1,440 min) for rich notifications with resource data
6. **EWS is being turned off October 1, 2026** - don't build anything new on it
7. **SMTP AUTH Basic auth complete deprecation: April 30, 2026**
8. **exchangelib uses EWS** - avoid for new projects given EWS deprecation timeline
9. **Graph throttling: 10,000 requests per 10 minutes per app per mailbox**, max 4 concurrent requests
10. **RBAC for Applications** is the new way to restrict daemon app access to specific mailboxes (replaces Application Access Policies)
11. **Conditional Access policies** can and often do block IMAP even with OAuth2 - this is a common gotcha
12. **Graph attachment limit: 3MB inline, use upload sessions for larger**
13. **IMAP connection limit in Exchange Online: ~8 concurrent connections** (not well documented, but reported in practice)
14. **Graph change notifications can be delivered via webhooks, Azure Event Hubs, or Azure Event Grid**
15. **imap_tools has .xoauth2() method** for M365 OAuth2 authentication
16. **python-o365 v2.1 (Feb 2025)** - actively maintained, supports client credentials, shared mailboxes

### Gotchas Discovered
- Enterprise App Object ID (not App Registration Object ID) must be used for New-ServicePrincipal
- Graph webhook notifications require HTTPS endpoint with TLS 1.2+
- Rich notifications require encryption certificate for resource data
- Conditional Access "block legacy auth" policies can block IMAP even with OAuth2 if not configured correctly
- Graph subscription must be renewed before expiry; lifecycle notifications help detect issues
- Delta queries can return events outside filter conditions (deletions, read state changes)
- RBAC permission changes have 30min-2hr cache delay
