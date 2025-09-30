from flask import Flask, url_for
import qrcode

def generate_qr_code():
    app = Flask(__name__)
    app.config['SERVER_NAME'] = 'localhost:5000'  # Change this to your production server name

    # URL for the join page
    join_url = url_for('join', _external=True)

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(join_url)
    qr.make(fit=True)

    # Create an image from the QR Code instance
    img = qr.make_image(fill_color="black", back_color="white")

    # Save the image
    img.save("static/qrcode.png")  # Save the QR code image in the static folder

if __name__ == "__main__":
    generate_qr_code()