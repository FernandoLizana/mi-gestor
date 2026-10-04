"""Datos del equipo para la pantalla de login del CRM."""

import os

LOGIN_FEATURED_ID = os.environ.get("LOGIN_FEATURED_ID", "").strip()


def _member_item(member: dict) -> dict:
    photo = (member.get("photo") or "").lstrip("/")
    if photo.startswith("static/"):
        photo = photo[len("static/") :]
    return {
        "id": member.get("id", ""),
        "name": member.get("name", ""),
        "role": member.get("role", ""),
        "quote": member.get("quote", ""),
        "initials": member.get("initials", "?"),
        "photo": photo,
    }


def build_login_team():
    try:
        from data.content import TEAM
        members = TEAM.get("members", [])
    except ImportError:
        members = _fallback_members()

    featured = None
    others = []
    for member in members:
        item = _member_item(member)
        if LOGIN_FEATURED_ID and member.get("id") == LOGIN_FEATURED_ID:
            featured = item
        else:
            others.append(item)

    if featured is None and members:
        featured = _member_item(members[0])
        others = [_member_item(m) for m in members[1:]]

    return featured, others


def _fallback_members():
    return [
        {
            "id": "equipo",
            "name": "Equipo comercial",
            "role": "Ventas",
            "quote": "Pipeline, seguimientos y propuestas en un solo lugar.",
            "initials": "EC",
            "photo": "",
        },
    ]
