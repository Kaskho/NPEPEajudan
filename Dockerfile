# Menggunakan Python 3.11 sebagai dasar, sama seperti bot utama
FROM python:3.11-slim

# Mengatur direktori kerja di dalam container
WORKDIR /app

# Menyalin file requirements terlebih dahulu untuk optimasi cache
COPY requirements.txt .

# Menginstal semua pustaka Python yang dibutuhkan
RUN pip install -r requirements.txt

# Menyalin semua file kode bot (sidekick_main.py, sidekick_logic.py, dll.)
COPY . .

# Perintah untuk menjalankan Sidekick Bot saat container dimulai
CMD ["python3", "sidekick_main.py"]
