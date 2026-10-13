export const meta = {
  name: 'riset-berita-lonjakan',
  description: 'Riset & validasi petunjuk sebelum rilis per jenis berita USD → arah lonjakan emas menit pertama; verifikasi adversarial kandidat',
  phases: [
    { title: 'Riset', detail: '6 kelompok berita, hipotesis ditetapkan dulu, uji tutup kertas + permutasi keluarga' },
    { title: 'Verifikasi', detail: '2 pemeriksa independen per kandidat: look-ahead/data live & statistik ulang' },
    { title: 'Kritik', detail: 'apa yang terlewat' },
  ],
}

const KONTEKS = [
  "You are working in the repo /home/user/Trading (Indonesian user; write docs/result text in Indonesian). Python 3.13,",
  "pandas/numpy/pyarrow/sklearn installed. Run Python as: cd /home/user/Trading && PYTHONPATH=. python3 -m research.<module>.",
  "Network is open (FRED_API_KEY env set; api.nasdaq.com, Kalshi API, GitHub raw, FRED all reachable).",
  "",
  "GOAL (user request 11 Oct 2026): for each USD news release, find pre-release clues that predict the DIRECTION of gold's",
  "largest move in the FIRST MINUTE after release ('lonjakan menit pertama'), validated honestly, so that only high-accuracy,",
  "trustworthy rules get installed in the app. CPI is already done (rule 'IDX|K': unrounded Nasdaq index consensus vote,",
  "fallback Kalshi; 65% tutup kertas 2016-2026, LAMA 65% / BARU 65%). A first broad pass on other news FAILED (0 rules passed)",
  "using: previous surprise (P), sum of last 3 surprises (P3), consensus vs previous actual (KON), NFP<-ADP/claims 4wk/ISM",
  "employment/Kalshi payrolls/Kalshi U3, PPI<-CPI, Retail<-CPI/vehicle sales, PCE<-core CPI/core PPI/Kalshi core PCE,",
  "ISM<-Chicago PMI/regional Fed/S&P Global PMI same morning, GDP<-GDPNow, JOLTS<-Indeed, Claims<-continuing claims,",
  "Consumer<-S&P500/gasoline. Results: docs/eksternal/hasil_lonjakan_uji_berita.txt and docs/eksternal/hasil_berita_detik.txt,",
  "summary docs/BERITA_DETIK.md. Your job is to go DEEPER and MORE CREATIVELY for your assigned news types: new data sources,",
  "better-defined versions of those clues, combinations decided BEFORE looking, and test them with the SAME honest framework.",
  "",
  "EXISTING INFRASTRUCTURE (read the code before using it):",
  "- Target: data/research/eksternal/lonjakan60.parquet (research/lonjakan.py): one row per release t0 (UTC) with grup",
  "  (CPI, PPI, NFP, ADP, RETAIL, PCE, ISM, GDP, JOLTS, CLAIMS, KONSUMEN, FOMC, ...), arah (+1 = largest first-minute move UP,",
  "  -1 DOWN, 0 flat), detik, besar, ex_arah (Exness feed), du_arah (Dukascopy feed). Secondary target (report too): direction",
  "  at seconds 2/3/5/10 from data/research/eksternal/pra_xau_semua_v2.parquet columns y{h}_XAU_EXNESS (fallback y{h}_XAU).",
  "  Releases in pra_xau_semua_v2 can be duplicated with a wrong time zone (e.g. 07:30 vs 08:30 NY): de-duplicate per (grup,",
  "  NY date) keeping the modal NY minute of that grup (see research/lonjakan.rilis()). Gold tick data for some groups ends",
  "  Jan 2026 (so 2026 coverage is partial for PPI/ISM/etc.).",
  "- Surprise/consensus data: research/nasdaq_kalender.py hari(date, ambil=False) returns cached Nasdaq/Investing.com calendar",
  "  rows for EVERY US weekday 2010-01-04..2026-10 (data/research/eksternal/nasdaq/<NY date>.json; fields gmt (UNRELIABLE",
  "  time), country, eventName, actual, consensus, previous). research/berita_detik.py has helpers: us(d), ambil(d, eventName)",
  "  -> (act, cons, prev) of the FIRST row with that name, kejutan(d, name), riwayat(name, before_date, days),",
  "  kalshi_lean(series, step, t0, cons), sp500(), and tabel() (cached per-release table with Nasdaq surprise column s, column",
  "  arah = USD sign of the main event, PLAFON, and the first-pass clues, all stored as good-for-USD sign so gold guess = minus).",
  "  Some event names appear twice on a date (m/m then y/y; order can be swapped: see research/nasdaq_kalender.cpi for an",
  "  order fix using FRED). ForexFactory calendar 2010-Jan 2026: research/news_prediksi.calendar().",
  "- Evaluation helpers in research/lonjakan_uji.py: tutup(usd_clue, y, th) = walk-forward 'tutup kertas' (year Y uses the rule",
  "  only if releases before Y were > 50% right with n >= 10; gold guess = -usd_clue); sk(guess, y, mask) -> (hits, n);",
  "  keluarga(C: dict rule->usd array, y, th, rng) -> per rule (p_2016+, p_2022+, observed) family permutation test (gold",
  "  outcomes shuffled 2000x, compared with the BEST rule of each shuffle; only rules with >= 40 releases since 2016 and >= 20",
  "  since 2022).",
  "- Other sources: FRED via research/eksternal_makro.fred(series) (vintage availability; CAUTION: for monthly data published",
  "  next month the 'available' date can be too early: prefer first-release dates via FRED output_type=4 as in",
  "  research/pra_per_berita.py / fred_<series>_awal.json), Cleveland Fed nowcasts incl. PCE & core PCE",
  "  (data/research/eksternal/cleveland/nowcast_month.json; parsing example research/cpi_gabung.nowcast_table), GDPNow",
  "  (research/berita_gabung.gdpnow()), Indeed postings (research/sumber_lain.indeed()), Kalshi market histories",
  "  data/research/eksternal/kalshi/{KXPAYROLLS,KXU3,KXPCECORE,KXFEDDECISION}/ (helpers research/kalshi_uji.curve/lean),",
  "  Polymarket (research/polymarket.py), ALFRED vintages alfred_*.json, regional Fed FRED series fred_*FRB*.json.",
  "  You may download more public data into data/research/eksternal/<new_subdir>/ (keep it modest, < 20 min of downloading).",
  "",
  "RULES (must follow):",
  "1. Do NOT modify existing files. Create only research/riset_<kode>*.py and docs/eksternal/hasil_riset_<kode>.txt.",
  "   Do not touch cloud/, tests/, android/, CLAUDE.md. Do NOT git commit/push.",
  "2. PRE-REGISTER: write every hypothesis (clue definition + expected sign + economic reason) in the script docstring BEFORE",
  "   you run any evaluation. Count EVERY rule you evaluate (including variants/thresholds) and include them all in the family",
  "   permutation test. If you add rules after seeing results, mark them 'pasca-lihat' and still include them in the family.",
  "3. NO LOOK-AHEAD: a clue may only use information published before t0 - 1 second (NY time). For same-day releases you must",
  "   know their real release time (e.g. S&P Global PMI 09:45 ET vs ISM 10:00 ET); do not trust the Nasdaq gmt field. Monthly",
  "   data must use first-release/publication dates, never revised values that were not known yet if revisions matter.",
  "4. Target = lonjakan arah (primary). Evaluate with tutup() per year from 2013; report: 2016-2026 overall, LAMA (2016..Sep",
  "   2021), BARU (>= Oct 2021), 2022+, 2026, per-year hits, baseline 'always up', plafon (true surprise), and secondary",
  "   detik 2-10.",
  "5. PASS CRITERIA (identical to CPI): tutup kertas >= 60% for 2016-2026 AND > 50% in LAMA and BARU (n >= 8 each) AND",
  "   family permutation p < 0.05 (2016+ or 2022+) AND >= 40 guessed releases since 2016 AND the clue is computable LIVE",
  "   before the release from sources reachable by a Vercel cloud function (Nasdaq API, FRED API, Kalshi/Polymarket API,",
  "   Indeed GitHub CSV, ForexFactory weekly JSON, Twelve Data): say exactly how.",
  "6. Be honest: if nothing passes, say so. Do not overfit (no dozens of thresholds hunting for p<0.05; keep variants few",
  "   and pre-registered).",
  "7. Keep total runtime reasonable (the machine has 4 CPUs shared with another agent): permutation 2000x is fine, avoid",
  "   minutes-long inner loops; cache intermediate tables under data/research/eksternal/.",
  "Write the result file in Indonesian with the full tables. Return the structured summary.",
].join("\n")

const GRUP = [
  { kode: 'nfp', nama: 'NFP (Nonfarm Payrolls + Unemployment Rate + Average Hourly Earnings, grup NFP)',
    ide: 'Ideas: ADP surprise AND ADP vs consensus NFP gap; initial/continuing claims in the survey week vs prior month survey week; Conference Board labor differential (jobs plentiful minus hard to get) change; ISM manufacturing+services employment change; Challenger job cuts; NFIB hiring plans; Indeed postings; Kalshi payrolls/U3 at 1h before; Polymarket; BLS survey-week length (4 vs 5 weeks, known effect on UR: PK5 rule exists in research/pra_per_berita.py); consensus disagreement (Investing vs ForexFactory); prior-month revision sign; unrounded AHE y/y consistency (FRED CES0500000003: implied y/y from m/m consensus vs y/y consensus, like CPI YOY). Gold reacts to a composite of NFP headline, UR (inverse) and AHE.' },
  { kode: 'inflasi', nama: 'PPI (grup PPI) dan PCE (grup PCE)',
    ide: 'Ideas: PPI: unrounded PPI index consensus if Nasdaq has it, m/m vs y/y consistency with FRED PPIFIS/PPIFID (base effects, like CPI YOY which was strong), CPI surprise earlier same month (only when CPI before PPI), import prices, ISM prices paid change, energy (WTI/gasoline/diesel) month change. PCE: Cleveland Fed PCE & core PCE nowcast (unrounded!) vs consensus (very promising analog of the CPI index rule); core PCE m/m vs y/y consistency with FRED PCEPILFE; Kalshi KXPCECORE lean; quarterly core PCE in the GDP release (Nasdaq Core PCE Prices) released before monthly PCE in some months.' },
  { kode: 'ism', nama: 'ISM Manufacturing PMI dan ISM Services (Non-Manufacturing) PMI (grup ISM; pisahkan keduanya)',
    ide: 'Ideas: S&P Global flash PMI (released about a week before, vs its consensus and vs previous), S&P Global final PMI 09:45 same day (revision vs flash), Chicago PMI (last business day of month, before ISM manufacturing), regional Fed surveys weighted (Empire, Philly, Richmond, KC, Dallas: FRED series exist), prior ISM new orders minus inventories (leading), consensus vs previous with mean reversion, seasonal residuals. Separate manufacturing and services (different timing and drivers). Note which same-day items are truly earlier than 10:00 ET.' },
  { kode: 'retail_gdp', nama: 'Retail Sales (grup RETAIL) dan GDP advance (grup GDP)',
    ide: 'Ideas Retail: unit vehicle sales (FRED TOTALSA first-release dates) vs prior month, gasoline price change (nominal sales), Redbook weekly same-store sales (Nasdaq rows, actual values) averaged over the reference month vs prior month, Chicago Fed CARTS (if downloadable), CPI goods surprise, consensus vs previous. GDP: GDPNow final vs consensus (also NY Fed/St. Louis nowcasts if obtainable), advance indicators (trade balance, inventories released before), Kalshi/Polymarket GDP markets, consensus vs previous; also GDP price index.' },
  { kode: 'kerja_lain', nama: 'ADP (grup ADP), JOLTS (grup JOLTS), Initial Jobless Claims (grup CLAIMS)',
    ide: 'Ideas ADP: claims trend, ADP weekly (2025+ ADP Employment Change Weekly in Nasdaq), prior NFP surprise, consensus vs previous. JOLTS: Indeed postings change (proper lag), NFIB job openings, prior quits/hires, Conference Board labor differential. Claims: holiday/seasonal weeks, prior week revision direction, continuing claims, Kalshi claims markets if any, consensus vs 4-week average.' },
  { kode: 'fomc_konsumen', nama: 'FOMC rate decision 14:00 ET (grup FOMC) dan sentimen konsumen UoM/Conference Board (grup KONSUMEN)',
    ide: 'Ideas FOMC: Kalshi KXFEDDECISION probabilities vs consensus (surprise probability), SEP vs non-SEP meetings, 2y yield change over the week before (FRED DGS2), pre-FOMC drift, gold trend into FOMC, Polymarket Fed markets; target is the first-minute gold move at the statement. KONSUMEN: UoM final vs prelim (prelim known: revision direction from stock/gas moves between prelim and final), UoM 1y inflation expectations, gasoline price change, S&P 500 change, CB vs UoM cross-release, consensus vs previous.' },
]

const HASIL_SCHEMA = {
  type: 'object',
  properties: {
    kode: { type: 'string' },
    file_skrip: { type: 'array', items: { type: 'string' } },
    file_hasil: { type: 'string' },
    jumlah_aturan_diuji: { type: 'number' },
    ringkasan: { type: 'string', description: 'Indonesian, 5-10 lines: what was tested, best results, honest verdict' },
    hasil: { type: 'array', items: { type: 'object', properties: {
      berita: { type: 'string' }, kode_aturan: { type: 'string' }, uraian: { type: 'string' },
      semua: { type: 'number' }, lama: { type: 'number' }, baru: { type: 'number' }, s2022: { type: 'number' },
      n_rilis: { type: 'number' }, p16: { type: 'number' }, p22: { type: 'number' }, lolos: { type: 'boolean' } },
      required: ['berita', 'kode_aturan', 'semua', 'n_rilis', 'lolos'] } },
    kandidat: { type: 'array', description: 'ONLY rules meeting ALL pass criteria', items: { type: 'object', properties: {
      berita: { type: 'string' }, kode_aturan: { type: 'string' }, aturan_lengkap: { type: 'string' },
      data_live: { type: 'string', description: 'exact live sources & computation before release' },
      cara_ulang: { type: 'string', description: 'exact command to reproduce' },
      semua: { type: 'number' }, lama: { type: 'number' }, baru: { type: 'number' }, s2022: { type: 'number' },
      n_rilis: { type: 'number' }, p16: { type: 'number' }, p22: { type: 'number' } },
      required: ['berita', 'kode_aturan', 'aturan_lengkap', 'data_live', 'cara_ulang', 'semua', 'n_rilis'] } },
  },
  required: ['kode', 'file_skrip', 'file_hasil', 'jumlah_aturan_diuji', 'ringkasan', 'hasil', 'kandidat'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    alasan: { type: 'string', description: 'Indonesian, concrete evidence' },
    angka_ulang: { type: 'object', properties: { semua: { type: 'number' }, lama: { type: 'number' }, baru: { type: 'number' },
      s2022: { type: 'number' }, n_rilis: { type: 'number' }, p16: { type: 'number' }, p22: { type: 'number' } } },
  },
  required: ['refuted', 'alasan'],
}

const LENSA = [
  { kode: 'lookahead', teks: 'LOOK-AHEAD & LIVE DATA lens: check, release by release for a sample of at least 15 releases across years, that every input of the clue was really published BEFORE t0-1s (exact release times of same-day items, first-release vs revised values, FRED vintage dates, Nasdaq date offset). Check the clue can be computed live by a Vercel function before the release (source reachable, field available pre-release: e.g. does Nasdaq show consensus/previous before release?). Refute if any leak or if not live-computable.' },
  { kode: 'statistik', teks: 'STATISTICS lens: independently re-implement the rule in your OWN short script (do not just re-run theirs), recompute tutup kertas 2016-2026/LAMA/BARU/2022+, and the family permutation using the TRUE number of rules the researcher tested (read their script/docstring; if they tested more variants than included in the family, redo the family test including all of them). Also check robustness: Exness-only vs Dukascopy-only target (lonjakan60.parquet ex_arah / du_arah), odd vs even releases, threshold +/- one step, and the secondary target detik 2-10. Refute if numbers do not reproduce, p >= 0.05 with the honest family, or results are fragile.' },
]

// args (opsional): daftar kode kelompok, mis. ["retail_gdp","kerja_lain","fomc_konsumen"]; kosong = semua
const PILIH = Array.isArray(args) && args.length ? GRUP.filter(g => args.includes(g.kode)) : GRUP
log('Kelompok: ' + PILIH.map(g => g.kode).join(', '))
phase('Riset')
const hasil = await pipeline(
  PILIH,
  (g) => agent(
    KONTEKS + "\n\nYOUR ASSIGNMENT: " + g.nama + ". Kode file: riset_" + g.kode + ".\n" + g.ide +
    "\n\nStart by reading research/lonjakan_uji.py, research/berita_detik.py and the first-pass results for your news types. Then pre-register, implement, run, and write docs/eksternal/hasil_riset_" + g.kode + ".txt. Return the structured summary (kandidat = only rules meeting ALL pass criteria)." +
    "\n\nIMPORTANT (resumable): first check whether research/riset_" + g.kode + "*.py and docs/eksternal/hasil_riset_" + g.kode + ".txt already exist from an earlier/interrupted session (see docs/LANJUTAN.md). If they do, do NOT start over: read them, keep the pre-registered hypotheses as written (new rules only as pasca-lihat and inside the family test), finish any remaining steps, re-run the evaluation to confirm the numbers reproduce, finalize the result file, and return the summary.",
    { label: 'riset:' + g.kode, phase: 'Riset', schema: HASIL_SCHEMA }),
  (r, g) => {
    if (!r) return null
    const kand = r.kandidat || []
    if (!kand.length) return { riset: r, verifikasi: [] }
    return parallel(kand.flatMap(k => LENSA.map(l => () => agent(
      KONTEKS + "\n\nADVERSARIAL VERIFICATION. A researcher claims this rule passes all criteria:\n" + JSON.stringify(k, null, 2) +
      "\nResearcher files: " + JSON.stringify(r.file_skrip) + ", result file " + r.file_hasil + ". Total rules they tested: " + r.jumlah_aturan_diuji +
      ".\n\n" + l.teks + "\nYour job is to try to REFUTE the claim. Default to refuted=true if you cannot reproduce it or are uncertain. You may create research/verif_" + g.kode + "_" + l.kode + ".py (do not modify other files). Return the verdict.",
      { label: 'verif:' + g.kode + ':' + k.kode_aturan + ':' + l.kode, phase: 'Verifikasi', schema: VERDICT_SCHEMA })
      .then(v => Object.assign({ kandidat: k.kode_aturan, berita: k.berita, lensa: l.kode }, v || { refuted: true, alasan: 'verifier failed' })))))
      .then(vs => ({ riset: r, verifikasi: vs.filter(Boolean) }))
  },
)

phase('Kritik')
const ringkas = hasil.filter(Boolean).map(h => ({ kode: h.riset.kode, ringkasan: h.riset.ringkasan, jumlah: h.riset.jumlah_aturan_diuji,
  kandidat: (h.riset.kandidat || []).map(k => k.kode_aturan), verifikasi: h.verifikasi.map(v => ({ k: v.kandidat, lensa: v.lensa, refuted: v.refuted })) }))
const kritik = await agent(
  KONTEKS + "\n\nCOMPLETENESS CRITIC. Here are the research summaries for all news groups:\n" + JSON.stringify(ringkas, null, 2) +
  "\nRead the result files docs/eksternal/hasil_riset_*.txt. In Indonesian, list concretely: (1) important clue ideas or data sources NOT tested that have a real economic reason and are obtainable (say where), (2) methodological weaknesses in any of the tests (look-ahead, multiple testing, small n), (3) which news types have the most realistic chance of a valid rule in a next round. Do not run long computations; you may run quick checks. Return plain text.",
  { label: 'kritik', phase: 'Kritik' })

return { hasil, kritik }
