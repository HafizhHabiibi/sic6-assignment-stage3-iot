from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Data disimpan sementara
data_terakhir = {}

@app.route('/')

def home():
    return "API AIoT Aktif!"

@app.route('/sensor', methods=['POST'])

def simpan_data():
    global data_terakhir
    data = request.get_json()

    if not data:
        return jsonify({"error":"TIdak ada data yang dikirim"}), 400
    
    data_terakhir = data
    print("Data DIterima :", data_terakhir)
    return jsonify({"message": "Data berhasil disimpan"}), 201

@app.route('/sensor', methods=['GET'])
def ambil_data():
    return jsonify(data_terakhir), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)