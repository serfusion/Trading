# Vektor ScalpDaily - Asymmetric AI Trading Engine (v8.0)

Vektor ScalpDaily adalah sebuah kerangka kerja (*framework*) *High-Frequency Algorithmic Trading* hibrida yang dirancang khusus untuk komoditas Emas (XAUUSD). Sistem ini memisahkan logika eksekusi *client-side* (MetaTrader 4) dengan otak kecerdasan buatan (*Machine Learning*) yang berjalan pada lingkungan Python.

Sistem ini didukung oleh **Dual-Model XGBoost** (Trend & Sideways) yang dilatih menggunakan *Bayesian Optimization* via Optuna, serta dilengkapi dengan pendeteksi *Exhaustion/Blow-off Top* berbasis *31-Feature Matrix*.

---

## 📁 Project Structure & Logic Mapping

Repositori ini telah dibersihkan dari *file* binari dan skrip usang. Fokus utamanya adalah menjembatani logika prediktif (Python) dengan logika pesanan (MQL4/MT4).

```text
kay_trade/
│
├── run_bot_v6.py                 # TITIK MASUK UTAMA (Entry Point)
│                                 # Skrip ini memantik inisialisasi lingkungan dan menjalankan otak utama AI.
│
├── src/                          # 🧠 KODE LOGIKA PYTHON (The AI Brain)
│   ├── vektor_v6/                # Modul Eksekusi Produksi (Current Version)
│   │   ├── main.py               # (Sang Eksekutor) Memonitor Macro Trend H1, memanggil AI, dan mengirim order ke MT4.
│   │   ├── quality.py            # (Sang Jembatan AI) Memuat model .joblib dan menghasilkan probabilitas prediktif 0-100%.
│   │   ├── config.py             # (Pusat Kendali) Pengaturan Threshold Probabilitas, SL Dinamis, TP, dan Trailing.
│   │   └── meta.py               # (Protokol Jaringan) Mengurus komunikasi socket ZMQ antara Python dan Terminal MT4.
│   │
│   └── scalpdaily/               # Mesin Kalkulus (Feature Engineering Engine)
│       ├── features_reduced.py   # Mengubah harga mentah menjadi 31-Feature Matrix (termasuk body_atr_ratio).
│       └── indicators.py         # Pustaka matematika internal (RSI, Bollinger, Keltner, ATR, ADX).
│
├── scripts/                      # 🤖 ALGORITMA PELATIHAN ML (Training Scripts)
│   ├── train_optuna.py           # Menjalankan Tree-structured Parzen Estimator untuk melatih ulang Model Utama (Breakout/Trend).
│   └── train_sideways.py         # Skrip pelatihan khusus untuk model Mean-Reversion (Pasar Sepi).
│
└── mt4/                          # 🖥️ KODE SUMBER METATRADER 4 (MQL4)
    ├── ScalpDaily_ML_EA_v6.mq4   # File Utama Expert Advisor (EA). Ditempelkan ke grafik XAUUSD M5 di MT4.
    ├── ScalpDaily_DataCollector.mqh # Fungsi untuk menarik data OHLC + Volume dan mengirimnya ke Python via ZMQ.
    └── ScalpDaily_OrderEngine.mqh   # Mesin penerima sinyal eksekusi (BUY/SELL) dari Python dan pengatur proteksi MT4.
```

## 🔄 Bagaimana Logika Sistem Bekerja?

1. **Ekstraksi Data (MQL4 -> Python):** 
   Setiap ada pembaruan detik pada *chart*, `ScalpDaily_ML_EA_v6.mq4` memanggil `DataCollector.mqh` untuk membaca bentuk *candle* dan mengirimkannya ke `meta.py` via ZMQ.
2. **Rekayasa Fitur (Python):** 
   `features_reduced.py` mengalkulasi indikator, volatilitas, dan mendeteksi anomali (contoh: *exhaustion body vs ATR*).
3. **Prediksi Asimetris (Machine Learning):** 
   `quality.py` menggunakan matriks tersebut pada model `XGBoost`. 
   * Jika pasar *trending* (ADX > 20), ia menggunakan `vektor_v6_ml.joblib`.
   * Jika pasar *sideways* (ADX < 20), ia menggunakan `vektor_v8_sideways.joblib`.
4. **Validasi & Eksekusi (Python -> MQL4):** 
   `main.py` mencocokkan prediksi AI dengan tren makro (H1). Jika probabilitas lulus *Threshold* (0.70 untuk Searah, 0.85 untuk Melawan Arah), perintah BUY/SELL dikirim kembali ke `ScalpDaily_OrderEngine.mqh` di MT4 untuk dieksekusi secara instan.

## 📥 Model AI (Hugging Face)
*Penting: Karena berukuran besar dan berbentuk binari, file model AI (`*.joblib`) tidak disimpan di GitHub.*
Model dapat diunduh secara terpisah atau dipanggil melalui *Hugging Face Hub*. Lihat penjelasan lengkap mengenai metrik *benchmark* model pada repositori Hugging Face proyek ini : https://huggingface.co/anggakayy/xauusd-regime-switching-ensemble

## 🚀 Setup & Cara Menjalankan
1. Instalasi dependensi: `pip install -r requirements.txt`
2. Pastikan Terminal MT4 menyala dan EA `ScalpDaily_ML_EA_v6.ex4` sudah ditempel (*attach*) di grafik XAUUSD M5.
3. Jalankan otak Python: `python run_bot_v6.py`
