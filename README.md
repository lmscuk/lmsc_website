# London Maths & Science College Website

A Flask-based marketing and admissions site for London Maths & Science College (LMSC) featuring dynamic content management, student lead capture, blog tooling, and a modern performance-focused frontend.

## Tech Stack

- **Backend:** Flask 3, SQLite, Flask-Mail, Flask-Compress
- **Frontend:** Tailwind CSS (via CDN), custom SCSS/CSS, Motion One animations, vanilla JavaScript
- **Tooling:** Lightning CSS, esbuild, Pillow, Click-based management scripts
- **Infrastructure:** WSGI-compatible application, configurable via environment variables, designed for deployment behind a reverse proxy

## Performance Enhancements

- **HTTP compression:** `Flask-Compress` serves HTML, JSON, CSS, and JS with gzip/Brotli to reduce transfer size.
- **Asset pipeline:** `scripts/build_assets.py` bundles/minifies CSS and JavaScript using `npx lightningcss` and `npx esbuild`, emitting cache-busted assets under `static/dist/`.
- **Responsive media pipeline:** `scripts/process_images.py` generates WebP/AVIF variants and responsive width sets, feeding `<picture>` macros for efficient image delivery.
- **Cache-busted asset URLs:** `asset_url` helper appends build timestamps to static references so browsers invalidate caches after deploys.
- **Long-lived caching headers:** Static responses (CSS/JS/images/sitemaps) inherit configurable cache-control headers via `STATIC_CACHE_SECONDS`.
- **Lazy loading images:** Jinja macro defaults to `loading="lazy"` and `decoding="async"` to defer non-critical media.

## Project Structure

```
LMSC_Website/
├── app.py                  # Flask application factory, routes, CLI commands
├── requirements.txt        # Python dependencies
├── scripts/
│   ├── build_assets.py     # CSS/JS bundling + minification pipeline
│   └── process_images.py   # Responsive image generation utilities
├── static/
│   ├── css/                # Source stylesheet(s)
│   ├── js/                 # Source JavaScript bundle
│   ├── dist/               # Minified build outputs (generated)
│   ├── Images/             # Publicly served imagery
│   └── uploads/            # Admin uploaded assets (blogs, policies, etc.)
├── templates/
│   ├── base.html           # Global layout wrapper
│   ├── partials/           # Shared components (navbar, footer, media macros)
│   ├── admin/              # Admin dashboard templates
│   └── *.html              # Public-facing pages
└── instance/
    └── lmsc.sqlite3        # Application database (generated)
```

## Application Features

- Public marketing pages covering courses, mission, policies, and blogs.
- Dynamic page management with slug-based routing and auto-template generation.
- Admin dashboard for leads, consultations, policies, blogs, and courses.
- Consultation scheduling and email notifications via Flask-Mail.
- Asset helper macros for responsive imagery and consistent media handling.
- Automated sitemap/robots endpoints and analytics tracking script.

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run
```

### Build Optimised Assets

```bash
python scripts/build_assets.py
```

Requires `npx` with `lightningcss` and `esbuild` available (installed automatically per command).

### Generate Responsive Images

```bash
flask process-images --sizes 480,768,1024,1440 --quality 82
```

Source originals reside within `static/source_images/`. Outputs are written to `static/Images/` alongside WebP/AVIF variants.

## Environment Configuration

Key environment variables:

| Variable                | Purpose                                              |
| ----------------------- | ---------------------------------------------------- |
| `SECRET_KEY`            | Flask session security key                           |
| `ENABLE_HTTPS_REDIRECT` | Force HTTPS redirects in production (`1`/`0`)        |
| `STATIC_CACHE_SECONDS`  | Cache-Control max-age for static responses (seconds) |
| `MAIL_USERNAME`         | Sender account (default aligns with admin user)      |
| `MAIL_PASSWORD`         | SMTP password/app password                           |

## Contributing

- Ensure `python scripts/build_assets.py` and `flask process-images --overwrite` (when modifying imagery) run cleanly before opening a PR.
- Run the Flask server locally and verify key user flows (homepage, consultation booking, admin login).
- Provide concise commit messages describing the intent of the change.

## License

Proprietary — all rights reserved by London Maths & Science College.
