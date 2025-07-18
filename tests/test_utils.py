"""Test utilities for AnkiMCP tests."""

from typing import Optional

from ankimcp.anki_interface import AnkiInterface
from ankimcp.permissions import PermissionManager


class MockAnkiInterface(AnkiInterface):
    """Mock Anki interface for testing without Anki."""

    def __init__(self):
        # Don't call super().__init__() since we don't have a collection
        # Initialize with permissive config for testing
        self.permissions = PermissionManager(
            {
                "permissions": {
                    "global": {"read": True, "write": True, "delete": True},
                    "mode": "denylist",
                    "deck_permissions": {"allowlist": [], "denylist": []},
                    "protected_decks": [],
                }
            }
        )

        self.decks = {
            1: {"id": 1, "name": "Default", "card_count": 10, "is_filtered": False},
            2: {"id": 2, "name": "Spanish", "card_count": 50, "is_filtered": False},
        }
        self.notes = {
            1: {
                "id": 1,
                "model_name": "Basic",
                "fields": {"Front": "Hello", "Back": "Hola"},
                "tags": ["spanish"],
                "card_count": 1,
            }
        }
        self.models = {
            "Basic": {
                "id": 1,
                "name": "Basic",
                "flds": [{"name": "Front"}, {"name": "Back"}],
                "tmpls": [
                    {
                        "name": "Card 1",
                        "qfmt": "{{Front}}",
                        "afmt": "{{FrontSide}}<hr id=answer>{{Back}}",
                    }
                ],
            }
        }
        self.next_deck_id = 3
        self.next_note_id = 2
        self.next_model_id = 2

    async def list_decks(self):
        # Apply permission filtering
        return self.permissions.filter_decks(list(self.decks.values()))

    async def get_deck_info(self, deck_name: str):
        # Check read permission
        from ankimcp.permissions import PermissionAction

        self.permissions.check_deck_permission(deck_name, PermissionAction.READ)

        for deck in self.decks.values():
            if deck["name"] == deck_name:
                return {
                    "id": deck["id"],
                    "name": deck["name"],
                    "card_count": deck["card_count"],
                    "new_count": 3,
                    "learning_count": 2,
                    "review_count": 5,
                    "is_filtered": deck["is_filtered"],
                    "config": {},
                }
        raise ValueError(f"Deck not found: {deck_name}")

    async def search_notes(self, query: str, limit: int = 50):
        # Simple search implementation
        results = []
        for note in self.notes.values():
            if "tag:" in query:
                tag_query = query.split("tag:")[1].strip()
                if tag_query in note["tags"]:
                    results.append(note)
            else:
                # Check if query matches any tag or field content
                query_lower = query.lower()
                # Check tags
                if any(query_lower in tag.lower() for tag in note["tags"]):
                    results.append(note)
                    continue
                # Check fields
                for value in note["fields"].values():
                    if query_lower in str(value).lower():
                        results.append(note)
                        break
        return results[:limit]

    async def get_note(self, note_id: int):
        if note_id in self.notes:
            return self.notes[note_id].copy()
        raise ValueError(f"Note not found: {note_id}")

    async def get_cards_for_note(self, note_id: int):
        if note_id == 1:
            return [
                {
                    "id": 1,
                    "note_id": 1,
                    "deck_name": "Spanish",
                    "type": 0,
                    "queue": 0,
                    "due": 0,
                    "interval": 0,
                    "ease_factor": 2500,
                    "reviews": 0,
                    "lapses": 0,
                    "last_review": 0,
                }
            ]
        return []

    async def get_review_stats(self, deck_name: Optional[str] = None):
        return {
            "deck_name": deck_name or "All Decks",
            "total_cards": 60,
            "new_cards": 10,
            "learning_cards": 5,
            "review_cards": 45,
            "mature_cards": 30,
        }

    async def create_deck(self, deck_name: str):
        # Check create permission
        from ankimcp.permissions import PermissionAction

        self.permissions.check_deck_permission(deck_name, PermissionAction.CREATE)

        # Check if deck already exists
        for deck in self.decks.values():
            if deck["name"] == deck_name:
                return {
                    "id": deck["id"],
                    "name": deck_name,
                    "created": False,
                    "config": {},
                }

        # Create new deck
        deck_id = self.next_deck_id
        self.next_deck_id += 1
        new_deck = {
            "id": deck_id,
            "name": deck_name,
            "card_count": 0,
            "is_filtered": False,
        }
        self.decks[deck_id] = new_deck

        return {
            "id": deck_id,
            "name": deck_name,
            "created": True,
            "config": {},
        }

    async def create_note_type(self, name: str, fields: list, templates: list):
        # Check permission
        from ankimcp.permissions import PermissionAction

        self.permissions.check_note_type_permission(name, PermissionAction.CREATE)

        # Check if model already exists
        if name in self.models:
            raise ValueError(f"Model already exists: {name}")

        model_id = self.next_model_id
        self.next_model_id += 1

        # Create model structure
        model_fields = [{"name": field} for field in fields]
        self.models[name] = {
            "id": model_id,
            "name": name,
            "flds": model_fields,
            "tmpls": templates,
        }

        return {
            "id": model_id,
            "name": name,
            "field_count": len(fields),
            "template_count": len(templates),
            "created": True,
        }

    async def create_note(
        self, model_name: str, fields: dict, deck_name: str, tags: Optional[list] = None
    ):
        # Check permissions
        from ankimcp.permissions import PermissionAction

        self.permissions.check_deck_permission(deck_name, PermissionAction.WRITE)
        if tags:
            self.permissions.check_tag_permission(tags, PermissionAction.WRITE)
        self.permissions.check_note_type_permission(model_name, PermissionAction.WRITE)

        # Check model exists
        if model_name not in self.models:
            raise ValueError(f"Model not found: {model_name}")

        # Check deck exists
        deck_id = None
        for deck in self.decks.values():
            if deck["name"] == deck_name:
                deck_id = deck["id"]
                break
        if deck_id is None:
            raise ValueError(f"Deck not found: {deck_name}")

        # Create note
        note_id = self.next_note_id
        self.next_note_id += 1

        new_note = {
            "id": note_id,
            "model_name": model_name,
            "fields": fields.copy(),
            "tags": tags or [],
            "card_count": len(self.models[model_name]["tmpls"]),
        }
        self.notes[note_id] = new_note

        # Update deck card count
        self.decks[deck_id]["card_count"] += new_note["card_count"]

        return new_note.copy()

    async def update_note(
        self, note_id: int, fields: Optional[dict] = None, tags: Optional[list] = None
    ):
        if note_id not in self.notes:
            raise ValueError(f"Note not found: {note_id}")

        note = self.notes[note_id]

        # Check permissions
        from ankimcp.permissions import PermissionAction

        # Check global write permission first (through deck permission)
        # For simplicity, assume the note is in the first deck
        if self.decks:
            first_deck = list(self.decks.values())[0]
            self.permissions.check_deck_permission(
                first_deck["name"], PermissionAction.WRITE
            )

        self.permissions.check_tag_permission(note["tags"], PermissionAction.WRITE)
        if tags is not None:
            self.permissions.check_tag_permission(tags, PermissionAction.WRITE)

        # Update fields
        if fields:
            note["fields"].update(fields)

        # Update tags
        if tags is not None:
            note["tags"] = tags

        return note.copy()

    async def delete_note(self, note_id: int):
        if note_id not in self.notes:
            raise ValueError(f"Note not found: {note_id}")

        note = self.notes[note_id]

        # Check permissions
        from ankimcp.permissions import PermissionAction

        self.permissions.check_tag_permission(note["tags"], PermissionAction.DELETE)

        # For simplicity, assume the note is in the first deck for permission check
        if self.decks:
            first_deck = list(self.decks.values())[0]
            self.permissions.check_deck_permission(
                first_deck["name"], PermissionAction.DELETE
            )

        card_count = note["card_count"]

        # Remove note
        del self.notes[note_id]

        # Update deck card count (simplified - assumes note was in first deck)
        if self.decks:
            first_deck = list(self.decks.values())[0]
            first_deck["card_count"] = max(0, first_deck["card_count"] - card_count)

        return {
            "note_id": note_id,
            "deleted": True,
            "cards_deleted": card_count,
        }
