from ..models import PlantillaMensaje, ProductoCatalogo


def render_plantilla(cuerpo: str, cliente, producto_nombre: str = "", vendedora: str = "") -> str:
    prod = producto_nombre or getattr(cliente, "producto_interes", "") or ""
    producto = ProductoCatalogo.query.filter(
        ProductoCatalogo.nombre.ilike(prod)
    ).first() if prod else None

    replacements = {
        "{{nombre_contacto}}": cliente.nombre_contacto or cliente.nombre or "",
        "{{nombre_negocio}}": cliente.empresa or cliente.nombre or "",
        "{{producto}}": prod,
        "{{comuna}}": cliente.comuna or "",
        "{{dolor_detectado}}": cliente.dolor_detectado or "",
        "{{link_demo}}": (producto.link_demo if producto else "") or "",
        "{{link_landing}}": (producto.link_landing if producto else "") or "",
        "{{vendedora}}": vendedora,
    }
    out = cuerpo
    for k, v in replacements.items():
        out = out.replace(k, v)
    return out


def whatsapp_url(cliente, mensaje: str) -> str:
    phone = (cliente.whatsapp or cliente.telefono or "").replace("+", "").replace(" ", "")
    if phone.startswith("56"):
        pass
    elif phone.startswith("9") and len(phone) == 9:
        phone = "56" + phone
    from urllib.parse import quote
    return f"https://wa.me/{phone}?text={quote(mensaje)}" if phone else "#"
