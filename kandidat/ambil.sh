#!/usr/bin/env bash
# Unduh repo ASLI (lengkap, termasuk data/biner) persis di commit yang diaudit, ke kandidat/_asli/ (di-gitignore).
# Pakai: bash kandidat/ambil.sh            -> semua
#        bash kandidat/ambil.sh samw2591   -> yang namanya mengandung kata itu
# Minhtan2005 (kode tersandi) sengaja TIDAK dicantumkan.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p _asli
FILTER="${1:-}"
ambil() {
  local repo=$1 sha=$2 dir="_asli/${1//\//__}"
  [[ -n "$FILTER" && "$repo" != *"$FILTER"* ]] && return 0
  [ -d "$dir/.git" ] && { echo "sudah ada: $dir"; return 0; }
  git init -q "$dir" && git -C "$dir" remote add origin "https://github.com/$repo"
  GIT_LFS_SKIP_SMUDGE=1 git -C "$dir" fetch -q --depth 1 origin "$sha" && git -C "$dir" checkout -q FETCH_HEAD
  echo "ok: $repo @ ${sha:0:10}"
}
ambil 0xagarg/xau-ai-trading-bot 7044c42b44eb3dfa641ae11c3f792a774ad2d331
ambil 3aLaee/xauusd-trading-bot 6fb632982b6e6ed653c614afcc1d5aa3355cb893
ambil AnggaKay/XAUUSD-Machine-Learning-EA 6953a9144b588b774d2711e637e23bb355e8b3aa
ambil Aniket-Jaiswal2002/xauusd-trading-bot 6d579ad3987792ebfbfebc24ab54153a490d0c49
ambil Askhat707/Gold-options-terminal 051598f3dfd1e41e387bb345a5f13dc4e557407f
ambil BizShibe/XAUUSD-ai-trading-bot 64b2adba9a5537e8b70bba2f3cedaebb897957d9
ambil BlamzKunG/XAUUSD-Grid-EA 9ffd0840f53b17c33396427721d02885e36b88cd
ambil FeziweMelvin/XAUUSD-Gold-Price 310bc3cdd7e55bc338c1f55738abab92aa745d0a
ambil Franklin6840/gold-trading-xauusd b4774c979327e1452c1f2ba595f900650bc4706c
ambil GifariKemal/xaubot-ai 10301c8665443d2b83569840df65de49b6890cbe
ambil HillaryMurimi/mt5-gold-ai-trader bdf8bf2c27e97e7e4ec372eb9f98f2784cbdbba5
ambil HisyamAlammar/YQTS 40d140850b0ee1190d86f6194a908b74dfea44aa
ambil ImranDev3/Gild-AI-Terminal 701b8f39df2c687b5381037632b7decc6a027971
ambil Kiran-Kumbar/XAU-USD-Signal-Bot 0887da8d85f26e415602a5985a218af94ae8bf94
ambil Leonard-zheng/GoldPilot cb3c72f851b950be403ee513d3a2adf41ee2ae87
ambil Likando21/nextgen-gold-bot e24f4bef6cb1958188d109bf8791dc5d3859cc0a
ambil Lin-Thet-Zaw/xauusd5mTimeFrameAndDailyTFrame c19f92b14ad344f3a7774089e2c4d3a9db7600f7
ambil MarketForgeX/xauusd-ai-terminal 673bd9ac3c9b549bdc549d5e1e4d0afb8fe26fbf
ambil Ming-jx/xauusd-trading-dashboard 24cc21a806c2e3b47ba495531086f504e477d6d3
ambil Mnauu2201/Bot-Trade-Fucking-Gold 6f8fd222c1f3751aab2c17f811d9459cd2ce8329
ambil P1Piyush/XAUUSD-Trading-Bots 777f619f4ee46b9505c1a74b19e455f4e0d5d591
ambil Pestador/aurum-intelligence df5f241f5028348259b82cb8d5344ee1fb180cc7
ambil RobertN1D/XAUUSD-GOLD-SCALPER-MT5-EA-FREE-SOURCE-CODE 2c7cc8dfe950cb000423048edc7994482034106d
ambil Sheyswaggz/gold-signal-provider-trading-bot--xauusd- 5e1c2e6f48fb0d84186a30f18c8d7fc14baa17fe
ambil Shivkeerth-Laj/XAUUSD-Backtesting 12a42c797b0362240e9730bfa7bbb21f78752c0e
ambil Srijan69/Gold-Indicator-For-XAUUSD-for-day-trader 3065a49116ed1096314613cedd69b89f14c471d2
ambil Takura-Z/Algo-Trading-Bot-Gold-Pressure-AI- 8faca0d689213fe7dac7c10043ba79fa14cc9fa1
ambil Turnipnator/Oanda_Gold 870e7964c3577ddabb77bc8ece3b008a89ac6d4e
ambil a1shmuk/xauusd-algo-trader 0d08a488f2622da3d6b3967661965380704bbf0b
ambil angelolockdev/trading-signals-generator 48cba098b2c7bb4fe6c7fc3674cec883f21bf737
ambil armza332/aurum-gold-desk 406ecf6a63512128b73b82317353a6dc39b2d829
ambil beingmushfiq/XAUUSD-Gold-SMC-Blueprint 81516ea2db9776cc353ae019a9ff0434982f8d39
ambil blackhunter4448-ops/Bot-trading-xau-usd 704fa28acb74eb3c4a398809702595315b0a6b39
ambil cacastudymarket/xauusd-analysis 51e5393827d56ecacc86d93e6566d331408b0f9a
ambil codebytemirza/XAUUSD_TRADING_ASISTENT_AI e00a047fd7974c3bf82d04ed659152936f514a11
ambil damaradam04-cmd/AI-TRADE-SYSTEM 9ccb5cbc02ce9d7ab22852803371fea0051cfef0
ambil francomascareloai/EA_SCALPER_XAUUSD b0087e93c8af6690102c6698b8123186703a9240
ambil haseebjaan610/XAUUSD-SafeScalper---MT5-Expert-Advisor 68433f30e3ad005e5711584725d2c7b08703904e
ambil iamvishalvasava/Verified-XAUUSD-Momentum-EA 04a7258ad1eda72d54ab2fcae839ffbb5ad7aa1f
ambil iiah656/okx-xaut-guide 082893a7a7dca9d37d151e0e09c8d207ebb3132a
ambil ilahuerta-IA/backtrader-pullback-window-xauusd 995c51b472bcb57bc51861994ec2a1c443dc2d63
ambil jlvalaty/gold-quant-trading 8846c92606ab9c832228656f4dd10e285da30440
ambil kaleemullahkhan786/Emperor-XAU-Expert-Advisor b9a4ef60d03504febd99054632fab618c3cc8883
ambil kalpeshsinghal0055-ai/xauusdrobot b45fb321fe175be39b5f15f8df375db34f1d72d7
ambil metalpriceapi/metalpriceapi-nodejs 3c05d0f01bafbf7ebc8a0399973a4982fb05db02
ambil nathanaela2002/Forex-Gold-Miner 4fa7b23a85af60e8cc42604b1eb6ce0040b73ea7
ambil nazhmi12/-XAUUSD-Hybrid-Trading-Bot-MT5- 87bafddb8b256184b8fc784b2b980216e3d00c0a
ambil phatnomenal/blackXAU_AUTOMATED-BOT-TRADE be74ebe2c4ba4f41c8a6a1a899ec73b8d63668f0
ambil pipela/AI-Trading-System-for-XAUUSD 16f2374e1fe1631b84c02178873cd8f93452d3d2
ambil sagarmeravi/XAUUSD-Pullback-Strategy-Development-Analysis- 1896dafc04c16db693805dad3b50f728968bd68a
ambil samw2591/gold-quant-trading c8827bb939f791a4c6a02b010db979a45061cc04
ambil sensesVoid/XAUUSD-AI-Agent a59875e30061267ea32f2a2c5ed0cf2e6b3be1b0
ambil shamshyder123-oss/gold-trading-ea 4d29f8608459837a2467d2ebc77ec0a9a529e695
ambil t54983200/algomatic-backend 24557a9d3fe6a15dbe47d11c00c3417135175cd5
ambil thanvish21/gold-dominator e8d640016c8a6d6a2dd1796c96a5d6ec1fc86007
ambil tolgahan38/xauusd 2b091e390d2aa98a4363a35f5cc8a3f0cd62a36d
ambil triqbit/mt5-ai-xauusd-trader de8c37da8f9cfbf565fbbbfffca83b60ca963231
ambil wael-slimi/T-XAU a59c516df3015d3cc5aa2fdb4670433febeac2b6
ambil yogeshkb-yoyo/PREDICTIVE-AND-PRESCRIPTIVE-ANALYSIS-ON-XAU e8bd60edc49508ba202bd5ff42896a278c35c8e0
