from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Data disimpan sementara
data_terakhir = {}
jadwal_pakan = [[7, 0], [12, 0], [18, 0]]  # Default: 3 kali sehari

@app.route('/')
def home():
    return "✅ API AIoT Aktif!"

# ======= ENDPOINT SENSOR ======= #
@app.route('/sensor', methods=['POST'])
def simpan_data():
    global data_terakhir
    data = request.get_json()

    if not data:
        return jsonify({"error": "Tidak ada data yang dikirim"}), 400

    data_terakhir = data
    print("📥 Data Diterima:", data_terakhir)
    return jsonify({"message": "Data berhasil disimpan"}), 201

@app.route('/sensor', methods=['GET'])
def ambil_data():
    return jsonify(data_terakhir), 200

# ======= ENDPOINT JADWAL PAKAN ======= #
@app.route('/jadwal_pakan', methods=['GET'])
def get_jadwal():
    # Bikin list of dictionary
    hasil = [{"jam": item[0], "menit": item[1]} for item in jadwal_pakan]
    return jsonify(hasil), 200

@app.route('/jadwal_pakan', methods=['POST'])
def set_jadwal():
    global jadwal_pakan
    data = request.get_json()

    if not data or "jadwal" not in data or not isinstance(data["jadwal"], list):
        return jsonify({"error": "Jadwal tidak valid"}), 400

    jadwal_baru = []
    for item in data["jadwal"]:
        if isinstance(item, list) and len(item) == 2:
            jam, menit = item
            if isinstance(jam, int) and isinstance(menit, int):
                jadwal_baru.append([jam, menit])
    
    if not jadwal_baru:
        return jsonify({"error": "Format jadwal salah atau kosong"}), 400

    jadwal_pakan = jadwal_baru
    print("🗓️ Jadwal pakan diperbarui:", jadwal_pakan)
    return jsonify({"message": "Jadwal berhasil disimpan"}), 200

# ======= JALANKAN SERVER ======= #
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)