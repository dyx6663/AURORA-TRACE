"""Small Todo domain used by the AURORA TRACE verification fixture."""


class TodoList:
    """Minimal in-memory todo list with a deliberately testable edge case."""

    def __init__(self, items=None):
        self.items = [item if isinstance(item, dict) else {"title": item, "done": False}
                      for item in (items or [])]

    def add(self, title):
        """Append a new, incomplete item."""
        self.items.append({"title": title, "done": False})

    def remove(self, index):
        """Remove an item by index; the fixture intentionally keeps a boundary bug."""
        # Intentional defect: the last item cannot be removed correctly.
        if 0 <= index < len(self.items) - 1:
            return self.items.pop(index)
        return None

    def completed(self):
        """Return all items marked as complete."""
        return [item for item in self.items if item["done"]]
