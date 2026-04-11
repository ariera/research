# ==============================================================================
# Exchange Online Service Principal Setup for M365 IMAP/Graph Access
# ==============================================================================
#
# Run this AFTER:
# 1. Creating the app registration in Entra ID
# 2. Adding API permissions (IMAP.AccessAsApp or Mail.Read)
# 3. Granting admin consent
#
# This script performs the Exchange Online side of the setup:
# - Registers the service principal in Exchange
# - Grants mailbox access
# - (Optional) Sets up RBAC for Applications scoping
#
# Requires: ExchangeOnlineManagement module
# ==============================================================================

# --- Configuration ---
$TenantId = "YOUR_TENANT_ID"
$AppId = "YOUR_APP_CLIENT_ID"
# IMPORTANT: This is the Object ID from Enterprise Applications, NOT App Registrations
$EnterpriseAppObjectId = "YOUR_ENTERPRISE_APP_OBJECT_ID"
$DisplayName = "Email Processor Service"
$TargetMailbox = "inbox@contoso.com"

# --- Install and Connect ---
if (-not (Get-Module -ListAvailable -Name ExchangeOnlineManagement)) {
    Install-Module -Name ExchangeOnlineManagement -Force -Scope CurrentUser
}
Import-Module ExchangeOnlineManagement
Connect-ExchangeOnline -Organization $TenantId

# ==============================================================================
# STEP 1: Register Service Principal in Exchange
# ==============================================================================
Write-Host "Registering service principal in Exchange Online..." -ForegroundColor Green

New-ServicePrincipal `
    -AppId $AppId `
    -ObjectId $EnterpriseAppObjectId `
    -DisplayName $DisplayName

# Verify
Write-Host "Verifying service principal..." -ForegroundColor Yellow
Get-ServicePrincipal | Where-Object { $_.AppId -eq $AppId } | Format-List

# ==============================================================================
# STEP 2: Grant Mailbox Access (for IMAP)
# ==============================================================================
# Only needed for IMAP. For Graph with RBAC, use Step 3 instead.

Write-Host "Granting FullAccess to $TargetMailbox..." -ForegroundColor Green

$ExoSP = Get-ServicePrincipal | Where-Object { $_.AppId -eq $AppId }

Add-MailboxPermission `
    -Identity $TargetMailbox `
    -User $ExoSP.Identity `
    -AccessRights FullAccess

Write-Host "Mailbox permission granted." -ForegroundColor Green

# ==============================================================================
# STEP 3 (Optional): RBAC for Applications - Scope Graph Access
# ==============================================================================
# Use this instead of (or in addition to) unscoped Mail.Read in Entra ID.
# This limits which mailboxes the app can access via Graph API.

# Create a management scope (filter-based)
# Example: only mailboxes with CustomAttribute1 = "EmailProcessor"
<#
New-ManagementScope -Name "EmailProcessorScope" `
    -RecipientRestrictionFilter "CustomAttribute1 -eq 'EmailProcessor'"

# Assign scoped Mail.Read role
New-ManagementRoleAssignment `
    -App $ExoSP.Identity `
    -Role "Application Mail.Read" `
    -CustomResourceScope "EmailProcessorScope"

# IMPORTANT: After setting up RBAC, remove the unscoped Mail.Read permission
# from Entra ID (Azure Portal > App Registration > API Permissions).
# Otherwise the union of scoped + unscoped = all mailboxes.

# Test the authorization
Test-ServicePrincipalAuthorization -Identity $ExoSP.Identity -Resource $TargetMailbox | Format-Table
#>

# ==============================================================================
# Verification
# ==============================================================================
Write-Host "`n--- Verification ---" -ForegroundColor Cyan
Write-Host "Service Principal:" -ForegroundColor Yellow
Get-ServicePrincipal | Where-Object { $_.AppId -eq $AppId } | Format-List

Write-Host "Mailbox Permissions:" -ForegroundColor Yellow
Get-MailboxPermission -Identity $TargetMailbox | Where-Object { $_.User -like "*$($ExoSP.Identity)*" } | Format-List

Write-Host "`nSetup complete." -ForegroundColor Green
Write-Host "IMAP endpoint: outlook.office365.com:993"
Write-Host "Token scope: https://outlook.office365.com/.default"
Write-Host "Graph endpoint: https://graph.microsoft.com/v1.0/users/$TargetMailbox/messages"

# Disconnect
Disconnect-ExchangeOnline -Confirm:$false
