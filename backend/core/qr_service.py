import qrcode 
from io import BytesIO

def generate_feedback_qr_code(event_id: int, base_url: str, template_id: int = None, box_size: int = 10, border: int = 4, fill_color: str = "black", back_color: str = "white"):
    """Generate a QR code image for event feedback form.
    If template_id is provided the QR encodes a URL with ?template_id= so the form loads the right template.
    """
    feedback_url = generate_feedback_url(event_id, base_url, template_id)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border
    )

    qr.add_data(feedback_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fill_color, back_color=back_color)

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return buffer 

def generate_feedback_url(event_id: int, base_url: str, template_id: int = None) -> str:
    """Generate the feedback form URL for an event, optionally for a specific template."""
    url = f"{base_url}/feedback/{event_id}"
    if template_id:
        url += f"?template_id={template_id}"
    return url


def generate_ticket_qr_png(token: str, base_url: str, box_size: int = 10, border: int = 4) -> BytesIO:
    """Generate a QR code PNG for an entrance ticket token.

    Encodes: {base_url}/ticket/{token}
    Returns a BytesIO buffer positioned at 0.
    """
    ticket_url = f"{base_url}/ticket/{token}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(ticket_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

