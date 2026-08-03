# Kurulum

## 1. VDS (AlmaLinux 8)

DNS `radar.kuvan.dev` kaydını VDS IP adresine yönlendirin. Sunucuda:

```bash
cd /opt
git clone https://github.com/burakuvan/airradar-pro.git
cd airradar-pro
chmod +x scripts/*.sh
sudo bash scripts/install-server.sh radar.kuvan.dev
```

Mevcut Let's Encrypt sertifikası yoksa önce Certbot ile oluşturun:

```bash
dnf install -y certbot python3-certbot-nginx
certbot --nginx -d radar.kuvan.dev
```

Kontroller:

```bash
systemctl status airradar --no-pager
curl https://radar.kuvan.dev/health
```

## 2. Raspberry Pi Zero 2 W / WPSD

```bash
cd /home/pi-star
git clone https://github.com/burakuvan/airradar-pro.git
cd airradar-pro
chmod +x scripts/*.sh
sudo bash scripts/install-pi.sh https://radar.kuvan.dev/api/update
```

Kontroller:

```bash
systemctl status airradar-pi --no-pager
journalctl -u airradar-pi -f
```

## 3. Güncelleme

VDS:

```bash
sudo /opt/airradar-pro/scripts/update-server.sh
```

Pi:

```bash
cd /home/pi-star/airradar-pro
git pull --ff-only
sudo systemctl restart airradar-pi
```

## Sorun giderme

- API boşsa Pi servis günlüğünü kontrol edin.
- `8090 port in use` hatasında eski elle başlatılmış Gunicorn sürecini kapatın.
- Nginx 404 veriyorsa `nginx -T` ile aynı domaini kullanan çakışan site tanımlarını kontrol edin.
- OpenSky verisi internet tabanlıdır; birkaç saniye gecikme ve eksik uçaklar normaldir.
