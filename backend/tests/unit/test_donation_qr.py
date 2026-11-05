from io import BytesIO

import qrcode
from PIL import Image

from core import qr_service


def test_donation_url_points_at_the_public_donation_page():
    assert qr_service.generate_donation_url(42, 'https://events.example.com') == 'https://events.example.com/event/42/donate'


def test_donation_qr_encodes_the_donation_url():
    url = 'https://events.example.com/event/42/donate'
    png = qr_service.generate_donation_qr_png(42, 'https://events.example.com', box_size=1, border=0)

    image = Image.open(png).convert('1')

    expected = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=1, border=0)
    expected.add_data(url)
    expected.make(fit=True)
    matrix = expected.get_matrix()

    assert image.size == (len(matrix), len(matrix))
    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            assert (image.getpixel((x, y)) == 0) == dark, f'module ({x}, {y}) differs'


def test_donation_qr_is_a_png_at_offset_zero():
    png = qr_service.generate_donation_qr_png(1, 'https://events.example.com')

    assert isinstance(png, BytesIO)
    assert png.tell() == 0
    assert png.read(8) == b'\x89PNG\r\n\x1a\n'
