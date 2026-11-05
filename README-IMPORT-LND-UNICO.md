# Aggiornamento unico – Attività di Base ASD Alto Garda

Caricare il contenuto di questo ZIP nella radice del repository `alto-garda/risultati`, sovrascrivendo i file omonimi. Non contiene i JSON: i calendari già importati non vengono sovrascritti.

## File inclusi
- `scripts/update_lnd.py`: importatore comune per le quattro categorie. Scarta i turni di riposo delle avversarie e conserva un riposo solo se la riga LND identifica Alto Garda senza avversario. La stessa regola vale per ogni giornata e per entrambe le fasi.
- `assets/base-lnd.js` e le quattro pagine: visualizzazione già concordata, badge aggiornamento e calendari separati Blu/Nera per U11.
- `.github/workflows/aggiorna-lnd.yml`: aggiornamento giornaliero e avvio manuale; all'avvio manuale consente di scegliere `first` (andata) o `second` (ritorno).

## Orario
Cron alle 01:00 UTC: 02:00 in Italia durante l'ora solare e 03:00 durante l'ora legale. GitHub può avviare il job con ritardo.
