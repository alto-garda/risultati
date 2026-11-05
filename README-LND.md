# Import automatico Gare LND – Attività di Base

Le quattro pagine Attività di Base leggono i calendari dai file `data/*.json`.

## Aggiornamento automatico
- Workflow: `.github/workflows/aggiorna-lnd.yml`
- Script: `scripts/update_lnd.py`
- Fonte: portale pubblico `gare.lnd.it`, stagione 2026/2027, solo girone di andata.
- Frequenza: ogni giorno alle 01:00 UTC (02:00 in Italia con ora solare; 03:00 con ora legale), oltre all'avvio manuale da GitHub Actions.
- I file vengono sostituiti solo dopo una risposta con un numero minimo di appuntamenti; se una competizione non risponde, il relativo JSON già presente viene conservato.

## Attivazione dopo il caricamento
1. Caricare l'intera cartella del progetto nel repository `alto-garda/risultati` (non in `AGInside`).
2. In GitHub aprire **Actions** e abilitare i workflow, se richiesto.
3. Selezionare **Aggiorna calendari LND** e premere **Run workflow** per il primo import.
4. Controllare il riepilogo del run: deve riportare le quattro competizioni senza errori.

Il file `data/pulcini-u10.json` contiene il calendario completo già fornito come base iniziale. Gli altri tre file vengono popolati al primo run riuscito. La pagina non mostra i punteggi, in coerenza con l'avviso Attività di Base già approvato.
