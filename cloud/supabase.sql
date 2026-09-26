-- Jalankan di Supabase: SQL Editor -> New query -> tempel -> Run.
-- GANTI dua nilai di bagian paling bawah: DOMAIN_KAMU dan CRON_SECRET_KAMU.

-- 1) Tabel status & riwayat sinyal
create table if not exists public.xau_state (
  id text primary key,
  data jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.xau_signals (
  id bigserial primary key,
  created_at timestamptz not null default now(),
  type text not null,
  payload jsonb not null
);

-- Hanya service_role (dipakai Vercel) yang boleh akses; publik tertutup.
alter table public.xau_state enable row level security;
alter table public.xau_signals enable row level security;

-- 2) Ekstensi penjadwal & HTTP
create extension if not exists pg_cron;
create extension if not exists pg_net;

-- 3) Jadwal: menit ke-2 dan ke-32 tiap jam (beri waktu candle H1 selesai terbentuk).
--    Mau lebih sering? ganti jadi '*/5 * * * *' (tiap 5 menit, masih dalam kuota gratis Twelve Data).
select cron.unschedule('xau-tick') where exists (select 1 from cron.job where jobname = 'xau-tick');
select cron.schedule(
  'xau-tick',
  '2,32 * * * *',
  $$ select net.http_get(
       url := 'https://DOMAIN_KAMU/api/tick?key=CRON_SECRET_KAMU',
       timeout_milliseconds := 60000
     ); $$
);

-- Cek jadwal:            select * from cron.job;
-- Cek hasil panggilan:   select status_code, content from net._http_response order by created desc limit 5;
-- Riwayat sinyal:        select created_at, type, payload from public.xau_signals order by id desc limit 20;
-- Hentikan:              select cron.unschedule('xau-tick');
