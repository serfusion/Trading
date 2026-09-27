# ─────────────────────────────────────────────────────────────────
#  VEKTOR Bot v6 — "Agresif Entry, Smart Exit"
#  Redesign berdasarkan analisis 168 trade:
#    - Win rate 50% → sudah bagus, pertahankan agresivitas entry
#    - Avg win +6.7 pip vs avg loss -14.8 pip → fix exit saja
#    - Solusi: TP fixed + BE lebih cepat + trail lebih lebar
# ─────────────────────────────────────────────────────────────────

LOT             = 0.01     # Fallback lot size jika DYNAMIC_LOT dinonaktifkan
TIMEFRAME       = "M5"
SPIKE_THRESHOLD = 20       # Arsitektur v9.2: naik dari 12 untuk menyaring ledakan volume nyata
GRIEF_SECONDS   = 30       # jeda 30 detik antar entry (cegah duplikat beruntun)
MAX_POSITIONS   = 3        # Maksimal 3 posisi terbuka bersamaan (Low Drawdown)

# ── Dynamic Risk Management (ARSTITEKTUR BARU) ────────────────────
DYNAMIC_LOT_ENABLED   = True     # Aktifkan perhitungan lot proporsional AI
DYNAMIC_SL_TP_ENABLED = True     # Aktifkan jarak SL/TP dinamis berbasis ATR M5
BASE_CAPITAL          = 1000.0   # Modal dasar acuan ($1000)
BASE_LOT              = 0.01     # Lot dasar sangat aman (Fixed Fractional Risk)
# ─────────────────────────────────────────────────────────────────

MOMENTUM_DEVIATION = 0.00030    # Arsitektur v9.2: dinaikkan dari 0.00008 (~14 pips di $4500 Gold)

# ── Exit Strategy (KUNCI PERUBAHAN OPTIMAL GOLD - Arsitektur v7.5) ─
SL_PIPS         = 30       # Batas resiko awal emas
TP_PIPS         = 45       # Target profit logis emas
BREAKEVEN_PIPS  = 20       # BE aktif setelah trade melaju aman (+20 pips)
TRAIL_STEP      = 0        # Nonaktifkan trailing stop agar emas bernapas menuju TP
# ─────────────────────────────────────────────────────────────────

# -- Risk Management -----------------------------------------------
MAX_DAILY_LOSS_PIPS      = 200   # stop jika total loss pip hari ini > 200 (~$20)
MAX_CONSECUTIVE_LOSSES   = 5     # pause jika 5 loss berturut-turut
PAUSE_MINUTES            = 30    # pause 30 menit
MAX_SPREAD               = 30    # pip max spread
# ─────────────────────────────────────────────────────────────────

# ── ML Gatekeeper ─────────────────────────────────────────────────────
ML_ENABLED  = True
ML_PROB_MIN = 0.550   # Threshold for 31-Feature Optuna Model (Lebih agresif untuk akun demo)

                     # Kelas B (0.50 - 0.59) | Kelas A (0.60 - 0.69) | Kelas A+ (>= 0.70)


# ─────────────────────────────────────────────────────────────────

# ── Target Harian ─────────────────────────────────────────────────
DAILY_PROFIT_TARGET_USD = 2000.0   # stop trading jika profit harian >= $2000
TIME_STOP_MINUTES       = 30     # force close posisi setelah 30 menit
# ─────────────────────────────────────────────────────────────────
