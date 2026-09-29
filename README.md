# Suivi de portefeuille
1. Crée un dépôt GitHub, dépose ces fichiers.
2. `holdings.csv` : remplis les tickers Yahoo Finance (colonne ticker, ex. DCAM.PA) et la vraie date d'achat. Les lignes dont le ticker commence par ? sont ignorées.
3. Onglet Actions : lance « Mise à jour nocturne » une première fois (Run workflow).
4. Settings > Pages : source = branche main, dossier /docs.
5. Confidentialité : GitHub Pages est public. Pour protéger, utilise Cloudflare Pages + Cloudflare Access.
Test local : pip install yfinance pandas && python update.py && python -m http.server -d docs
