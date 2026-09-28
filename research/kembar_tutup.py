"""Sinyal kembar (beberapa set Donchian di candle sama) di-entry sekali: harga TUTUP set mana yang dipakai?

python -m research.kembar_tutup

Pertanyaan pengguna (28 Sep 2026): kartu menampilkan 3 harga TUTUP (T40/15, T55/20, T80/30) padahal entry hanya
sekali; minta satu harga saja. Dibandingkan R tiap set pada entry yang sama (sinyal 💰, mesin research/eksternal).
"""
from __future__ import annotations

from .eksternal import asset

NAMES = {0: "T40/15", 1: "T55/20", 2: "T80/30"}


def main() -> None:
    for name in ("XAUUSD", "BTCUSD"):
        a = asset(name)
        m = a.money
        m = m.assign(nset=m.groupby(["t", "dir"]).set.transform("size"))
        tw = m[m.nset >= 2]
        print(f"\n{name}: sinyal 💰 {len(m)}, dalam grup kembar {len(tw)} ({tw.groupby(['t', 'dir']).ngroups} grup)")
        piv = tw[tw.nset == 3].pivot_table(index=["t", "dir"], columns="set", values="R")
        for s in (0, 1, 2):
            r = piv[s]
            y = r.index.get_level_values(0)
            print(f"  grup 3 set (n={len(piv)}): keluar {NAMES[s]}: WR {100 * (r > 0).mean():.0f}% rata {r.mean():+.3f}R "
                  f"total {r.sum():+.1f}R | latih {r[y < a.split].mean():+.3f} uji {r[y >= a.split].mean():+.3f}")
        avg = piv.mean(axis=1)
        print(f"  rata-rata 3 set (cara aplikasi lama): rata {avg.mean():+.3f}R total {avg.sum():+.1f}R")
        two = tw[tw.nset == 2]
        combo = two.groupby(["t", "dir"]).set.transform(lambda x: "+".join(NAMES[i] for i in sorted(x)))
        for c, g in two.groupby(combo):
            p = g.pivot_table(index=["t", "dir"], columns="set", values="R")
            print(f"  grup 2 set {c} (n={len(p)}): " + " | ".join(f"{NAMES[k]} rata {p[k].mean():+.3f}R" for k in p.columns))


if __name__ == "__main__":
    main()
