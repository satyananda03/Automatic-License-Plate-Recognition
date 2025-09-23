import streamlit as st
import cv2
from ultralytics import YOLO
import numpy as np
import easyocr
from PIL import Image
from text_processing import remove_pattern_strings
from text_processing import extract_plate

# Konversi file gambar yang diupload ke Streamlit menjadi format OpenCV (BGR)
def streamlit_image_to_cv2(image):
    image = Image.open(image)
    image = np.array(image.convert('RGB'))
    image = image[:, :, ::-1].copy()
    return image

# Crop bagian gambar berdasarkan koordinat bounding box (xyxy)
def crop_image(image, xyxy):
    # HWC (Height, Width, Channel), y1-y2, x1-x2
    return image[xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]]

# Ambil semua koordinat bounding box (xyxy) output dari model yolo
def get_xyxys(results):
    xyxys = results.boxes.xyxy.cpu().numpy().astype(np.int32).tolist()
    return xyxys

# Load model 
yolo = YOLO("models/yolov8n.pt")         
plate = YOLO("models/license_plate_detector.pt") 
ocr = easyocr.Reader(['en'], gpu=False)

st.title("Deteksi Plat Nomor Kendaraan🚘")
st.write("Upload gambar kendaraan yang ingin dideteksi")
image = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'])

# Jika ada gambar yang diupload
if image is not None:
    img = streamlit_image_to_cv2(image)
    st.image(img, channels="BGR")

    # Deteksi kendaraan (hanya kelas tertentu: mobil, bus, truk, motor)
    results = yolo(img, classes=[2, 5, 7, 8], agnostic_nms=True, conf=0.5)
    img_out = results[0].plot()

    # Ambil bounding box kendaraan dan crop tiap kendaraan
    vehicle_xyxy = get_xyxys(results[0])
    vehicle_list = [crop_image(img.copy(), xyxy) for xyxy in vehicle_xyxy]

    # Loop setiap kendaraan yang terdeteksi
    for idx, vl in enumerate(vehicle_list):
        # Deteksi plat nomor pada tiap kendaraan
        results_plate = plate(vl, agnostic_nms=True, conf=0.5)
        # Ambil koordinat plat
        plate_xyxy = get_xyxys(results_plate[0])  

        # Skip jika tidak ada plat yg terdeteksi
        if len(plate_xyxy) == 0:
            continue

        # Hitung koordinat plat relatif terhadap gambar asli
        x1 = plate_xyxy[0][0] + vehicle_xyxy[idx][0]
        y1 = plate_xyxy[0][1] + vehicle_xyxy[idx][1]
        x2 = plate_xyxy[0][2] + vehicle_xyxy[idx][0]
        y2 = plate_xyxy[0][3] + vehicle_xyxy[idx][1]
        cv2.rectangle(img_out, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Skip jika bounding box terlalu kecil (karena OCR model akan gagal membacanya)
        if plate_xyxy[0][2] - plate_xyxy[0][0] < 90:
            continue

        # Crop bagian plat dan konversi ke RGB
        plate_img = crop_image(vl.copy(), plate_xyxy[0])
        plate_img = cv2.cvtColor(plate_img, cv2.COLOR_BGR2RGB)

        # Gunakan OCR untuk membaca teks pada plat
        plate_text = ocr.readtext(plate_img)

        # Ambil hanya teks (string) dari setiap hasil OCR, lalu gabung jadi satu string.
        if len(plate_text) == 0:
            raw_text = ""
        else:
            raw_text = " ".join([pt[1] for pt in plate_text]) 

        # Normalisasi huruf besar + ganti ':' jadi '.'
        raw_text = raw_text.upper().replace(":", ".")

        # Hapus pola yang tidak diinginkan (fungsi custom)
        raw_text = remove_pattern_strings(raw_text)

        # Ekstrak nomor plat yang valid + daerah asal
        plate_normalized, daerah = extract_plate(raw_text)

        # Jika tidak valid, isi dengan N/A
        if plate_normalized is None:
            plate_normalized = "N/A"
            daerah_str = "N/A"
        else:
            if isinstance(daerah, list):
                daerah_str = ", ".join(daerah) if daerah else "N/A"
            else:
                daerah_str = daerah if daerah is not None else "N/A"

        # Tampilkan hasil teks plat & daerah diatas bounding box plate
        y_offset = 15 # Jarak teks terhadap bounding box plate
        cv2.putText(img_out, plate_normalized, (x1, y1 - y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.putText(img_out, daerah_str, (x1, y1 - y_offset - 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

    # Tampilkan hasil deteksi
    st.text("Hasil Deteksi & Pembacaan Plat Nomor Kendaraan ✅")
    st.image(img_out, channels="BGR")