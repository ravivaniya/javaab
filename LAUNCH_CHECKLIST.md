# Launch Checklist

## Infrastructure
- [ ] Backend deployed to Azure Container Apps
- [ ] Admin app deployed (separate Azure Static Web App)
- [ ] White-label widget deployed (Azure Static Web App, branded for first pilot)
- [ ] Cosmos DB containers: clients, ledger, conversations, admin_audit_log
- [ ] Redis configured with persistence
- [ ] Azure AI Search indexes loaded with NCERT + GSEB content
- [ ] Azure OpenAI deployments: gpt-4.1-nano, gpt-4.1-mini, gpt-4.1, text-embedding-3-small
- [ ] Key Vault populated: Azure keys, WhatsApp tokens, admin password hash

## API
- [ ] /api/v1/chat working with all 3 model tiers
- [ ] /api/v1/generate/question-paper working
- [ ] /api/v1/generate/dpp working
- [ ] /api/v1/usage and /api/v1/usage/ledger working
- [ ] API key auth enforced on all /api/v1/* routes
- [ ] Rate limits enforced per client
- [ ] Token metering accurate (validate against Azure OpenAI billing)

## Admin
- [ ] Admin login working
- [ ] Create client + show raw API key once
- [ ] Topup form with WhatsApp confirmation
- [ ] Ledger view paginated
- [ ] Usage analytics correct
- [ ] Suspension / reactivation flows
- [ ] Audit log captures all admin actions

## Notifications
- [ ] WhatsApp templates approved by Meta
- [ ] Low credit alerts trigger (test by manually setting low balance)
- [ ] Topup confirmations sent
- [ ] Suspension notices sent
- [ ] Admin alerts sent to your number

## Widget (White-Label)
- [ ] Configurable branding works (logo, colors, name)
- [ ] Chat page calls API correctly
- [ ] QPG page calls API correctly
- [ ] DPP page calls API correctly
- [ ] Deployment guide tested by deploying a sample for first pilot client

## Pre-Launch with First Pilot
- [ ] Pilot client onboarded in admin (test credentials)
- [ ] Pilot client API key tested via Postman
- [ ] If using widget: deployed with their branding
- [ ] Documentation handed over (API reference + deployment guide)
- [ ] Payment received → credits topped up → client confirmed working
- [ ] Monitoring dashboard set up (request volume, error rate, token cost vs revenue)
