import streamlit as st
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import tempfile
import os
import io
from PIL import Image
import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

st.set_page_config(page_title="Garage Door QC App", layout="centered")
st.title("Garage Door QC Form")

with st.form("qc_form"):
    st.subheader("Job Information")
    project = st.text_input("Project")
    builder = st.text_input("Builder")
    lot_number = st.text_input("Lot Number")
    date_today = st.date_input("QC Date", value=date.today())
    install_date = st.date_input("Install Date")
    installer_name = st.text_input("Installer Name")
    qc_manager = st.text_input("QC Manager")

    st.subheader("QC Checklist")
    qc_items = {
        "All Screws Installed": st.checkbox("All Screws Installed"),
        "Center Bearing Plate has Sleeve Anchor": st.checkbox("Center Bearing Plate has Sleeve Anchor"),
        "Door has correct tension": st.checkbox("Door has correct tension"),
        "Track Installed correctly": st.checkbox("Track Installed Correctly"),
        "Motor working": st.checkbox("Motor working"),
        "Remotes working": st.checkbox("Remotes working"),
        "Sensor aligned": st.checkbox("Sensor aligned"),
        "No visible damage": st.checkbox("No visible damage"),
        "Trim Installed": st.checkbox("Trim Installed")
    }

    st.subheader("Photo Checklist (Camera Only)")
    photos = {
        "Inside Garage Door": st.camera_input("Inside Garage Door"),
        "Center Bearing Plate": st.camera_input("Center Bearing Plate"),
        "Motor": st.camera_input("Motor"),
        "Back Drop (Left)": st.camera_input("Back Drop (Left)"),
        "Back Drop (Right)": st.camera_input("Back Drop (Right)"),
        "Outside Garage Door": st.camera_input("Outside Garage Door"),
    }

    notes = st.text_area("Additional Notes")
    submitted = st.form_submit_button("Send QC Report")

# ---------------- PDF Generator ------------------
def generate_pdf(filepath, form_data, qc_items, notes, photos):
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Garage Door QC Report")

    c.setFont("Helvetica", 12)
    y = height - 80
    for label, value in form_data.items():
        c.drawString(50, y, f"{label}: {value}")
        y -= 20

    c.drawString(50, y, "QC Checklist:")
    y -= 20
    for item, checked in qc_items.items():
        status = "✅" if checked else "❌"
        c.drawString(70, y, f"{status} {item}")
        y -= 15

    c.drawString(50, y, "Notes:")
    y -= 20
    for line in notes.split("\n"):
        c.drawString(70, y, line)
        y -= 15

    y -= 30
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Photos:")
    c.setFont("Helvetica", 12)
    y -= 20

    for label, file in photos.items():
        if file:
            c.drawString(50, y, label)
            y -= 15
            image = Image.open(io.BytesIO(file.getvalue()))
            image.thumbnail((300, 300))
            image_io = io.BytesIO()
            image.save(image_io, format='PNG')
            image_io.seek(0)
            img_reader = ImageReader(image_io)

            if y < 200:
                c.showPage()
                y = height - 50

            c.drawImage(img_reader, 70, y - 150, width=150, height=150)
            y -= 170

    c.save()

# ---------------- SendGrid Email ------------------
def send_email_with_attachment(recipient_email, subject, body, attachment_path):
    with open(attachment_path, 'rb') as f:
        data = f.read()
        encoded_file = base64.b64encode(data).decode()

    attachment = Attachment(
        FileContent(encoded_file),
        FileName("QC_Report.pdf"),
        FileType("application/pdf"),
        Disposition("attachment")
    )

    message = Mail(
        from_email=st.secrets["sendgrid"]["from_email"],
        to_emails=recipient_email,
        subject=subject,
        plain_text_content=body.encode('utf-8').decode('utf-8')

    )
    message.attachment = attachment

    try:
        sg = SendGridAPIClient(st.secrets["sendgrid"]["api_key"])
        sg.send(message)
        st.success("QC report emailed successfully!")
    except Exception as e:
        st.error(f"Email failed to send: {e}")

# ---------------- Handle Submission ------------------
if submitted:
    missing_photos = [k for k, v in photos.items() if v is None]
    if missing_photos:
        st.error(f"Please take all required photos: {', '.join(missing_photos)}")
    else:
        with st.spinner("Generating and emailing QC report..."):
            form_data = {
                "Project": project,
                "Builder": builder,
                "Lot Number": lot_number,
                "QC Date": str(date_today),
                "Install Date": str(install_date),
                "Installer Name": installer_name,
                "QC Manager": qc_manager,
            }

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                pdf_path = tmp_file.name
                generate_pdf(pdf_path, form_data, qc_items, notes, photos)

            send_email_with_attachment(
                recipient_email=st.secrets["sendgrid"]["to_email"],
                subject = f"QC Report - {project} Lot {lot_number}",
                body="Attached is the completed Garage Door QC Report.",
                attachment_path=pdf_path
            )

            os.remove(pdf_path)


