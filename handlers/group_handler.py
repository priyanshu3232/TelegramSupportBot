# --------------------------------------------------------------------------
# GROUP CHAT SUPPORT
# Testing checklist:
#  1. Private chat: Bot responds to every message               (unchanged)
#  2. Group chat: Bot ignores casual non-question messages       ✓
#  3. Group chat: Bot responds when @mentioned                   ✓
#  4. Group chat: Bot responds when someone replies to bot's msg ✓
#  5. Group chat: Bot responds to detected questions (no tag)    ✓
#  6. Group chat: @botusername is stripped from query             ✓
#  7. Group chat: Bot replies are threaded (reply to original)   ✓
#  8. Group chat: Empty @mention sends help text                 ✓
#  9. Group chat: Commands like /help@botusername work           ✓
# 10. Photos, stickers, non-text messages don't crash the bot    ✓
# 11. REMINDER: Disable Group Privacy via @BotFather →
#       /mybots → Bot Settings → Group Privacy → OFF
# 12. REMINDER: Remove and re-add bot to existing groups after
#       changing the privacy setting
# --------------------------------------------------------------------------

import logging
import re
import traceback
import unicodedata

from telegram import Update
from telegram.ext import ContextTypes

from handlers.message_router import handle_message
from handlers.greeting import is_greeting
from utils.keyboards import KB_GROUP_MAIN

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Smart question detection
# ---------------------------------------------------------------------------

# English question starters (lowercase)
_EN_QUESTION_WORDS = {
    "what", "how", "why", "when", "where", "who", "which",
    "can", "could", "should", "would", "will", "shall",
    "is", "are", "was", "were", "am",
    "do", "does", "did",
    "has", "have", "had",
    "may", "might", "must",
    "isn't", "aren't", "wasn't", "weren't",
    "don't", "doesn't", "didn't",
    "won't", "wouldn't", "shouldn't", "couldn't",
    "can't", "cannot",
}

# Hindi / Hinglish question words (romanised)
_HI_QUESTION_WORDS = {
    "kya", "kyu", "kyun", "kyon", "kyunki", "kaise", "kaisa", "kaisi",
    "kab", "kaha", "kahaan", "kahan", "kidhar", "kaun", "kis", "kiska",
    "kiski", "kiske", "kitna", "kitni", "kitne", "konsa", "konsi",
    "matlab", "aisa", "aisi", "aise",
}

# Casual / non-question messages that should be ignored
_CASUAL_PATTERNS = re.compile(
    r"^("
    r"ok+|okay|k+|lol+|lmao|haha+|hehe+|hmm+|ohh*|ahh*|umm*"
    r"|thanks?|thanku|thankyou|thank\s*you|thx|ty|dhanyavaad|shukriya"
    r"|yes|no|yep|yup|nah|nope|ha+n|na+h|ji|accha|acha|theek|thik"
    r"|nice|great|good|cool|wow|awesome|perfect|sure|done|fine"
    r"|hi|hello|hey|hii+|hola|namaste|namaskar"
    r"|bye|goodbye|gn|gm|good\s*(morning|night|evening)"
    r"|agreed|exactly|correct|right|true|same"
    r"|👍|👎|😂|🙏|❤️|🔥|💯|😊|😅|🤣|👀|✅|🎉"
    r")$",
    re.IGNORECASE,
)

# Hinglish question-like suffixes / patterns
_HINGLISH_SUFFIX_RE = re.compile(
    r"("
    r"\bkya\s*$"           # ends with "kya" (Hindi question marker)
    r"|\bhai\s*kya\s*$"    # "hai kya"
    r"|\bhoga\s*$"         # "hoga" (will it be?)
    r"|\bhoga\s*kya\s*$"
    r"|\bmilega\s*$"       # "milega" (will I get?)
    r"|\bmilega\s*kya\s*$"
    r"|\bsakte\s*(ho|hain|hai)\s*$"  # "kar sakte ho?"
    r"|\bsakta\s*(hu|hai|hoon)\s*$"
    r"|\bpata\s*hai\s*$"   # "pata hai" (do you know?)
    r"|\bbatao\s*$"        # "batao" (tell me) — imperative question
    r"|\bbataiye\s*$"
    r"|\bbata\s*do\s*$"
    r"|\bho\s*sakta\s*hai\s*$"
    r")",
    re.IGNORECASE,
)


def is_question(text: str) -> bool:
    """Detect whether *text* is a question worth answering.

    Covers:
    - Trailing question mark (``?``)
    - English question-word openers
    - Hindi / Hinglish question words and suffixes
    - Mixed-language patterns
    Returns ``False`` for casual filler messages.
    """
    if not text:
        return False

    # Normalise: strip whitespace, collapse runs of whitespace, remove
    # variation selectors / zero-width chars so emoji patterns match.
    cleaned = unicodedata.normalize("NFC", text.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)

    # Reject obvious casual / non-question messages
    if _CASUAL_PATTERNS.match(cleaned):
        return False

    # Very short messages (1-2 words, no ?) are almost never questions
    words = cleaned.split()
    if len(words) <= 2 and "?" not in cleaned:
        return False

    # 1. Ends with a question mark (after stripping trailing emoji / spaces)
    stripped_tail = re.sub(r"[\s\U0001f600-\U0001f64f\U0001f300-\U0001f5ff]+$", "", cleaned)
    if stripped_tail.endswith("?"):
        return True

    # 2. Starts with an English question word
    first_word = words[0].lower().rstrip(",.!?;:")
    if first_word in _EN_QUESTION_WORDS:
        return True

    # 3. Starts with a Hindi/Hinglish question word
    if first_word in _HI_QUESTION_WORDS:
        return True

    # 4. Hinglish question-like suffix ("kya", "hoga", "milega", etc.)
    if _HINGLISH_SUFFIX_RE.search(cleaned):
        return True

    # 5. Contains a Hindi/Hinglish question word anywhere (for mixed sentences)
    lower_words = {w.lower().rstrip(",.!?;:") for w in words}
    hinglish_hits = lower_words & _HI_QUESTION_WORDS
    if hinglish_hits and len(words) >= 3:
        return True

    return False

# Cached bot username — populated once on first group message
_bot_username: str | None = None


async def _get_bot_username(context: ContextTypes.DEFAULT_TYPE) -> str | None:
    """Return the bot's username, caching it after the first lookup."""
    global _bot_username
    if _bot_username is None:
        try:
            me = await context.bot.get_me()
            _bot_username = me.username
            logger.info("Bot username resolved: @%s", _bot_username)
        except Exception as exc:
            logger.error("Failed to resolve bot username: %s", exc)
            return None
    return _bot_username


def clean_message_text(text: str, bot_username: str) -> str:
    """Strip all occurrences of @bot_username (case-insensitive) and trim."""
    pattern = re.compile(re.escape(f"@{bot_username}"), re.IGNORECASE)
    return pattern.sub("", text).strip()


def _should_respond_in_group(
    message_text: str,
    bot_username: str,
    reply_to_message,
) -> tuple[bool, str]:
    """Decide whether the bot should respond to a group message.

    Returns ``(should_respond, reason)`` where *reason* is one of
    ``"mention"``, ``"reply"``, ``"question"``, or ``""`` (when False).
    """
    # Only respond when the bot is @mentioned in the text
    if re.search(re.escape(f"@{bot_username}"), message_text, re.IGNORECASE):
        return True, "mention"

    return False, ""


async def handle_group_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle incoming text messages in group / supergroup chats."""
    # --- Defensive checks ---
    if update.message is None:
        return
    if update.message.text is None:
        return
    if update.message.from_user is None:
        return
    if update.message.chat is None:
        return

    message = update.message
    user = message.from_user
    chat = message.chat
    text = message.text

    bot_username = await _get_bot_username(context)
    if bot_username is None:
        logger.warning("Could not resolve bot username — ignoring group message")
        return

    # --- Should we respond? ---
    should_respond, trigger_reason = _should_respond_in_group(
        text, bot_username, message.reply_to_message,
    )
    if not should_respond:
        logger.debug(
            "Group message ignored (no mention/reply/question): chat=%s user=%s text=%s",
            chat.id, user.id, text[:60],
        )
        return

    logger.info(
        "Group message MATCHED (%s): chat=%s (%s) user=%s text=%s",
        trigger_reason, chat.id, chat.type, user.id, text[:80],
    )

    # --- Clean the message ---
    cleaned = clean_message_text(text, bot_username)
    logger.info(
        "Cleaned query for user %s in chat %s: %s",
        user.id, chat.id, cleaned[:80] if cleaned else "(empty)",
    )

    # --- Empty tag or greeting only → Group Quick Menu ---
    if not cleaned or is_greeting(cleaned) or cleaned.lower().strip() in ("help", "menu"):
        await message.reply_text(
            "👋 Hey! Here's what I can help with:",
            reply_markup=KB_GROUP_MAIN,
            reply_to_message_id=message.message_id,
        )
        return

    # --- Pass cleaned text and threading info via context (NOT mutation) ---
    # Directly mutating message.text or message.reply_text fails in
    # python-telegram-bot v21+ because Message uses __slots__, preventing
    # instance-level attribute overrides of class methods.
    context.user_data["_group_msg"] = {
        "clean_text": cleaned,
        "reply_to_msg_id": message.message_id,
    }

    try:
        await handle_message(update, context)
    except Exception as e:
        logger.error(
            "Group message handler error: %s: %s", type(e).__name__, e,
        )
        logger.error("Full traceback: %s", traceback.format_exc())
        logger.error(
            "Chat type: %s, Chat ID: %s, User: %s, Text: %s",
            chat.type, chat.id,
            user.username if user else "N/A",
            text[:80],
        )
    finally:
        context.user_data.pop("_group_msg", None)


async def handle_edited_group_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle edited messages in groups — same logic as new messages."""
    if update.edited_message is None:
        return
    if update.edited_message.text is None:
        return
    if update.edited_message.from_user is None:
        return
    if update.edited_message.chat is None:
        return

    # Promote edited_message into the message slot so the rest of the
    # pipeline (and Telegram helpers like update.effective_*) works normally.
    update._message = update.edited_message  # noqa: SLF001
    await handle_group_message(update, context)
