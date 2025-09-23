import re
import string
import json
from fuzzywuzzy import fuzz

# Load data yang berisi daftar kode plat nomor sesuai daerahnya
data = json.load(open("data.json"))

# Fungsi untuk menata ulang format string plat nomor
# Contoh: "AB1234CD" -> "AB 1234 CD"
def process_pattern(input_string):
    pattern = re.compile(r'([a-zA-Z]{1,3})\s*(\d{2,4})\s*([a-zA-Z]{2,3})')
    result = re.sub(pattern, r'\1 \2 \3', input_string)
    return result

# Fungsi untuk menghapus pola tertentu yang tidak diinginkan dari hasil OCR
# Contoh pola: "12.34" atau "<1><2>.<3><4>"
def remove_pattern_strings(text):
    pattern = r'\b\d{2}\.\d{2}\b|\b<\d><\d>\.<\d><\d>\b'
    cleaned_text = re.sub(pattern, '', text)
    return cleaned_text

# Fungsi untuk menghapus tanda baca pada string
def remove_punctuation(input_string):
    translator = str.maketrans("", "", string.punctuation)
    return input_string.translate(translator)

# Fungsi untuk koreksi typo pada kode daerah plat
# - Ambil token pertama (kode daerah, misalnya "AB")
# - Bandingkan dengan daftar di data.json menggunakan fuzzy matching
# - Jika mirip > 40% dan paling tinggi, ganti dengan kode yang benar
# - Mengembalikan string yang sudah dikoreksi + daftar daerah
def typo_correction(text):
    text_to_correct = text.split(" ")[0]
    maximum = 0
    text_result = ""
    daerah = []
    for d in data["plat_nomor"]:
        ratio = fuzz.ratio(text_to_correct, d["kode"])
        if ratio > maximum and ratio > 40:
            maximum = ratio
            text_result = d["kode"]
            daerah = d["daerah"]
    if maximum > 0:
        text = text.replace(text_to_correct, text_result)
        return text, daerah
    return text, None

# Fungsi untuk mengekstrak plat nomor dari hasil OCR
# - format nomor plat: 2 huruf + 2-5 digit angka + 1-3 huruf (mis. AB 1234 CD)
# - Mengembalikan tuple: (plat_normalized, daerah) atau (None, None)
def extract_plate(raw_text, strict=False):
    if not raw_text:
        return None, None

    # Normalisasi awal: huruf besar, hapus tanda baca, rapikan spasi
    t = raw_text.upper()
    t = remove_punctuation(t)
    t = re.sub(r'\s+', ' ', t).strip()

    pattern = re.compile(r'([A-Z]{1,2})\s*([0-9]{2,5})\s*([A-Z]{1,3})')

    # Cari pola yang cocok
    m = pattern.search(t)
    if not m:
        return None, None

    # Ambil bagian kode daerah (left), angka (mid), dan akhiran huruf (right)
    left, mid, right = m.group(1), m.group(2), m.group(3)
    normalized = f"{left} {mid} {right}"

    # Koreksi typo pada kode daerah
    normalized, daerah = typo_correction(normalized)
    return normalized, daerah


# # --- Regex Test ---
# examples = [
#     "AB 1234 CDX 50",    # trailing angka -> harus diabaikan
#     "AB1234CDX50",       # tanpa spasi -> tetap bisa dipisah jadi AB 1234 CDX
#     "AB 1234 CDD",       # format normal
#     "AD 1 2345",         # OCR salah pecah angka
#     "B-1234-XYZ 99",     # ada tanda baca dan angka tambahan
# ]
#
# for s in examples:
#     plate, daerah = extract_plate(s)
#     plate_str = plate if plate is not None else "N/A"
#     if isinstance(daerah, list):
#         daerah_str = ", ".join(daerah) if daerah else "N/A"
#     else:
#         daerah_str = daerah if daerah is not None else "N/A"
#     print(f"raw: {s:25} -> plate: {plate_str:15} | daerah: {daerah_str}")