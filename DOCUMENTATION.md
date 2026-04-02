# Endl Support Bot — Complete Project Documentation

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [How It Works](#4-how-it-works)
   - [Architecture Overview](#41-architecture-overview)
   - [Private Chat Flow](#42-private-chat-flow)
   - [Group Chat Flow](#43-group-chat-flow)
   - [OTP Verification Flow](#44-otp-verification-flow)
   - [Escalation Flow](#45-escalation-flow)
5. [Core Modules Deep Dive](#5-core-modules-deep-dive)
   - [Bot Entry Point](#51-bot-entry-point--botpy)
   - [Configuration](#52-configuration--configpy)
   - [Database Layer](#53-database-layer)
   - [Message Handlers](#54-message-handlers)
   - [AI Integration](#55-ai-integration)
   - [Utilities](#56-utilities)
   - [Services](#57-services)
   - [Knowledge Base](#58-knowledge-base)
6. [Database Schema](#6-database-schema)
7. [Environment Variables](#7-environment-variables)
8. [Installation & Setup](#8-installation--setup)
9. [Deployment](#9-deployment)
10. [Security Considerations](#10-security-considerations)
11. [Future Scope](#11-future-scope)

---

## 1. Project Overview

**Endl Support Bot** is a production-grade AI-powered Telegram customer support bot built for **Endl**, a global business payments platform. It handles customer queries about onboarding, KYC/KYB verification, payments, currencies, corporate cards, account security, and escalation to human support agents.

### What Problem Does It Solve?

Endl's customer support team receives hundreds of repetitive queries daily about:
- KYC/KYB application status and documentation
- Which currencies and payment rails are supported
- How to send or receive international payments
- Onboarding document requirements
- Account security and corporate cards

Manually handling these at scale is slow, expensive, and inconsistent. This bot provides **instant, accurate, 24/7 support** for both individual and business users across private Telegram DMs and group chats.

### Key Capabilities

| Capability | Description |
|---|---|
| AI-Powered Q&A | Claude AI understands free-text questions and gives accurate answers |
| Account Type Routing | Separate flows and menus for Individual vs Business users |
| Button-Driven Navigation | Inline keyboard menus for structured, guided support |
| KYC Status Check | Email OTP verification before showing sensitive account status |
| Group Chat Support | Responds only when @mentioned in groups; plain text, no buttons |
| Escalation Tickets | Creates structured support tickets with conversation transcripts |
| Multi-Language Detection | Detects English and Hindi/Hinglish questions in group chats |
| Rate Limiting | Per-user message throttling to prevent abuse |
| Persistent Sessions | Conversation state and verified emails survive restarts |

---

## 2. Technology Stack

### Core Runtime

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Language | Python | 3.11+ | Primary application language |
| Telegram SDK | python-telegram-bot | >=20.7, <22.0 | Async Telegram Bot API wrapper |
| AI Model | Anthropic Claude | Haiku (latest) | Natural language understanding and response generation |
| Claude SDK | anthropic | >=0.40.0 | Python client for Claude API |
| Database | SQLite + aiosqlite | >=0.19.0 | Async persistent storage |
| Config | python-dotenv | >=1.0.0 | Environment variable management |
| Email | smtplib (stdlib) | — | OTP email delivery via SMTP |

### Auxiliary / Future Integrations

| Layer | Technology | Purpose | Status |
|---|---|---|---|
| KYC/KYB | SumSub API | Live applicant status lookups | Ready (not live) |
| Email Alt. | SendGrid (@sendgrid/mail) | Transactional email fallback | Installed (npm) |
| Caching Alt. | Upstash Redis (@upstash/redis) | Distributed response caching | Installed (npm) |
| Containerization | Docker | Reproducible deployments | Dockerfile present |
| Process Manager | Systemd | Linux service management | .service file present |

### Why These Choices?

- **Python 3.11 async/await**: python-telegram-bot v20+ is fully async, requiring modern Python. Async I/O ensures the bot handles hundreds of simultaneous users without blocking.
- **SQLite over PostgreSQL**: For a single-instance bot, SQLite with WAL (Write-Ahead Logging) mode provides sufficient concurrent read performance without the operational overhead of a separate database server.
- **Claude Haiku**: Optimized for low latency and cost at scale. Intent classification responses are structured JSON; Haiku's instruction-following capability is sufficient for this use case.
- **In-memory rate limiting**: Simple dict-based throttling avoids a Redis dependency for MVP. Redis upgrade path is already installed via npm.

---

## 3. Project Structure

```
TelegramAutomation_Recreated/
│
├── bot.py                          # Application entry point, handler registration
├── config.py                       # Centralized environment config loader
├── requirements.txt                # Python dependencies
├── package.json                    # Node.js dependencies (SendGrid, Redis)
├── Dockerfile                      # Docker container build instructions
├── telegram-bot.service            # Systemd Linux service definition
├── .env.example                    # Environment variable template (commit this)
├── .env                            # Actual secrets (NEVER commit)
├── .gitignore
├── .dockerignore
│
├── database/
│   ├── __init__.py
│   ├── db.py                       # SQLite connection, schema creation, WAL mode
│   └── models.py                   # Async data access functions (no ORM)
│
├── handlers/
│   ├── __init__.py
│   ├── start.py                    # /start and /help command handlers
│   ├── message_router.py           # Core private chat routing logic (527 lines)
│   ├── callback_handler.py         # Inline button press handler (861 lines)
│   ├── group_handler.py            # Group chat filtering and mention routing (289 lines)
│   ├── greeting.py                 # Greeting phrase detection utility
│   ├── classifier.py               # Keyword-based Individual/Business classifier
│   ├── intent_detector.py          # Keyword fallback intent detection
│   └── escalation.py               # Support ticket creation and severity logic
│
├── ai/
│   ├── __init__.py
│   ├── claude_client.py            # Claude API wrapper (get_ai_response, get_freetext_response)
│   └── system_prompt.py            # All system prompts (main, freetext, group) ~600 lines
│
├── utils/
│   ├── __init__.py
│   ├── keyboards.py                # InlineKeyboardMarkup builders for all menus (269 lines)
│   ├── otp.py                      # OTP generation, storage, verification, email (214 lines)
│   ├── rate_limiter.py             # Per-user sliding window rate limiter
│   ├── logger.py                   # Async interaction logging to database
│   ├── formatter.py                # Claude response sanitization (anti-markdown, truncation)
│   └── cache.py                    # In-memory static response cache for common questions
│
├── services/
│   ├── __init__.py
│   └── sumsub_client.py            # SumSub KYC/KYB API integration (HMAC-signed, 142 lines)
│
├── knowledge/
│   ├── __init__.py
│   └── knowledge_base.py           # 46-entry structured FAQ dict (143 lines)
│
├── flows/                          # Future: Separated workflow modules (currently placeholders)
│   ├── __init__.py
│   ├── document_help.py
│   ├── eligibility.py
│   ├── general_faq.py
│   ├── privacy_data.py
│   ├── rejection_error.py
│   └── status_progress.py
│
└── data/
    └── endl_bot.db                 # SQLite database (created at runtime)
```

---

## 4. How It Works

### 4.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       Telegram API                          │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS Long Polling
┌──────────────────────────▼──────────────────────────────────┐
│                        bot.py                               │
│         (ApplicationBuilder, Handler Registration)          │
└──┬────────────┬────────────┬─────────────┬──────────────────┘
   │            │            │             │
   ▼            ▼            ▼             ▼
start.py   message_router  callback_    group_handler
           .py             handler.py   .py
   │            │            │             │
   │            ▼            │             │
   │     ┌─────────────┐     │             │
   │     │ claude_     │     │             │
   │     │ client.py   │◄────┘             │
   │     │ (AI Layer)  │◄──────────────────┘
   │     └──────┬──────┘
   │            │
   ▼            ▼
┌──────────────────────────────────────────────────────────────┐
│                       database/                              │
│         sessions, conversation_history, tickets,            │
│         otp_codes, verified_users, logs                     │
└──────────────────────────────────────────────────────────────┘
   │            │
   ▼            ▼
utils/       services/
keyboards    sumsub_client
otp          (KYC API)
formatter
cache
```

The bot runs as a **single async Python process**. All I/O operations (Telegram API calls, database reads/writes, Claude API calls, email sending) are non-blocking via `asyncio`. A single event loop handles all concurrent users.

---

### 4.2 Private Chat Flow

This is the primary interaction mode.

```
User sends /start
      │
      ▼
Session created in DB
      │
      ▼
Step 0: "Are you an Individual or Business user?"
[Individual] [Business]
      │
      ▼ (button press)
Account type stored in session
Step 1: Main menu shown (differs by account type)
      │
      ├─── User clicks a menu button ──────────────────────────────┐
      │                                                            │
      │         callback_handler.py routes by prefix:             │
      │         nav: → navigation                                 │
      │         about: → product questions                        │
      │         curr: → currency/fee questions                    │
      │         payi: → individual payment questions              │
      │         payb: → business SWIFT questions                  │
      │         onb: → onboarding document questions              │
      │         card: → corporate card questions                  │
      │         sec: → security questions                         │
      │         sup: → support options                            │
      │         status: → KYC status check flow                   │
      │         otp: → OTP verification actions                   │
      │                                                            │
      └─── User sends free-text message ──────────────────────────┤
                                                                   │
                  Rate limit check                                 │
                        │                                          │
                        ▼                                          │
                  Greeting detection                               │
                  (exact match: "hi", "hello", etc.)              │
                        │                                          │
                        ▼                                          │
                  Cache lookup                                     │
                  (common Q&As cached in memory)                   │
                        │                                          │
                        ▼                                          │
                  get_freetext_response() → Claude API             │
                  Returns JSON:                                     │
                  {                                                 │
                    "intent": "currencies_fees",                    │
                    "reply": "Endl supports USD, EUR...",           │
                    "buttons": "currencies",                        │
                    "account_type_hint": null,                      │
                    "confidence": "high"                            │
                  }                                                 │
                        │                                          │
                        ▼                                          │
                  sanitize_response() → clean reply text           │
                        │                                          │
                        ▼                                          │
                  get_kb_by_name() → resolve button keyboard       │
                        │                                          │
                        ▼                                          │
                  Send reply + keyboard to user ◄──────────────────┘
```

**State Machine** — The session `state` field tracks where a user is in a flow:

| State | Meaning |
|---|---|
| `active` | Normal conversation |
| `status_awaiting_email` | Waiting for user to type their email |
| `status_awaiting_otp` | OTP sent, waiting for 6-digit code entry |
| `status_verified` | Email verified, can show status directly |
| `escalated` | Ticket created, awaiting human agent |

---

### 4.3 Group Chat Flow

Group chat is a read-only Q&A mode. The bot never sends unsolicited messages in groups.

```
Message arrives in group
        │
        ▼
group_handler.py filters:
  ├── Is the bot @mentioned? ──No──► Ignore completely
  │
  └── Yes → Clean @botname from text
              │
              ▼
        Is this a question/request?
        (English or Hindi/Hinglish keyword detection)
              │
        ├── No (casual: "ok", "lol", emojis) ──► Ignore
        │
        └── Yes ──► Pass cleaned text to message_router()
                          │
                          ▼
                    Claude API with GROUP_SYSTEM_PROMPT
                    (no buttons, 2-5 sentences max,
                     redirects KYC/OTP queries to DM)
                          │
                          ▼
                    Reply threaded to original message
```

**Group System Prompt rules:**
- Never ask for personal information in the group
- Redirect sensitive queries (KYC status, documents, OTP) with: "Please DM me for that"
- No bullet points, no markdown, no emojis
- 2–5 sentence limit per response

---

### 4.4 OTP Verification Flow

This flow protects access to sensitive account status information.

```
User clicks "Check My Status"
        │
        ▼
Session state → status_awaiting_email
"Please enter your registered email address"
        │
        ▼
User types email address
        │
        ├── Invalid format → "Please enter a valid email"
        │
        └── Valid → generate_otp() → 6-digit code
                         │
                         ▼
                   store_otp() in DB with:
                   - expiry timestamp (5 min)
                   - max 3 resend attempts per 15 min
                         │
                         ▼
                   send_otp_email() via SMTP (Gmail)
                   HTML + plain text email
                         │
                         ▼
                   Session state → status_awaiting_otp
                   "Enter the 6-digit code from your email"
                        │
                        │
        ┌───────────────┴─────────────────┐
        │                                 │
User enters code                  User clicks Resend
        │                                 │
        ▼                                 ▼
  verify_otp()                   Check resend rate limit
  ├── Expired → "Code expired"   (max 3 per 15 min)
  ├── Wrong code:                       │
  │   attempts++                  Generate new OTP
  │   ├── <3 left → retry          Send new email
  │   └── >=3 → lock session
  └── Correct:
        │
        ▼
  save_verified_user() → permanent DB record
  Session state → active
  Show status (SumSub lookup or placeholder)
```

Once verified, the email is stored permanently. Future "Check Status" requests skip the OTP flow entirely.

---

### 4.5 Escalation Flow

Triggered automatically when Claude detects repeated frustration, or manually when the user clicks "Contact Support".

```
Trigger conditions:
  A) User clicks "Escalate / Contact Agent" button
  B) Claude detects intent = "frustration" twice in same session
  C) OTP verification fails 3 times
        │
        ▼
escalation.py:
  1. Determine severity:
     - CRITICAL: "fraud", "locked", "suspended", "stolen"
     - HIGH:     "urgent", "emergency", "immediately"
     - MEDIUM:   general escalation
  2. Fetch conversation transcript from DB
  3. Call Claude to generate a 2-sentence AI summary
  4. Save ticket: user_id, severity, transcript, summary
  5. Return ticket ID (e.g. TKT-20260330-4821)
        │
        ▼
User receives:
  "Your case has been escalated. Ticket: TKT-XXXXXXXX
   A support agent will contact you within 24 hours."
  [Support Group Link] button shown
```

---

## 5. Core Modules Deep Dive

### 5.1 Bot Entry Point — `bot.py`

Initializes the entire application:

1. Builds the Telegram `Application` with the bot token
2. Registers all handlers with priority ordering:
   ```
   Priority 1:  /start, /help, /ticket commands
   Priority 2:  Group messages (all text in groups)
   Priority 3:  Callback queries (button presses)
   Priority 4:  Private text messages
   Priority 5:  Non-text messages (photos, docs → gentle redirect)
   ```
3. `post_init` hook: initializes the SQLite database schema and validates the Claude API key
4. On Windows: applies `asyncio.WindowsSelectorEventLoopPolicy` to fix known Python/asyncio compatibility issue
5. Runs `application.run_polling()` for continuous updates

---

### 5.2 Configuration — `config.py`

Single source of truth for all runtime settings. Loads `.env` at startup and exposes typed constants:

```python
BOT_TOKEN            # Telegram bot token
ANTHROPIC_API_KEY    # Claude API key
CLAUDE_MODEL         # e.g. "claude-haiku-4-5-20251001"
CLAUDE_MAX_TOKENS    # Response token ceiling (default: 1024)
CLAUDE_TEMPERATURE   # Creativity 0.0–1.0 (default: 0.2)
DB_PATH              # SQLite file path
RATE_LIMIT_MESSAGES  # Max messages per window (default: 10)
RATE_LIMIT_WINDOW_SECONDS  # Window length (default: 60)
SUPPORT_LINK         # Telegram group URL for escalation
SMTP_HOST/PORT/USER/PASSWORD/FROM_EMAIL  # Email settings
OTP_EXPIRY_SECONDS   # OTP validity window (default: 300)
OTP_MAX_ATTEMPTS     # Wrong attempts before lockout (default: 3)
SUMSUB_APP_TOKEN / SUMSUB_SECRET_KEY / SUMSUB_BASE_URL
```

---

### 5.3 Database Layer

#### `database/db.py` — Schema & Connection

Creates an async SQLite connection with `PRAGMA journal_mode=WAL` for concurrent reads. Schema consists of 8 tables:

| Table | Purpose |
|---|---|
| `sessions` | Per-user conversation state, email, account type, frustration count |
| `conversation_history` | Full message-by-message transcript per session |
| `conversation_logs` | Analytics: intent, response time, cache hit, escalation flag |
| `escalation_tickets` | Support tickets with severity, summary, transcript |
| `otp_codes` | Active OTP codes with expiry and attempt tracking |
| `otp_resend_counts` | Rate limiting for OTP resend requests |
| `verified_users` | Permanent email→user_id mapping after OTP success |

#### `database/models.py` — Data Access

Async functions that abstract all SQL. Key functions:

```python
get_or_create_session(user_id)          # Fetch or initialize session
update_session(user_id, **kwargs)        # Update any session fields
save_message(user_id, role, content)     # Append to conversation_history
get_conversation_history(user_id, n=20) # Last N messages for Claude context
save_ticket(user_id, severity, ...)      # Create escalation ticket
save_verified_user(user_id, email)       # Store verified email permanently
get_verified_email(user_id)              # Check if user already verified
```

---

### 5.4 Message Handlers

#### `handlers/message_router.py` — Core Brain (527 lines)

The most complex module. Entry point: `handle_message(update, context)`.

Decision tree at a high level:
```
1. Extract user_id, text, session
2. Rate limit check → early exit if exceeded
3. Is greeting? → show welcome message
4. Is session in status_awaiting_email? → validate + send OTP
5. Is session in status_awaiting_otp? → verify OTP code
6. Get Claude's freetext intent + reply (get_freetext_response)
7. Track frustration count
8. Auto-escalate if frustration_count >= 2
9. Resolve button keyboard from Claude's `buttons` field
10. Sanitize response text
11. Save message to history
12. Send reply + keyboard to user
```

#### `handlers/callback_handler.py` — Button Routing (861 lines)

Routes every button press. Each callback_data has a prefix:

| Prefix | Handler Section |
|---|---|
| `nav:` | Navigation (back, main menu, sub-menus) |
| `acct:` | Account type selection |
| `about:` | Product information questions |
| `curr:` | Currency and fee questions |
| `payi:` | Individual payment questions |
| `payb:` | Business SWIFT questions |
| `onb:` | Onboarding document questions |
| `card:` | Corporate card questions |
| `sec:` | Security questions |
| `sup:` | Support contact options |
| `status:` | KYC/KYB status check flow |
| `otp:` | OTP actions (resend, cancel) |
| `grp:` | Group chat quick menu |

#### `handlers/group_handler.py` — Group Chat Filter (289 lines)

Smart filtering logic:
- Only activates on `@botname` mention
- `is_question_or_request()`: checks English question words (what, how, why, when, where, can, does, is) AND Hindi/Hinglish words (kya, kaise, kyun, batao, bolo, etc.)
- `is_casual_message()`: filters out acknowledgments ("ok", "thanks", "lol") and pure emoji messages
- Strips @mention before passing to AI to avoid confusing Claude

---

### 5.5 AI Integration

#### `ai/claude_client.py`

Two main functions:

**`get_ai_response(messages, system_prompt, model, max_tokens, temperature)`**
- Direct Claude API call with conversation history
- Handles the API's requirement that messages alternate user/assistant
- 60-second timeout
- Returns plain text string

**`get_freetext_response(user_message, session, conversation_history)`**
- Calls Claude with `FREETEXT_SYSTEM_PROMPT`
- Instructs Claude to return strict JSON:
  ```json
  {
    "intent": "currencies_fees",
    "reply": "Endl supports USD, EUR, GBP, AED...",
    "buttons": "currencies",
    "account_type_hint": "business",
    "confidence": "high"
  }
  ```
- Parses JSON with fallback error handling
- Uses `temperature=0.1` for consistent, deterministic intent classification

#### `ai/system_prompt.py`

Three system prompts totaling ~600 lines:

**`SYSTEM_PROMPT_TEMPLATE`** (Main, ~312 lines):
- Defines bot as "Endl Support Assistant"
- Hard rules: never pretend to be human, never invent features, never generate welcome messages
- Per-intent response guidelines (document help, status, rejection errors, etc.)
- Embedded knowledge base: currencies, fees, onboarding docs, payment rails, SWIFT codes
- Escalation triggers: Dubai tax ID questions, SWIFT incoming queries, repeated failures
- Output rules: ≤2 sentences, no dashes, no `**bold**`, no emojis

**`FREETEXT_SYSTEM_PROMPT`** (~150 lines):
- Returns structured JSON only (no prose)
- Defines 16 intent types with exact `buttons` values for keyboard resolution
- Full knowledge base embedded inline

**`GROUP_SYSTEM_PROMPT`** (~80 lines):
- Community-appropriate version
- Redirects sensitive queries to DM
- No buttons, no markdown, 2–5 sentence max

---

### 5.6 Utilities

#### `utils/keyboards.py`
Centralizes all `InlineKeyboardMarkup` construction. Uses a `_mk(rows)` helper where rows are lists of `(label, callback_data)` tuples. Key keyboards:

- `KB_ACCOUNT_TYPE` — Individual / Business selection
- `kb_main(account_type)` — Main menu (6 options, varies by type)
- `KB_ABOUT` — 5 product overview questions
- `KB_CURRENCIES` — 4 currency/fee questions
- `KB_PAY_IND` — 6 individual payment questions
- `KB_PAY_BIZ` — 5 SWIFT/business questions
- `KB_ONBOARDING` — 8 document verification questions
- `KB_CARD` — 5 corporate card questions
- `KB_SECURITY` — 3 security questions
- `KB_SUPPORT` — 4 support options
- `KB_GROUP_MAIN` — Simplified group chat menu
- `get_kb_by_name(name)` — Resolves button set name from Claude's JSON to a keyboard object

#### `utils/otp.py`
Full OTP lifecycle management:
- `generate_otp()` → Random `randint(100000, 999999)` as string
- `store_otp(user_id, email, code)` → DB insert with expiry + resend rate check
- `verify_otp(user_id, entered_code)` → Validates code, expiry, attempt count; returns status string
- `cancel_otp(user_id)` → Deletes pending OTP (user cancelled)
- `send_otp_email(to_email, otp_code)` → SMTP email with HTML and plain text body

#### `utils/formatter.py`
Protects users from raw Claude output artifacts:
- `_is_welcome_message()` → Detects forbidden AI-generated welcome messages (contains "Welcome to Endl", "How can I assist", etc.)
- `sanitize_response()`:
  - Replaces `- item` with `1. item` (numbered lists instead of dashes)
  - Strips `**bold**` markdown
  - Removes em-dashes as separators (`— `)
  - Hard truncates at 4096 characters (Telegram message limit)

#### `utils/cache.py`
Prevents redundant Claude API calls for the most common questions:
- 7 pre-computed Q&A pairs (what is Endl, what currencies, what fees, etc.)
- Variants per account type (individual vs business answers differ)
- `get_cached_response(question, account_type)` → Returns cached text or `None`

#### `utils/rate_limiter.py`
In-memory per-user throttling:
- Dict of `{user_id: [timestamps]}`
- Sliding window: removes timestamps older than `RATE_LIMIT_WINDOW_SECONDS`
- Returns `True` (rate limited) if count exceeds `RATE_LIMIT_MESSAGES`
- Periodic cleanup every 100 calls to avoid unbounded memory growth

#### `utils/logger.py`
- `log_interaction(user_id, intent, user_type, response_time, cache_hit, escalated)` → Async write to `conversation_logs` table
- Used for analytics and support auditing

---

### 5.7 Services

#### `services/sumsub_client.py` — KYC/KYB API (142 lines)

Full HMAC-SHA256 signed SumSub API integration:
- `_sign_request(method, url, body)` → Generates `X-App-Token` and `X-App-Access-Sig` headers
- `search_applicant_by_email(email)` → POST `/resources/applicants/-;externalUserId={email}/one`
- `get_applicant_status(applicant_id)` → GET review status: `completed`, `pending`, `rejected`
- `get_document_status(applicant_id)` → GET per-document verification state
- `format_status_message(applicant_id)` → Human-readable Telegram message with status emoji

**Status**: Fully implemented but not yet connected to live production. The callback handler has a placeholder that would call this after OTP verification.

---

### 5.8 Knowledge Base

#### `knowledge/knowledge_base.py`

46-entry structured dict organized by topic:

```python
{
  "general": [
    {"q": "What is Endl?", "a": "Endl is a global business payments..."},
    {"q": "Who can use Endl?", ...},
    ...
  ],
  "onboarding": [...],
  "kyc_kyb": [...],
  "payments_receiving": [...],
  "payments_sending": [...],
  "security": [...],
  "cards": [...],
  "support": [...]
}
```

This knowledge base is **embedded directly into the Claude system prompts** so Claude always has authoritative answers without external retrieval. It is also used by `callback_handler.py` for button-press answers that don't need Claude.

---

## 6. Database Schema

### `sessions`
```sql
CREATE TABLE sessions (
  user_id          INTEGER PRIMARY KEY,
  state            TEXT DEFAULT 'active',
  account_type     TEXT,               -- 'individual' or 'business'
  email            TEXT,               -- email during OTP flow
  verified_email   TEXT,               -- confirmed email
  frustration_count INTEGER DEFAULT 0,
  last_active      TIMESTAMP,
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### `conversation_history`
```sql
CREATE TABLE conversation_history (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER,
  role       TEXT,    -- 'user' or 'assistant'
  content    TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### `escalation_tickets`
```sql
CREATE TABLE escalation_tickets (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id   TEXT UNIQUE,  -- e.g. TKT-20260330-4821
  user_id     INTEGER,
  severity    TEXT,          -- 'critical', 'high', 'medium'
  summary     TEXT,          -- Claude-generated 2-sentence summary
  transcript  TEXT,          -- Full conversation JSON
  status      TEXT DEFAULT 'open',
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### `otp_codes`
```sql
CREATE TABLE otp_codes (
  user_id    INTEGER PRIMARY KEY,
  email      TEXT,
  code       TEXT,
  expires_at TIMESTAMP,
  attempts   INTEGER DEFAULT 0
)
```

### `verified_users`
```sql
CREATE TABLE verified_users (
  user_id    INTEGER PRIMARY KEY,
  email      TEXT,
  verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

---

## 7. Environment Variables

Copy `.env.example` to `.env` and fill in all values:

```bash
# Telegram
BOT_TOKEN=                        # From @BotFather

# Anthropic Claude
ANTHROPIC_API_KEY=                # From console.anthropic.com
CLAUDE_MODEL=claude-haiku-4-5-20251001
CLAUDE_MAX_TOKENS=1024
CLAUDE_TEMPERATURE=0.2

# Database
DB_PATH=data/endl_bot.db

# Rate Limiting
RATE_LIMIT_MESSAGES=10
RATE_LIMIT_WINDOW_SECONDS=60

# Support
SUPPORT_LINK=https://t.me/your_support_group

# Email (OTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_app_password    # Gmail App Password, not account password
SMTP_FROM_EMAIL=support@endl.com

# OTP Settings
OTP_EXPIRY_SECONDS=300
OTP_MAX_ATTEMPTS=3

# SumSub KYC/KYB (optional for now)
SUMSUB_APP_TOKEN=
SUMSUB_SECRET_KEY=
SUMSUB_BASE_URL=https://api.sumsub.com

# SendGrid (optional alternative to SMTP)
SENDGRID_API_KEY=

# Upstash Redis (optional distributed cache)
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
```

---

## 8. Installation & Setup

### Prerequisites

- Python 3.11 or higher
- pip
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- An [Anthropic API key](https://console.anthropic.com/)
- A Gmail account with App Password enabled (for OTP)

### Steps

```bash
# 1. Clone the repository
git clone <repo-url>
cd TelegramAutomation_Recreated

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # Linux/Mac
venv\Scripts\activate             # Windows

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your values

# 5. Run the bot
python bot.py
```

The database file (`data/endl_bot.db`) is created automatically on first run.

### For Group Chat Support

In [@BotFather](https://t.me/BotFather):
1. `/mybots` → Select your bot → `Bot Settings` → `Group Privacy`
2. Set to **DISABLED** (so the bot can read all messages)
3. Add the bot to your group and make it an admin if needed

---

## 9. Deployment

### Docker

```bash
# Build image
docker build -t endl-support-bot .

# Run container
docker run -d \
  --name endl-bot \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  endl-support-bot
```

The `Dockerfile` uses:
- `python:3.11-slim` base image
- Non-root user (`botuser`) for security
- `/app/data` volume for persistent SQLite database

### Linux Systemd Service

```bash
# Copy service file
sudo cp telegram-bot.service /etc/systemd/system/

# Edit paths and user in the service file
sudo nano /etc/systemd/system/telegram-bot.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable endl-bot
sudo systemctl start endl-bot

# Check status
sudo systemctl status endl-bot
sudo journalctl -u endl-bot -f
```

The service file includes security hardening:
- `ProtectSystem=full`
- `ProtectHome=true`
- `PrivateTmp=true`
- Auto-restart on failure

---

## 10. Security Considerations

### Current Protections

| Mechanism | Implementation |
|---|---|
| Secrets management | `.env` file excluded from git via `.gitignore` |
| OTP verification | 5-minute expiry, 3-attempt lockout, 3 resends per 15 min |
| Rate limiting | Per-user message throttling (10 msg/60s default) |
| Non-root Docker | Container runs as `botuser`, not root |
| Systemd hardening | `ProtectSystem`, `ProtectHome`, `PrivateTmp` |
| Input sanitization | Claude response formatter strips injection artifacts |
| HMAC signing | SumSub API calls are HMAC-SHA256 signed |

### Known Risks & Recommendations for Production

| Risk | Severity | Recommendation |
|---|---|---|
| SQLite stores plaintext messages | Medium | Encrypt at rest (SQLCipher), or migrate to PostgreSQL with row-level encryption |
| SMTP credentials in `.env` | Medium | Use a secrets manager (HashiCorp Vault, AWS Secrets Manager) |
| In-memory rate limiter resets on restart | Low | Migrate to Redis (already installed via npm) |
| No Telegram webhook signature verification | Low | Add `X-Telegram-Bot-Api-Secret-Token` header check if switching to webhooks |
| OTP sent only via email | Low | Add SMS (Twilio) as a fallback for users without email access |
| Group Privacy setting is manual | Low | Document this clearly in ops runbook; monitor with bot health checks |

---

## 11. Future Scope

The codebase has been deliberately designed for extension. Below are the planned and potential improvements.

### High Priority — Near Term

#### 1. Live SumSub KYC/KYB Status
- `services/sumsub_client.py` is fully implemented and awaits connection
- Connect `format_status_message()` to the post-OTP-verification callback in `callback_handler.py`
- Enables real-time "Your KYC application is: Approved / In Review / Rejected" responses

#### 2. Redis-Based Distributed Cache
- `@upstash/redis` is already installed (`package.json`)
- Replace `utils/cache.py` in-memory dict with Redis calls
- Enables horizontal scaling (multiple bot instances behind a load balancer)
- Session state could also move to Redis for stateless Python processes

#### 3. SendGrid Email Migration
- `@sendgrid/mail` is already installed
- Replace SMTP in `utils/otp.py` with SendGrid for better deliverability, open tracking, and template management

#### 4. Webhook Mode
- Switch from long-polling to Telegram webhooks for lower latency and reduced server load
- Requires a public HTTPS endpoint (Nginx reverse proxy + Let's Encrypt)

---

### Medium Priority — Product Features

#### 5. Flows Module Completion
The `flows/` directory contains six placeholder modules. Complete them as isolated, testable flow classes:

| Flow | Purpose |
|---|---|
| `flows/status_progress.py` | Full KYC/KYB status check journey |
| `flows/document_help.py` | Step-by-step document verification guidance |
| `flows/rejection_error.py` | Guide users through rejection reasons and re-submission |
| `flows/eligibility.py` | Pre-check if a user's country/business type is eligible |
| `flows/general_faq.py` | Standalone FAQ retrieval with semantic search |
| `flows/privacy_data.py` | GDPR data deletion / access request handling |

#### 6. Multilingual Support
- The group handler already detects Hindi/Hinglish questions
- Add Claude prompts in Arabic (key market: UAE) and Hindi for full multilingual responses
- Store user language preference in `sessions` table

#### 7. Admin Dashboard
- Build a Flask/FastAPI web UI to:
  - View open escalation tickets
  - Close / assign tickets to agents
  - View conversation transcripts
  - Analytics: common intents, resolution times, escalation rates

#### 8. Human Handoff Integration
- Integrate with Zendesk, Freshdesk, or Intercom API
- On escalation: automatically create a ticket in the support platform with transcript attached
- Two-way sync: when agent closes ticket, bot notifies the Telegram user

#### 9. Proactive Messaging
- Use Telegram's `bot.send_message()` for outbound notifications:
  - "Your KYC application has been approved!"
  - "Your payment of $1,000 has been received"
  - "Action required: please resubmit your passport"
- Requires a background worker (APScheduler or Celery) polling SumSub webhooks

---

### Long Term — Architecture

#### 10. PostgreSQL Migration
- Replace SQLite for true multi-instance horizontal scaling
- Add `pgcrypto` for encrypted message storage
- Use Alembic for database migrations

#### 11. RAG (Retrieval-Augmented Generation)
- Move the knowledge base from hardcoded system prompts into a vector database (Pinecone, Weaviate, or pgvector)
- Automatically embed new FAQ entries; Claude retrieves relevant chunks at query time
- Enables the knowledge base to scale to thousands of articles without prompt bloat

#### 12. Voice Message Support
- Telegram supports voice messages; use Whisper API (OpenAI) or AssemblyAI to transcribe
- Pass transcript to existing message_router pipeline
- Particularly valuable for users who are not comfortable typing

#### 13. Analytics Pipeline
- Stream `conversation_logs` to a data warehouse (BigQuery, Redshift)
- Build dashboards for:
  - Daily active users
  - Intent distribution (what are users asking most?)
  - Escalation rate trends
  - OTP completion funnel
  - Response time P50/P95

#### 14. A/B Testing System Prompts
- Route a percentage of users to an alternative system prompt
- Log which variant was used in `conversation_logs`
- Measure escalation rate and user satisfaction per variant

#### 15. Multi-Bot Architecture
- Separate bots for different regions (Endl UAE, Endl Europe) with locale-specific system prompts
- Shared database with `region` partitioning
- Central admin dashboard aggregates across all bots

---

## Appendix: Intent Types Reference

The AI classifies every free-text message into one of 16 intents:

| Intent | Triggers | Button Set |
|---|---|---|
| `check_status` | "what is my status", "kyc approved?" | `status_flow` |
| `about_endl` | "what is endl", "tell me about" | `about` |
| `currencies_fees` | "which currencies", "what are fees" | `currencies` |
| `payments_individual` | "how do I send money", "receive payment" | `pay_ind` |
| `payments_business` | "SWIFT", "business transfer", "invoice" | `pay_biz` |
| `onboarding` | "documents", "verification", "how to apply" | `onboarding` |
| `card` | "corporate card", "debit card" | `card` |
| `security` | "password", "2FA", "account locked" | `security` |
| `support` | "talk to agent", "contact support" | `support` |
| `frustration` | "useless", "not working", "this is terrible" | `escalate` |
| `menu` | "menu", "options", "help" | `main` |
| `greeting` | "hi", "hello", "good morning" | `main` |
| `account_switch` | "I'm a business", "actually individual" | _(updates session)_ |
| `rejection_error` | "rejected", "error", "failed" | `support` |
| `eligibility` | "can I use", "is my country supported" | `about` |
| `unknown` | anything else | `main` |
