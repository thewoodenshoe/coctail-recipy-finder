# Ubuntu Deployment

These steps deploy the MVP on the Ubuntu host without touching CHS Finds nginx or Cloudflare.

## One-Time Setup

```bash
cd ~/projects/coctail-recipy-finder
git pull --ff-only
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
mkdir -p data
DATABASE_URL=sqlite:////home/ubuntu/projects/coctail-recipy-finder/data/cocktail_index.db .venv/bin/python -m app.cli init-db
DATABASE_URL=sqlite:////home/ubuntu/projects/coctail-recipy-finder/data/cocktail_index.db .venv/bin/python -m app.cli sync-creators
```

## Direct-Port Smoke Run

```bash
APP_ENV=production \
APP_HOST=0.0.0.0 \
APP_PORT=8000 \
DATABASE_URL=sqlite:////home/ubuntu/projects/coctail-recipy-finder/data/cocktail_index.db \
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## systemd Services

```bash
sudo cp deploy/cocktail-index.service /etc/systemd/system/cocktail-index.service
sudo cp deploy/cocktail-index-sync.service /etc/systemd/system/cocktail-index-sync.service
sudo cp deploy/cocktail-index-sync.timer /etc/systemd/system/cocktail-index-sync.timer
sudo systemctl daemon-reload
sudo systemctl enable --now cocktail-index.service
sudo systemctl enable --now cocktail-index-sync.timer
```

## Verification

```bash
systemctl status cocktail-index.service --no-pager
systemctl list-timers cocktail-index-sync.timer --no-pager
curl -fsS http://127.0.0.1:8000/
```

## Rollback

```bash
sudo systemctl disable --now cocktail-index.service
sudo systemctl disable --now cocktail-index-sync.timer
sudo rm -f /etc/systemd/system/cocktail-index.service
sudo rm -f /etc/systemd/system/cocktail-index-sync.service
sudo rm -f /etc/systemd/system/cocktail-index-sync.timer
sudo systemctl daemon-reload
```
