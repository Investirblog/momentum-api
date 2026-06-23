# Momentum ETF Screener — API Backend

FastAPI + yfinance · Déployé sur Render.com (gratuit)

---

## Déploiement sur Render (à faire une seule fois)

### Étape 1 — Créer le repo GitHub

```bash
cd ~/Bureau/marketfighter
mkdir momentum-api && cd momentum-api
# Copie les 3 fichiers : main.py, requirements.txt, render.yaml
git init
git add .
git commit -m "Initial momentum API"
```

Sur github.com → New repository → nom : `momentum-api` → Create
```bash
git remote add origin https://github.com/TON_USERNAME/momentum-api.git
git branch -M main
git push -u origin main
```

### Étape 2 — Créer le service sur Render

1. Va sur **render.com** → Sign up with GitHub
2. Dashboard → **New +** → **Web Service**
3. Connecte ton repo `momentum-api`
4. Render détecte automatiquement Python
5. Vérifie ces paramètres :
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan** : Free
6. Clique **Deploy Web Service**
7. Attends 2-3 minutes → tu obtiens une URL :
   `https://momentum-api.onrender.com`

### Étape 3 — Tester l'API

Ouvre dans ton navigateur :
```
https://momentum-api.onrender.com/api/momentum
```
Tu dois voir du JSON avec les 14 ETF et leurs scores.

### Étape 4 — Mettre à jour le HTML

Dans `momentum-screener.html`, remplace la ligne :
```javascript
const API_URL = 'LOCAL'; // mode CSV local
```
par :
```javascript
const API_URL = 'https://momentum-api.onrender.com';
```

---

## Notes importantes

- **Cold start** : Le service s'endort après 15 min d'inactivité.
  Le premier chargement peut prendre 30-60 secondes.
- **Cache** : Les données sont mises en cache 6h côté serveur.
  Si deux lecteurs chargent dans la même heure, le deuxième est instantané.
- **Forcer le recalcul** : `/api/momentum?force=true`

---

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Status de l'API |
| `GET /health` | Health check (Render + UptimeRobot) |
| `GET /api/momentum` | Scores momentum 14 ETF (cache 6h) |
| `GET /api/momentum?force=true` | Recalcul forcé |
