# Miro.Care — Product Requirements Document

## Original Problem Statement
Hybrid AI-psychologist platform (React + FastAPI + MongoDB) with Fish Audio S2-Pro streaming TTS, emotional markers, multi-language and responsive support. Voice selection (male "Мирон" / female "Оксана") with locked prosody and emotional control.

## Core Requirements
- Voice synthesis via Fish Audio S2-Pro (streaming, balanced latency, bracket emotion syntax)
- LLM chat via OpenRouter (Claude Sonnet 4.5) with Anthropic prompt-caching
- Protected voice configuration in `voice_config.py` (no unauthorized edits)
- Protected landing-page CSS (`App.css` lines 70–240, clearly marked 🔒 LOCKED SECTION)
- At-rest encryption of chat messages & session notes (Fernet AES-128 + HMAC, key in `CHAT_ENCRYPTION_KEY`)
- Confidentiality-aware system prompt (§7): Мирон/Оксана честно отвечают что разговор защищён
- Agent switch in chat: click other avatar → new session, full fresh greeting, new voice
- Typing indicator: avatar + 3-dot animation + localized "печатает…" label
- Multi-language (ru/en/zh/es/ar/fr/de/hi), responsive mobile + desktop UI
- Deployment to Emergent platform (K8s + Cloudflare) — currently blocked by platform wrapper timeout

## 🔒 PERMANENT PROJECT RULES (apply to ALL future updates)
1. **Always-fresh PWA** — users MUST see the latest deployed version on every revisit. Service Worker `/frontend/public/sw.js` uses network-first for HTML + assets, passes-through `/api/*`. Registration in `index.html` calls `reg.update()` on load and auto-reloads on `controllerchange`. **Never** switch to cache-first for the shell. Bump `CACHE` version when sw.js logic changes.
2. **Voice IDs are locked to two values only.** Leon = `d9247a00779649adbe7f4fdde2ac11c8` (Brad Pitt), Kylie = `7a98513e3a7d439682fa68f8d4da34c0`. No other voice IDs allowed anywhere in code, env, docs, or tests.
3. **Landing page CSS (`App.css` 🔒 LOCKED SECTION) and `voice_config.py` are NEVER edited** without explicit user request.

## Locked / Protected
- `voice_config.py` — Fish Audio voice IDs, prosody, emotion markers, cleanup rules
- Landing-page CSS (`App.css` lines 70–240) — marked with 🔒 LOCKED SECTION banner
- AI names: **Мирон** (male), **Оксана** (female)
- Male voice ID: `5cfccfb8aae14938be283ea6400b4a8a`
- Female voice ID: `7a98513e3a7d439682fa68f8d4da34c0`
- Confidentiality contract: диалог зашифрован at-rest; доступ только у пользователя через его личный кабинет

## Changelog
- 2026-04-26: **Language grid stagger** — 8 language buttons cascade in with `translateY(8px → 0)` + opacity, 60ms apart (40/100/160/220/280/340/400/460ms), 320ms duration each. Pure CSS via `:nth-child` + same `cubic-bezier(0.16, 1, 0.3, 1)` ease as the rest of the menu.
- 2026-04-26: **Burger menu staggered reveal** — items now fade in with a 16px slide-from-right, 60ms apart (delays 600/660/720/780/840/900ms), settling just before the 2s panel slide finishes. iOS-Settings-like feel; pure CSS via `:nth-of-type` + `cubic-bezier(0.16, 1, 0.3, 1)`.
- 2026-04-26: **Burger menu redesign** — panel now opens to exactly half the viewport (`50vw` desktop, `70vw` tablet, `85vw` mobile). Glassmorphism: `background: rgba(20,22,30,0.42)` + `backdrop-filter: blur(8px) saturate(1.4)` (minimal blur, content behind stays readable). Typography: thin Helvetica Neue (`font-weight: 200`, `letter-spacing: 0.01-0.02em`) on every menu element. Slide-in animation: pure 2s `cubic-bezier(0.16, 1, 0.3, 1)` ease-out, no opacity flash. Verified via Playwright computed styles.
- 2026-04-26: **Barge-in support** — clicking the mic button now silences any in-flight TTS via `stopTTS()` before `startListening()`, so the user's recording doesn't overlap with Leon/Kylie's voice and STT no longer captures the agent's audio. Other barge-in paths (sending text → `resetTTSQueue→stopTTS`, sending an image → `playTTS→stopTTS`, clicking another bubble's speaker icon) already worked.
- 2026-04-26: **Magic Link auth (Email + WhatsApp)** — new `POST /api/auth/magic/request {channel, destination}` mints a `secrets.token_urlsafe(32)` token (TTL 24h via Mongo `magic_tokens.expires_at` index, unique on `token`), sends a one-tap link via `notifications.send_magic_link()`. **Senders are STUBBED** — they log `MAGIC_LINK_EMAIL_STUB` / `MAGIC_LINK_WHATSAPP_STUB` to the backend log; replace with Resend / Twilio in `notifications.py` once API keys land. `POST /api/auth/magic/verify {token}` is single-use, sets the existing httpOnly cookies, returns the user. Authenticated guests get promoted to `role='user'`, `is_guest=False`, with their email/phone attached — chat history is preserved across the upgrade. Frontend: new `/magic/:token` route (`MagicVerify.jsx`) auto-redirects to `/chat`; `AuthPromptModal` now has working "Email me a link" + "WhatsApp" inputs (E.164 + email regex validation) plus a confirmation screen. Apple stays "coming soon". Verified curl E2E: invalid email/phone → 400; valid → 200; verify → 200 + cookie set; reuse → 400 ("already used"); bogus token → 400; guest promotion sets role='user'/is_guest=False.
- 2026-04-26: **Contextual PWA install prompt** — install card no longer auto-pops 12s after landing. New trigger: `miro:show-install-prompt` window event, dispatched 6s after `intakeStep === -2` (intake completed) so the user has had a real, valuable interaction with Leon/Kylie first. Verified via Playwright: 13s on landing → 0 prompts; manual dispatch → 1 prompt rendered. 7-day dismiss-cooldown (`miro_install_dismissed_until`) preserved.
- 2026-04-26: **JWT migration to httpOnly Secure cookies** — auth tokens no longer stored in `localStorage` (XSS-resistant). `apiClient.js` uses `withCredentials:true`; all `fetch` calls (`useChat`, `useAudioStream`, `useSpeechRecognition`, `ChatPage` greeting preload) use `credentials:'include'` and dropped `Authorization: Bearer` injection. `AuthContext` no longer reads/writes `localStorage`. Backend `auth_utils.set_auth_cookies` honors `COOKIE_SECURE` env (default `true`); `get_current_user` reads cookie first, then Bearer header (backward-compat preserved for tests/older clients). `/auth/logout` clears both cookies. Verified: 14/14 new + 33/33 regression tests pass; live preview shows `localStorage.access_token === null`, cookies invisible to JS (httpOnly), `credentials:include` returns 200 vs `credentials:omit` returns 401 — cookie is authoritative.
- 2026-04-26: **Voice strict mode (Leon/Kylie never cross)** — backend `/api/tts` rejects (HTTP 400) any voice that's not exactly "male" or "female" instead of silently falling back to Kylie; frontend `useAudioStream` queue stores `{sentence, voice}` tuples per-sentence (no shared mutable ref) and `playTTS`/`enqueueSentence` refuse to play without a strict voice tag; `useChat` now passes `voice` explicitly to every `enqueueSentence` call. Fixes regression where Leon could switch to a female voice mid-response.
- 2026-04-26: **Intake localization (8 langs)** — `intakeQuestions.js` rewritten as `INTAKE_BY_LANG` with full translations for ru/en/zh/es/ar/fr/de/hi (intro/outro/options); `IntakeCard` buttons + placeholders read from `getIntakeButtons(lang)`; TTS voices intake intro + each question in user's selected language.
- 2026-04-26: **Streaming chat + sentence-by-sentence TTS** — new `/api/chat/stream` SSE endpoint streams Claude tokens; frontend `useChat` accumulates deltas and dispatches per-sentence TTS via `useAudioStream` queue (sentences ≥ 8 chars triggered on `.!?…` boundaries).
- 2026-04-26: **Independent chat histories per agent** — Leon and Kylie maintain separate `session_id` and messages arrays (`sessionsByVoiceRef` / `messagesByVoiceRef` in `useChat`). `switchVoice(newVoice, prevVoice)` snapshot-saves before activeVoice swaps.
- 2026-04-26: **Tone unification** — both agents speak in calm/professional/attentive/warm tone. `voice_config.EMOTION_MARKERS.base` → `[calm][professional][attentive][warm]`; `SYSTEM_PROMPT` style block adds «спокойный, профессиональный, внимательный, тёплый».
- 2026-04-18: Replaced female voice ID → `7a98513e3a7d439682fa68f8d4da34c0` (kept name "Оксана")
- 2026-04-18: Rolled back unauthorized deployment fixes (metrics, lazy loading) at user's request
- 2026-04-18: Added `/health` and `/api/health` for K8s readiness, moved DB init to background task, lazy SDK imports (33s → 0.45s cold start)
- 2026-04-19: **Bug fix** — chat responses no longer truncate mid-word. Raised max_tokens (short 80→160, medium 220→400, long 600→900) and added `_truncate_to_sentence()` fallback on `finish_reason=='length'`
- 2026-04-19: **Confidentiality** — at-rest Fernet encryption for `chat_messages.user_message`, `chat_messages.ai_response`, `users.session_notes`. New module `crypto_utils.py` with `ENC1::` prefix for backward compatibility. API endpoints auto-decrypt. SYSTEM_PROMPT §7 added.
- 2026-04-19: **Agent switch mid-dialog** — both avatars always clickable; clicking other agent starts a new `session_id`, clears history, plays full greeting in current language with new voice
- 2026-04-19: **Typing indicator** enhanced — avatar + 3-dot animation + localized label (`typingMiron`/`typingOksana` in 8 languages)
- 2026-04-19: **TTS stability** — rewrote `useAudioStream.js` with clean MSE→blob fallback, handlers cleanup, silenced benign `AbortError`/`DataCloneError` from CRA HMR. Also reduced cyclomatic complexity.
- 2026-04-19: **Landing CSS lock** — wrapped lines 70–240 in explicit 🔒 LOCKED SECTION banner
- 2026-04-25: **Slim You rebrand (A)** — Мирон→Leon, Оксана→Kylie globally; default UI lang switched to English. Landing replaced with fullscreen looping video (`/media/landing.mp4`).
- 2026-04-25: **Voice swap** — Leon voice ID changed from `5cfccfb8aae14938be283ea6400b4a8a` to `d9247a00779649adbe7f4fdde2ac11c8` (Brad Pitt model from fish.audio).
- 2026-04-25: **Cleanup** — deleted unused `miron-avatar.jpg`, `oksana-avatar.jpg`, `landing.webm`. New avatars: `leon-avatar.jpg` (Brad Pitt-like senior man), `kylie-avatar.jpg` (warm brunette woman).
- 2026-04-25: **Slim You B1–B5 redesign** — completed in one pass (backend 7/7 pytest, frontend smoke OK):
  - B1: ChatHeader rebuilt — back-btn left, `Leon • Kylie` avatars centered, TTS + ⋯ + burger right. New `QuickReplies` chip bar (`I feel good / Need support / Ask about food`) shown only after intake completes.
  - B2: BurgerMenu restructured to spec — Language, My Account, Talk to a Specialist, About Clinic, Pricing, Get App. `Get App` triggers PWA install prompt or "Coming soon" toast.
  - B3: New `SpecialistContactModal` with 3 channels (WhatsApp wa.me link, tel: call, contact form). New backend endpoint `POST /api/specialist/request` persists to `specialist_requests` collection.
  - B4: New `HeaderMenu` (⋯ popup) with `Clear chat`. New backend endpoint `DELETE /api/chat/messages` — wipes chat_messages + in-memory session histories ONLY; keeps users/profile/intake intact.
  - B5: New `AuthPromptModal` — auto-shown 1.5s after intake completes, **only for guests**, only **once** per session. 4 buttons: Continue with Google (→ /auth), Apple (Coming soon toast), WhatsApp (Coming soon toast), Continue as Guest (close modal).
- 2026-04-19: **i18n pass #2** — fixed hardcoded Russian strings: ChatPage alert & greeting pre-cache (now uses current `lang`), useChat error message, useSpeechRecognition alerts (3 places), PaymentSuccess fallback strings, BookingCalendar (legend/tz/price unit/month/weekday names). Added translation keys: `errorTryAgain`, `bookingFailed`, `advance` across 8 languages. `ChatInputArea` now accepts `unsupportedTitle` prop. Iter-18 verified OK; zh missing keys patched by tester.
- 2026-04-19: **PWA install flow** — added `manifest.json` (Miro.Care icons 192/512 + maskable), minimal service worker (`sw.js`) with shell cache + network-first for /api/. Replaced v2 SW-unregister script with v3 that keeps SW alive. Added `InstallPrompt` component: appears 12s after landing load (unless `display-mode: standalone` or dismissed), uses `beforeinstallprompt` + `appinstalled` native API, has install spinner + progress bar + success checkmark, 7-day dismiss cooldown. Localized in 8 languages (`installTitle`, `installSubtitle`, `installCta`, `installing`, `installed`, `installRetry`, `close`). RTL-aware close button.
- 2026-02-xx (iter21): **SYSTEM_PROMPT extended** — добавлены 4 новых блока между определением Mode 2 и «ЛОГИКА ВЕДЕНИЯ ДИАЛОГА» в `/app/backend/config.py`:
  1. **ОБРАБОТКА ДАННЫХ АНКЕТЫ** — молчаливое построение профиля клиента (ИМТ по формуле, цель 0.5–1 кг/нед, главный паттерн, триггер из В10, время из В9, риск из В13, мотивация из В14).
  2. **АКТИВНОЕ ИСПОЛЬЗОВАНИЕ ПРОФИЛЯ** — поведение триггеров (Стресс / Усталость / Скука), времени (Вечер / Ночь), истории неудачных попыток, ИМТ 35+, уровней мотивации 1-3 и 9-10, ограничений здоровья.
  3. **КОНТЕКСТ РАЗГОВОРА** — запрет повторять вопросы, использование уже сказанного.
  4. **ЗАПРЕТ ЗАКРЫТЫХ ОТВЕТОВ** — «Понятно./Ясно./Хорошо./Окей./Принято.» запрещены как финал; каждый ответ заканчивается вопросом / отражением / новым углом.
  Регрессия iteration_21: backend 10/10 pytest, frontend smoke 100%, Claude Sonnet 4.5 соблюдает все 4 правила (проверено на 5 живых вызовах + intake-recall на двух последовательных ходах той же сессии).
- 2026-02-xx (iter22): **Photo feature** — фото клиента в чат (функция была частично заложена ранее, доведена до спек-TZ):
  1. `SYSTEM_PROMPT` получил блок **АНАЛИЗ ФОТО** (ОДНО / ВТОРОЕ / ТРИ+ фото, «ЧЕГО НЕ ДЕЛАЕШЬ», «КОГДА САМ ПРОСИШЬ ФОТО», ПРИВАТНОСТЬ).
  2. `/app/backend/routes/chat.py`: введён `session_photo_count: OrderedDict` (LRU MAX_SESSIONS=500), и в `/chat/image` инжектится photo-directive в vision-prompt в зависимости от количества (1-е / 2-е / 3+).
  3. `ImagePickerModal.jsx`: добавлена надпись приватности с testid `photo-privacy-note`.
  4. `MessageList.jsx`: под каждым пузырьком с фото показывается подпись `t('photoSent')` (testid `photo-sent-caption-<i>`).
  5. i18n-ключи `photoSent` и `photoPrivacy` добавлены на все 8 языков (ru/en/zh/es/ar/fr/de/hi).
  6. CSS: расширил `.xc-image-picker-modal` (180×140), добавил `.xc-image-picker-privacy` + `.xc-chat-message-image-caption` — лендинг CSS (строки 70–240) не тронут.
  Регрессия iteration_22: backend 10/10 pytest, frontend smoke 100%. Claude Sonnet 4.5 Vision: 2-й ответ в той же сессии отличается от 1-го (comparison-mode работает), и AI не использует «ожирение / диагноз / идеал» (запреты соблюдаются).
- 2026-04-25: **Landing → fullscreen video** — старый лендинг (фото Мирона + glass-panel + бургер) полностью заменён на fullscreen зацикленное видео. Файлы в `/app/frontend/public/media/`: `landing.mp4` (1.1 MB, H.264, +faststart, без аудио), `landing.webm` (870 KB, VP9), `landing-poster.jpg` (первый кадр, 57 KB). Видео: `autoPlay muted loop playsInline preload="auto"`, `object-fit: contain` (без обрезки), чёрный фон. Поверх кнопки «BEGIN» в видео — прозрачная кнопка `[data-testid=landing-cta-overlay]` (~72vw × 9vh, bottom 8%) → `/chat`. Клик по самому видео тоже ведёт в чат. `LandingPage.jsx` переписан под новый минималистичный layout. Лендинг-CSS в `App.css` (строки 70–240) НЕ тронут — старые классы `.landing-*` остаются, но больше не используются. Smoke-test: видео грузится, прозрачная кнопка кликабельна, переход на `/chat` подтверждён.
- 2026-04-25: **Rebrand Step A — Leon / Kylie + English default** (Slim You spec):
  • Все упоминания `Мирон / Miron` заменены на `Leon`, `Оксана / Oksana` — на `Kylie` в `backend/{config,voice_config,server,routes/chat,routes/tts}.py`, frontend `pages/{ChatPage,SpecialistsPage,VoiceSelect,AboutPage}.jsx`, `components/chat/*`, `contexts/translations-extra.js`. Также заменены транслитерации в zh/es/ar/hi (米伦/奥克萨娜/Mirón/ميرون/أوكسانا/मिरोन/ओक्साना → Leon/Kylie).
  • Аватары: добавлены `/leon-avatar.jpg` и `/kylie-avatar.jpg` (копии существующих изображений), все ссылки в коде обновлены.
  • i18n-ключи `typingMiron/typingOksana` переименованы в `typingLeon/typingKylie` во всех 8 языках.
  • Дефолтный язык: `LanguageContext` — миграция `miro_lang_v3` ставит `en` как default (старые пользователи получат `en` при первой загрузке после деплоя).
  • Дефолтный агент: `Kylie (female)` — обновлены `ChatPage.setActiveVoice`, `useChat.voice`, `useAudioStream.voice`, `voice_config.get_voice_id` fallback, `tts.py` log fallback, `chat.py` persona-directive default.
  • Английский greeting обновлён под спек: «Hi, I'm Leon/Kylie — I'm here to support you. How are you feeling today?»; switch-greeting: «Good to see you again. Let's continue. — Leon/Kylie».
  • Persona-directive в `routes/chat.py` переписан с русского на английский (для cross-language согласованности): «Your name is Leon/Kylie. You identify as male/female. In any language with grammatical gender, speak in masculine/feminine form».
  • Voice IDs (Fish Audio Мирон/Оксана hash) НЕ тронуты — locked rule соблюдён.
  • Голосовая запись/MP3 lookup идёт по ключам `male/female` — переименование имён их не затрагивает.
  • Lint: backend ruff ✅, frontend ESLint ✅. Smoke: chat preview показывает аватары `LEON / KYLIE`, lang=`en`.

## Testing Status
- Iteration 17 (backend+frontend): **100% pass** — 12/12 scenarios including 8 languages, gender switching, encryption, TTS, UI flows
- Iteration 18 (i18n regression): **PASS** — /booking, /payment-success, RTL verified for ru/en/zh/ar; chat flow blocked by OpenRouter 402 (unrelated to code)
- Console warnings: **0** after useAudioStream rewrite

## Known Issues / Blocked
- 🔴 Production deployment: Cloudflare 520 / 120s wrapper timeout — **Emergent infra bug**, escalated to support. Do NOT attempt code fixes.
- 🔴 `POST /api/chat` → 402 Insufficient credits on OpenRouter. User must top up balance at https://openrouter.ai/settings/credits (or rotate `OPENROUTER_API_KEY` / swap model). Blocks live chat testing.

## Backlog (P2)
- Streaming Claude text → streaming TTS via SSE with barge-in
- Crisis-escalation logic (suicide risk detection)
- RAG / embeddings for `session_notes`
- Email/push notifications 24h before consultation
- YuKassa / Telegram Stars payments
- ~~PWA support~~ (done 2026-04-19)
- Admin panel
- Refactor: move API routes to `/app/backend/routes`, models to `/app/backend/models`, tests to `/app/backend/tests`

## Technical Debt (P1, optional)
- Remove hardcoded secret in `tests/test_iteration16_tts_streaming.py:20`
- Fix missing React hook dependencies: `useSpeechRecognition.js`, `useImageUpload.js`, `PaymentSuccess.jsx`, `useCountdown.js`
- Move auth token from `localStorage` to `httpOnly` cookie (security)

## Integrations
- OpenRouter (Claude Sonnet 4.5) — user API key
- Fish Audio S2-Pro (streaming TTS) — user API key
- Stripe (payments) — test key
- Emergent Universal LLM Key (configured as fallback)
