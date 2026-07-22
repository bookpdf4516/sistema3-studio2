"""
Studio 2 — Sistema 3 come filtro selettivo della resa cognitiva
================================================================

Questionario sperimentale Streamlit con:
- 90 partecipanti, 10 team da 9;
- tre domini assegnati per team secondo schema 4-3-3;
- tre qualità di output LLM controbilanciate entro ciascun team;
- misure P, G, H, convergenza C, affidamento appropriato AR,
  resa cognitiva CS e flessibilità direzionale F;
- ABM e Monte Carlo nel back office;
- esportazione CSV/Excel, grafici PNG ed email opzionale.

NOTA METODOLOGICA
I benchmark e gli output non calibrati inclusi qui sono una versione
operativa preliminare. Prima della raccolta definitiva devono essere
validati da un panel indipendente di esperti.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import smtplib
import sqlite3
import uuid
from collections import OrderedDict
from datetime import datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Iterable

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import streamlit as st


def _ensure_streamlit_runtime() -> None:
    """Avvia automaticamente Streamlit quando il file è eseguito come Python normale."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        try:
            ctx = get_script_run_ctx(suppress_warning=True)
        except TypeError:
            # Compatibilità con versioni Streamlit meno recenti.
            ctx = get_script_run_ctx()
        in_streamlit = ctx is not None
    except Exception:
        in_streamlit = False

    if in_streamlit:
        return

    script_path = Path(__file__).resolve()
    print("\nAvvio dell'applicazione Streamlit nel browser...")
    print(f"Comando: {sys.executable} -m streamlit run \"{script_path}\"\n")

    env = os.environ.copy()
    env["STUDIO2_AUTOLAUNCH"] = "1"

    try:
        completed = subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(script_path)],
            env=env,
            check=False,
        )
        raise SystemExit(completed.returncode)
    except KeyboardInterrupt:
        raise SystemExit(0)
    except Exception as exc:
        print("Impossibile avviare Streamlit automaticamente.")
        print(f"Errore: {exc}")
        print("Esegui manualmente: python -m streamlit run studio2_script_teorico_operativo_avvio_corretto.py")
        raise SystemExit(1)


_ensure_streamlit_runtime()


st.set_page_config(
    page_title="Questionario Sistema 3 — Studio 2",
    page_icon="🧠",
    layout="wide",
)

# ============================================================
# CONFIGURAZIONE GENERALE
# ============================================================

APP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = Path(os.getenv("STUDIO2_OUTPUT_DIR", APP_DIR / "studio2_data"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = OUTPUT_DIR / "studio2_risposte.sqlite"
CSV_RESPONSES = OUTPUT_DIR / "studio2_risposte.csv"
EXCEL_RESPONSES = OUTPUT_DIR / "studio2_risposte.xlsx"

MAX_P = 90
TEAM_SIZE = 9
N_TEAMS = MAX_P // TEAM_SIZE
BASE_SEED = 2026
RESERVATION_HOURS = 4

# Parametri rapidi predefiniti. Nel back office sono modificabili.
DEFAULT_N_SYNTH = 20
DEFAULT_N_MC = 75

try:
    ADMIN_PWD = str(st.secrets.get("admin_password", "sasa"))
except Exception:
    ADMIN_PWD = "sasa"

DOMINI = {
    "A": "Infrastrutture critiche tecnologiche",
    "B": "Criminalità organizzata transnazionale",
    "C": "Sicurezza economica e acquisizioni strategiche",
}

# Dieci team omogenei: 4 nel dominio A, 3 nel B, 3 nel C.
TEAM_DOMAIN_ORDER = ["A", "A", "A", "A", "B", "B", "B", "C", "C", "C"]

# L'ordine narrativo resta fisso. Si controbilancia la qualità dell'LLM,
# non la sequenza temporale dei briefing.
CONDIZIONI = ["T1", "T2", "T3"]
COND_LABEL = {
    "T1": "Configurazione α — Sessione analitica ordinaria",
    "T2": "Configurazione β — Sessione analitica straordinaria",
    "T3": "Configurazione γ — Sessione analitica di crisi",
}
COND_CONTESTO = {
    "T1": (
        "**Configurazione α** — Il team opera in condizioni standard. "
        "Non è richiesta una decisione operativa immediata."
    ),
    "T2": (
        "**Configurazione β** — Il quadro informativo si è evoluto. "
        "Il tempo di analisi è ridotto e la sintesi è richiesta con urgenza."
    ),
    "T3": (
        "**Configurazione γ** — Il quadro richiede una valutazione immediata. "
        "La decisione deve essere formulata prima del completamento di tutte le verifiche."
    ),
}

DOMANDA = {
    "A": (
        "Gli elementi disponibili costituiscono evidenza di una minaccia operativa "
        "alle infrastrutture critiche che richieda l'attivazione immediata delle "
        "misure di protezione?"
    ),
    "B": (
        "Gli elementi disponibili costituiscono evidenza sufficiente per avviare "
        "un'indagine formale coordinata con attivazione delle misure di contrasto?"
    ),
    "C": (
        "Gli elementi disponibili costituiscono evidenza di un'operazione di "
        "acquisizione ostile che richieda l'attivazione della procedura di golden power?"
    ),
}

BRIEFING = {'A': {'T1': '**BRIEFING OPERATIVO — RISERVATO**\n'
             '\n'
             '---\n'
             '\n'
             '**Contesto operativo.** I sistemi di supervisione di una rete di distribuzione\n'
             "energetica in un'area portuale del nord Italia hanno registrato anomalie nei\n"
             'log di accesso nelle ultime settimane. Il personale tecnico ha segnalato\n'
             'interrogazioni non autorizzate a sottosistemi di controllo remoto.\n'
             '\n'
             "**Fonte primaria.** Una fonte HUMINT con accesso tecnico all'impianto riferisce\n"
             'di aver osservato connessioni da indirizzi IP non censiti nel registro degli\n'
             "accessi autorizzati. L'attendibilità della fonte è parziale — non è possibile\n"
             'escludere un errore di configurazione tecnica.\n'
             '\n'
             '**Elemento di corroborazione.** Monitoraggio OSINT rileva discussioni su forum\n'
             'specializzati relativi a vulnerabilità nei protocolli SCADA utilizzati\n'
             "dall'impianto. La diffusione di queste informazioni potrebbe essere casuale\n"
             'o preparatoria.\n'
             '\n'
             "**Elemento anomalo.** L'impianto ha recentemente completato un ciclo di\n"
             'penetration test autorizzato da parte di una società esterna. Le anomalie\n'
             'nei log potrebbero essere residui di tale attività non correttamente\n'
             'documentati.\n'
             '\n'
             '**Lacuna informativa.** Non è disponibile il report finale del penetration test.\n'
             'La società incaricata non ha ancora trasmesso la documentazione completa.\n'
             '\n'
             '**Fonti:** HUMINT (attendibilità parziale), OSINT (verificata), tecnica (in '
             'analisi).\n'
             '\n'
             '---',
       'T2': '**BRIEFING OPERATIVO — RISERVATO**\n'
             '\n'
             '---\n'
             '\n'
             '**Contesto operativo.** Le anomalie precedentemente segnalate sui sistemi\n'
             "di supervisione dell'area portuale si sono intensificate. Si registrano\n"
             'ora tentativi di accesso a sottosistemi critici che controllano la\n'
             'distribuzione verso utenze industriali strategiche.\n'
             '\n'
             "**Fonte primaria.** Due fonti HUMINT indipendenti — una interna all'impianto\n"
             "e una esterna con accesso al settore — confermano l'esistenza di tentativi\n"
             'sistematici non riconducibili al penetration test autorizzato. La società\n'
             'incaricata del test ha nel frattempo trasmesso il proprio report, che non\n'
             'documenta le anomalie rilevate.\n'
             '\n'
             '**Elemento di corroborazione.** Intercettazione SIGINT di comunicazioni\n'
             'cifrate tra soggetti non identificati con riferimenti a termini tecnici\n'
             "specifici dell'impianto. Il contenuto non è stato completamente decifrato.\n"
             '\n'
             "**Elemento anomalo.** Un ex dipendente dell'impianto, congedato sei mesi\n"
             'fa per ragioni disciplinari, risulta aver contattato recentemente uno\n'
             'dei soggetti nelle comunicazioni SIGINT. Il collegamento potrebbe essere\n'
             'casuale o indicare un vettore interno.\n'
             '\n'
             "**Lacuna informativa.** L'identità dei soggetti nelle comunicazioni SIGINT\n"
             'non è stata ancora stabilita. Non è chiaro se agiscano per conto proprio\n'
             'o per conto di terzi.\n'
             '\n'
             '**Fonti:** HUMINT (verificata), SIGINT (parzialmente decifrata), OSINT '
             '(verificata).\n'
             '\n'
             '---',
       'T3': '**BRIEFING OPERATIVO — RISERVATO**\n'
             '\n'
             '---\n'
             '\n'
             '**Contesto operativo.** Nelle ultime ore la situazione si è deteriorata\n'
             "significativamente. Si registra un'interruzione parziale dei sistemi di\n"
             "supervisione dell'impianto portuale. Il gestore ha dichiarato uno stato\n"
             'di allerta interno. Non si registrano conseguenze operative immediate\n'
             'sulla distribuzione energetica.\n'
             '\n'
             '**Fonte primaria.** Fonte HUMINT ad alta attendibilità riferisce che\n'
             "l'interruzione è stata causata da un codice malevolo introdotto attraverso\n"
             'un vettore di accesso remoto. Il codice presenta caratteristiche coerenti\n'
             'con strumenti utilizzati da gruppi APT (Advanced Persistent Threat) noti.\n'
             '\n'
             '**Elemento di corroborazione.** Analisi tecnica preliminare del codice\n'
             'malevolo rileva componenti già osservati in attacchi a infrastrutture\n'
             "energetiche in altri Paesi europei negli ultimi diciotto mesi. L'attribuzione\n"
             'formale richiede ulteriori verifiche.\n'
             '\n'
             "**Elemento anomalo.** L'interruzione ha colpito esclusivamente i sistemi\n"
             'di supervisione, lasciando intatti i sistemi di controllo operativo.\n'
             'Questo potrebbe indicare un obiettivo di ricognizione piuttosto che\n'
             "di sabotaggio, oppure una fase preparatoria di un'azione più ampia.\n"
             '\n'
             '**Lacuna informativa.** Non è ancora noto se il codice malevolo sia ancora\n'
             "attivo in altri sottosistemi non ancora analizzati. L'analisi forense\n"
             'completa richiede tempi non compatibili con la necessità di una risposta\n'
             'operativa immediata.\n'
             '\n'
             '**Fonti:** HUMINT (alta attendibilità), tecnica (in analisi), comparativa '
             '(verificata).\n'
             '\n'
             '---'},
 'B': {'T1': '**BRIEFING OPERATIVO — RISERVATO**\n'
             '\n'
             '---\n'
             '\n'
             '**Contesto operativo.** La Financial Intelligence Unit ha trasmesso una\n'
             'segnalazione relativa a movimenti finanziari anomali attraverso una catena\n'
             "di società schermo in tre giurisdizioni diverse nell'arco degli ultimi\n"
             'quattro mesi. I movimenti complessivi ammontano a cifre significative\n'
             'con struttura frammentata caratteristica del layering.\n'
             '\n'
             '**Fonte primaria.** Analisi della segnalazione FIU evidenzia che le società\n'
             'terminali della catena hanno effettuato acquisti di materiale elettronico\n'
             'classificabile come dual-use attraverso intermediari in un Paese terzo\n'
             "non soggetto a regime di controllo all'esportazione.\n"
             '\n'
             '**Elemento di corroborazione.** Uno degli intestatari delle società schermo\n'
             'risulta citato in un procedimento penale per riciclaggio conclusosi tre\n'
             'anni fa con patteggiamento. Non emergono collegamenti diretti con\n'
             'organizzazioni criminali strutturate.\n'
             '\n'
             '**Elemento anomalo.** Uno degli altri intestatari è un collaboratore di\n'
             'giustizia con protezione attiva sotto falsa identità. Non è chiaro se\n'
             'la sua presenza nella struttura societaria sia una coincidenza, un errore\n'
             'operativo della protezione o un elemento intenzionale.\n'
             '\n'
             "**Lacuna informativa.** Non è disponibile l'analisi del destinatario finale\n"
             'del materiale dual-use. Non è noto se il materiale sia già stato consegnato.\n'
             '\n'
             '**Fonti:** FIU (verificata), anagrafica (verificata), giudiziaria (verificata).\n'
             '\n'
             '---',
       'T2': '**BRIEFING OPERATIVO — RISERVATO**\n'
             '\n'
             '---\n'
             '\n'
             '**Contesto operativo.** Sviluppi investigativi nelle ultime settimane hanno\n'
             'arricchito il quadro informativo sulla struttura societaria precedentemente\n'
             'segnalata. Sono emersi ulteriori livelli della catena di intermediazione\n'
             'e nuovi soggetti non precedentemente identificati.\n'
             '\n'
             '**Fonte primaria.** Una fonte HUMINT con accesso alla struttura criminale\n'
             'riferisce che il materiale dual-use è destinato a un soggetto in un Paese\n'
             'sotto embargo internazionale. Il transito avviene attraverso un Paese terzo\n'
             'con regime doganale permissivo. La fonte chiede protezione in cambio della\n'
             'collaborazione — la sua attendibilità non è ancora stata valutata.\n'
             '\n'
             '**Elemento di corroborazione.** Intercettazione di comunicazioni tra due\n'
             'degli intestatari contiene riferimenti a tempistiche di consegna e a\n'
             'un committente indicato con un nome in codice non ancora decifrato.\n'
             'Il tenore delle comunicazioni è coerente con una transazione commerciale\n'
             'illecita internazionale.\n'
             '\n'
             '**Elemento anomalo.** Il collaboratore di giustizia precedentemente\n'
             'identificato risulta aver contattato il proprio referente nella struttura\n'
             'di protezione nelle stesse ore delle comunicazioni intercettate. Non è\n'
             'chiaro se stia operando autonomamente o se la struttura di protezione\n'
             'sia consapevole della sua partecipazione.\n'
             '\n'
             "**Lacuna informativa.** L'identità del committente finale rimane sconosciuta.\n"
             'Non è chiaro il ruolo del collaboratore di giustizia — vittima, complice\n'
             'o agente infiltrato non dichiarato.\n'
             '\n'
             '**Fonti:** HUMINT (attendibilità non verificata), SIGINT (verificata), FIU '
             '(verificata).\n'
             '\n'
             '---',
       'T3': '**BRIEFING OPERATIVO — RISERVATO**\n'
             '\n'
             '---\n'
             '\n'
             "**Contesto operativo.** Il quadro investigativo ha subito un'evoluzione\n"
             'critica. La fonte HUMINT ha fornito documentazione che consente di\n'
             'identificare il committente finale come un ente parastatale di un Paese\n'
             'sotto embargo. La consegna del materiale dual-use è imminente — entro\n'
             'quarantotto ore secondo le informazioni disponibili.\n'
             '\n'
             '**Fonte primaria.** La fonte HUMINT — la cui attendibilità è stata nel\n'
             'frattempo parzialmente verificata attraverso riscontri indipendenti —\n'
             'indica il porto di transito e le generalità del trasportatore. I tempi\n'
             'non consentono di attendere la verifica completa.\n'
             '\n'
             '**Elemento di corroborazione.** Analisi finanziaria aggiornata rivela\n'
             'un bonifico in uscita dalle società schermo verso il conto del\n'
             "trasportatore effettuato nelle ultime ventiquattro ore. L'importo è\n"
             'coerente con le tariffe di trasporto internazionale del tipo di materiale\n'
             'indicato.\n'
             '\n'
             '**Elemento anomalo.** Il collaboratore di giustizia è scomparso dal\n'
             'proprio domicilio protetto nelle ultime dodici ore. Il referente nella\n'
             'struttura di protezione sostiene di non essere a conoscenza della sua\n'
             'localizzazione attuale. Non è chiaro se sia in pericolo, se abbia\n'
             'abbandonato la protezione volontariamente o se stia operando su mandato\n'
             'non dichiarato.\n'
             '\n'
             '**Lacuna informativa.** Il contenuto esatto del materiale da consegnare\n'
             'non è stato ancora verificato fisicamente. La fonte indica "componenti\n'
             'elettronici avanzati" senza ulteriori dettagli tecnici.\n'
             '\n'
             '**Fonti:** HUMINT (parzialmente verificata), finanziaria (verificata), operativa (in '
             'corso).\n'
             '\n'
             '---'},
 'C': {'T1': '**BRIEFING OPERATIVO — RISERVATO**\n'
             '\n'
             '---\n'
             '\n'
             "**Contesto operativo.** Analisi OSINT finanziaria condotta nell'ambito\n"
             'del monitoraggio degli investimenti esteri in settori sensibili ha\n'
             "identificato l'acquisizione di partecipazioni minoritarie in quattro\n"
             'aziende italiane ad alta tecnologia da parte di un fondo sovrano estero\n'
             'attraverso veicoli societari in cascata in tre giurisdizioni.\n'
             '\n'
             "**Fonte primaria.** L'analisi delle strutture societarie intermedie\n"
             'rivela che il fondo sovrano non compare direttamente in nessuna delle\n'
             'operazioni. La titolarità effettiva è stata ricostruita attraverso\n'
             "l'analisi dei beneficiari finali dichiarati nei registri societari\n"
             'delle giurisdizioni coinvolte.\n'
             '\n'
             '**Elemento di corroborazione.** Due delle quattro aziende target hanno\n'
             'recentemente ottenuto contratti con la difesa nazionale per la fornitura\n'
             'di componenti in settori ad alta sensibilità tecnologica. Le altre due\n'
             'operano in settori di interesse strategico non direttamente connessi\n'
             'alla difesa.\n'
             '\n'
             '**Elemento anomalo.** Le acquisizioni sono avvenute in quattro momenti\n'
             "distinti nell'arco di diciotto mesi con importi appena al di sotto\n"
             'delle soglie che avrebbero attivato la notifica obbligatoria al Comitato\n'
             "di coordinamento per le politiche di controllo dell'esportazione.\n"
             'Questa frammentazione potrebbe essere casuale o deliberata.\n'
             '\n'
             "**Lacuna informativa.** Non è disponibile l'analisi delle clausole\n"
             'contrattuali delle acquisizioni — in particolare eventuali diritti\n'
             'di accesso a informazioni tecniche riservate.\n'
             '\n'
             '**Fonti:** OSINT finanziaria (verificata), registri societari (verificati), '
             'contrattuale (non disponibile).\n'
             '\n'
             '---',
       'T2': '**BRIEFING OPERATIVO — RISERVATO**\n'
             '\n'
             '---\n'
             '\n'
             "**Contesto operativo.** L'analisi delle acquisizioni precedentemente\n"
             'segnalate ha prodotto elementi aggiuntivi che modificano il quadro\n'
             'valutativo. Sono emersi contatti tra i rappresentanti del fondo sovrano\n'
             'e personale tecnico delle aziende target che vanno oltre la normale\n'
             'relazione investitore-partecipata.\n'
             '\n'
             '**Fonte primaria.** Una fonte HUMINT con accesso a una delle aziende\n'
             'target riferisce che rappresentanti del fondo hanno richiesto\n'
             'documentazione tecnica non prevista dagli accordi di investimento,\n'
             'inclusi brevetti in fase di registrazione e specifiche di prodotto\n'
             'non pubbliche. La richiesta è stata parzialmente evasa prima che\n'
             'la direzione aziendale ne venisse informata.\n'
             '\n'
             '**Elemento di corroborazione.** Analisi dei flussi di comunicazione\n'
             'digitale tra le aziende target e indirizzi riconducibili al fondo\n'
             'sovrano rivela un volume di scambi significativamente superiore a\n'
             'quello atteso per una partecipazione minoritaria di natura finanziaria.\n'
             '\n'
             '**Elemento anomalo.** Uno dei rappresentanti del fondo risulta aver\n'
             "ricoperto in passato un incarico in un'agenzia di intelligence del\n"
             'Paese di riferimento. Il profilo LinkedIn è stato modificato\n'
             'rimuovendo questo elemento nelle ultime settimane.\n'
             '\n'
             '**Lacuna informativa.** Non è noto se la documentazione tecnica\n'
             'trasferita includa informazioni coperte da segreto industriale\n'
             'rilevante ai fini della sicurezza nazionale. La valutazione richiede\n'
             "competenze tecniche settoriali non disponibili nell'unità.\n"
             '\n'
             '**Fonti:** HUMINT (attendibilità parziale), SIGINT (verificata), OSINT '
             '(verificata).\n'
             '\n'
             '---',
       'T3': '**BRIEFING OPERATIVO — RISERVATO**\n'
             '\n'
             '---\n'
             '\n'
             '**Contesto operativo.** Il quadro si è evoluto in modo significativo.\n'
             'Una quinta azienda italiana — operante in un settore direttamente\n'
             'connesso a sistemi di comunicazione militare — risulta oggetto di\n'
             "un'offerta di acquisizione da parte di una società riconducibile\n"
             "alla stessa catena del fondo sovrano. L'offerta è stata presentata\n"
             'quarantotto ore fa e richiede risposta entro tempi brevi.\n'
             '\n'
             '**Fonte primaria.** Fonte HUMINT ad alta attendibilità con accesso\n'
             "alle strutture decisionali del fondo sovrano riferisce che l'obiettivo\n"
             "strategico dell'operazione complessiva è l'accesso a tecnologie\n"
             "proprietarie in tre settori specifici. L'acquisizione della quinta\n"
             "azienda è descritta come l'elemento conclusivo di un piano strutturato\n"
             'nel tempo.\n'
             '\n'
             '**Elemento di corroborazione.** Analisi comparativa con operazioni\n'
             'analoghe condotte dallo stesso fondo sovrano in altri Paesi europei\n'
             "nell'ultimo decennio mostra un pattern coerente: acquisizioni\n"
             'frammentate sotto soglia, seguita da trasferimento progressivo di\n'
             'know-how, conclusa con acquisizione di controllo o dismissione\n'
             "dell'investimento dopo l'estrazione delle informazioni rilevanti.\n"
             '\n'
             '**Elemento anomalo.** Il consiglio di amministrazione della quinta\n'
             "azienda ha espresso disponibilità all'operazione, nonostante la\n"
             'valutazione offerta sia inferiore alle stime di mercato. Non è\n'
             'chiaro se questa disponibilità rifletta difficoltà finanziarie\n'
             "dell'azienda, pressioni esterne non dichiarate o accordi paralleli\n"
             'non documentati.\n'
             '\n'
             "**Lacuna informativa.** Non è disponibile la valutazione dell'impatto\n"
             "dell'acquisizione sulla sicurezza dei contratti con la difesa nazionale\n"
             'già in essere. Il Comitato competente non è ancora stato formalmente\n'
             'attivato.\n'
             '\n'
             '**Fonti:** HUMINT (alta attendibilità), comparativa (verificata), finanziaria '
             '(verificata).\n'
             '\n'
             '---'}}

# ============================================================
# CONTROBILANCIAMENTO DELLA QUALITÀ LLM
# ============================================================

QUALITA = ["calibrato", "sovrastimante", "sottostimante"]
SEQUENZE_QUALITA = {
    "S1": {"T1": "calibrato", "T2": "sovrastimante", "T3": "sottostimante"},
    "S2": {"T1": "sottostimante", "T2": "calibrato", "T3": "sovrastimante"},
    "S3": {"T1": "sovrastimante", "T2": "sottostimante", "T3": "calibrato"},
}

# Benchmark preliminari da validare con panel di esperti.
EXPERT_BENCHMARK = {
    "A": {"T1": 35, "T2": 68, "T3": 88},
    "B": {"T1": 40, "T2": 67, "T3": 90},
    "C": {"T1": 45, "T2": 72, "T3": 90},
}
QUALITY_SHIFT = {"calibrato": 0, "sovrastimante": 20, "sottostimante": -20}

SCALA_ORDINALE = [
    "— seleziona —",
    "No — nessuna evidenza",
    "Probabilmente no — segnali deboli",
    "Incerto — elementi contrastanti",
    "Probabilmente sì — convergenza significativa",
    "Sì — evidenza solida",
]
ORDINAL_SCORE = {
    "No — nessuna evidenza": 1,
    "Probabilmente no — segnali deboli": 2,
    "Incerto — elementi contrastanti": 3,
    "Probabilmente sì — convergenza significativa": 4,
    "Sì — evidenza solida": 5,
}

AREE_OPERATIVE = ["Intelligence / sicurezza", "Investigativa / law enforcement"]
AREE_CIVILI = [
    "Cyber / tecnologia",
    "Economico-finanziaria",
    "OSINT / analisi fonti aperte",
    "Accademica / ricerca",
    "Linguistica / area studies",
]
ROLE_INFLUENCE = {
    "Team Leader": 1.00,
    "Analista Senior": 0.70,
    "Analista Junior": 0.45,
    "Analista Civile": 0.55,
}

# Indicatori: 1=basso, 2=medio, 3=elevato. Il tipo "support" sostiene
# la minaccia; "caution" rappresenta spiegazioni alternative o lacune.
INDICATORI_BASE = {
    "A": {
        "T1": [
            ("Anomalie nei log di accesso", 2, "support"),
            ("Discussioni OSINT su vulnerabilità SCADA", 1, "support"),
            ("Possibile spiegazione alternativa: penetration test", 3, "caution"),
        ],
        "T2": [
            ("Due fonti HUMINT indipendenti", 3, "support"),
            ("Comunicazioni SIGINT con riferimenti tecnici", 2, "support"),
            ("Identità e attribuzione dei soggetti non definite", 2, "caution"),
        ],
        "T3": [
            ("Codice malevolo e interruzione dei sistemi", 3, "support"),
            ("Componenti coerenti con precedenti attacchi APT", 3, "support"),
            ("Finalità ancora incerta: ricognizione o sabotaggio", 2, "caution"),
        ],
    },
    "B": {
        "T1": [
            ("Layering attraverso società schermo", 2, "support"),
            ("Acquisti di componenti dual-use", 2, "support"),
            ("Destinatario finale e ruolo degli intestatari non definiti", 3, "caution"),
        ],
        "T2": [
            ("Indicazione HUMINT di destinazione sotto embargo", 2, "support"),
            ("Comunicazioni coerenti con transazione illecita", 2, "support"),
            ("Attendibilità della fonte e ruolo del collaboratore incerti", 3, "caution"),
        ],
        "T3": [
            ("Committente parastatale sotto embargo identificato", 3, "support"),
            ("Consegna imminente e pagamento al trasportatore", 3, "support"),
            ("Contenuto materiale non verificato fisicamente", 2, "caution"),
        ],
    },
    "C": {
        "T1": [
            ("Acquisizioni ripetute appena sotto soglia", 2, "support"),
            ("Presenza di imprese con contratti della difesa", 2, "support"),
            ("Clausole di accesso tecnico non disponibili", 3, "caution"),
        ],
        "T2": [
            ("Richieste di documentazione tecnica non prevista", 3, "support"),
            ("Volume anomalo di comunicazioni e trasferimenti", 2, "support"),
            ("Rilevanza di sicurezza del materiale non ancora qualificata", 2, "caution"),
        ],
        "T3": [
            ("Offerta su impresa di comunicazioni militari", 3, "support"),
            ("Fonte HUMINT e pattern comparativo convergenti", 3, "support"),
            ("Impatto sui contratti della difesa non ancora stimato", 2, "caution"),
        ],
    },
}

OUTPUT_COMPONENTS = {
    "A": {
        "T1": {
            "evidence": (
                "Le anomalie tecniche e le discussioni sulle vulnerabilità indicano un possibile "
                "interesse ostile verso l'impianto, ma nessun evento operativo è stato ancora verificato."
            ),
            "gap": (
                "Il report del penetration test non è disponibile e offre una spiegazione alternativa "
                "plausibile per almeno una parte delle anomalie."
            ),
            "cal": "Sono giustificati acquisizione urgente del report e monitoraggio rafforzato, non l'attivazione piena delle misure operative.",
            "over": "La convergenza degli indicatori deve essere trattata come preparazione ostile; è opportuno attivare immediatamente le misure di protezione.",
            "under": "Gli elementi restano compatibili con normali anomalie tecniche; è sufficiente attendere la documentazione del penetration test senza modificare l'assetto operativo.",
        },
        "T2": {
            "evidence": (
                "Le fonti HUMINT convergono e il report del penetration test non spiega gli accessi; "
                "le comunicazioni SIGINT rafforzano l'ipotesi di un'attività intenzionale."
            ),
            "gap": (
                "L'identità, l'affiliazione e la finalità dei soggetti restano non attribuite."
            ),
            "cal": "Il quadro giustifica misure di contenimento tecnico immediate e un innalzamento selettivo della protezione, mentre l'attribuzione procede in parallelo.",
            "over": "La combinazione HUMINT-SIGINT dimostra una campagna coordinata già operativa; è necessario attivare il massimo livello di protezione e risposta.",
            "under": "In assenza di attribuzione certa non vi sono basi sufficienti per misure operative; il monitoraggio ordinario può proseguire fino all'identificazione dei soggetti.",
        },
        "T3": {
            "evidence": (
                "Un codice malevolo ha già prodotto un'interruzione e presenta componenti coerenti con precedenti attacchi contro infrastrutture energetiche."
            ),
            "gap": (
                "Non è ancora definito se la finalità sia ricognitiva o distruttiva e l'attribuzione resta preliminare."
            ),
            "cal": "Gli elementi sono sufficienti per attivare misure immediate di protezione e risposta, mantenendo separata la successiva attribuzione dell'attacco.",
            "over": "L'evento costituisce un sabotaggio strategico attribuibile a un attore APT; occorre attivare senza ritardo tutte le misure di crisi e risposta esterna.",
            "under": "Poiché i sistemi operativi non sono stati colpiti e l'attribuzione è incompleta, l'evento può essere gestito come anomalia di supervisione senza escalation immediata.",
        },
    },
    "B": {
        "T1": {
            "evidence": (
                "La struttura finanziaria presenta caratteristiche di layering e gli acquisti dual-use meritano approfondimento."
            ),
            "gap": (
                "Non sono noti il destinatario finale, la consegna effettiva e il significato della presenza del collaboratore di giustizia."
            ),
            "cal": "Il quadro richiede approfondimenti urgenti e conservazione degli elementi, ma non consente ancora di qualificare una struttura criminale coordinata.",
            "over": "La combinazione tra layering, dual-use e precedenti giudiziari indica una rete criminale strutturata; l'indagine formale e le misure di contrasto devono iniziare subito.",
            "under": "La segnalazione rientra nei normali pattern FIU e non presenta elementi sufficienti per ulteriori iniziative oltre alla verifica amministrativa di routine.",
        },
        "T2": {
            "evidence": (
                "La destinazione indicata in un Paese sotto embargo e le comunicazioni intercettate sono coerenti con una possibile transazione illecita internazionale."
            ),
            "gap": (
                "L'attendibilità della fonte HUMINT non è verificata, il committente non è identificato e il ruolo del collaboratore resta ambiguo."
            ),
            "cal": "Gli elementi consentono l'apertura di un'indagine coordinata e misure investigative urgenti, senza assumere come dimostrata l'identità del committente.",
            "over": "Le informazioni dimostrano un traffico internazionale già in corso e impongono il blocco immediato della transazione e l'arresto dei soggetti individuati.",
            "under": "Le dichiarazioni di una fonte interessata e le comunicazioni ambigue non superano la soglia del sospetto; non è ancora opportuno avviare un'indagine formale.",
        },
        "T3": {
            "evidence": (
                "Il committente sotto embargo, il porto di transito, il trasportatore e il pagamento sono stati identificati, mentre la consegna è imminente."
            ),
            "gap": (
                "Il contenuto materiale non è stato verificato fisicamente e la posizione del collaboratore di giustizia resta incerta."
            ),
            "cal": "Le misure di contrasto devono essere attivate immediatamente; le incertezze residue riguardano la gestione operativa, non la necessità dell'intervento.",
            "over": "Il quadro prova una struttura criminale-statuale pienamente definita e autorizza un intervento coercitivo esteso su tutti i soggetti e le società collegate.",
            "under": "Senza verifica fisica del materiale e chiarimento sul collaboratore, un intervento potrebbe compromettere l'indagine; è preferibile proseguire l'osservazione.",
        },
    },
    "C": {
        "T1": {
            "evidence": (
                "La frammentazione sotto soglia e la selezione di imprese tecnologiche sensibili configurano un pattern meritevole di attenzione."
            ),
            "gap": (
                "Non sono disponibili le clausole contrattuali né prove di accesso a informazioni tecniche riservate."
            ),
            "cal": "Sono necessari esame immediato degli accordi e monitoraggio rafforzato, ma gli elementi non giustificano ancora l'attivazione piena della procedura.",
            "over": "La ripetizione delle acquisizioni sotto soglia dimostra un piano ostile di aggiramento; la procedura di golden power deve essere attivata immediatamente.",
            "under": "Le partecipazioni sono minoritarie e conformi alla prassi di investimento; non emergono elementi che richiedano un monitoraggio diverso da quello ordinario.",
        },
        "T2": {
            "evidence": (
                "Le richieste tecniche estranee agli accordi e il trasferimento parziale di documentazione indicano una finalità diversa dal semplice investimento finanziario."
            ),
            "gap": (
                "Non è ancora accertato se il materiale trasferito abbia effettiva rilevanza per la sicurezza nazionale."
            ),
            "cal": "La procedura deve essere attivata per impedire ulteriori trasferimenti, mentre la qualificazione tecnica del materiale prosegue in parallelo.",
            "over": "Il comportamento del fondo costituisce un'operazione di intelligence economica già comprovata e richiede blocco, revoca delle partecipazioni e misure sanzionatorie immediate.",
            "under": "Le richieste informative possono rientrare nella normale governance dell'investimento; senza classificazione del materiale non vi sono basi per attivare la procedura.",
        },
        "T3": {
            "evidence": (
                "L'offerta sulla quinta impresa, la fonte ad alta attendibilità e il pattern comparativo indicano un piano coerente di acquisizione tecnologica."
            ),
            "gap": (
                "Manca ancora la valutazione completa dell'impatto sui contratti della difesa e delle motivazioni del consiglio di amministrazione."
            ),
            "cal": "La procedura di golden power deve essere attivata immediatamente sull'offerta e accompagnata dalla revisione delle acquisizioni precedenti.",
            "over": "Le evidenze dimostrano un'operazione ostile diretta da un servizio straniero; tutte le partecipazioni devono essere annullate e i soggetti esclusi dal mercato nazionale.",
            "under": "La valutazione sotto mercato può dipendere da difficoltà finanziarie e l'impatto sulla difesa non è noto; la decisione può essere rinviata fino al completamento delle verifiche.",
        },
    },
}

PESO_LABEL = {1: "basso", 2: "medio", 3: "elevato"}
COERENZA_BASE = {"T1": 1, "T2": 2, "T3": 3}
COERENZA_LABEL = {1: "bassa", 2: "moderata", 3: "elevata"}
INCERTEZZA_BASE = {"T1": 3, "T2": 2, "T3": 1}
INCERTEZZA_LABEL = {1: "bassa", 2: "moderata", 3: "elevata"}


def clamp(value: float, low: float, high: float) -> float:
    return float(max(low, min(high, value)))


def ordinal_from_probability(value: float) -> str:
    value = float(value)
    if value <= 20:
        return "No — nessuna evidenza"
    if value <= 40:
        return "Probabilmente no — segnali deboli"
    if value <= 60:
        return "Incerto — elementi contrastanti"
    if value <= 80:
        return "Probabilmente sì — convergenza significativa"
    return "Sì — evidenza solida"


def ai_reference(dominio: str, condizione: str, qualita: str) -> int:
    base = EXPERT_BENCHMARK[dominio][condizione]
    return int(round(clamp(base + QUALITY_SHIFT[qualita], 5, 95)))


def q_quality(qualita: str) -> int:
    return 1 if qualita == "calibrato" else 0


def adjusted_indicators(dominio: str, condizione: str, qualita: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for label, base, direction in INDICATORI_BASE[dominio][condizione]:
        weight = base
        if qualita == "sovrastimante":
            weight += 1 if direction == "support" else -1
        elif qualita == "sottostimante":
            weight += -1 if direction == "support" else 1
        weight = int(clamp(weight, 1, 3))
        rows.append((label, PESO_LABEL[weight]))
    return rows


def llm_output(dominio: str, condizione: str, qualita: str) -> dict[str, Any]:
    ref = ai_reference(dominio, condizione, qualita)
    base_coh = COERENZA_BASE[condizione]
    base_unc = INCERTEZZA_BASE[condizione]
    if qualita == "sovrastimante":
        coh = int(clamp(base_coh + 1, 1, 3))
        unc = int(clamp(base_unc - 1, 1, 3))
        conclusion = OUTPUT_COMPONENTS[dominio][condizione]["over"]
        bridge = "Le lacune residue non modificano la direzione principale del giudizio."
    elif qualita == "sottostimante":
        coh = int(clamp(base_coh - 1, 1, 3))
        unc = int(clamp(base_unc + 1, 1, 3))
        conclusion = OUTPUT_COMPONENTS[dominio][condizione]["under"]
        bridge = "Le lacune informative limitano la possibilità di attribuire significato operativo agli indicatori."
    else:
        coh = base_coh
        unc = base_unc
        conclusion = OUTPUT_COMPONENTS[dominio][condizione]["cal"]
        bridge = "Le evidenze e le lacune devono essere considerate congiuntamente."

    comp = OUTPUT_COMPONENTS[dominio][condizione]
    analysis = f"{comp['evidence']} {comp['gap']} {bridge} {conclusion}"
    return {
        "reference": ref,
        "ordinal": ordinal_from_probability(ref),
        "indicators": adjusted_indicators(dominio, condizione, qualita),
        "coherence": COERENZA_LABEL[coh],
        "uncertainty": INCERTEZZA_LABEL[unc],
        "analysis": analysis,
    }


# ============================================================
# DATABASE, MIGRAZIONE E PRENOTAZIONE CONCORRENTE DEGLI SLOT
# ============================================================

BASE_COLUMNS: OrderedDict[str, str] = OrderedDict([
    ("session_uuid", "TEXT PRIMARY KEY"),
    ("participant_index", "INTEGER UNIQUE"),
    ("timestamp", "TEXT"),
    ("team_id", "INTEGER"),
    ("posizione_team", "INTEGER"),
    ("dominio", "TEXT"),
    ("sequenza_output", "TEXT"),
    ("ruolo", "TEXT"),
    ("experience", "TEXT"),
    ("coordination", "INTEGER"),
    ("specialist_area", "TEXT"),
    ("domain_experience", "INTEGER"),
    ("ai_use", "INTEGER"),
    ("ai_critical", "INTEGER"),
    ("ai_llm_use", "INTEGER"),
    ("ai_llm_trust", "INTEGER"),
    ("email_status", "TEXT"),
])

PER_T_COLUMNS: OrderedDict[str, str] = OrderedDict([
    ("output_quality", "TEXT"),
    ("ai_reference", "REAL"),
    ("ai_ordinal", "TEXT"),
    ("pre_ai", "REAL"),
    ("pre_ordinale", "TEXT"),
    ("conf_pre", "INTEGER"),
    ("post_choice", "TEXT"),
    ("post_ai", "REAL"),
    ("post_ordinale", "TEXT"),
    ("suffic_cat", "TEXT"),
    ("motivo", "TEXT"),
    ("llm_utile", "INTEGER"),
    ("trust_ai", "INTEGER"),
    ("confidence", "INTEGER"),
    ("leader_acceptance", "INTEGER"),
    ("need_group", "INTEGER"),
    ("gravity", "INTEGER"),
    ("uncertainty", "INTEGER"),
    ("strategic", "INTEGER"),
    ("pressione_1", "INTEGER"),
    ("pressione_2", "INTEGER"),
    ("pressione_3", "INTEGER"),
    ("critica_llm", "INTEGER"),
    ("lacuna_testo", "TEXT"),
    ("delta_raw", "REAL"),
    ("convergence_C", "REAL"),
    ("appropriate_reliance_AR", "REAL"),
    ("cognitive_surrender_CS", "REAL"),
    ("pressure_P", "REAL"),
    ("context_G", "REAL"),
    ("hierarchy_H", "REAL"),
    ("flexibility_F", "REAL"),
])


def expected_columns() -> OrderedDict[str, str]:
    cols = OrderedDict(BASE_COLUMNS)
    for t in CONDIZIONI:
        for name, sql_type in PER_T_COLUMNS.items():
            cols[f"{t}_{name}"] = sql_type
    return cols


def get_conn() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_PATH), timeout=30)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    cols = expected_columns()
    con = get_conn()
    try:
        column_sql = ",\n        ".join(f'"{name}" {sql_type}' for name, sql_type in cols.items())
        con.execute(f"CREATE TABLE IF NOT EXISTS risposte (\n        {column_sql}\n        )")
        existing = {row[1] for row in con.execute("PRAGMA table_info(risposte)").fetchall()}
        for name, sql_type in cols.items():
            if name not in existing:
                safe_type = sql_type.replace(" PRIMARY KEY", "").replace(" UNIQUE", "")
                con.execute(f'ALTER TABLE risposte ADD COLUMN "{name}" {safe_type}')

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS reservations (
                session_token TEXT PRIMARY KEY,
                participant_index INTEGER UNIQUE,
                created_at TEXT,
                completed INTEGER DEFAULT 0
            )
            """
        )
        con.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES ('closed','0')")
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def load_risposte() -> pd.DataFrame:
    con = get_conn()
    try:
        return pd.read_sql_query(
            "SELECT * FROM risposte ORDER BY participant_index, timestamp", con
        )
    finally:
        con.close()


def completed_count() -> int:
    con = get_conn()
    try:
        row = con.execute("SELECT COUNT(*) FROM risposte").fetchone()
        return int(row[0])
    finally:
        con.close()


def is_closed() -> bool:
    con = get_conn()
    try:
        row = con.execute("SELECT value FROM settings WHERE key='closed'").fetchone()
        return bool(row and row[0] == "1")
    finally:
        con.close()


def set_closed(value: bool) -> None:
    con = get_conn()
    try:
        con.execute(
            "INSERT OR REPLACE INTO settings(key,value) VALUES ('closed',?)",
            ("1" if value else "0",),
        )
        con.commit()
    finally:
        con.close()


def reserve_slot() -> tuple[str, int]:
    token = str(uuid.uuid4())
    threshold = (datetime.now() - timedelta(hours=RESERVATION_HOURS)).isoformat(timespec="seconds")
    con = get_conn()
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "DELETE FROM reservations WHERE completed=0 AND created_at < ?",
            (threshold,),
        )
        completed = {
            int(row[0])
            for row in con.execute(
                "SELECT participant_index FROM risposte WHERE participant_index IS NOT NULL"
            ).fetchall()
        }
        active = {
            int(row[0])
            for row in con.execute(
                "SELECT participant_index FROM reservations WHERE completed=0"
            ).fetchall()
        }
        available = next((i for i in range(MAX_P) if i not in completed and i not in active), None)
        if available is None:
            raise RuntimeError("Non sono disponibili ulteriori slot per la rilevazione.")
        con.execute(
            "INSERT INTO reservations(session_token,participant_index,created_at,completed) "
            "VALUES (?,?,?,0)",
            (token, available, datetime.now().isoformat(timespec="seconds")),
        )
        con.commit()
        return token, int(available)
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def save_response(row: dict[str, Any], reservation_token: str) -> None:
    expected = expected_columns()
    unknown = set(row) - set(expected)
    if unknown:
        raise ValueError(f"Colonne non previste: {sorted(unknown)}")

    con = get_conn()
    try:
        con.execute("BEGIN IMMEDIATE")
        reservation = con.execute(
            "SELECT participant_index, completed FROM reservations WHERE session_token=?",
            (reservation_token,),
        ).fetchone()
        if not reservation:
            raise RuntimeError("Prenotazione non trovata o scaduta.")
        if int(reservation[1]) == 1:
            raise RuntimeError("Questa sessione è già stata inviata.")
        if int(reservation[0]) != int(row["participant_index"]):
            raise RuntimeError("Lo slot della sessione non coincide con la risposta.")

        cols = list(row.keys())
        col_sql = ",".join(f'"{c}"' for c in cols)
        placeholders = ",".join("?" for _ in cols)
        con.execute(
            f"INSERT INTO risposte ({col_sql}) VALUES ({placeholders})",
            [row[c] for c in cols],
        )
        con.execute(
            "UPDATE reservations SET completed=1 WHERE session_token=?",
            (reservation_token,),
        )
        if int(row["participant_index"]) + 1 >= MAX_P:
            con.execute("UPDATE settings SET value='1' WHERE key='closed'")
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def update_email_status(session_uuid: str, status: str) -> None:
    con = get_conn()
    try:
        con.execute(
            "UPDATE risposte SET email_status=? WHERE session_uuid=?",
            (status, session_uuid),
        )
        con.commit()
    finally:
        con.close()


def reset_database() -> None:
    con = get_conn()
    try:
        con.execute("DELETE FROM risposte")
        con.execute("DELETE FROM reservations")
        con.execute("UPDATE settings SET value='0' WHERE key='closed'")
        con.commit()
    finally:
        con.close()
    for path in [CSV_RESPONSES, EXCEL_RESPONSES]:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


# ============================================================
# ASSEGNAZIONE DI TEAM, DOMINIO, SEQUENZA E RUOLO
# ============================================================


def assignment_for_index(index: int) -> dict[str, Any]:
    team = index // TEAM_SIZE
    position = index % TEAM_SIZE
    if team >= len(TEAM_DOMAIN_ORDER):
        raise ValueError("Indice partecipante fuori dal disegno sperimentale.")
    # Rotazione latina: ciascun team contiene tre S1, tre S2 e tre S3,
    # mentre la sequenza del Team Leader ruota tra i team e non resta
    # confusa sistematicamente con il ruolo.
    sequence = ["S1", "S2", "S3"][(position + team) % 3]
    return {
        "participant_index": index,
        "team_id": team,
        "posizione_team": position,
        "dominio": TEAM_DOMAIN_ORDER[team],
        "sequenza_output": sequence,
    }


def experience_years(label: str) -> int:
    return {
        "Meno di 5 anni": 2,
        "5-10 anni": 7,
        "11-20 anni": 15,
        "Oltre 20 anni": 25,
    }.get(label, 7)


def assegna_ruolo(experience: str, specialist_area: str, position: int) -> str:
    if position == 0:
        return "Team Leader"
    if specialist_area in AREE_CIVILI:
        return "Analista Civile"
    return "Analista Junior" if experience_years(experience) <= 10 else "Analista Senior"


# ============================================================
# MISURE EMPIRICHE DELLO STUDIO 2
# ============================================================


def likert01(value: Any) -> float:
    return clamp((float(value) - 1.0) / 6.0, 0.0, 1.0)


def compute_P(row: pd.Series | dict[str, Any], t: str) -> float:
    p1 = float(row[f"{t}_pressione_1"])
    p2_reversed = 8.0 - float(row[f"{t}_pressione_2"])
    p3 = float(row[f"{t}_pressione_3"])
    return clamp((np.mean([p1, p2_reversed, p3]) - 1.0) / 6.0, 0.0, 1.0)


def compute_G(row: pd.Series | dict[str, Any], t: str) -> float:
    values = [
        float(row[f"{t}_gravity"]),
        float(row[f"{t}_uncertainty"]),
        float(row[f"{t}_strategic"]),
    ]
    return clamp((np.mean(values) - 1.0) / 6.0, 0.0, 1.0)


def compute_H(row: pd.Series | dict[str, Any], t: str) -> float:
    leader = float(row[f"{t}_leader_acceptance"])
    group = float(row[f"{t}_need_group"])
    return float(leader / (leader + group + 1e-9))


def compute_C(pre: float, post: float, ai_ref: float) -> float:
    return float(abs(pre - ai_ref) - abs(post - ai_ref))


def compute_AR(convergence: float, quality: str) -> float:
    q = q_quality(quality)
    return float(convergence * (2 * q - 1))


def compute_CS(convergence: float, quality: str) -> float:
    q = q_quality(quality)
    return float(max(0.0, convergence) * (1 - q))


def compute_F(pre: float, post: float, ai_ref: float, conf_pre: float) -> float:
    ai_direction = ai_ref - pre
    movement = post - pre
    if abs(ai_direction) < 1e-9 or abs(movement) < 1e-9:
        return 0.0
    sign = float(np.sign(movement * ai_direction))
    return float(sign * abs(movement) / 100.0 * float(conf_pre) / 7.0)


def add_derived_measures(row: dict[str, Any]) -> dict[str, Any]:
    for t in CONDIZIONI:
        pre = float(row[f"{t}_pre_ai"])
        post = float(row[f"{t}_post_ai"])
        ref = float(row[f"{t}_ai_reference"])
        quality = str(row[f"{t}_output_quality"])
        convergence = compute_C(pre, post, ref)
        row[f"{t}_delta_raw"] = post - pre
        row[f"{t}_convergence_C"] = convergence
        row[f"{t}_appropriate_reliance_AR"] = compute_AR(convergence, quality)
        row[f"{t}_cognitive_surrender_CS"] = compute_CS(convergence, quality)
        row[f"{t}_pressure_P"] = compute_P(row, t)
        row[f"{t}_context_G"] = compute_G(row, t)
        row[f"{t}_hierarchy_H"] = compute_H(row, t)
        row[f"{t}_flexibility_F"] = compute_F(
            pre, post, ref, float(row[f"{t}_conf_pre"])
        )
    return row


# ============================================================
# ESPORTAZIONE ED EMAIL
# ============================================================


def dataframe_to_excel_bytes(df: pd.DataFrame, extra_sheets: dict[str, pd.DataFrame] | None = None) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Risposte", index=False)
        if extra_sheets:
            for name, data in extra_sheets.items():
                safe_name = name[:31]
                data.to_excel(writer, sheet_name=safe_name, index=False)
    buffer.seek(0)
    return buffer.getvalue()


def persist_exports(df: pd.DataFrame) -> tuple[bool, str]:
    try:
        df.to_csv(CSV_RESPONSES, index=False, encoding="utf-8-sig")
        EXCEL_RESPONSES.write_bytes(dataframe_to_excel_bytes(df))
        return True, "CSV ed Excel aggiornati."
    except (OSError, ValueError, ImportError) as exc:
        return False, f"Esportazione non completata: {exc}"


def get_email_config() -> dict[str, str] | None:
    try:
        cfg = st.secrets["email"]
        return {
            "mittente": str(cfg["mittente"]),
            "password": str(cfg["password"]),
            "destinatario": str(cfg.get("destinatario", "castiello.mauro@gmail.com")),
        }
    except Exception:
        return None


def attach_bytes(msg: MIMEMultipart, payload: bytes, filename: str) -> None:
    part = MIMEBase("application", "octet-stream")
    part.set_payload(payload)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)


def send_response_email(row: dict[str, Any], test: bool = False) -> tuple[bool, str]:
    cfg = get_email_config()
    if not cfg:
        return False, "Configurazione email assente in .streamlit/secrets.toml."
    try:
        df = load_risposte()
        msg = MIMEMultipart()
        msg["From"] = cfg["mittente"]
        msg["To"] = cfg["destinatario"]
        msg["Subject"] = (
            "TEST — Studio 2" if test else
            f"Studio 2 — risposta {int(row.get('participant_index', -1)) + 1} "
            f"Team {row.get('team_id', '?')}"
        )
        body = (
            "Messaggio di test del sistema email." if test else
            "È stata acquisita una nuova risposta dello Studio 2.\n\n"
            f"Partecipante: {int(row['participant_index']) + 1}\n"
            f"Team: {row['team_id']}\n"
            f"Dominio: {DOMINI[row['dominio']]}\n"
            f"Sequenza: {row['sequenza_output']}\n"
            f"Timestamp: {row['timestamp']}"
        )
        msg.attach(MIMEText(body, "plain", "utf-8"))
        if not df.empty:
            attach_bytes(
                msg,
                df.to_csv(index=False).encode("utf-8-sig"),
                "studio2_risposte.csv",
            )
            attach_bytes(msg, dataframe_to_excel_bytes(df), "studio2_risposte.xlsx")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
            smtp.login(cfg["mittente"], cfg["password"])
            smtp.sendmail(cfg["mittente"], cfg["destinatario"], msg.as_string())
        return True, "Email inviata correttamente."
    except (smtplib.SMTPException, OSError, ValueError) as exc:
        return False, f"Invio email non riuscito: {exc}"


# ============================================================
# ABM DEL FILTRO SELETTIVO E MONTE CARLO
# ============================================================


def prepare_team(df: pd.DataFrame) -> pd.DataFrame:
    team = df.copy().reset_index(drop=True)
    if "ruolo" not in team.columns:
        team["ruolo"] = team.apply(
            lambda r: assegna_ruolo(
                str(r["experience"]), str(r["specialist_area"]), int(r["posizione_team"])
            ),
            axis=1,
        )
    team["role_influence"] = team["ruolo"].map(ROLE_INFLUENCE).fillna(0.45)
    return team


def build_network(team: pd.DataFrame, t: str) -> tuple[nx.Graph, list[str], int, float]:
    graph = nx.Graph()
    codes = [str(v)[:8] for v in team["session_uuid"].tolist()]
    h_mean = float(np.mean([compute_H(row, t) for _, row in team.iterrows()]))
    need_mean = float(np.mean([likert01(row[f"{t}_need_group"]) for _, row in team.iterrows()]))
    leader_idx = next(
        (i for i, role in enumerate(team["ruolo"].tolist()) if role == "Team Leader"),
        0,
    )
    for i, code in enumerate(codes):
        graph.add_node(code, role=str(team.iloc[i]["ruolo"]))
    for i, code in enumerate(codes):
        if i != leader_idx:
            target_influence = float(team.iloc[leader_idx]["role_influence"])
            graph.add_edge(
                codes[leader_idx], code,
                weight=(0.20 + 0.60 * h_mean) * target_influence,
            )
    horizontal = 0.08 + 0.50 * (1.0 - h_mean) * need_mean
    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            if graph.has_edge(codes[i], codes[j]):
                continue
            influence = float(
                np.mean([team.iloc[i]["role_influence"], team.iloc[j]["role_influence"]])
            )
            graph.add_edge(codes[i], codes[j], weight=horizontal * influence)
    return graph, codes, leader_idx, h_mean


def simulate_abm(team: pd.DataFrame, t: str, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    team = prepare_team(team)
    graph, codes, leader_idx, h_mean = build_network(team, t)
    index_by_code = {code: i for i, code in enumerate(codes)}

    pre = team[f"{t}_pre_ai"].astype(float).to_numpy()
    beliefs = team[f"{t}_post_ai"].astype(float).to_numpy()
    ai_ref = team[f"{t}_ai_reference"].astype(float).to_numpy()
    qualities = team[f"{t}_output_quality"].astype(str).to_numpy()
    q_arr = np.array([q_quality(q) for q in qualities], dtype=float)
    trust = np.array([likert01(v) for v in team[f"{t}_trust_ai"]], dtype=float)
    confidence = np.array([likert01(v) for v in team[f"{t}_confidence"]], dtype=float)
    critical = np.array([likert01(v) for v in team[f"{t}_critica_llm"]], dtype=float)
    h_arr = np.array([compute_H(row, t) for _, row in team.iterrows()], dtype=float)
    p_arr = np.array([compute_P(row, t) for _, row in team.iterrows()], dtype=float)
    g_arr = np.array([compute_G(row, t) for _, row in team.iterrows()], dtype=float)
    f_arr = np.array([
        compute_F(
            float(row[f"{t}_pre_ai"]),
            float(row[f"{t}_post_ai"]),
            float(row[f"{t}_ai_reference"]),
            float(row[f"{t}_conf_pre"]),
        )
        for _, row in team.iterrows()
    ])
    need_arr = np.array([likert01(v) for v in team[f"{t}_need_group"]], dtype=float)

    p_mean = float(np.mean(p_arr))
    g_mean = float(np.mean(g_arr))
    sigma_p = 0.05 + 0.15 * p_mean
    steps = 6 if p_mean < 0.35 else (5 if p_mean < 0.65 else 4)
    history: list[dict[str, float | str | int]] = []

    for step in range(steps + 1):
        leader_belief = float(beliefs[leader_idx])
        convergence = np.abs(pre - ai_ref) - np.abs(beliefs - ai_ref)
        ar = convergence * (2 * q_arr - 1)
        cs = np.maximum(0.0, convergence) * (1 - q_arr)
        consensus = clamp(1.0 - float(np.std(beliefs)) / 50.0, 0.0, 1.0)
        deliberation = clamp(
            (1.0 - p_mean)
            * (1.0 - h_mean)
            * float(np.mean(need_arr))
            * (0.40 + float(np.mean(np.abs(f_arr)))),
            0.0,
            1.0,
        )
        ar_score = clamp(0.5 + float(np.mean(ar)) / 100.0, 0.0, 1.0)
        cs_score = clamp(float(np.mean(cs)) / 100.0, 0.0, 1.0)
        selective_filter = clamp(
            0.55 * ar_score
            + 0.20 * deliberation
            + 0.15 * (1.0 - cs_score)
            + 0.10 * (1.0 - h_mean * p_mean),
            0.0,
            1.0,
        )
        hierarchy_index = clamp(
            1.0 - float(np.mean(np.abs(beliefs - leader_belief))) / 50.0,
            0.0,
            1.0,
        )
        history.append({
            "condition": t,
            "step": step,
            "group_mean": float(np.mean(beliefs)),
            "consensus": consensus,
            "convergence_mean": float(np.mean(convergence)),
            "appropriate_reliance_mean": float(np.mean(ar)),
            "cognitive_surrender_mean": float(np.mean(cs)),
            "selective_filter": selective_filter,
            "deliberation": deliberation,
            "hierarchy_index": hierarchy_index,
            "P": p_mean,
            "G": g_mean,
            "H": h_mean,
            "sigma_P": sigma_p,
        })
        if step == steps:
            break

        updated = beliefs.copy()
        for i, code in enumerate(codes):
            neighbours = list(graph.neighbors(code))
            if neighbours:
                neighbour_values = []
                neighbour_weights = []
                for nb in neighbours:
                    j = index_by_code[nb]
                    neighbour_values.append(beliefs[j])
                    neighbour_weights.append(graph[code][nb]["weight"])
                local = float(np.average(neighbour_values, weights=neighbour_weights))
            else:
                local = float(beliefs[i])

            ai_salient = clamp(ai_ref[i] * (1.0 + rng.normal(0.0, sigma_p)), 0.0, 100.0)
            w_ai = clamp(
                0.06 + 0.28 * trust[i] + 0.18 * p_arr[i] + 0.10 * g_arr[i]
                - 0.18 * critical[i],
                0.02,
                0.72,
            )
            w_leader = clamp(0.04 + 0.42 * h_mean * h_arr[i], 0.02, 0.65)
            w_network = clamp(
                0.08 + 0.42 * (1.0 - p_arr[i]) * (1.0 - h_mean) * need_arr[i],
                0.02,
                0.60,
            )
            w_self = max(0.05, 1.0 - (w_ai + w_leader + w_network))
            total = w_self + w_ai + w_leader + w_network
            w_self, w_ai, w_leader, w_network = [
                x / total for x in (w_self, w_ai, w_leader, w_network)
            ]
            target = (
                w_self * beliefs[i]
                + w_ai * ai_salient
                + w_leader * leader_belief
                + w_network * local
            )
            inertia = 0.45 + 0.35 * confidence[i]
            noise = rng.normal(0.0, 1.5 + 3.5 * p_mean)
            updated[i] = clamp(beliefs[i] + (1.0 - inertia) * (target - beliefs[i]) + noise, 0.0, 100.0)
        beliefs = updated

    return pd.DataFrame(history)


def run_abm(team: pd.DataFrame, seed: int = BASE_SEED) -> pd.DataFrame:
    return pd.concat(
        [simulate_abm(team, t, seed + 1000 * idx) for idx, t in enumerate(CONDIZIONI)],
        ignore_index=True,
    )


def perturb_team(team: pd.DataFrame, seed: int, noise: float = 0.08) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    result = team.copy()
    for t in CONDIZIONI:
        for col in [f"{t}_pre_ai", f"{t}_post_ai"]:
            result[col] = np.clip(
                result[col].astype(float) * rng.normal(1.0, noise, len(result)),
                0,
                100,
            )
        for suffix in [
            "conf_pre", "llm_utile", "trust_ai", "confidence", "leader_acceptance",
            "need_group", "gravity", "uncertainty", "strategic", "pressione_1",
            "pressione_2", "pressione_3", "critica_llm",
        ]:
            col = f"{t}_{suffix}"
            result[col] = np.clip(
                result[col].astype(float) * rng.normal(1.0, noise, len(result)),
                1,
                7,
            )
    return result


def run_montecarlo(team: pd.DataFrame, n_synth: int, n_mc: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    finals: list[dict[str, Any]] = []
    for synth in range(int(n_synth)):
        synthetic = perturb_team(team, BASE_SEED + synth)
        for run in range(int(n_mc)):
            for idx, t in enumerate(CONDIZIONI):
                sim = simulate_abm(
                    synthetic,
                    t,
                    BASE_SEED + synth * 100_000 + run * 10 + idx,
                )
                last = sim.iloc[-1].to_dict()
                last["synthetic_team"] = synth
                last["run"] = run
                finals.append(last)
    mc = pd.DataFrame(finals)
    summary = mc.groupby("condition", as_index=False).agg(
        AR_mean=("appropriate_reliance_mean", "mean"),
        AR_ci95=(
            "appropriate_reliance_mean",
            lambda x: 1.96 * x.std(ddof=1) / np.sqrt(max(len(x), 1)),
        ),
        CS_mean=("cognitive_surrender_mean", "mean"),
        CS_ci95=(
            "cognitive_surrender_mean",
            lambda x: 1.96 * x.std(ddof=1) / np.sqrt(max(len(x), 1)),
        ),
        filter_mean=("selective_filter", "mean"),
        filter_ci95=(
            "selective_filter",
            lambda x: 1.96 * x.std(ddof=1) / np.sqrt(max(len(x), 1)),
        ),
        consensus_mean=("consensus", "mean"),
        P=("P", "mean"),
        G=("G", "mean"),
        H=("H", "mean"),
    )
    order = pd.Categorical(summary["condition"], categories=CONDIZIONI, ordered=True)
    summary = summary.assign(_order=order).sort_values("_order").drop(columns="_order")
    return mc, summary


def plot_abm_trajectories(abm: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(9, 5.5))
    styles = {"T1": "-", "T2": "--", "T3": ":"}
    markers = {"T1": "o", "T2": "s", "T3": "^"}
    for t in CONDIZIONI:
        data = abm[abm["condition"] == t]
        ax.plot(
            data["step"],
            data["selective_filter"],
            linestyle=styles[t],
            marker=markers[t],
            linewidth=2,
            label=f"{t} — filtro selettivo",
        )
    ax.set_xlabel("Step")
    ax.set_ylabel("Indice 0–1")
    ax.set_ylim(0, 1.05)
    ax.set_title("ABM — capacità selettiva del Sistema 3")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    return fig


def plot_mc_summary(summary: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = np.arange(len(summary))
    ax.errorbar(
        x - 0.08,
        summary["AR_mean"],
        yerr=summary["AR_ci95"],
        fmt="o-",
        capsize=5,
        label="Affidamento appropriato (AR)",
    )
    ax.errorbar(
        x + 0.08,
        summary["CS_mean"],
        yerr=summary["CS_ci95"],
        fmt="s--",
        capsize=5,
        label="Resa cognitiva (CS)",
    )
    ax.axhline(0, linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(summary["condition"])
    ax.set_ylabel("Punti di convergenza")
    ax.set_title("Monte Carlo — affidamento appropriato e resa cognitiva")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    return fig


def figure_to_png(fig: plt.Figure, dpi: int = 300) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi, bbox_inches="tight")
    buffer.seek(0)
    return buffer.getvalue()


# ============================================================
# FUNZIONI DI SUPPORTO UI
# ============================================================


def relative_ai_message(pre: float, reference: float) -> str:
    diff = int(round(reference - pre))
    if diff > 0:
        return (
            f"La stima complessiva prodotta dal sistema è **superiore** alla tua "
            f"valutazione iniziale di **{diff} punti percentuali**."
        )
    if diff < 0:
        return (
            f"La stima complessiva prodotta dal sistema è **inferiore** alla tua "
            f"valutazione iniziale di **{abs(diff)} punti percentuali**."
        )
    return "La stima complessiva prodotta dal sistema è **allineata** alla tua valutazione iniziale."


def show_llm_output(dominio: str, t: str, quality: str, pre: float) -> dict[str, Any]:
    output = llm_output(dominio, t, quality)
    st.info(
        "**Sistema di supporto analitico — output precompilato del modello linguistico**\n\n"
        "Il modello ha elaborato le stesse informazioni del briefing e presenta "
        "la propria analisi in forma strutturata."
    )
    st.markdown(f"### Valutazione complessiva\n**{output['ordinal']}**")
    st.markdown(relative_ai_message(pre, output["reference"]))
    indicator_df = pd.DataFrame(output["indicators"], columns=["Indicatore", "Peso attribuito"])
    st.dataframe(indicator_df, hide_index=True, use_container_width=True)
    c1, c2 = st.columns(2)
    c1.metric("Coerenza tra le fonti", str(output["coherence"]).capitalize())
    c2.metric("Incertezza residua", str(output["uncertainty"]).capitalize())
    st.markdown("### Analisi argomentata")
    st.markdown(output["analysis"])
    st.caption("Il giudizio analitico finale rimane responsabilità del partecipante.")
    return output


def clear_participant_state() -> None:
    preserve = {"submission_success", "submission_email_message"}
    for key in list(st.session_state.keys()):
        if key not in preserve:
            del st.session_state[key]


def build_response_row() -> dict[str, Any]:
    assignment = st.session_state["assignment"]
    profile = st.session_state["profile"]
    row: dict[str, Any] = {
        "session_uuid": str(uuid.uuid4()),
        "participant_index": int(assignment["participant_index"]),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "team_id": int(assignment["team_id"]),
        "posizione_team": int(assignment["posizione_team"]),
        "dominio": str(assignment["dominio"]),
        "sequenza_output": str(assignment["sequenza_output"]),
        "ruolo": str(st.session_state["ruolo"]),
        "experience": profile["experience"],
        "coordination": int(profile["coordination"]),
        "specialist_area": profile["specialist_area"],
        "domain_experience": int(profile["domain_experience"]),
        "ai_use": int(profile["ai_use"]),
        "ai_critical": int(profile["ai_critical"]),
        "ai_llm_use": int(profile["ai_llm_use"]),
        "ai_llm_trust": int(profile["ai_llm_trust"]),
        "email_status": "non tentata",
    }
    for t in CONDIZIONI:
        quality = SEQUENZE_QUALITA[assignment["sequenza_output"]][t]
        output = llm_output(assignment["dominio"], t, quality)
        pre = float(st.session_state[f"{t}_pre_saved"])
        post_choice = str(st.session_state.get(f"{t}_post_choice"))
        post = pre if post_choice.startswith("Confermo") else float(st.session_state[f"{t}_post_slider"])
        values = {
            "output_quality": quality,
            "ai_reference": float(output["reference"]),
            "ai_ordinal": output["ordinal"],
            "pre_ai": pre,
            "pre_ordinale": st.session_state[f"{t}_pre_ord_saved"],
            "conf_pre": int(st.session_state[f"{t}_conf_pre_saved"]),
            "post_choice": post_choice,
            "post_ai": post,
            "post_ordinale": st.session_state[f"{t}_post_ord"],
            "suffic_cat": st.session_state[f"{t}_suffic"],
            "motivo": st.session_state[f"{t}_motivo"],
            "llm_utile": int(st.session_state[f"{t}_llm_utile"]),
            "trust_ai": int(st.session_state[f"{t}_trust_ai"]),
            "confidence": int(st.session_state[f"{t}_confidence"]),
            "leader_acceptance": int(st.session_state[f"{t}_leader_acceptance"]),
            "need_group": int(st.session_state[f"{t}_need_group"]),
            "gravity": int(st.session_state[f"{t}_gravity"]),
            "uncertainty": int(st.session_state[f"{t}_uncertainty"]),
            "strategic": int(st.session_state[f"{t}_strategic"]),
            "pressione_1": int(st.session_state[f"{t}_pressione_1"]),
            "pressione_2": int(st.session_state[f"{t}_pressione_2"]),
            "pressione_3": int(st.session_state[f"{t}_pressione_3"]),
            "critica_llm": int(st.session_state[f"{t}_critica_llm"]),
            "lacuna_testo": str(st.session_state.get(f"{t}_lacuna_testo", "")),
        }
        for key, value in values.items():
            row[f"{t}_{key}"] = value
    return add_derived_measures(row)


def validate_final_answers() -> list[str]:
    errors: list[str] = []
    for t in CONDIZIONI:
        if not st.session_state.get(f"{t}_confirmed", False):
            errors.append(f"{t}: valutazione iniziale non confermata")
            continue
        choice = st.session_state.get(f"{t}_post_choice")
        if choice not in {
            "Confermo intenzionalmente la valutazione iniziale",
            "Modifico la valutazione iniziale",
        }:
            errors.append(f"{t}: indicare se si conferma o modifica la stima")
        if choice == "Modifico la valutazione iniziale":
            pre = float(st.session_state[f"{t}_pre_saved"])
            post = float(st.session_state.get(f"{t}_post_slider", pre))
            if abs(post - pre) < 1e-9:
                errors.append(f"{t}: la stima è dichiarata modificata ma non è stata variata")
        for key, label in [
            (f"{t}_post_ord", "scala qualitativa post-AI"),
            (f"{t}_suffic", "sufficienza informativa"),
            (f"{t}_motivo", "motivazione"),
        ]:
            value = st.session_state.get(key, "— seleziona —")
            if value == "— seleziona —" or value is None:
                errors.append(f"{t}: completare {label}")
    return errors


# ============================================================
# AVVIO DELL'APPLICAZIONE
# ============================================================

init_db()

st.title("Questionario Sistema 3 — Studio 2")
st.markdown(
    "Valutazione individuale, qualità dell'output LLM e mediazione organizzativa del Sistema 3"
)

admin = st.sidebar.text_input("Password back office", type="password")

# ------------------------------------------------------------
# BACK OFFICE
# ------------------------------------------------------------
if admin == ADMIN_PWD:
    st.sidebar.success("Back office attivo")
    st.header("Back Office — Studio 2")
    df = load_risposte()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risposte acquisite", len(df))
    c2.metric("Rilevazione", "Chiusa" if is_closed() else "Aperta")
    complete_teams = []
    if not df.empty:
        complete_teams = [
            int(team_id)
            for team_id, group in df.groupby("team_id")
            if len(group) == TEAM_SIZE and group["dominio"].nunique() == 1
        ]
    c3.metric("Team completi", len(complete_teams))
    c4.metric("Email configurata", "Sì" if get_email_config() else "No")

    if not df.empty:
        st.subheader("Distribuzione del campione")
        domain_counts = (
            df.groupby("dominio").size().rename("N").reset_index()
        )
        domain_counts["Dominio"] = domain_counts["dominio"].map(DOMINI)
        st.dataframe(domain_counts[["dominio", "Dominio", "N"]], hide_index=True)

        quality_rows = []
        for t in CONDIZIONI:
            counts = df[f"{t}_output_quality"].value_counts()
            for quality, n in counts.items():
                quality_rows.append({"Condizione": t, "Qualità": quality, "N": int(n)})
        st.dataframe(pd.DataFrame(quality_rows), hide_index=True, use_container_width=True)

        st.subheader("Composizione osservata dei team")
        composition = (
            df.groupby(["team_id", "dominio", "ruolo"])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )
        st.dataframe(composition, hide_index=True, use_container_width=True)

    controls = st.columns(4)
    if controls[0].button("Chiudi rilevazione"):
        set_closed(True)
        st.rerun()
    if controls[1].button("Riapri rilevazione"):
        set_closed(False)
        st.rerun()
    if controls[2].button("Test email"):
        ok, message = send_response_email(
            {"participant_index": -1, "team_id": "TEST", "dominio": "A", "timestamp": datetime.now().isoformat(), "sequenza_output": "TEST"},
            test=True,
        )
        (st.success if ok else st.error)(message)
    if controls[3].button("🗑️ Reset completo"):
        reset_database()
        st.success("Database e file di esportazione eliminati.")
        st.rerun()

    st.divider()
    if not df.empty:
        st.subheader("Dati acquisiti")
        st.dataframe(df, hide_index=True, use_container_width=True)
        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
        excel_bytes = dataframe_to_excel_bytes(df)
        d1, d2 = st.columns(2)
        d1.download_button(
            "⬇️ Scarica CSV",
            csv_bytes,
            "studio2_risposte.csv",
            "text/csv",
        )
        d2.download_button(
            "⬇️ Scarica Excel",
            excel_bytes,
            "studio2_risposte.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.subheader("Sintesi degli esiti sperimentali")
        summary_rows = []
        for t in CONDIZIONI:
            for (domain, quality), group in df.groupby(["dominio", f"{t}_output_quality"]):
                summary_rows.append({
                    "Condizione": t,
                    "Dominio": DOMINI.get(domain, domain),
                    "Qualità": quality,
                    "N": len(group),
                    "Delta medio": group[f"{t}_delta_raw"].mean(),
                    "C medio": group[f"{t}_convergence_C"].mean(),
                    "AR medio": group[f"{t}_appropriate_reliance_AR"].mean(),
                    "CS medio": group[f"{t}_cognitive_surrender_CS"].mean(),
                    "P medio": group[f"{t}_pressure_P"].mean(),
                    "G medio": group[f"{t}_context_G"].mean(),
                    "H medio": group[f"{t}_hierarchy_H"].mean(),
                })
        st.dataframe(pd.DataFrame(summary_rows).round(3), hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("ABM e Monte Carlo")
    if complete_teams:
        selected_team = st.selectbox("Team completo", complete_teams)
        team_df = df[df["team_id"] == selected_team].copy()
        st.caption(
            f"Dominio: {DOMINI.get(str(team_df['dominio'].iloc[0]), team_df['dominio'].iloc[0])} — "
            f"Partecipanti: {len(team_df)}"
        )
        st.dataframe(
            team_df[["participant_index", "ruolo", "experience", "specialist_area", "sequenza_output"]],
            hide_index=True,
            use_container_width=True,
        )
        p1, p2, p3 = st.columns(3)
        n_synth = int(p1.number_input("Team sintetici", min_value=1, max_value=100, value=DEFAULT_N_SYNTH))
        n_mc = int(p2.number_input("Run per team sintetico", min_value=1, max_value=1000, value=DEFAULT_N_MC))
        automatic = p3.toggle("Esecuzione automatica", value=False)
        run_clicked = st.button("▶ Esegui/aggiorna ABM + Monte Carlo", type="primary")
        if automatic or run_clicked:
            with st.spinner(f"Simulazione in corso: {n_synth} × {n_mc} × 3 condizioni..."):
                prepared = prepare_team(team_df)
                abm = run_abm(prepared)
                mc, mc_summary = run_montecarlo(prepared, n_synth, n_mc)
                fig1 = plot_abm_trajectories(abm)
                fig2 = plot_mc_summary(mc_summary)
            st.pyplot(fig1)
            st.pyplot(fig2)
            st.subheader("Sintesi Monte Carlo")
            st.dataframe(mc_summary.round(4), hide_index=True, use_container_width=True)
            analysis_excel = dataframe_to_excel_bytes(
                team_df,
                {
                    "ABM dinamica": abm,
                    "Monte Carlo": mc,
                    "Sintesi Monte Carlo": mc_summary,
                },
            )
            a1, a2, a3 = st.columns(3)
            a1.download_button(
                "⬇️ Analisi Excel",
                analysis_excel,
                f"studio2_team_{selected_team}_analisi.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            a2.download_button(
                "⬇️ Plot ABM 300 dpi",
                figure_to_png(fig1),
                f"studio2_team_{selected_team}_abm.png",
                "image/png",
            )
            a3.download_button(
                "⬇️ Plot Monte Carlo 300 dpi",
                figure_to_png(fig2),
                f"studio2_team_{selected_team}_montecarlo.png",
                "image/png",
            )
            plt.close(fig1)
            plt.close(fig2)
    else:
        st.info("L'analisi ABM richiede almeno un team completo di nove risposte omogenee per dominio.")
    st.stop()

# ------------------------------------------------------------
# QUESTIONARIO PARTECIPANTE
# ------------------------------------------------------------

if st.session_state.get("submission_success"):
    st.success(
        "✅ Hai concluso con successo il questionario. La risposta è stata acquisita correttamente. "
        "Grazie per la partecipazione."
    )
    email_message = st.session_state.get("submission_email_message")
    if email_message:
        st.caption(email_message)
    if st.button("Nuova compilazione su questo dispositivo"):
        st.session_state.clear()
        st.rerun()
    st.stop()

if is_closed() or completed_count() >= MAX_P:
    st.info("La rilevazione è terminata. Grazie per l'interesse.")
    st.stop()

st.progress(completed_count() / MAX_P, text=f"Risposte completate: {completed_count()}/{MAX_P}")

if "assignment" not in st.session_state:
    st.subheader("Avvio della sessione")
    st.markdown(
        "Premendo il pulsante viene riservato uno slot sperimentale. "
        "Le sessioni abbandonate vengono liberate automaticamente dopo "
        f"{RESERVATION_HOURS} ore."
    )
    if st.button("Avvia la sessione", type="primary"):
        try:
            token, index = reserve_slot()
            st.session_state["reservation_token"] = token
            st.session_state["assignment"] = assignment_for_index(index)
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))
    st.stop()

assignment = st.session_state["assignment"]
dominio = assignment["dominio"]
sequence = assignment["sequenza_output"]

if "profile" not in st.session_state:
    st.subheader("Profilo professionale")
    st.info(f"Dominio assegnato: **{DOMINI[dominio]}**")
    with st.form("profile_form"):
        experience = st.selectbox(
            "Anni di esperienza nel settore",
            ["— seleziona —", "Meno di 5 anni", "5-10 anni", "11-20 anni", "Oltre 20 anni"],
        )
        coordination = st.slider("Esperienza nel coordinamento di gruppi", 1, 7, 4)
        specialist_area = st.selectbox(
            "Area operativa prevalente",
            ["— seleziona —"] + AREE_OPERATIVE + AREE_CIVILI,
        )
        domain_experience = st.slider(
            f"Esperienza specifica in: {DOMINI[dominio]}",
            1,
            7,
            4,
            help="1 = nessuna esperienza specifica; 7 = esperienza molto elevata",
        )
        ai_use = st.slider("Frequenza di utilizzo di strumenti di analisi automatizzata", 1, 7, 4)
        ai_critical = st.slider("Capacità percepita di valutare criticamente output automatizzati", 1, 7, 4)
        ai_llm_use = st.slider("Frequenza di utilizzo di modelli linguistici (LLM)", 1, 7, 4)
        ai_llm_trust = st.slider("Fiducia generale negli output LLM in contesti analitici", 1, 7, 4)
        start = st.form_submit_button("Inizia il questionario", type="primary")
    if start:
        if experience == "— seleziona —" or specialist_area == "— seleziona —":
            st.error("Completa gli elementi obbligatori del profilo.")
        else:
            st.session_state["profile"] = {
                "experience": experience,
                "coordination": coordination,
                "specialist_area": specialist_area,
                "domain_experience": domain_experience,
                "ai_use": ai_use,
                "ai_critical": ai_critical,
                "ai_llm_use": ai_llm_use,
                "ai_llm_trust": ai_llm_trust,
            }
            st.session_state["ruolo"] = assegna_ruolo(
                experience, specialist_area, int(assignment["posizione_team"])
            )
            st.rerun()
    st.stop()

st.caption(
    f"Sessione {int(assignment['participant_index']) + 1} — Team {assignment['team_id']} — "
    f"Dominio: {DOMINI[dominio]}"
)
with st.expander("Istruzioni operative", expanded=True):
    st.markdown(
        """
        Il questionario comprende tre condizioni progressive, T1–T3.

        1. Leggi integralmente il briefing.
        2. Formula e conferma la valutazione iniziale prima di vedere il modello.
        3. Consulta l'output strutturato del modello linguistico.
        4. Dichiara esplicitamente se confermi o modifichi la stima.
        5. Valuta il contesto, la pressione e la qualità percepita dell'output.

        L'output costituisce un supporto alla decisione e non sostituisce il giudizio
        professionale. Non esistono risposte attese: esprimi una valutazione autonoma.
        """
    )

for t in CONDIZIONI:
    st.divider()
    st.header(f"{t} — {COND_LABEL[t]}")
    previous = CONDIZIONI[:CONDIZIONI.index(t)]
    if not all(st.session_state.get(f"{p}_completed", False) for p in previous):
        st.info("🔒 Completa la condizione precedente per proseguire.")
        continue

    st.info(COND_CONTESTO[t])
    with st.expander("📄 Briefing operativo", expanded=not st.session_state.get(f"{t}_confirmed", False)):
        st.markdown(BRIEFING[dominio][t])

    if not st.session_state.get(f"{t}_confirmed", False):
        st.subheader("Sezione I — Valutazione autonoma")
        st.markdown(f"**{DOMANDA[dominio]}**")
        pre_value = st.slider("Probabilità stimata (0–100)", 0, 100, 50, key=f"{t}_pre_slider")
        pre_ord = st.selectbox("Valutazione qualitativa", SCALA_ORDINALE, key=f"{t}_pre_ord")
        conf_pre = st.slider("Sicurezza della valutazione iniziale", 1, 7, 4, key=f"{t}_conf_pre")
        if st.button(f"✅ Conferma la valutazione iniziale — {t}", key=f"{t}_confirm"):
            if pre_ord == "— seleziona —":
                st.error("Seleziona la valutazione qualitativa.")
            else:
                st.session_state[f"{t}_pre_saved"] = float(pre_value)
                st.session_state[f"{t}_pre_ord_saved"] = pre_ord
                st.session_state[f"{t}_conf_pre_saved"] = int(conf_pre)
                st.session_state[f"{t}_confirmed"] = True
                st.rerun()
        st.warning("Conferma la valutazione iniziale per rendere visibile l'output del modello.")
        continue

    pre_saved = float(st.session_state[f"{t}_pre_saved"])
    quality = SEQUENZE_QUALITA[sequence][t]
    st.success("Valutazione iniziale registrata.")
    st.subheader("Sezione II — Output del modello linguistico")
    show_llm_output(dominio, t, quality, pre_saved)

    st.subheader("Sezione III — Valutazione finale")
    post_choice = st.radio(
        "Dopo aver consultato il modello:",
        [
            "Confermo intenzionalmente la valutazione iniziale",
            "Modifico la valutazione iniziale",
        ],
        index=None,
        key=f"{t}_post_choice",
    )
    if post_choice == "Confermo intenzionalmente la valutazione iniziale":
        st.metric("Valutazione finale", f"{pre_saved:.0f}%")
    elif post_choice == "Modifico la valutazione iniziale":
        st.slider(
            "Nuova probabilità stimata (0–100)",
            0,
            100,
            int(pre_saved),
            key=f"{t}_post_slider",
        )

    st.selectbox("Valutazione qualitativa finale", SCALA_ORDINALE, key=f"{t}_post_ord")
    st.selectbox(
        "Valuta la sufficienza delle informazioni e la tua decisione:",
        [
            "— seleziona —",
            "Le informazioni sono sufficienti — confermo la valutazione iniziale",
            "Le informazioni sono sufficienti — modifico la valutazione iniziale",
            "Le informazioni non sono sufficienti — confermo la valutazione iniziale",
            "Le informazioni non sono sufficienti — modifico la valutazione iniziale",
        ],
        key=f"{t}_suffic",
    )
    st.selectbox(
        "Motivazione principale della decisione finale",
        [
            "— seleziona —",
            "Fiducia nella valutazione del modello",
            "Rivalutazione autonoma delle informazioni del briefing",
            "Coerenza tra output del modello e giudizio iniziale",
            "Individuazione di lacune o forzature nell'output del modello",
            "Nessuna modifica significativa",
        ],
        key=f"{t}_motivo",
    )

    st.subheader("Sezione IV — Valutazione dell'output e del contesto")
    st.slider("Utilità dell'analisi del modello", 1, 7, 4, key=f"{t}_llm_utile")
    st.slider("Attendibilità attribuita al modello in questo scenario", 1, 7, 4, key=f"{t}_trust_ai")
    st.slider("Sicurezza della valutazione finale", 1, 7, 4, key=f"{t}_confidence")
    st.slider("Disponibilità ad accettare la sintesi del Team Leader", 1, 7, 4, key=f"{t}_leader_acceptance")
    st.slider("Necessità di confronto con gli altri analisti", 1, 7, 4, key=f"{t}_need_group")
    st.slider("Gravità percepita del contesto", 1, 7, 4, key=f"{t}_gravity")
    st.slider("Incertezza percepita dello scenario", 1, 7, 4, key=f"{t}_uncertainty")
    st.slider("Impatto strategico potenziale", 1, 7, 4, key=f"{t}_strategic")
    st.slider("Ho percepito pressione a decidere rapidamente", 1, 7, 4, key=f"{t}_pressione_1")
    st.slider("Il tempo disponibile era adeguato alla complessità", 1, 7, 4, key=f"{t}_pressione_2")
    st.slider("Ho dovuto rispondere prima di completare l'analisi", 1, 7, 4, key=f"{t}_pressione_3")
    st.slider(
        "L'analisi del modello presenta lacune, forzature o inferenze contestabili",
        1,
        7,
        4,
        key=f"{t}_critica_llm",
    )
    st.text_area(
        "Indica, se presente, l'elemento più contestabile dell'analisi del modello",
        key=f"{t}_lacuna_testo",
        max_chars=800,
    )

    if not st.session_state.get(f"{t}_completed", False):
        if st.button(f"Completa la condizione {t}", key=f"{t}_complete", type="primary"):
            temp_errors = []
            choice = st.session_state.get(f"{t}_post_choice")
            if choice is None:
                temp_errors.append("indicare se si conferma o modifica la stima")
            if choice == "Modifico la valutazione iniziale":
                post = float(st.session_state.get(f"{t}_post_slider", pre_saved))
                if abs(post - pre_saved) < 1e-9:
                    temp_errors.append("modificare effettivamente il valore oppure scegliere conferma")
            for key, label in [
                (f"{t}_post_ord", "valutazione qualitativa finale"),
                (f"{t}_suffic", "sufficienza informativa"),
                (f"{t}_motivo", "motivazione"),
            ]:
                if st.session_state.get(key, "— seleziona —") == "— seleziona —":
                    temp_errors.append(label)
            if temp_errors:
                st.error("Completa: " + "; ".join(temp_errors) + ".")
            else:
                st.session_state[f"{t}_completed"] = True
                st.rerun()
    else:
        st.success(f"Condizione {t} completata.")

if all(st.session_state.get(f"{t}_completed", False) for t in CONDIZIONI):
    st.divider()
    st.header("Invio finale")
    st.warning("Dopo l'invio le risposte non potranno essere modificate.")
    if st.button("📨 Invia il questionario", type="primary"):
        errors = validate_final_answers()
        if errors:
            st.error("Impossibile inviare:\n- " + "\n- ".join(errors))
        else:
            try:
                row = build_response_row()
                save_response(row, st.session_state["reservation_token"])
                email_ok, email_message = send_response_email(row)
                update_email_status(
                    row["session_uuid"],
                    "inviata" if email_ok else email_message,
                )
                df = load_risposte()
                persist_ok, persist_message = persist_exports(df)
                st.session_state["submission_success"] = True
                st.session_state["submission_email_message"] = (
                    email_message if email_ok else
                    "La risposta è stata salvata; l'email amministrativa non è stata inviata. " + email_message
                )
                clear_participant_state()
                st.rerun()
            except (sqlite3.Error, RuntimeError, ValueError, OSError) as exc:
                st.error(f"Invio non completato: {exc}")
