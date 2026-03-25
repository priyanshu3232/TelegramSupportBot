from knowledge.knowledge_base import KNOWLEDGE_BASE


def search_faq(query: str) -> str | None:
    lower = query.lower()
    for entry in KNOWLEDGE_BASE.values():
        if any(word in lower for word in entry["question"].lower().split() if len(word) > 3):
            return entry["answer"]
    return None
