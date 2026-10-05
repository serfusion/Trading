# Cek kompilasi & pratinjau UI tanpa Android SDK

```bash
bash tools/compose_check/run.sh compile                       # "KOMPILASI LOLOS"
bash tools/compose_check/run.sh preview gelap out.png         # PNG kartu status + 💎 spot (data contoh)
bash tools/compose_check/run.sh preview terang out.png
```

- Compose Desktop (Maven Central). Kompilasi: CMP 1.6.11 + Kotlin 1.9.24. Pratinjau: CMP 1.5.12 + Kotlin 1.9.21
  (runtime CMP 1.6 butuh Google Maven yang diblokir jaringan sesi); `Theme.kt` ditambal otomatis (tanpa
  `surfaceContainer*`).
- `stubs/`: pengganti API Android (Context, SharedPreferences, LocalContext) & objek yang memakai API Android
  (NewsAlarm, SignalPoller, idrText/moneyMain/idrLine dari MainActivity). `preview/`: data contoh (`Preview.kt`) dan
  pengganti ChatClient.
- Tidak dicek: MainActivity, Notifications, NewsAlarm, SignalPoller (API Android) → CI "Android APK" tetap pemeriksa akhir.
- Bila menambah file UI baru: tambahkan ke daftar di `run.sh`; bila galat "Unresolved reference", tambah stub.
- Emoji bendera tampil sebagai huruf di desktop (di Android normal).
