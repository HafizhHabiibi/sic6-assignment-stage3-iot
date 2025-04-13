from machine import Pin, PWM, RTC
import onewire, ds18x20
import network
import ntptime
from hcsr04 import HCSR04
from time import sleep, sleep_ms, time
import urequests  # Tambahan: untuk HTTP POST ke Flask

# ======= INISIALISASI PIN DAN SENSOR ======= #
ds_pin = Pin(4)  # Pin data untuk sensor suhu DS18B20
relay = Pin(26, Pin.OUT)  # Relay untuk mengontrol pompa air
ow = onewire.OneWire(ds_pin)
ds_sensor = ds18x20.DS18X20(ow)

PIN_SERVO = 18  # Pin untuk servo motor
servo = PWM(Pin(PIN_SERVO), freq=50)  # Inisialisasi PWM untuk servo
TRIGGER_PIN = 12
ECHO_PIN = 14
sensor = HCSR04(trigger_pin=TRIGGER_PIN, echo_pin=ECHO_PIN, echo_timeout_us=10000)  # Sensor ultrasonik untuk cek pakan

# ======= WIFI DAN WAKTU ======= #
SSID = "OOO"
PASSWORD = "12345678"

# ======= PARAMETER SERVO ======= #
BUKA_ANGLE = 90  # Sudut saat servo membuka pintu pakan
TUTUP_ANGLE = 0  # Sudut saat servo menutup pintu pakan

# ======= PARAMETER PAKAN ======= #
TINGGI_WADAH_CM = 10  # Tinggi total wadah pakan
JARAK_MIN_CM = 2      # Jarak minimum saat pakan penuh

# ======= JADWAL PAKAN (WIB) ======= #
jadwal_pakan = [(10, 57), (12, 0), (18, 00)]  # Daftar jam dan menit untuk memberi pakan

# ======= FUNGSI ======= #
def gerak_servo(angle):
    # Fungsi untuk menggerakkan servo ke sudut tertentu
    min_duty = 26
    max_duty = 128
    duty = int(min_duty + (angle / 180) * (max_duty - min_duty))
    servo.duty(duty)

def buka_tutup_pakan():
    # Fungsi untuk membuka dan menutup pintu pakan sebanyak 3 kali
    for i in range(3):
        print(f"Pakan #{i+1} keluar...")
        gerak_servo(BUKA_ANGLE)
        sleep(2)
        gerak_servo(TUTUP_ANGLE)
        sleep(2)
    print("Selesai memberi pakan.")

def hitung_persen_isi(jarak_cm):
    # Menghitung persentase isi pakan berdasarkan jarak ultrasonik
    if jarak_cm > TINGGI_WADAH_CM:
        jarak_cm = TINGGI_WADAH_CM
    if jarak_cm < JARAK_MIN_CM:
        jarak_cm = JARAK_MIN_CM
    tinggi_isi = TINGGI_WADAH_CM - jarak_cm
    kapasitas_max = TINGGI_WADAH_CM - JARAK_MIN_CM
    persen = (tinggi_isi / kapasitas_max) * 100
    return round(persen)

def konek_wifi(ssid, password):
    # Menyambungkan ke jaringan WiFi
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Menyambung ke WiFi...")
        wlan.connect(ssid, password)
        while not wlan.isconnected():
            sleep(1)
    print("Terhubung ke WiFi:", wlan.ifconfig())

def sync_waktu():
    # Sinkronisasi waktu menggunakan NTP
    try:
        print("Sinkronisasi waktu NTP...")
        ntptime.settime()
        print("Waktu berhasil disinkronkan!")
    except:
        print("Gagal sinkronisasi waktu!")

def cek_jadwal(jam, menit):
    # Mengecek apakah waktu sekarang cocok dengan jadwal pakan
    for j, m in jadwal_pakan:
        if jam == j and menit == m:
            return True
    return False

def suhu():
    # Membaca suhu dari sensor dan mengontrol relay
    roms = ds_sensor.scan()
    if not roms:
        print('Sensor DS18B20 Tidak Ditemukan!')
        return None, None
    ds_sensor.convert_temp()
    sleep_ms(750)
    for rom in roms:
        suhu = ds_sensor.read_temp(rom)
        print("Suhu saat ini: {:.2f} °C".format(suhu))
        if suhu > 30:
            print("Suhu > 30°C, Pompa HIDUP")
            relay.value(1)
            return suhu, 1
        else:
            print("Suhu <= 30°C, Pompa MATI")
            relay.value(0)
            return suhu, 0

def kirim_data_ke_api(suhu, persen_pakan, status_pompa):
    # Mengirim data ke backend Flask API
    url = "http://192.168.43.102:5000/sensor"  # GANTI dengan IP backend Flask kamu
    data = {
        "suhu": suhu,
        "pakan(%)": persen_pakan,
        "pompa": status_pompa
    }
    try:
        response = urequests.post(url, json=data)
        print("Data berhasil dikirim ke API:", response.text)
        response.close()
    except Exception as e:
        print("Gagal kirim data ke API:", e)

# ======= MAIN PROGRAM ======= #
konek_wifi(SSID, PASSWORD)
sync_waktu()
rtc = RTC()

# Waktu terakhir masing-masing fungsi dijalankan
last_suhu_check = 0
last_pakan_check = 0
last_jadwal_check = 0
last_jam_eksekusi = -1

suhu_skrg = None
status_pompa = None

while True:
    current_time = time()  # Ambil waktu saat ini (sejak board nyala)

    # Cek suhu tiap 10 detik
    if current_time - last_suhu_check >= 5:
        suhu_skrg, status_pompa = suhu()
        last_suhu_check = current_time

    # Cek level pakan tiap 30 detik
    if current_time - last_pakan_check >= 10:
        try:
            jarak = sensor.distance_cm()
            persen_pakan = hitung_persen_isi(jarak)
            print("Jarak: {:.2f} cm | Sisa pakan: {}%".format(jarak, persen_pakan))

            # Kirim data ke API jika suhu tersedia
            if suhu_skrg is not None:
                kirim_data_ke_api(suhu_skrg, persen_pakan, status_pompa)

        except Exception as e:
            print("Gagal baca sensor:", e)
        last_pakan_check = current_time

    # Cek jadwal pakan tiap 60 detik
    if current_time - last_jadwal_check >= 5:
        now = rtc.datetime()
        jam = (now[4] + 7) % 24  # Konversi ke zona WIB
        menit = now[5]
        print("Sekarang jam {:02d}:{:02d}".format(jam, menit))

        if cek_jadwal(jam, menit) and jam != last_jam_eksekusi:
            buka_tutup_pakan()
            last_jam_eksekusi = jam

        last_jadwal_check = current_time

    sleep(1)  # Delay 1 detik agar loop tidak terlalu cepat