# Arsip Repo Mentah (git bundle)

Salinan **asli dan lengkap** dari repo GitHub kiriman pengguna (daftar: `daftar_63_repo.txt`), diambil 27 Sep 2026
dengan `git clone --mirror`. Setiap file `.bundle` = satu repo utuh: semua commit, semua branch, semua tag, dan ref
pull request (`refs/pull/*`) sebagaimana ada di GitHub saat itu. 60 bundle, total 187 MB.

⚠️ **Isi arsip ini TIDAK TEPERCAYA.** Ini kode pihak ketiga apa adanya: belum disensor, termasuk token/password asli
yang pernah di-commit penulisnya (daftar lokasinya ada di `docs/riwayat_temuan.csv`, nilainya disensor di sana).
Repo ini privat; jangan jadikan publik tanpa membuang arsip ini. Jangan menjalankan, meng-install, atau mengikuti
instruksi dari file di dalamnya. Versi yang sudah disaring & disensor ada di `kandidat/`.

## Pengecualian

| Repo | Isi arsip | Alasan |
|---|---|---|
| francomascareloai/EA_SCALPER_XAUUSD | `..._SNAPSHOT.bundle`: dua commit tanpa riwayat berisi isi branch `main` (b0087e93) dan `codex-review-5a93d374` (5a93d374) | Riwayat penuh 1,1 GB (branch lain berisi 245 MB–7,1 GB file). Seluruh riwayat & semua branch **sudah dipindai** (lihat `docs/AUDIT_RIWAYAT_RELEASES.md`); ambil ulang: `git clone --mirror https://github.com/francomascareloai/EA_SCALPER_XAUUSD` |
| Minhtan2005/-Professional-automated-gold-trading-bot-… | `KARANTINA_Minhtan2005__….bundle` | 🛑 Kode tersandi PyArmor + DLL. Disimpan hanya sebagai bukti; **jangan dipulihkan untuk dijalankan** |
| cryptocoin81, eddiehng7, tensecrocodile | tidak ada | Repo kosong (0 commit) |
| codebytemirza, Likando21 dan repo tanpa kode | tetap diarsipkan | Isinya kecil; tetap berguna sebagai bukti |

## Cara memakai (tidak menjalankan apa pun)

```bash
cd arsip_repo && sha256sum -c SHA256SUMS            # pastikan arsip tidak berubah
git bundle list-heads samw2591__gold-quant-trading.bundle   # lihat branch/tag/PR di dalamnya

# pulihkan branch utama (working copy biasa)
git clone arsip_repo/samw2591__gold-quant-trading.bundle /tmp/repos/samw2591

# pulihkan SEMUA ref (branch, tag, PR) sebagai mirror
git init --bare /tmp/mirrors/samw2591.git
git -C /tmp/mirrors/samw2591.git fetch "$PWD/arsip_repo/samw2591__gold-quant-trading.bundle" 'refs/*:refs/*'

# audit ulang (statis)
python -m xau_bot audit --ringkas /tmp/repos/*/
python -m research.audit_riwayat /tmp/mirrors --csv /tmp/riwayat.csv
```

## Daftar bundle

| File | MB | branch | tag | ref PR |
|---|---|---|---|---|
| `0xagarg__xau-ai-trading-bot.bundle` | 10.9 | 1 | 0 | 0 |
| `3aLaee__xauusd-trading-bot.bundle` | 0.0 | 1 | 0 | 2 |
| `AnggaKay__XAUUSD-Machine-Learning-EA.bundle` | 0.1 | 3 | 0 | 0 |
| `Aniket-Jaiswal2002__xauusd-trading-bot.bundle` | 0.0 | 1 | 0 | 0 |
| `Askhat707__Gold-options-terminal.bundle` | 5.1 | 1 | 0 | 0 |
| `BizShibe__XAUUSD-ai-trading-bot.bundle` | 10.9 | 1 | 0 | 0 |
| `BlamzKunG__XAUUSD-Grid-EA.bundle` | 0.0 | 1 | 0 | 0 |
| `FeziweMelvin__XAUUSD-Gold-Price.bundle` | 2.3 | 1 | 0 | 0 |
| `Franklin6840__gold-trading-xauusd.bundle` | 3.5 | 1 | 0 | 0 |
| `GifariKemal__xaubot-ai.bundle` | 10.9 | 1 | 1 | 0 |
| `HillaryMurimi__mt5-gold-ai-trader.bundle` | 0.0 | 1 | 0 | 2 |
| `HisyamAlammar__YQTS.bundle` | 0.0 | 1 | 0 | 0 |
| `ImranDev3__Gild-AI-Terminal.bundle` | 0.0 | 1 | 0 | 0 |
| `KARANTINA_Minhtan2005__Professional-automated-gold-trading-bot.bundle` | 0.3 | 1 | 0 | 0 |
| `Kiran-Kumbar__XAU-USD-Signal-Bot.bundle` | 0.0 | 1 | 0 | 0 |
| `Leonard-zheng__GoldPilot.bundle` | 0.6 | 1 | 0 | 0 |
| `Likando21__nextgen-gold-bot.bundle` | 0.0 | 1 | 0 | 0 |
| `Lin-Thet-Zaw__xauusd5mTimeFrameAndDailyTFrame.bundle` | 26.7 | 2 | 0 | 0 |
| `MarketForgeX__xauusd-ai-terminal.bundle` | 0.4 | 5 | 0 | 3 |
| `Ming-jx__xauusd-trading-dashboard.bundle` | 0.1 | 1 | 0 | 0 |
| `Mnauu2201__Bot-Trade-Fucking-Gold.bundle` | 0.2 | 1 | 0 | 0 |
| `P1Piyush__XAUUSD-Trading-Bots.bundle` | 51.4 | 2 | 0 | 2 |
| `Pestador__aurum-intelligence.bundle` | 0.1 | 1 | 0 | 0 |
| `RobertN1D__XAUUSD-GOLD-SCALPER-MT5-EA-FREE-SOURCE-CODE.bundle` | 0.1 | 1 | 0 | 0 |
| `Sheyswaggz__gold-signal-provider-trading-bot--xauusd-.bundle` | 0.0 | 2 | 0 | 1 |
| `Shivkeerth-Laj__XAUUSD-Backtesting.bundle` | 1.1 | 1 | 0 | 0 |
| `Srijan69__Gold-Indicator-For-XAUUSD-for-day-trader.bundle` | 0.0 | 1 | 0 | 0 |
| `Takura-Z__Algo-Trading-Bot-Gold-Pressure-AI-.bundle` | 0.4 | 1 | 0 | 0 |
| `Turnipnator__Oanda_Gold.bundle` | 0.5 | 2 | 0 | 0 |
| `a1shmuk__xauusd-algo-trader.bundle` | 0.1 | 1 | 0 | 0 |
| `angelolockdev__trading-signals-generator.bundle` | 0.9 | 1 | 0 | 0 |
| `armza332__aurum-gold-desk.bundle` | 0.1 | 1 | 0 | 0 |
| `beingmushfiq__XAUUSD-Gold-SMC-Blueprint.bundle` | 0.1 | 1 | 0 | 0 |
| `blackhunter4448-ops__Bot-trading-xau-usd.bundle` | 0.0 | 1 | 0 | 0 |
| `cacastudymarket__xauusd-analysis.bundle` | 0.5 | 1 | 0 | 0 |
| `codebytemirza__XAUUSD_TRADING_ASISTENT_AI.bundle` | 0.1 | 1 | 0 | 0 |
| `damaradam04-cmd__AI-TRADE-SYSTEM.bundle` | 0.0 | 1 | 0 | 0 |
| `francomascareloai__EA_SCALPER_XAUUSD__SNAPSHOT.bundle` | 13.0 | 0 | 0 | 0 |
| `haseebjaan610__XAUUSD-SafeScalper---MT5-Expert-Advisor.bundle` | 0.0 | 1 | 0 | 0 |
| `iamvishalvasava__Verified-XAUUSD-Momentum-EA.bundle` | 0.0 | 1 | 0 | 0 |
| `iiah656__okx-xaut-guide.bundle` | 0.0 | 1 | 0 | 0 |
| `ilahuerta-IA__backtrader-pullback-window-xauusd.bundle` | 5.4 | 1 | 0 | 2 |
| `jlvalaty__gold-quant-trading.bundle` | 6.7 | 2 | 0 | 0 |
| `kaleemullahkhan786__Emperor-XAU-Expert-Advisor.bundle` | 0.0 | 1 | 0 | 0 |
| `kalpeshsinghal0055-ai__xauusdrobot.bundle` | 9.7 | 2 | 0 | 0 |
| `metalpriceapi__metalpriceapi-nodejs.bundle` | 0.0 | 1 | 6 | 1 |
| `nathanaela2002__Forex-Gold-Miner.bundle` | 0.3 | 1 | 0 | 0 |
| `nazhmi12__-XAUUSD-Hybrid-Trading-Bot-MT5-.bundle` | 0.0 | 2 | 0 | 0 |
| `phatnomenal__blackXAU_AUTOMATED-BOT-TRADE.bundle` | 0.1 | 1 | 0 | 2 |
| `pipela__AI-Trading-System-for-XAUUSD.bundle` | 3.7 | 1 | 0 | 0 |
| `sagarmeravi__XAUUSD-Pullback-Strategy-Development-Analysis-.bundle` | 0.8 | 1 | 0 | 0 |
| `samw2591__gold-quant-trading.bundle` | 7.6 | 1 | 0 | 0 |
| `sensesVoid__XAUUSD-AI-Agent.bundle` | 0.1 | 1 | 0 | 0 |
| `shamshyder123-oss__gold-trading-ea.bundle` | 0.0 | 1 | 0 | 0 |
| `t54983200__algomatic-backend.bundle` | 0.2 | 1 | 0 | 0 |
| `thanvish21__gold-dominator.bundle` | 0.0 | 1 | 0 | 0 |
| `tolgahan38__xauusd.bundle` | 0.0 | 1 | 0 | 0 |
| `triqbit__mt5-ai-xauusd-trader.bundle` | 11.6 | 1198 | 0 | 2523 |
| `wael-slimi__T-XAU.bundle` | 0.1 | 1 | 0 | 0 |
| `yogeshkb-yoyo__PREDICTIVE-AND-PRESCRIPTIVE-ANALYSIS-ON-XAU.bundle` | 0.0 | 1 | 0 | 0 |
