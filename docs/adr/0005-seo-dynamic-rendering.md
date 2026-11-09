# ADR 0005: SEO by server-rendered pages for bots

Status: accepted (answers SRS open question 22 and the "Open" item of ADR 0001)

- The website stays a React single-page app for people.
- Caddy sends search-engine and link-preview bots (Googlebot, Bingbot, WhatsApp, Facebook, …) on product and
  category URLs to `/api/v1/store/seo/...`, which returns plain HTML with title, description, canonical, Open
  Graph and Product JSON-LD.
- `/sitemap.xml` and `/robots.txt` are served by the API from live catalogue data.
- The React app also sets title, description and JSON-LD per page (`lib/seo.ts`) for bots that run JavaScript.

Why: full server rendering (Next.js or similar) would mean a second front-end stack. Dynamic rendering for bots
gives indexable product pages with the current stack.

Consequence: bot and user pages must show the same content (they read the same API). New public page types need
an SEO endpoint and a Caddy rule.
