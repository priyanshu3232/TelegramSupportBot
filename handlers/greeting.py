_GREETINGS = {
    "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
    "howdy", "sup", "what's up", "yo", "greetings", "hola", "start",
}


def is_greeting(message: str) -> bool:
    lower = message.lower().strip().rstrip("!.,?")
    # Only match exact greetings, not messages that start with a greeting word
    # e.g. "hi" is a greeting, but "hi how do I send money" is not
    return lower in _GREETINGS
