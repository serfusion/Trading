#!/usr/bin/env bash
# Cek kompilasi & pratinjau UI aplikasi Android TANPA Android SDK (Compose Desktop + stub Android).
#   bash tools/compose_check/run.sh compile            # kompilasi file UI (Compose MP 1.6.11, Maven Central)
#   bash tools/compose_check/run.sh preview [gelap|terang] [out.png]
#        render PNG kartu status (XAU/BTC/ETH + hitung mundur) & kartu 💎 Spot dengan data contoh
#        (Compose MP 1.5.12: runtime hanya Maven Central; 1.6 butuh Google Maven yang diblokir jaringan sesi)
# Butuh: gradle (ada di /opt/gradle), JDK 17+, akses repo.maven.apache.org & plugins.gradle.org.
# File yang memakai API Android murni (MainActivity, Notifications, NewsAlarm, SignalPoller) TIDAK ikut dicek —
# CI GitHub (Android APK) tetap pemeriksa akhir.
set -euo pipefail
MODE=${1:-compile}
HERE=$(cd "$(dirname "$0")" && pwd)
APP=$(cd "$HERE/../../android/app/src/main/java/com/xausignal/app" && pwd)
WORK=${COMPOSE_CHECK_DIR:-${TMPDIR:-/tmp}/compose_check_$MODE}
mkdir -p "$WORK/src/main/kotlin"
rm -rf "$WORK/src/main/kotlin"/*
cat > "$WORK/settings.gradle.kts" <<'G'
pluginManagement { repositories { gradlePluginPortal(); mavenCentral() } }
rootProject.name = "compose_check"
G
if [ "$MODE" = compile ]; then KV=1.9.24; CV=1.6.11; else KV=1.9.21; CV=1.5.12; fi
cat > "$WORK/build.gradle.kts" <<G
plugins {
    kotlin("jvm") version "$KV"
    id("org.jetbrains.compose") version "$CV"
}
repositories { mavenCentral() }
kotlin { jvmToolchain(21) }
dependencies {
    implementation(compose.desktop.currentOs)
    implementation(compose.material3)
    implementation(compose.materialIconsExtended)
    implementation("org.json:json:20240303")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-swing:1.8.1")
}
tasks.register<JavaExec>("preview") {
    classpath = sourceSets["main"].runtimeClasspath
    mainClass.set("com.xausignal.app.PreviewKt")
    args = listOf(project.findProperty("mode")?.toString() ?: "dark", project.findProperty("out")?.toString() ?: "preview.png")
}
G
SRC="$WORK/src/main/kotlin"
cp "$HERE/stubs/"*.kt "$SRC/"
if [ "$MODE" = compile ]; then
    for f in Theme Appearance StatusCard SpotCard SignalScreen SignalRepository ChatScreen StatsScreen RankCard TermsDialog; do
        cp "$APP/$f.kt" "$SRC/"
    done
    (cd "$WORK" && gradle compileKotlin --console=plain -q)
    echo "KOMPILASI LOLOS"
else
    for f in Theme Appearance StatusCard SpotCard SignalRepository; do cp "$APP/$f.kt" "$SRC/"; done
    cp "$HERE/preview/"*.kt "$SRC/"
    # material3 versi CMP 1.5 belum punya warna surfaceContainer*
    python3 - "$SRC/Theme.kt" <<'P'
import re, sys
p = sys.argv[1]
s = open(p).read()
s = re.sub(r'\s*surfaceContainer\w*\s*=\s*(?:[^,()\n]|\([^()]*\))+,', '', s)
open(p, 'w').write(s)
P
    MODEARG=$([ "${2:-gelap}" = terang ] && echo light || echo dark)
    OUT=$(realpath -m "${3:-preview_$MODEARG.png}")
    (cd "$WORK" && gradle preview -Pmode="$MODEARG" -Pout="$OUT" --console=plain -q)
    echo "PRATINJAU -> $OUT"
fi
