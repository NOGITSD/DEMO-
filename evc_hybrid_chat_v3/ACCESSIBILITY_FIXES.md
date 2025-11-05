Accessibility & server/header fixes
=================================

This file documents remaining audit items that cannot be fully resolved from inside the Streamlit Python app and require server/reverse-proxy configuration or build-time fixes.

1) Content-Type / font MIME
--
If you serve font files (woff2) from your own server, ensure the server responds with:

  Content-Type: font/woff2; charset=utf-8

For Nginx example:

  location /static/fonts/ {
    add_header Cache-Control "public, max-age=31536000, immutable";
    types { .woff2 font/woff2; }
    try_files $uri =404;
  }

2) Cache-Control for static resources
--
Add long-lived cache headers for immutable static assets (JS/CSS/fonts/images):

  Cache-Control: public, max-age=31536000, immutable

3) Security headers
--
Add these headers at the server/reverse-proxy level:

  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer-when-downgrade (or stricter)
  X-Frame-Options: DENY

For cookies set by your app (if any), ensure secure flags:

  Set-Cookie: session=...; Secure; HttpOnly; SameSite=Lax

4) ARIA attributes and Streamlit-internal DOM
--
Streamlit injects many ARIA attributes for widget behavior. If your audit flags e.g. aria-expanded on Streamlit elements, options are:

- Adjust the audit rules to allow Streamlit's ARIA attributes (recommended for internal apps).
- Replace the specific widget with custom HTML/JS so you control ARIA attributes (higher effort).

5) CSS property compatibility
--
Where necessary, include vendor-prefixed properties in your CSS (we inject some in `web.py`). Example:

  -webkit-text-size-adjust / text-size-adjust
  -webkit-backdrop-filter / backdrop-filter
  -webkit-user-select / user-select

6) Running behind a production reverse proxy
--
For production deployments, run Streamlit behind Nginx/Caddy/Traefik so you can:

- set response headers
- serve static assets with correct MIME types and cache headers
- enable TLS and Secure cookies

Example Nginx snippet to add headers (add inside server block):

  location / {
    proxy_pass http://127.0.0.1:8501;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    add_header X-Content-Type-Options "nosniff" always;
    add_header Cache-Control "public, max-age=31536000, immutable";
  }

7) Lighthouse/Performance notes
--
- Avoid animating layout properties like left/width/height. Use transform/opacity instead.
- Use cache-busting for static resources (fingerprinted filenames).

If you'd like, I can prepare an Nginx config file tailored to your deployment and update the Streamlit app to serve bundled fonts via base64 (to avoid MIME header issues). Tell me which option you prefer.
