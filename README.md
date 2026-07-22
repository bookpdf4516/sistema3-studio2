# Sistema 3 — Studio 2

Applicazione Streamlit per lo Studio 2 sul Sistema 3 come filtro organizzativo dell'influenza algoritmica.

## Struttura

- `app.py`: applicazione Streamlit.
- `requirements.txt`: dipendenze Python.
- `AVVIA_STUDIO2.bat`: avvio locale su Windows.
- `secrets.example.toml`: esempio privo di credenziali reali.
- `docs/`: articolo teorico in LaTeX e PDF.

## Avvio locale

Installare le dipendenze:

```bash
py -m pip install -r requirements.txt
```

Avviare l'app:

```bash
py -m streamlit run app.py
```

Oppure, su Windows, fare doppio clic su `AVVIA_STUDIO2.bat`.

## Credenziali locali

Creare il file `.streamlit/secrets.toml` copiando la struttura di `secrets.example.toml` e inserendo le credenziali reali. Il file è escluso da Git mediante `.gitignore` e non deve essere caricato nel repository.

## Distribuzione su Streamlit Community Cloud

Selezionare il repository, il branch `main` e il file `app.py`. Inserire le credenziali nella sezione **Secrets** delle impostazioni dell'app, non su GitHub.

## Persistenza dei dati

L'app crea SQLite, CSV ed Excel nella directory `studio2_data`. Questo è adatto all'esecuzione locale. Su Streamlit Community Cloud la persistenza del file system locale non è garantita; per una raccolta definitiva è consigliato un database esterno persistente.
