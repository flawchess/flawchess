# Hetzner vs. Vercel + Supabase: Hardware per Dollar

**Date:** 2026-04-09
**Context:** FlawChess runs on Hetzner Cloud (CX33: 4 shared vCPUs, 8 GB RAM, 80 GB NVMe). This report compares hardware power per dollar between the current Hetzner setup and a hypothetical Vercel + Supabase stack.

---

## Current FlawChess Server

**Hetzner CX33:** 4 shared vCPUs, 8 GB RAM, 80 GB NVMe, 20 TB traffic — **EUR 6.49/mo (~$7)**

Stack: PostgreSQL 18 + FastAPI/Uvicorn + Caddy 2.11.2 (all on one box)

---

## Vercel Pro + Supabase Pro: Cost for Equivalent Resources

| Component | Monthly cost |
|---|---|
| Vercel Pro (1 seat) | $20 |
| Supabase Pro base | $25 |
| Supabase compute upgrade to Large (2-core dedicated ARM, 8 GB) | +$110 |
| **Total** | **$155/mo** |

The Supabase Large instance only provides 2 dedicated ARM cores + 8 GB RAM — less CPU than the current 4 shared vCPUs. Matching 4 dedicated cores requires XL at ~$210/mo, pushing the total to **$255/mo**.

### Price ratio: ~22x more expensive for comparable (or worse) specs

| | Hetzner CX33 | Vercel Pro + Supabase Pro (Large) |
|--|--|--|
| Monthly cost | **EUR 6.49 (~$7)** | **$155** |
| CPU | 4 shared vCPUs | 2 dedicated ARM cores (DB only) + serverless (backend) |
| RAM | 8 GB (shared across everything) | 8 GB (DB only) — no persistent backend RAM |
| Storage | 80 GB NVMe | 8 GB included, then $0.125/GB |
| Bandwidth | 20 TB included | 1 TB (Vercel) + 250 GB (Supabase) |
| Bandwidth overage | ~EUR 1/TB | $0.15/GB ($150/TB) Vercel + $0.09/GB ($90/TB) Supabase |

---

## What $155/mo Buys on Hetzner Instead

| Option | Specs | Price |
|---|---|---|
| **CCX33** (dedicated) | 8 dedicated vCPUs, 32 GB RAM, 240 GB NVMe, 3 TB traffic | EUR 62.49 |
| **CCX43** (dedicated) | 16 dedicated vCPUs, 64 GB RAM, 360 GB NVMe, 4 TB traffic | EUR 124.99 |
| **CX53** (shared) | 16 vCPUs, 32 GB RAM, 320 GB NVMe, 20 TB traffic | EUR 22.49 |
| **Two CX43s** (separate DB + app) | 8 vCPUs + 16 GB each, 160 GB each, 20 TB each | EUR 23.98 |

For $155/mo on Hetzner: a **CCX43 with 16 dedicated vCPUs and 64 GB RAM** — 4x the CPU and 8x the RAM of the current setup.

---

## Bandwidth Comparison

| Provider | Included | Cost at 5 TB |
|---|---|---|
| Hetzner CX33 | 20 TB | $0 |
| Vercel Pro | 1 TB | $600 (4 TB x $0.15/GB) |
| Supabase Pro | 250 GB | $427 (4.75 TB x $0.09/GB) |
| **Vercel + Supabase combined** | 1.25 TB | **$1,027** |

Hetzner bandwidth overage: ~EUR 1/TB. Vercel: $150/TB. Supabase: $90/TB. Hetzner is 90-150x cheaper per TB.

---

## Architectural Mismatch

Beyond cost, Vercel + Supabase cannot run FlawChess's backend without a major rewrite:

| FlawChess Requirement | Hetzner | Vercel Serverless |
|---|---|---|
| Background import workers (chess.com sequential archive fetch with rate-limit delays) | Works natively | Impossible — 60s function timeout |
| Persistent FastAPI process | Yes | No — cold starts, stateless |
| Streaming lichess NDJSON import | Yes | No — no long-running connections |
| Docker + full control | Yes | No |

A separate compute provider (Railway, Fly.io, Render) would be needed for the backend, adding yet another bill.

---

## Hetzner Cloud Full Pricing Reference (April 2026)

*Post April 1, 2026 price adjustment (~25-37% increase).*

### CX Line — Shared vCPU, Intel (Germany/Finland)

| Plan | vCPUs | RAM | Storage | Traffic | EUR/mo |
|------|-------|-----|---------|---------|--------|
| CX23 | 2 | 4 GB | 40 GB | 20 TB | 3.99 |
| CX33 | 4 | 8 GB | 80 GB | 20 TB | 6.49 |
| CX43 | 8 | 16 GB | 160 GB | 20 TB | 11.99 |
| CX53 | 16 | 32 GB | 320 GB | 20 TB | 22.49 |

### CAX Line — Shared vCPU, Ampere ARM (Germany/Finland)

| Plan | vCPUs | RAM | Storage | Traffic | EUR/mo |
|------|-------|-----|---------|---------|--------|
| CAX11 | 2 | 4 GB | 40 GB | 20 TB | 4.49 |
| CAX21 | 4 | 8 GB | 80 GB | 20 TB | 7.99 |
| CAX31 | 8 | 16 GB | 160 GB | 20 TB | 15.99 |
| CAX41 | 16 | 32 GB | 320 GB | 20 TB | 31.49 |

### CPX Line — Shared vCPU, AMD (All Regions)

| Plan | vCPUs | RAM | Storage | Traffic | EUR/mo |
|------|-------|-----|---------|---------|--------|
| CPX22 | 2 | 4 GB | 80 GB | 20 TB | 7.99 |
| CPX32 | 4 | 8 GB | 160 GB | 20 TB | 13.99 |
| CPX42 | 8 | 16 GB | 320 GB | 20 TB | 25.49 |
| CPX52 | 12 | 24 GB | 480 GB | 20 TB | 36.49 |
| CPX62 | 16 | 32 GB | 640 GB | 20 TB | 50.49 |

### CCX Line — Dedicated vCPU, AMD (All Regions)

| Plan | vCPUs | RAM | Storage | Traffic | EUR/mo |
|------|-------|-----|---------|---------|--------|
| CCX13 | 2 | 8 GB | 80 GB | 1 TB | 15.99 |
| CCX23 | 4 | 16 GB | 160 GB | 2 TB | 31.49 |
| CCX33 | 8 | 32 GB | 240 GB | 3 TB | 62.49 |
| CCX43 | 16 | 64 GB | 360 GB | 4 TB | 124.99 |
| CCX53 | 32 | 128 GB | 600 GB | 6 TB | 249.99 |
| CCX63 | 48 | 192 GB | 960 GB | 8 TB | 374.49 |

---

## Vercel Pro Pricing Reference (April 2026)

**Base:** $20/user/month (includes $20 usage credit)

| Resource | Included | Overage |
|---|---|---|
| Edge Requests | 10M/month | $2/1M |
| Fast Data Transfer | 1 TB/month | $0.15/GB |
| Functions Active CPU | — | $0.128/hour |
| Functions Provisioned Memory | — | $0.0106/GB-hour |
| Functions Invocations | — | $0.60/1M |
| Build Minutes (Standard) | — | $0.014/minute |
| Blob Storage | — | $0.023/GB |
| Blob Data Transfer | — | $0.05/GB |

**Key limits:** Serverless function timeout 60s (Pro). No persistent processes, no Docker, no background workers.

---

## Supabase Pro Pricing Reference (April 2026)

**Base:** $25/month (includes Micro compute)

### Included Allowances and Overage

| Resource | Included | Overage |
|---|---|---|
| Database disk | 8 GB | $0.125/GB |
| Egress | 250 GB | $0.09/GB |
| File storage | 100 GB | $0.021/GB |
| Auth MAUs | 100,000 | $0.00325/MAU |
| Edge Function invocations | 2M | $2/1M |
| Realtime connections | 500 concurrent | $10/1,000 |
| Backups | 7-day retention | — |

### Compute Add-Ons

| Size | CPU | RAM | ~Monthly | Max Connections |
|------|-----|-----|----------|-----------------|
| Micro (included) | 2-core ARM (shared) | 1 GB | ~$10 | 60 |
| Small | 2-core ARM (shared) | 2 GB | ~$15 | 90 |
| Medium | 2-core ARM (shared) | 4 GB | ~$60 | 120 |
| Large | 2-core ARM (dedicated) | 8 GB | ~$110 | 160 |
| XL | 4-core ARM (dedicated) | 16 GB | ~$210 | 240 |
| 2XL | 8-core ARM (dedicated) | 32 GB | ~$410 | 380 |
| 4XL | 16-core ARM (dedicated) | 64 GB | ~$960 | 480 |

---

## Bottom Line

For FlawChess's architecture (persistent Python backend, background workers, PostgreSQL on the same box), Hetzner delivers **~22x more hardware per dollar** with zero architectural constraints. The Vercel + Supabase stack is designed for JAMstack/Next.js apps with managed databases — it is a poor fit for a FastAPI + async worker setup regardless of price.

*Prices sourced from provider websites and verified third-party calculators, April 2026. Verify at hetzner.com/cloud, vercel.com/pricing, supabase.com/pricing.*
