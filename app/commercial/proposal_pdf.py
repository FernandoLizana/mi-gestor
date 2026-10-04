"""PDF simple de propuesta comercial."""
import io
import os

from fpdf import FPDF

from ..branding import brand_company, contact_email


def _pick_font_pair():
    regular_candidates = []
    env_font = os.environ.get("PDF_FONT", "").strip()
    if env_font:
        regular_candidates.append(env_font)
    regular_candidates.extend([
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ])
    bold_for = {
        r"C:\Windows\Fonts\segoeui.ttf": r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arial.ttf": r"C:\Windows\Fonts\arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    }
    for regular in regular_candidates:
        if os.path.isfile(regular):
            bold = bold_for.get(regular, regular)
            if not os.path.isfile(bold):
                bold = regular
            return regular, bold
    return None, None


def build_propuesta_pdf(propuesta, vendedora: str | None = None) -> bytes:
    company = brand_company()
    seller = vendedora or company
    email = contact_email()
    c = propuesta.cliente
    pdf = FPDF()
    regular, bold = _pick_font_pair()
    if regular:
        pdf.add_font("Body", "", regular)
        pdf.add_font("Body", "B", bold)
        family = "Body"
    else:
        family = "Helvetica"
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font(family, "B", 16)
    pdf.cell(0, 10, company, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(family, "", 11)
    pdf.cell(0, 8, "Propuesta comercial", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font(family, "B", 12)
    pdf.cell(0, 8, f"Cliente: {c.empresa or c.nombre}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(family, "", 10)
    pdf.cell(0, 6, f"Producto: {propuesta.producto or '-'}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Plan: {propuesta.plan or '-'}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    setup = (propuesta.setup or 0) - (propuesta.descuento_setup or 0)
    mensual = (propuesta.mensualidad or 0) - (propuesta.descuento_mensualidad or 0)
    pdf.cell(0, 6, f"Setup: ${setup:,.0f} CLP", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Mensualidad: ${mensual:,.0f} CLP", new_x="LMARGIN", new_y="NEXT")
    if propuesta.fecha_vencimiento:
        pdf.cell(0, 6, f"Válida hasta: {propuesta.fecha_vencimiento.strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    if propuesta.incluye:
        pdf.set_font(family, "B", 10)
        pdf.cell(0, 7, "Incluye:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(family, "", 10)
        pdf.multi_cell(0, 5, propuesta.incluye)
        pdf.ln(2)

    if propuesta.condiciones:
        pdf.set_font(family, "B", 10)
        pdf.cell(0, 7, "Condiciones:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(family, "", 9)
        pdf.multi_cell(0, 5, propuesta.condiciones)

    pdf.ln(8)
    pdf.set_font(family, "", 9)
    contact = f"Contacto comercial: {seller}"
    if email:
        contact += f" — {email}"
    pdf.cell(0, 6, contact, new_x="LMARGIN", new_y="NEXT")

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
