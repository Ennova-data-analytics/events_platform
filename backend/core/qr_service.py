import qrcode 
from io import BytesIO

def generate_feedback_qr_code(event_id: int, base_url: str, box_size: int = 10, border: int = 4, fill_color: str = "black", back_color: str = "white"):
    """Generate a QR code image for event feedback form"""
    feedback_url = f"{base_url}/feedback/{event_id}"

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

def generate_feedback_url(event_id: int, base_url: str) -> str:
    """Generate the feedback form URL for an event"""
    return f"{base_url}/feedback/{event_id}"

