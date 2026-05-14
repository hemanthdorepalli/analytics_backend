cat > ~/analytics_platform/README.md << 'EOF'
# Analytics Platform

A real-time analytics and reporting platform — lightweight Mixpanel/Metabase alternative built as a technical assessment for Wexa AI.

## Live Demo

- **Backend API:** https://analytics-platform-api.onrender.com
- **Health Check:** https://analytics-platform-api.onrender.com/api/v1/auth/health/

> Note: Backend is on Render free tier — first request may take 30s to wake up.

---

## What It Does

Companies instrument their apps by sending events via REST API. Events flow into dashboards in real-time. Alert rules trigger notifications when thresholds are exceeded. Full multi-tenant RBAC with team management.

**Core flow:**

