# AirRadar Pro

Adnan Menderes Havalimanı (LTBJ / ADB) merkezli, internet tabanlı canlı uçak radar sistemi.

## Bileşenler

- **Pi Agent:** OpenSky state vector verisini alır ve VDS API'ye gönderir.
- **Backend:** Flask + SQLite API; rota bilgisini adsb.lol VRS standing data ile zenginleştirir.
- **Frontend:** Vue 3 + Vite tabanlı profesyonel ATC radar arayüzü.
- **Deployment:** Gunicorn, Nginx, systemd ve HTTPS uyumlu yapılandırmalar.

## Hızlı kurulum

### VDS

```bash
cd /opt
git clone https://github.com/burakuvan/airradar-pro.git
cd airradar-pro
sudo bash scripts/install-server.sh radar.kuvan.dev
```

### Raspberry Pi / WPSD

```bash
cd /home/pi-star
git clone https://github.com/burakuvan/airradar-pro.git
cd airradar-pro
sudo bash scripts/install-pi.sh https://radar.kuvan.dev/api/update
```

Ayrıntılar: `docs/INSTALL.md`

## Veri kaynakları

- OpenSky REST API: canlı state vectors.
- adsb.lol VRS standing data: callsign tabanlı rota zenginleştirme.

> Bu proje gerçek hava trafik kontrolü için değildir. Hobi ve görselleştirme amaçlıdır; veriler gecikmeli, eksik veya hatalı olabilir.
