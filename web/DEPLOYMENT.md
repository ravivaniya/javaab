# Javaab Widget — Deployment Guide

This guide is for schools and coaching institutes deploying the Javaab white-label widget.

---

## 1. Configure the widget

Open `src/config/widget.config.ts` and fill in your details:

```typescript
export const widgetConfig: WidgetConfig = {
  apiBaseUrl: "https://api.javaab.ai",   // do not change unless told otherwise
  apiKey: "jvb_live_YOUR_KEY_HERE",       // your Javaab API key (from the admin portal)

  institute: {
    name: "Shree Coaching Institute",     // shown in header and printed documents
    logo_url: "https://your-cdn.com/logo.png",  // null = Javaab logo
    primary_color: "#1A56DB",             // your brand colour (hex)
    secondary_color: "#EEF2FF",           // light tint (usually auto-derived)
  },

  defaults: {
    board: "CBSE",            // CBSE | GSEB
    class_level: 10,          // 6–12
    language: "en",           // en | hi | gu
  },

  features: {
    chat: true,               // AI Q&A chat
    qpg: true,                // Question Paper Generator
    dpp: true,                // Daily Practice Problems
  },

  branding: {
    show_javaab_credit: true, // "Powered by Javaab" footer — required on free tier
  },
};
```

### Using environment variables (recommended for CI/CD)

Create a `.env` file at the project root (never commit this):

```env
VITE_API_URL=https://api.javaab.ai
VITE_API_KEY=jvb_live_YOUR_KEY_HERE
VITE_INSTITUTE_NAME=Shree Coaching Institute
VITE_LOGO_URL=https://your-cdn.com/logo.png
VITE_PRIMARY_COLOR=#1A56DB
VITE_DEFAULT_BOARD=CBSE
VITE_DEFAULT_CLASS=10
VITE_DEFAULT_LANGUAGE=en
VITE_FEATURE_CHAT=true
VITE_FEATURE_QPG=true
VITE_FEATURE_DPP=false
VITE_SHOW_JAVAAB_CREDIT=true

# Optional: sandbox key for /demo route (sales calls)
VITE_DEMO_API_KEY=jvb_demo_SANDBOX_KEY
```

Env vars override everything in `widget.config.ts`.

---

## 2. Build

```bash
# Install dependencies
npm install       # or: pnpm install / yarn

# Production build → outputs to dist/
npm run build

# Preview the build locally
npm run preview
```

---

## 3. Deploy

### Option A — Vercel (easiest)

1. Push the `/web` folder to a GitHub repo.
2. Connect the repo to [vercel.com](https://vercel.com).
3. Set **Root Directory** to `web` (if in a monorepo).
4. Add your env vars in Vercel → Project → Settings → Environment Variables.
5. Deploy. Vercel handles CDN, HTTPS, and auto-deploys on every push.

### Option B — Netlify

1. Push to GitHub, connect repo at [netlify.com](https://netlify.com).
2. Set **Base directory**: `web`, **Build command**: `npm run build`, **Publish directory**: `web/dist`.
3. Add env vars in Netlify → Site settings → Environment Variables.
4. Optionally create `web/public/_redirects`:
   ```
   /*    /index.html   200
   ```
   This ensures client-side routing works correctly.

### Option C — Azure Static Web Apps

1. In Azure Portal → Create resource → Static Web App.
2. Connect GitHub repo, set app location to `web`, output location to `dist`.
3. Add your env vars in the Azure SWA configuration panel.
4. Azure automatically provisions a CDN and a free TLS certificate.

### Option D — Your own server (nginx/Apache)

```bash
# After running npm run build, upload the contents of dist/ to your server
scp -r dist/* user@yourserver:/var/www/javaab-widget/

# nginx site config
server {
    listen 443 ssl;
    server_name widget.yourinstitute.com;
    root /var/www/javaab-widget;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;   # SPA routing
    }

    # Optional: proxy API calls to avoid CORS issues
    location /api/ {
        proxy_pass https://api.javaab.ai/;
        proxy_set_header Host api.javaab.ai;
    }
}
```

---

## 4. Embed as an iframe in your existing site

If you already have a website and want the Javaab widget as a floating panel or embedded section:

```html
<!-- Embed the widget in an iframe -->
<iframe
  src="https://widget.yourinstitute.com"
  title="Javaab AI"
  width="100%"
  height="700"
  style="border: none; border-radius: 16px;"
  allow="clipboard-write"
></iframe>
```

For a **floating chat bubble** style:

```html
<style>
  #javaab-bubble {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 420px;
    height: 640px;
    border-radius: 20px;
    border: none;
    box-shadow: 0 24px 48px rgba(0,0,0,0.15);
    display: none;
    z-index: 9999;
  }
  #javaab-bubble.open { display: block; }
</style>

<iframe id="javaab-bubble" src="https://widget.yourinstitute.com/chat"></iframe>

<button onclick="document.getElementById('javaab-bubble').classList.toggle('open')">
  💬 Ask AI
</button>
```

---

## 5. Custom domain

Point your domain's DNS to your hosting provider:

- **Vercel / Netlify**: Add a CNAME record `widget → cname.vercel-dns.com` (or Netlify equivalent).
- **Azure SWA**: Add a CNAME in your DNS provider pointing to the SWA hostname.
- **Own server**: A-record pointing to your server IP.

TLS certificates are provisioned automatically on Vercel, Netlify, and Azure SWA. On your own server, use [Let's Encrypt / Certbot](https://certbot.eff.org/).

---

## 6. Security notes

- **Never commit your API key** to version control. Always use environment variables.
- The API key is embedded in the browser bundle; Javaab's backend rate-limits and monitors usage by key. Treat it like a read-heavy public key — it cannot write data or access other clients.
- Enable **origin allowlisting** in the Javaab admin portal to restrict which domains can use your key.
- If your key is ever compromised, rotate it from the admin portal immediately — the old key stops working instantly.

---

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Blank page after deploy | Check `_redirects` / nginx `try_files` — SPA routing needs the server to return `index.html` for all paths |
| `401 Unauthorized` in the browser console | API key is missing or wrong — check your env vars and rebuild |
| Logo not showing | Ensure `VITE_LOGO_URL` is an absolute HTTPS URL accessible from the browser |
| Wrong brand colour | `VITE_PRIMARY_COLOR` must be a 6-digit hex (`#RRGGBB`) |
| Chat works but QPG doesn't | Set `VITE_FEATURE_QPG=true` and make sure your plan includes QPG access |
| CORS errors | Contact Javaab support to add your domain to the API allowlist |

---

## 8. Demo mode

Navigate to `/demo` on your deployment to launch a sandbox with all features enabled. Useful during sales calls — no real credits are consumed if `VITE_DEMO_API_KEY` is a sandbox key.
