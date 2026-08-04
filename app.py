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
import gspread
from google.oauth2.service_account import Credentials


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

def get_admin_password() -> str | None:
    """Legge la password del back office esclusivamente dai Secrets di Streamlit."""
    try:
        password = str(st.secrets["admin_password"]).strip()
        return password or None
    except Exception:
        return None


ADMIN_PWD = get_admin_password()
EMAIL_DESTINAZIONE = "castiello.mauro@gmail.com"

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
    "T1": "Configurazione α",
    "T2": "Configurazione β",
    "T3": "Configurazione γ",
}
COND_CONTESTO = {
    "T1": "",
    "T2": "",
    "T3": "",
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

BRIEFING = {

"A": {

"T1": """**BRIEFING OPERATIVO — RISERVATO**

---

I sistemi di supervisione di una rete di distribuzione energetica in un'area
portuale hanno registrato quarantadue segnalazioni di accessi non previsti
nel corso delle ultime tre settimane. Il personale tecnico interno non ha
rilevato anomalie nei flussi fisici di distribuzione.

Un tecnico con accesso diretto ai log segnala connessioni da indirizzi IP
non censiti nel registro degli accessi autorizzati. Lo stesso tecnico precisa
che un ciclo di penetration test autorizzato da una società esterna si è
concluso dieci giorni prima delle prime segnalazioni, e che la fascia di
indirizzi coinvolta è la stessa utilizzata durante quel test. Il report
finale della società esterna non è ancora stato consegnato nonostante
le richieste formali del responsabile della sicurezza dell'impianto.
La società ha risposto indicando difficoltà organizzative interne.

Su un forum tecnico specializzato sono comparsi nelle stesse settimane
post anonimi con richieste di informazioni sulle vulnerabilità del
protocollo SCADA utilizzato dall'impianto. I post hanno ricevuto risposte
da profili tecnici con storico credibile.

---""",

"T2": """**BRIEFING OPERATIVO — RISERVATO**

---

Le segnalazioni tecniche sull'impianto portuale si sono intensificate.
Si registrano ora accessi a sottosistemi che controllano la distribuzione
verso utenze industriali. Il gestore ha avviato un audit interno senza
ancora produrre risultati definitivi. Il personale operativo non rileva
anomalie nei flussi fisici.

Il report del penetration test è ora disponibile. Il documento certifica
che l'attività è stata condotta su un sottoinsieme limitato di sistemi
che non comprende i sottosistemi che hanno generato le segnalazioni
recenti. Due fonti con accesso diverso all'impianto descrivono tentativi
sistematici non riconducibili ad attività tecnica autorizzata. Le due fonti
si conoscono tra loro e frequentano gli stessi ambienti professionali.

Le comunicazioni intercettate tra soggetti non identificati contengono
termini tecnici specifici dell'impianto. Il contenuto non è stato
completamente decifrato. Un ex tecnico dell'impianto che ha lasciato
la società sei mesi fa per ragioni non documentate risulta in contatto
con uno dei soggetti nelle comunicazioni. L'ex tecnico ha contattato
il suo ex responsabile nei giorni successivi all'intensificazione delle
segnalazioni, riferendo di aver ricevuto proposte di consulenza
da una società non identificata. Il responsabile non ha formalizzato
la segnalazione.

---""",

"T3": """**BRIEFING OPERATIVO — RISERVATO**

---

Nelle ultime ore si è verificata un'interruzione parziale dei sistemi
di supervisione dell'impianto portuale. I sistemi operativi di distribuzione
non risultano compromessi. Il gestore ha dichiarato uno stato di allerta
interno e ha isolato i sistemi di supervisione dalla rete principale.

L'analisi tecnica preliminare ha isolato un codice malevolo con
caratteristiche riconducibili a strumenti APT documentati. Lo stesso tipo
di codice è stato osservato in due incidenti analoghi in impianti energetici
europei negli ultimi diciotto mesi, uno dei quali si è risolto senza
conseguenze operative dopo l'isolamento dei sistemi. I log di accesso
mostrano una sequenza di operazioni avvenuta nelle ore precedenti
l'interruzione, compatibile con una fase di ricognizione dei sistemi
di supervisione. Non sono stati rilevati tentativi di accesso ai sistemi
operativi di distribuzione.

L'analisi forense completa richiede tempi non compatibili con la necessità
di una risposta immediata. Un ex tecnico dell'impianto precedentemente
segnalato ai fini investigativi non risponde ai contatti dall'ora di pranzo
di ieri. Il responsabile della sicurezza ritiene che questa coincidenza
temporale possa essere non significativa dato il contesto personale
dell'ex tecnico. Non è noto se il codice malevolo sia presente in altri
sottosistemi non ancora analizzati.

---""",
},

"B": {

"T1": """**BRIEFING OPERATIVO — RISERVATO**

---

La Financial Intelligence Unit ha trasmesso una segnalazione relativa
a movimenti finanziari attraverso una catena di società schermo in tre
giurisdizioni. I movimenti nell'arco di quattro mesi mostrano importi
sistematicamente sotto le soglie di segnalazione automatica. Le società
terminali della catena sono registrate in giurisdizioni con regime
di controllo doganale differenziato.

L'analisi evidenzia acquisti di componenti elettronici attraverso
intermediari in un Paese terzo. La classificazione dual-use di questi
componenti dipende dalla configurazione finale d'uso, non determinabile
dall'analisi finanziaria. Uno degli intestatari delle società schermo
è un collaboratore di giustizia con protezione attiva, registrato
con identità alternativa. Il collaboratore ha regolarmente dichiarato
alla struttura di protezione le sue attività commerciali ordinarie.
Non è possibile stabilire se la sua presenza nella struttura societaria
attuale sia stata dichiarata o meno. Un secondo intestatario ha un
precedente giudiziario per riciclaggio conclusosi con patteggiamento
tre anni fa, in una transazione distinta ma con struttura societaria
analoga.

---""",

"T2": """**BRIEFING OPERATIVO — RISERVATO**

---

Gli sviluppi delle ultime settimane hanno prodotto nuovi elementi
sulla struttura societaria precedentemente segnalata. Sono stati
identificati ulteriori livelli di intermediazione e nuovi soggetti.
Il volume e la frequenza delle transazioni sono aumentati.

Una fonte con accesso alla struttura riferisce che i componenti sono
destinati a un soggetto in un Paese sotto embargo internazionale,
con transito attraverso un Paese terzo con regime doganale permissivo.
La fonte ha richiesto misure di protezione in cambio della collaborazione
e non ha ancora fornito elementi verificabili indipendentemente.
Le comunicazioni intercettate tra due intestatari contengono riferimenti
a tempistiche di consegna e a un committente indicato con un nome
in codice. Il tenore delle comunicazioni è compatibile sia con una
transazione commerciale lecita sia con la gestione di un'operazione
illecita. Un bonifico di importo compatibile con i costi di trasporto
internazionale del tipo di merce indicato è stato effettuato nelle
ultime ventiquattro ore verso un conto riconducibile a un operatore
logistico in un Paese terzo. Il collaboratore di giustizia ha contattato
il proprio referente nella struttura di protezione in orari non usuali
nelle ultime quarantotto ore.

---""",

"T3": """**BRIEFING OPERATIVO — RISERVATO**

---

La situazione operativa ha registrato un'evoluzione nelle ultime ore.
La fonte ha fornito documentazione che consentirebbe di identificare
il committente finale come entità riconducibile a un Paese sotto embargo.
La consegna è indicata come imminente. Il collaboratore di giustizia
non risponde ai contatti della struttura di protezione dall'ora di pranzo
di oggi.

La fonte ha fornito documenti che identificano il committente. La stessa
fonte ha fornito in passato informazioni accurate in due casi separati,
ma non è mai stata impiegata in contesti operativi di questa portata.
I documenti non recano elementi di autenticazione verificabili in tempi
brevi. L'analisi finanziaria aggiornata conferma il bonifico verso il conto
dell'operatore logistico già segnalato. Il contenuto fisico della merce
non è stato verificato. Il legale della società terminale della catena
ha contattato nella mattinata il registro delle imprese per una richiesta
di documentazione societaria di routine, compatibile con una operazione
commerciale ordinaria in fase di chiusura.

---""",
},

"C": {

"T1": """**BRIEFING OPERATIVO — RISERVATO**

---

Il monitoraggio degli investimenti esteri in settori tecnologici sensibili
ha identificato l'acquisizione di partecipazioni minoritarie in quattro
aziende italiane da parte di un fondo sovrano estero attraverso veicoli
societari in cascata in tre giurisdizioni. Le operazioni si sono distribuite
nell'arco di diciotto mesi. Le aziende coinvolte operano in settori ad alta
densità brevettuale.

Il fondo sovrano non compare direttamente in nessuna delle operazioni.
La ricostruzione della titolarità effettiva è basata sull'analisi dei
registri societari, con lacune documentali in una delle giurisdizioni.
Due delle quattro aziende hanno ottenuto contratti con la difesa nazionale
negli ultimi tre anni per forniture di componenti non classificate. Le quattro
acquisizioni presentano importi sistematicamente inferiori alle soglie che
avrebbero attivato la notifica obbligatoria. La probabilità statistica di
questa frammentazione su quattro operazioni indipendenti è bassa, ma non
esclude strategie di ottimizzazione fiscale che producono lo stesso effetto.
Due delle aziende target hanno rifiutato in passato offerte di acquisizione
da operatori nazionali con valorizzazioni superiori. I motivi non sono
documentati pubblicamente. Le clausole contrattuali delle acquisizioni
non sono disponibili.

---""",

"T2": """**BRIEFING OPERATIVO — RISERVATO**

---

L'analisi delle acquisizioni ha prodotto nuovi elementi. Sono emersi
contatti diretti tra rappresentanti del fondo e personale tecnico delle
aziende target che vanno oltre la normale relazione tra investitore
e partecipata in quota minoritaria.

Una fonte con accesso a una delle aziende riferisce di richieste di
documentazione tecnica non prevista dagli accordi di investimento, relative
a brevetti in fase di registrazione. La richiesta è stata parzialmente evasa
prima che la direzione ne fosse informata. La stessa fonte ha sollevato
in passato segnalazioni interne su questioni non correlate, accolte solo
in parte dalla direzione aziendale. L'analisi dei flussi di comunicazione
tra le aziende e indirizzi riconducibili al fondo mostra un volume
significativamente superiore a quello atteso per una partecipazione
minoritaria di natura finanziaria. Uno dei rappresentanti del fondo
risulta aver ricoperto un incarico in un'agenzia governativa del Paese
di riferimento prima di passare al settore privato undici anni fa. Il profilo
pubblico di questo rappresentante è stato modificato nelle ultime settimane
rimuovendo il riferimento all'incarico governativo. L'analisi contrattuale
delle due aziende per cui è disponibile non evidenzia clausole anomale
di accesso a informazioni tecniche. Il trasferimento di documentazione è
avvenuto al di fuori dei canali previsti dagli accordi.

---""",

"T3": """**BRIEFING OPERATIVO — RISERVATO**

---

Una quinta azienda italiana, operante in un settore connesso a sistemi
di comunicazione per applicazioni sia civili sia militari, risulta oggetto
di un'offerta di acquisizione da parte di una società riconducibile alla
stessa catena del fondo sovrano. L'offerta è stata presentata quarantotto
ore fa al consiglio di amministrazione.

Una fonte con accesso alle strutture del fondo riferisce che le acquisizioni
precedenti costituiscono il primo stadio di un piano in due fasi, di cui
la quinta azienda rappresenta la conclusione. La fonte è stata acquisita
recentemente e non ha un track record verificabile. L'analisi comparativa
con operazioni condotte dallo stesso fondo in altri Paesi europei negli
ultimi dieci anni mostra un pattern ricorrente: acquisizioni minoritarie
in settori tecnologici sensibili seguite da un'acquisizione in un settore
con applicazioni duali. In tre casi su sei il pattern si è interrotto
prima della seconda fase. Il consiglio di amministrazione della quinta
azienda ha espresso disponibilità all'operazione nonostante la valorizzazione
proposta sia inferiore del diciotto percento rispetto alle stime di mercato.
L'azienda ha registrato un calo del fatturato nell'ultimo esercizio.
Non è disponibile la valutazione dell'impatto dell'acquisizione sui contratti
con la difesa nazionale.

---""",
},
}

# ── TESTI LLM PRECOMPILATI — 27 TESTI (3 domini × 3 condizioni × 3 versioni) ──
# Versioni: C = calibrato, S = sovrastimante, U = sottostimante
# Struttura identica: 3 paragrafi — certezza / incertezza / giudizio sufficienza
# Nessuna classificazione fonti, prosa argomentata

LLM_TESTI = {
"A":{
"T1":{
"C":"""Dal briefing emergono con certezza due elementi: il personale tecnico ha rilevato
connessioni da indirizzi non censiti nei registri autorizzati, e un ciclo di
penetration test è stato completato di recente da una società esterna senza che
la documentazione finale sia ancora disponibile. Questi due elementi coesistono
senza che sia possibile stabilire una relazione causale tra loro.

Ciò che manca è l'elemento che permetterebbe di distinguere le due ipotesi
principali. Se le anomalie rientrano nell'attività documentata dal pentest,
il quadro è privo di carattere operativo. Se sono successive o esterne a
quell'attività, il quadro cambia significativamente. La fonte tecnica interna
non ha la posizione informativa necessaria per escludere nessuna delle due.

Gli elementi disponibili non sono sufficienti per attivare misure operative
immediate. Sono invece sufficienti per richiedere con urgenza la documentazione
del penetration test e per avviare un monitoraggio tecnico rafforzato.""",

"S":"""Dal briefing emergono con certezza anomalie tecniche ricorrenti su sottosistemi
critici di un impianto energetico portuale strategico. Le connessioni non
autorizzate mostrano un pattern sistematico che difficilmente è riconducibile
a errori di configurazione o a residui di attività tecnica autorizzata.
La fonte interna è in posizione privilegiata per distinguere accessi ordinari
da accessi anomali, e la sua segnalazione non va sottovalutata.

L'assenza del report finale del penetration test è in sé un elemento di
preoccupazione: la documentazione dovrebbe essere disponibile entro tempi
certi. Il ritardo, combinato con le anomalie rilevate, suggerisce che qualcosa
non ha seguito il percorso procedurale atteso.

Gli elementi disponibili sono sufficienti per avviare misure di contenimento
tecniche immediate senza attendere la documentazione del pentest. Il rischio
di un falso positivo è significativamente inferiore al rischio di inazione
di fronte a un possibile accesso non autorizzato a infrastrutture critiche.""",

"U":"""Dal briefing emerge un quadro di anomalie tecniche che presenta spiegazioni
alternative plausibili. Le connessioni da indirizzi non censiti potrebbero
essere residui dell'attività di penetration test autorizzata, fenomeni di
configurazione errata documentati in ambienti di rete complessi, o accessi
da sottoreti non correttamente registrate nel sistema di inventario.

La fonte interna ha un accesso tecnico all'impianto ma non necessariamente
la visibilità completa sull'architettura di rete e sulle attività del team
esterno di sicurezza. La segnalazione è in buona fede ma potrebbe riflettere
una conoscenza parziale del contesto operativo complessivo.

Gli elementi disponibili non giustificano misure operative. L'acquisizione del
report del penetration test è il passo preliminare necessario prima di
qualsiasi valutazione della minaccia. Procedere senza questa informazione
rischierebbe di produrre una risposta sproporzionata a un evento tecnico
di routine.""",

},
"T2":{
"C":"""Dal briefing emergono con certezza due sviluppi rispetto alla situazione
precedente: due fonti indipendenti convergono nel descrivere tentativi
sistematici di accesso, e il report del penetration test ora disponibile
non documenta le anomalie rilevate. L'assenza di questa spiegazione tecnica
aumenta il peso degli altri elementi ma non li rende conclusivi.

Resta incerta l'identità dei soggetti nelle comunicazioni intercettate e
la natura del loro interesse verso l'impianto. Il collegamento con l'ex
dipendente è una correlazione temporale, non una prova di connessione
causale. Le comunicazioni parzialmente decifrate non consentono
di stabilire se si tratti di attori con capacità tecniche significative
o di soggetti con accesso a informazioni parziali.

Il quadro si trova in una zona di confine. La convergenza di due fonti
indipendenti e la discrepanza con il report del pentest giustificano
misure di contenimento tecnico immediate. Non giustificano ancora
una risposta operativa di più ampia portata.""",

"S":"""Dal briefing emerge un quadro in cui più elementi indipendenti convergono
nella stessa direzione. Due fonti con accesso diverso all'impianto
descrivono tentativi sistematici che non trovano spiegazione nell'attività
autorizzata. Il report del pentest, ora disponibile, conferma questa
valutazione per esclusione. La presenza di un ex dipendente nelle
comunicazioni intercettate indica un possibile vettore interno che
aumenta significativamente il rischio operativo.

L'incertezza residua riguarda l'identità e le intenzioni dei soggetti
nelle comunicazioni. Questa incertezza è reale ma non può essere
risolta attendendo — ogni ritardo nella risposta tecnica aumenta
l'esposizione dell'impianto.

Gli elementi disponibili sono sufficienti per attivare misure operative
urgenti. La combinazione di convergenza tra fonti, esclusione
dell'ipotesi benigna e possibile vettore interno supera la soglia
che giustifica un'azione immediata.""",

"U":"""Dal briefing emerge una situazione in cui la convergenza apparente tra
le fonti richiede un'analisi critica. Le due fonti HUMINT hanno accesso
diverso all'impianto e potrebbero condividere le stesse informazioni
di base attraverso canali informali, producendo una convergenza
che non è indipendente nel senso metodologico del termine.

Il collegamento tra l'ex dipendente e i soggetti nelle comunicazioni
è una correlazione che potrebbe riflettere reti sociali preesistenti
non connesse ad attività ostile. Le comunicazioni parzialmente decifrate
non consentono di escludere spiegazioni alternative lecite.

Gli elementi disponibili giustificano un approfondimento tecnico
e investigativo ma non misure operative immediate. La decifrazione
completa delle comunicazioni intercettate è il passo prioritario prima
di qualsiasi escalation della risposta.""",

},
"T3":{
"C":"""Dal briefing emerge con certezza un evento operativo concreto: i sistemi
di supervisione dell'impianto hanno subito un'interruzione causata da
codice malevolo. L'analisi tecnica preliminare indica caratteristiche
coerenti con strumenti APT, ma l'attribuzione formale non è ancora
disponibile e l'analisi forense completa richiede tempi incompatibili
con la necessità di una risposta immediata.

L'elemento più rilevante per la valutazione è la limitazione dell'attacco
ai soli sistemi di supervisione. Questo potrebbe indicare un obiettivo
di ricognizione — l'attaccante raccoglie informazioni sull'architettura
prima di agire sui sistemi operativi — oppure riflettere i limiti
tecnici dell'accesso ottenuto finora.

Gli elementi disponibili sono sufficienti per attivare misure operative
immediate sui sistemi di supervisione. La risposta non può attendere
il completamento dell'analisi forense senza aumentare significativamente
il rischio di compromissione dei sistemi operativi.""",

"S":"""Dal briefing emerge un incidente cyber in corso con caratteristiche
che rendono l'ipotesi di un attore sofisticato la più probabile.
Il codice malevolo presenta componenti già osservati in attacchi
documentati a infrastrutture energetiche europee. La limitazione
ai sistemi di supervisione è coerente con una fase di ricognizione
preparatoria — un pattern riconoscibile nell'analisi delle campagne
APT contro infrastrutture critiche.

L'incertezza residua sull'attribuzione è reale ma non modifica
la valutazione operativa. In contesti di questo tipo l'attribuzione
formale richiede sempre tempi superiori a quelli disponibili
per la risposta. La decisione di attendere una certezza analitica
completa produrrebbe un ritardo che l'attaccante potrebbe sfruttare.

Gli elementi disponibili rendono necessaria un'attivazione immediata
e completa delle misure di protezione delle infrastrutture critiche.
Il rischio di inazione supera di gran lunga il rischio di una risposta
tempestiva in assenza di attribuzione definitiva.""",

"U":"""Dal briefing emerge un incidente tecnico confermato ma la cui interpretazione
richiede cautela. Il codice malevolo rilevato presenta caratteristiche
genericamente associate a strumenti APT, ma questa categoria è ampia
e include attori con capacità e motivazioni molto diverse. La coerenza
con attacchi precedenti in altri Paesi europei è un indicatore indiretto
che non costituisce prova di connessione o coordinamento.

La limitazione ai sistemi di supervisione potrebbe indicare un attacco
nella fase iniziale, ma anche un attacco con obiettivi specifici limitati
a quella componente — non necessariamente preparatorio a un'azione
più ampia. L'analisi forense incompleta impedisce di distinguere
tra queste interpretazioni.

Gli elementi disponibili giustificano misure di contenimento tecnico
immediate sui sistemi compromessi ma non un'attivazione completa
delle misure di protezione delle infrastrutture critiche. La risposta
deve essere proporzionata all'evidenza disponibile.""",

},
},
"B":{
"T1":{
"C":"""Dal briefing emerge con certezza una struttura finanziaria anomala con
caratteristiche di layering documentate dalla FIU. Gli acquisti di materiale
dual-use attraverso intermediari in giurisdizioni con regime doganale
permissivo sono un elemento concreto. La presenza di un collaboratore
di giustizia tra gli intestatari è un fatto verificato che distingue
questa segnalazione da un caso ordinario.

Ciò che manca è la connessione tra questi elementi. Non è noto se il
collaboratore sia coinvolto consapevolmente, se sia stato utilizzato
a sua insaputa, o se la sua presenza sia una coincidenza. Non è nota
l'identità del destinatario finale del materiale dual-use né la sua
rilevanza rispetto ai regimi di controllo delle esportazioni.

Gli elementi disponibili non sono sufficienti per avviare un'indagine
formale coordinata. Sono sufficienti per due approfondimenti urgenti
in parallelo: la verifica della posizione del collaboratore di giustizia
rispetto alla struttura societaria e l'identificazione del destinatario.""",

"S":"""Dal briefing emerge una struttura che presenta troppe anomalie per essere
ricondotta a un caso di riciclaggio ordinario. La frammentazione sotto
le soglie di notifica, la scelta di giurisdizioni specifiche, l'acquisto
di materiale dual-use attraverso intermediari selezionati e la presenza
di un collaboratore di giustizia costituiscono un insieme che difficilmente
si spiega con la casualità. La segnalazione FIU non è una fonte debole —
è il risultato di un'analisi finanziaria strutturata.

Le lacune informative sul destinatario finale e sul ruolo del collaboratore
sono reali ma non annullano il peso degli elementi disponibili. In
operazioni di questo tipo le lacune sono spesso create deliberatamente
per rallentare la risposta investigativa.

Gli elementi disponibili sono sufficienti per avviare misure investigative
immediate. Attendere ulteriori approfondimenti prima di agire rischia
di consentire il completamento dell'operazione.""",

"U":"""Dal briefing emerge una segnalazione FIU che, pur presentando elementi
anomali, non supera la soglia che distingue un caso sospetto da un
caso che richiede risposta immediata. La struttura di layering è
frequente in transazioni commerciali internazionali legali in settori
con margini elevati. Il materiale dual-use è una categoria ampia
che include componenti con utilizzi prevalentemente civili.

La presenza del collaboratore di giustizia è l'elemento più significativo,
ma la sua spiegazione potrebbe essere banale — un'identità protetta
utilizzata per transazioni commerciali ordinarie senza connessione
all'attività criminale per cui collabora.

Gli elementi disponibili giustificano un monitoraggio rafforzato ma non
l'avvio di misure formali. Le risorse investigative andrebbero concentrate
sulla verifica del destinatario finale prima di qualsiasi escalation.""",

},
"T2":{
"C":"""Dal briefing emerge uno sviluppo significativo: le informazioni disponibili indicano
un destinatario finale in un Paese sotto embargo. Se questo elemento
fosse confermato, trasformerebbe la natura della segnalazione.
Il bonifico al trasportatore nelle ultime ventiquattro ore è un
elemento concreto che modifica i tempi della decisione.

L'attendibilità della fonte non è ancora verificata — una fonte che
chiede protezione in cambio di informazioni ha incentivi propri.
Il comportamento del collaboratore di giustizia rimane ambiguo:
il contatto con il referente nella struttura di protezione potrebbe
riflettere allarme, comunicazione ordinaria o qualcosa di diverso.

Gli elementi disponibili si trovano in una zona di confine tra
approfondimento e intervento. La finestra temporale indicata dalla
fonte non consente di attendere la verifica completa senza rischiare
di perdere la possibilità di intervento. Misure di contrasto
immediate sono giustificate con riserva sulla fonte.""",

"S":"""Dal briefing emerge una situazione in cui i tempi non consentono
l'ordinario processo di verifica. La convergenza tra la segnalazione
della fonte, il bonifico confermato e la destinazione indicata
produce un quadro che, anche in presenza di incertezze sulla fonte,
richiede una risposta immediata.

La richiesta di protezione da parte della fonte non ne invalida
le informazioni — spesso le fonti più preziose sono quelle che
hanno qualcosa da guadagnare dalla collaborazione e qualcosa
da perdere se le informazioni sono false. Il bonifico al trasportatore
è un elemento verificabile indipendentemente dalla fonte.

Gli elementi disponibili rendono necessario avviare misure di contrasto
immediate. La finestra di intervento è limitata e il costo
di un falso positivo è significativamente inferiore al costo
di un'inazione che consente la consegna del materiale.""",

"U":"""Dal briefing emerge una situazione in cui la fonte principale
non è ancora verificata e il comportamento del collaboratore
di giustizia introduce ulteriori incertezze. Una fonte che chiede
protezione in cambio di informazioni ha un incentivo diretto
a esagerare la gravità della situazione.

Il bonifico al trasportatore è un elemento concreto ma potrebbe
essere relativo a una transazione lecita intercettata nel momento
sbagliato. Il collegamento tra questo bonifico e il contesto
investigativo non è ancora stabilito con certezza.

Gli elementi disponibili non giustificano misure di contrasto immediate.
La verifica della fonte e del comportamento del collaboratore
sono passaggi necessari prima di qualsiasi escalation operativa.
Un intervento prematuro basato su una fonte non verificata
rischierebbe di compromettere l'intera operazione investigativa.""",

},
"T3":{
"C":"""Dal briefing emerge che le principali lacune informative precedenti
sono state colmate o superate dagli eventi. Il committente finale
è identificato. L'attendibilità della fonte è parzialmente verificata.
Il bonifico è confermato. La consegna è imminente.

Rimangono due elementi non risolti di natura diversa. Il contenuto
esatto del materiale non è verificato fisicamente — la fonte usa
una descrizione generica. La scomparsa del collaboratore introduce
una variabile operativa non controllata che potrebbe interferire
con l'intervento.

Gli elementi disponibili sono sufficienti per attivare misure di
contrasto immediate. L'incertezza sul collaboratore e sul contenuto
esatto del materiale sono elementi da gestire operativamente
nella pianificazione dell'intervento, non ragioni per rinviarlo.""",

"S":"""Dal briefing emerge un quadro in cui la convergenza degli elementi
disponibili è sufficiente per giustificare un'azione immediata senza
ulteriori verifiche. L'identificazione del committente come ente
parastatale di un Paese sotto embargo, la verifica parziale della fonte
e il bonifico confermato costituiscono una base probatoria solida
per contesti operativi che non ammettono i tempi dell'accertamento giudiziario.

La scomparsa del collaboratore non è una ragione per ritardare
l'intervento — potrebbe anzi indicare che qualcuno nella rete
è consapevole dell'operazione investigativa, rendendo urgente
un'azione prima che l'operazione sia neutralizzata.

Gli elementi disponibili rendono necessaria un'attivazione immediata
e completa delle misure di contrasto. Ogni ritardo aumenta
il rischio di perdere definitivamente la possibilità di intervento.""",

"U":"""Dal briefing emerge una situazione in cui la pressione temporale
indicata dalla fonte rischia di comprimere indebitamente il processo
decisionale. La verifica parziale dell'attendibilità non equivale
a verifica completa. Il contenuto esatto del materiale non è noto.
La scomparsa del collaboratore introduce un elemento di rischio
operativo significativo per l'intervento.

In contesti investigativi complessi, un'azione precipitosa basata
su elementi parzialmente verificati può compromettere operazioni
di più lungo periodo e mettere a rischio soggetti protetti.

Gli elementi disponibili giustificano un elevato stato di allerta
e la pianificazione dell'intervento, ma non la sua attivazione
immediata senza la verifica del contenuto del materiale
e senza chiarire la posizione del collaboratore.""",

},
},
"C":{
"T1":{
"C":"""Dal briefing emerge con certezza un pattern di acquisizioni che presenta
una caratteristica statisticamente significativa: quattro operazioni
con importi sistematicamente inferiori alle soglie di notifica obbligatoria.
La probabilità che questa frammentazione sia casuale su quattro operazioni
indipendenti è bassa. Due delle aziende target hanno contratti difesa attivi.

Ciò che manca è l'analisi delle clausole contrattuali delle acquisizioni.
In operazioni di questo tipo il valore non sta nella quota azionaria
ma nei diritti di accesso a informazioni tecniche negoziati contestualmente.
Senza questa analisi non è possibile valutare se il fondo abbia già
ottenuto quello che cercava.

Gli elementi disponibili non sono sufficienti per attivare la procedura
di golden power ma richiedono un'analisi immediata delle clausole
e un monitoraggio rafforzato dei contatti tra il fondo e il management.""",

"S":"""Dal briefing emerge un pattern che difficilmente può essere attribuito
a una strategia finanziaria ordinaria. La frammentazione sistematica
sotto le soglie di notifica su quattro operazioni distinte in diciotto
mesi indica una conoscenza precisa dei meccanismi di controllo.
La concentrazione su aziende con contratti difesa, tra tutte quelle
disponibili nel settore tecnologico italiano, non è casuale.

La mancanza dell'analisi contrattuale è una lacuna reale ma non annulla
il peso degli altri elementi. In operazioni di intelligence economica
il danno può prodursi anche attraverso contatti informali durante
il processo di acquisizione, prima della firma di qualsiasi clausola.

Gli elementi disponibili sono sufficienti per avviare immediatamente
la procedura di golden power in via cautelativa e per condurre
in parallelo l'analisi contrattuale.""",

"U":"""Dal briefing emerge un quadro che presenta elementi anomali ma che
potrebbe avere spiegazioni alternative plausibili. La frammentazione
sotto le soglie di notifica è frequente nella strutturazione di
investimenti internazionali per ragioni fiscali e non necessariamente
indica conoscenza dei meccanismi di controllo sulla sicurezza nazionale.

La presenza di aziende con contratti difesa tra le target potrebbe
riflettere criteri di selezione basati su performance finanziaria
o posizione di mercato piuttosto che interesse per le tecnologie sensibili.

Gli elementi disponibili non giustificano l'attivazione della procedura
di golden power. L'analisi delle clausole contrattuali è il passo
necessario per qualsiasi valutazione successiva.""",

},
"T2":{
"C":"""Dal briefing emerge un cambiamento significativo: non si tratta più
di inferire l'intenzione del fondo dalla struttura delle acquisizioni,
ma di valutare comportamenti anomali già osservati. La richiesta
di documentazione tecnica non prevista dagli accordi e il volume
anomalo di comunicazioni sono elementi concreti. Il trasferimento
parziale di documentazione tecnica è già avvenuto.

Il profilo del rappresentante con background in un'agenzia di intelligence
e la modifica deliberata del profilo pubblico sono elementi che aumentano
il sospetto ma non costituiscono prova. La lacuna sulla qualificazione
del materiale trasferito è critica: se include informazioni sensibili
per la sicurezza nazionale, parte del danno si è già prodotto.

Gli elementi disponibili sono sufficienti per attivare la procedura
di golden power sulle acquisizioni esistenti e per bloccare
ulteriori trasferimenti di documentazione.""",

"S":"""Dal briefing emerge un quadro in cui l'operazione di intelligence
economica è già in corso e ha già prodotto effetti concreti.
Il trasferimento parziale di documentazione tecnica non è un'ipotesi
ma un fatto. La modifica del profilo del rappresentante dopo l'avvio
dell'analisi indica consapevolezza dell'osservazione — un elemento
che aumenta l'urgenza della risposta.

In operazioni di questo tipo il tempo è un fattore critico:
ogni giorno di ritardo consente un trasferimento aggiuntivo
di informazioni che non potrà essere recuperato.

Gli elementi disponibili rendono necessaria un'attivazione immediata
della procedura di golden power, il blocco di qualsiasi trasferimento
di documentazione e la valutazione del materiale già trasferito
come priorità assoluta.""",

"U":"""Dal briefing emerge una situazione in cui il comportamento anomalo
osservato potrebbe avere spiegazioni alternative. Le richieste
di documentazione tecnica potrebbero riflettere una due diligence
approfondita legittima da parte di un investitore che vuole
comprendere il valore reale dell'asset.

Il profilo del rappresentante con background in intelligence non implica
necessariamente che stia operando per conto di un'agenzia. Molti
professionisti con questo background lavorano nel settore privato
per ragioni puramente commerciali.

Gli elementi disponibili giustificano un'analisi approfondita
del materiale trasferito ma non l'attivazione immediata
della procedura di golden power, che avrebbe conseguenze significative
sul rapporto con il fondo e sui mercati finanziari.""",

},
"T3":{
"C":"""Dal briefing emerge la fase conclusiva di un'operazione strutturata.
La quinta azienda target — settore comunicazioni militari — è
l'elemento che conferisce coerenza all'intera sequenza. La fonte
ad alta attendibilità descrive un piano preordinato. Il pattern
comparativo con operazioni analoghe in altri Paesi europei fornisce
una base empirica alla valutazione.

La disponibilità anomala del consiglio di amministrazione a una
valutazione sotto mercato e l'assenza di una valutazione di impatto
sui contratti difesa sono lacune significative ma non modificano
la valutazione principale.

Gli elementi disponibili sono sufficienti per attivare immediatamente
la procedura di golden power sull'offerta sulla quinta azienda
e per avviare una revisione delle acquisizioni già completate.""",

"S":"""Dal briefing emerge un quadro in cui ogni elemento disponibile
converge nella stessa direzione. La fonte ad alta attendibilità,
il pattern comparativo documentato, la natura dell'obiettivo finale
e la disponibilità anomala del consiglio di amministrazione
costituiscono un insieme che supera qualsiasi ragionevole soglia
di attivazione delle misure di protezione.

In operazioni di intelligence economica strutturate nel tempo
l'ultima acquisizione è spesso quella che completa il piano
e rende irreversibile il trasferimento di know-how strategico.
Il ritardo nell'attivazione aumenta il rischio di consolidamento
irreversibile della posizione del fondo.

Gli elementi disponibili rendono necessaria un'attivazione immediata
e completa di tutte le misure disponibili, inclusa la revisione
retrospettiva delle acquisizioni precedenti.""",

"U":"""Dal briefing emerge una situazione in cui la pressione verso
l'azione immediata merita una valutazione critica. La fonte
ad alta attendibilità descrive un piano preordinato ma il piano
descritto potrebbe riflettere la prospettiva della fonte piuttosto
che una realtà verificata. Il pattern comparativo con altri Paesi
europei è suggestivo ma ogni caso ha caratteristiche specifiche
che rendono difficile l'analogia diretta.

La disponibilità anomala del consiglio di amministrazione potrebbe
riflettere difficoltà finanziarie dell'azienda non note al mercato
che rendono l'offerta, anche se inferiore alle stime, l'unica
alternativa realisticamente disponibile.

Gli elementi disponibili giustificano un'analisi approfondita
e accelerata ma non l'attivazione immediata della procedura
di golden power prima che questa analisi sia completata.""",

},
},
}


# ============================================================
# CONTROBILANCIAMENTO DELLA QUALITÀ DELL'OUTPUT LLM
# ============================================================

SEQUENZE_QUALITA = {
    "S1": {
        "T1": "calibrato",
        "T2": "sovrastimante",
        "T3": "sottostimante",
    },
    "S2": {
        "T1": "sottostimante",
        "T2": "calibrato",
        "T3": "sovrastimante",
    },
    "S3": {
        "T1": "sovrastimante",
        "T2": "sottostimante",
        "T3": "calibrato",
    },
}

# Benchmark operativi preliminari, da validare con un panel indipendente.
EXPERT_BENCHMARK = {
    "A": {"T1": 35, "T2": 68, "T3": 88},
    "B": {"T1": 40, "T2": 67, "T3": 90},
    "C": {"T1": 45, "T2": 72, "T3": 90},
}

QUALITY_SHIFT = {
    "calibrato": 0,
    "sovrastimante": 20,
    "sottostimante": -20,
}

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
    "Comunicazione e media",
    "Settore privato della sicurezza",
    "Affari legali",
    "Marketing",
    "Altro",
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
    """Connessione SQLite locale, usata come copia operativa temporanea."""
    con = sqlite3.connect(str(DB_PATH), timeout=30)
    con.row_factory = sqlite3.Row
    return con


# ============================================================
# ARCHIVIO PERSISTENTE GOOGLE SHEETS
# ============================================================

RISPOSTE_SHEET = "Risposte"
PRENOTAZIONI_SHEET = "Prenotazioni"
LOG_SHEET = "Log"

PRENOTAZIONI_HEADERS = [
    "session_token",
    "participant_index",
    "created_at",
    "status",
    "completed_at",
]

LOG_HEADERS = [
    "event_timestamp",
    "event_type",
    "session_uuid",
    "participant_index",
    "team_id",
    "dominio",
    "outcome",
    "details",
]


def _google_credentials_info() -> tuple[dict[str, str], str]:
    """Costruisce le credenziali senza richiedere che tutti i campi siano nei Secrets."""
    try:
        cfg = dict(st.secrets["google_sheets"])
    except Exception as exc:
        raise RuntimeError(
            "Configurazione Google Sheets assente nei Secrets di Streamlit."
        ) from exc

    spreadsheet_id = str(cfg.pop("spreadsheet_id", "")).strip()
    if not spreadsheet_id:
        raise RuntimeError("spreadsheet_id non configurato nei Secrets.")

    required = ("project_id", "private_key", "client_email")
    missing = [field for field in required if not str(cfg.get(field, "")).strip()]
    if missing:
        raise RuntimeError(
            "Credenziali Google Sheets incomplete: " + ", ".join(missing)
        )

    private_key = str(cfg["private_key"])
    cfg["private_key"] = private_key.replace("\\n", "\n")
    cfg.setdefault("type", "service_account")
    cfg.setdefault("token_uri", "https://oauth2.googleapis.com/token")
    cfg.setdefault("auth_uri", "https://accounts.google.com/o/oauth2/auth")
    cfg.setdefault(
        "auth_provider_x509_cert_url",
        "https://www.googleapis.com/oauth2/v1/certs",
    )
    return {str(k): str(v) for k, v in cfg.items()}, spreadsheet_id


@st.cache_resource(show_spinner=False)
def get_google_spreadsheet():
    """Apre il foglio persistente condiviso con il service account."""
    credentials_info, spreadsheet_id = _google_credentials_info()
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=scopes,
        )
        client = gspread.authorize(credentials)
        return client.open_by_key(spreadsheet_id)
    except Exception as exc:
        raise RuntimeError(
            "Impossibile collegarsi a Google Sheets. "
            "Verifica Secrets, condivisione del foglio e API abilitate."
        ) from exc


def _worksheet(name: str, headers: list[str]):
    """Restituisce un worksheet e crea/verifica la riga delle intestazioni."""
    spreadsheet = get_google_spreadsheet()
    try:
        ws = spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=name,
            rows=max(200, MAX_P + 20),
            cols=max(20, len(headers) + 5),
        )

    first_row = ws.row_values(1)
    if not first_row:
        ws.append_row(headers, value_input_option="RAW")
    elif first_row != headers:
        # Per Risposte consente l'estensione dello schema senza eliminare dati.
        if name == RISPOSTE_SHEET:
            missing = [h for h in headers if h not in first_row]
            if missing:
                merged = first_row + missing
                ws.update(
                    range_name=f"A1:{gspread.utils.rowcol_to_a1(1, len(merged))}",
                    values=[merged],
                    value_input_option="RAW",
                )
        else:
            raise RuntimeError(
                f"Le intestazioni del foglio '{name}' non corrispondono allo script."
            )
    return ws


@st.cache_resource(show_spinner=False)
def get_risposte_sheet():
    return _worksheet(RISPOSTE_SHEET, list(expected_columns().keys()))


@st.cache_resource(show_spinner=False)
def get_prenotazioni_sheet():
    return _worksheet(PRENOTAZIONI_SHEET, PRENOTAZIONI_HEADERS)


@st.cache_resource(show_spinner=False)
def get_log_sheet():
    return _worksheet(LOG_SHEET, LOG_HEADERS)


def _sheet_records(ws) -> list[dict[str, Any]]:
    try:
        return ws.get_all_records(
            default_blank="",
            numericise_ignore=["all"],
        )
    except TypeError:
        # Compatibilità con versioni meno recenti di gspread.
        return ws.get_all_records(default_blank="")


def _clean_sheet_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return "" if np.isnan(value) else float(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return value


def _append_dict(ws, row: dict[str, Any], headers: list[str]) -> None:
    ws.append_row(
        [_clean_sheet_value(row.get(column, "")) for column in headers],
        value_input_option="RAW",
    )
    load_risposte.clear()
    _latest_collection_state.clear()


def _find_row_by_value(ws, column_name: str, value: Any) -> tuple[int, dict[str, Any]] | None:
    headers = ws.row_values(1)
    if column_name not in headers:
        return None
    records = _sheet_records(ws)
    target = str(value)
    for row_number, record in enumerate(records, start=2):
        if str(record.get(column_name, "")) == target:
            return row_number, record
    return None


def _update_sheet_cell_by_header(ws, row_number: int, header: str, value: Any) -> None:
    headers = ws.row_values(1)
    if header not in headers:
        raise RuntimeError(f"Colonna '{header}' assente nel foglio '{ws.title}'.")
    ws.update_cell(row_number, headers.index(header) + 1, _clean_sheet_value(value))
    load_risposte.clear()
    _latest_collection_state.clear()


def _sync_row_to_local_sqlite(row: dict[str, Any]) -> None:
    """Copia locale non autoritativa; eventuali errori non compromettono Google Sheets."""
    con = get_conn()
    try:
        cols = list(row.keys())
        col_sql = ",".join(f'"{c}"' for c in cols)
        placeholders = ",".join("?" for _ in cols)
        con.execute(
            f"INSERT OR REPLACE INTO risposte ({col_sql}) VALUES ({placeholders})",
            [row[c] for c in cols],
        )
        con.commit()
    finally:
        con.close()


def _sync_reservation_to_local(
    session_token: str,
    participant_index: int,
    created_at: str,
    completed: int = 0,
) -> None:
    con = get_conn()
    try:
        con.execute(
            """
            INSERT OR REPLACE INTO reservations(
                session_token, participant_index, created_at, completed
            ) VALUES (?, ?, ?, ?)
            """,
            (session_token, participant_index, created_at, completed),
        )
        con.commit()
    finally:
        con.close()


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
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS insertion_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                session_uuid TEXT,
                participant_index INTEGER,
                team_id INTEGER,
                dominio TEXT,
                outcome TEXT NOT NULL,
                details TEXT
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


NUMERIC_BASE_COLUMNS = {
    "participant_index",
    "team_id",
    "posizione_team",
    "coordination",
    "domain_experience",
    "ai_use",
    "ai_critical",
    "ai_llm_use",
    "ai_llm_trust",
}

NUMERIC_T_SUFFIXES = {
    "ai_reference",
    "pre_ai",
    "conf_pre",
    "post_ai",
    "llm_utile",
    "trust_ai",
    "confidence",
    "leader_acceptance",
    "need_group",
    "gravity",
    "uncertainty",
    "strategic",
    "pressione_1",
    "pressione_2",
    "pressione_3",
    "critica_llm",
    "delta_raw",
    "convergence_C",
    "appropriate_reliance_AR",
    "cognitive_surrender_CS",
    "pressure_P",
    "context_G",
    "hierarchy_H",
    "flexibility_F",
}


def coerce_numeric_response_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Converte in numerico i campi restituiti da Google Sheets come testo."""
    result = df.copy()
    numeric_columns = set(NUMERIC_BASE_COLUMNS)

    for t in CONDIZIONI:
        numeric_columns.update(f"{t}_{suffix}" for suffix in NUMERIC_T_SUFFIXES)

    for column in numeric_columns:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce")

    return result


@st.cache_data(ttl=60, show_spinner=False)
def load_risposte() -> pd.DataFrame:
    """Carica le risposte dall'archivio persistente Google Sheets."""
    ws = get_risposte_sheet()
    records = _sheet_records(ws)
    columns = list(expected_columns().keys())
    if not records:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(records)
    for column in columns:
        if column not in df.columns:
            df[column] = np.nan
    df = df[columns]

    df = coerce_numeric_response_columns(df)

    return df.sort_values(
        ["participant_index", "timestamp"],
        na_position="last",
    ).reset_index(drop=True)


def completed_count() -> int:
    df = load_risposte()
    if df.empty or "session_uuid" not in df.columns:
        return 0
    return int(df["session_uuid"].astype(str).replace("", np.nan).dropna().nunique())


@st.cache_data(ttl=60, show_spinner=False)
def _latest_collection_state() -> bool | None:
    """Restituisce True=chiusa, False=aperta, None=nessuna impostazione."""
    ws = get_log_sheet()
    records = _sheet_records(ws)
    for record in reversed(records):
        event = str(record.get("event_type", ""))
        if event == "rilevazione_chiusa":
            return True
        if event == "rilevazione_aperta":
            return False
    return None


def is_closed() -> bool:
    try:
        explicit = _latest_collection_state()
        if explicit is not None:
            return explicit
        return completed_count() >= MAX_P
    except gspread.exceptions.APIError as exc:
        # Evita il blocco dell'intera app in caso di quota temporaneamente esaurita.
        if getattr(exc, "response", None) is not None and exc.response.status_code == 429:
            st.warning(
                "Google Sheets ha raggiunto temporaneamente il limite di lettura. "
                "Attendi circa un minuto e ricarica la pagina."
            )
            st.stop()
        raise


def set_closed(value: bool) -> None:
    log_event(
        event_type="rilevazione_chiusa" if value else "rilevazione_aperta",
        outcome="ok",
        details="Impostazione persistente salvata su Google Sheets.",
    )


def _active_and_completed_indices() -> tuple[set[int], set[int]]:
    responses = load_risposte()
    completed: set[int] = set()
    if not responses.empty and "participant_index" in responses.columns:
        completed = {
            int(value)
            for value in pd.to_numeric(
                responses["participant_index"], errors="coerce"
            ).dropna()
        }

    now = datetime.now()
    threshold = now - timedelta(hours=RESERVATION_HOURS)
    reservations = _sheet_records(get_prenotazioni_sheet())
    active: set[int] = set()

    for record in reservations:
        status = str(record.get("status", "")).strip().lower()
        if status != "attiva":
            continue
        try:
            created_at = datetime.fromisoformat(str(record.get("created_at", "")))
            participant_index = int(record.get("participant_index"))
        except (TypeError, ValueError):
            continue
        if created_at >= threshold and participant_index not in completed:
            active.add(participant_index)

    return completed, active


def reserve_slot() -> tuple[str, int]:
    """Riserva uno slot persistente; risolve anche rare collisioni simultanee."""
    ws = get_prenotazioni_sheet()

    for attempt in range(8):
        token = str(uuid.uuid4())
        created_at = datetime.now().isoformat(timespec="microseconds")
        completed, active = _active_and_completed_indices()
        available = next(
            (i for i in range(MAX_P) if i not in completed and i not in active),
            None,
        )
        if available is None:
            raise RuntimeError("Non sono disponibili ulteriori slot per la rilevazione.")

        _append_dict(
            ws,
            {
                "session_token": token,
                "participant_index": available,
                "created_at": created_at,
                "status": "attiva",
                "completed_at": "",
            },
            PRENOTAZIONI_HEADERS,
        )

        # Controllo anti-collisione: per lo stesso indice vince la prenotazione
        # attiva con timestamp più antico; le altre ritentano su un nuovo indice.
        records = _sheet_records(ws)
        contenders: list[tuple[str, str, int]] = []
        for row_number, record in enumerate(records, start=2):
            try:
                same_index = int(record.get("participant_index")) == int(available)
            except (TypeError, ValueError):
                same_index = False
            if same_index and str(record.get("status", "")).lower() == "attiva":
                contenders.append(
                    (
                        str(record.get("created_at", "")),
                        str(record.get("session_token", "")),
                        row_number,
                    )
                )

        contenders.sort(key=lambda item: (item[0], item[1]))
        if contenders and contenders[0][1] == token:
            try:
                _sync_reservation_to_local(token, int(available), created_at, 0)
            except Exception:
                pass
            return token, int(available)

        own = next((item for item in contenders if item[1] == token), None)
        if own:
            _update_sheet_cell_by_header(ws, own[2], "status", "annullata_collisione")

    raise RuntimeError(
        "Non è stato possibile riservare uno slot a causa di accessi simultanei. "
        "Riprova tra pochi secondi."
    )


def save_response(row: dict[str, Any], reservation_token: str) -> None:
    """Salva prima su Google Sheets e poi crea una copia locale SQLite."""
    expected = expected_columns()
    unknown = set(row) - set(expected)
    if unknown:
        raise ValueError(f"Colonne non previste: {sorted(unknown)}")

    reservations_ws = get_prenotazioni_sheet()
    reservation_match = _find_row_by_value(
        reservations_ws,
        "session_token",
        reservation_token,
    )
    if not reservation_match:
        raise RuntimeError("Prenotazione non trovata o scaduta.")

    reservation_row_number, reservation = reservation_match
    status = str(reservation.get("status", "")).strip().lower()
    if status == "completata":
        raise RuntimeError("Questa sessione è già stata inviata.")
    if status != "attiva":
        raise RuntimeError("La prenotazione non è più attiva.")

    try:
        reserved_index = int(reservation.get("participant_index"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Indice della prenotazione non valido.") from exc

    if reserved_index != int(row["participant_index"]):
        raise RuntimeError("Lo slot della sessione non coincide con la risposta.")

    responses_ws = get_risposte_sheet()
    session_uuid = str(row.get("session_uuid", ""))
    if session_uuid and _find_row_by_value(responses_ws, "session_uuid", session_uuid):
        raise RuntimeError("Questa risposta risulta già acquisita.")

    existing_index = _find_row_by_value(
        responses_ws,
        "participant_index",
        int(row["participant_index"]),
    )
    if existing_index:
        raise RuntimeError(
            "Lo slot risulta già completato da un'altra risposta. "
            "Contatta il responsabile della rilevazione."
        )

    headers = responses_ws.row_values(1)
    _append_dict(responses_ws, row, headers)

    _update_sheet_cell_by_header(
        reservations_ws,
        reservation_row_number,
        "status",
        "completata",
    )
    _update_sheet_cell_by_header(
        reservations_ws,
        reservation_row_number,
        "completed_at",
        datetime.now().isoformat(timespec="seconds"),
    )

    try:
        _sync_row_to_local_sqlite(row)
        _sync_reservation_to_local(
            reservation_token,
            int(row["participant_index"]),
            str(reservation.get("created_at", "")),
            1,
        )
    except Exception:
        # Google Sheets è l'archivio autoritativo; la copia SQLite è secondaria.
        pass


def update_email_status(session_uuid: str, status: str) -> None:
    ws = get_risposte_sheet()
    match = _find_row_by_value(ws, "session_uuid", session_uuid)
    if match:
        row_number, _ = match
        _update_sheet_cell_by_header(ws, row_number, "email_status", status)

    con = get_conn()
    try:
        con.execute(
            "UPDATE risposte SET email_status=? WHERE session_uuid=?",
            (status, session_uuid),
        )
        con.commit()
    finally:
        con.close()


def log_event(
    event_type: str,
    row: dict[str, Any] | None = None,
    outcome: str = "ok",
    details: str = "",
) -> None:
    """Registra eventi tecnici persistenti senza metadati del browser."""
    row = row or {}
    event_row = {
        "event_timestamp": datetime.now().isoformat(timespec="seconds"),
        "event_type": str(event_type),
        "session_uuid": row.get("session_uuid", ""),
        "participant_index": row.get("participant_index", ""),
        "team_id": row.get("team_id", ""),
        "dominio": row.get("dominio", ""),
        "outcome": str(outcome),
        "details": str(details)[:1500],
    }

    _append_dict(get_log_sheet(), event_row, LOG_HEADERS)

    # Copia locale secondaria.
    con = get_conn()
    try:
        con.execute(
            """
            INSERT INTO insertion_logs (
                event_timestamp, event_type, session_uuid, participant_index,
                team_id, dominio, outcome, details
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(event_row[column] for column in LOG_HEADERS),
        )
        con.commit()
    finally:
        con.close()


def load_insertion_logs() -> pd.DataFrame:
    records = _sheet_records(get_log_sheet())
    if not records:
        return pd.DataFrame(columns=["log_id"] + LOG_HEADERS)
    df = pd.DataFrame(records)
    df.insert(0, "log_id", range(1, len(df) + 1))
    return df.iloc[::-1].reset_index(drop=True)


def reset_database() -> None:
    """Cancella risposte e prenotazioni anche dal foglio persistente; conserva il Log."""
    responses_ws = get_risposte_sheet()
    reservations_ws = get_prenotazioni_sheet()

    responses_ws.clear()
    responses_ws.append_row(list(expected_columns().keys()), value_input_option="RAW")
    reservations_ws.clear()
    reservations_ws.append_row(PRENOTAZIONI_HEADERS, value_input_option="RAW")

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

    log_event(
        event_type="rilevazione_aperta",
        outcome="ok",
        details="Reset completo: risposte e prenotazioni eliminate; log conservato.",
    )


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
        mittente = str(cfg["mittente"]).strip()
        password = str(cfg["password"]).replace(" ", "").strip()
        if not mittente or not password:
            return None
        return {
            "mittente": mittente,
            "password": password,
            "destinatario": EMAIL_DESTINAZIONE,
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
        logs_df = load_insertion_logs()
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
        if not logs_df.empty:
            attach_bytes(
                msg,
                logs_df.to_csv(index=False).encode("utf-8-sig"),
                "studio2_log_inserimenti.csv",
            )
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



def show_llm_output(dominio: str, t: str, quality: str) -> dict[str, Any]:
    """Mostra al partecipante soltanto l'analisi argomentata del modello.

    La stima quantitativa, la valutazione ordinale e la qualità sperimentale
    dell'output restano nascoste nell'interfaccia e vengono conservate nel
    database esclusivamente per le successive analisi.
    """
    output = llm_output(dominio, t, quality)
    st.info(
        "**Sistema di supporto analitico — output precompilato del modello linguistico**\n\n"
        "Il modello ha elaborato le stesse informazioni del briefing e presenta "
        "la propria analisi argomentata."
    )
    st.markdown("### Analisi argomentata")
    st.markdown(output["analysis"])
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
            # Variabili sperimentali interne: non sono mostrate al partecipante,
            # ma vengono conservate per ricostruire la condizione assegnata
            # e calcolare affidamento appropriato e resa cognitiva.
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
            "Confermo la mia valutazione iniziale",
            "Modifico la valutazione iniziale",
        }:
            errors.append(f"{t}: scegli Confermo la mia valutazione iniziale oppure Modifico la valutazione iniziale")
        if choice == "Modifico la valutazione iniziale":
            pre = float(st.session_state[f"{t}_pre_saved"])
            post = float(st.session_state.get(f"{t}_post_slider", pre))
            if abs(post - pre) < 1e-9:
                errors.append(f"{t}: hai scelto Modifico la valutazione iniziale, ma lo slider non è stato spostato")
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

def torna_al_questionario() -> None:
    """Esce dal back office azzerando il campo password in modo compatibile con Streamlit."""
    st.session_state["admin_password_input"] = ""


init_db()

st.title("Questionario Sistema 3 — Studio 2")
st.markdown(
    "Valutazione individuale, qualità dell'output LLM e mediazione organizzativa del Sistema 3"
)

admin = st.sidebar.text_input(
    "Password back office",
    type="password",
    key="admin_password_input",
)

if admin:
    if ADMIN_PWD is None:
        st.sidebar.error(
            "Password del back office non configurata nei Secrets di Streamlit."
        )
    elif admin != ADMIN_PWD:
        st.sidebar.error("Password errata. Controlla e riprova.")

# ------------------------------------------------------------
# BACK OFFICE
# ------------------------------------------------------------
if ADMIN_PWD is not None and admin == ADMIN_PWD:
    st.sidebar.success("Back office attivo")

    st.sidebar.button(
        "← Torna al questionario",
        key="back_to_questionnaire",
        on_click=torna_al_questionario,
    )

    st.header("Back Office — Studio 2")
    df = coerce_numeric_response_columns(load_risposte())

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
    email_cfg = get_email_config()
    c4.metric(
        "Destinazione email",
        email_cfg["destinatario"] if email_cfg else "Non configurata",
    )

    with st.expander("📥 Importa risposte già acquisite in Google Sheets"):
        st.caption(
            "Usa questa funzione una sola volta per trasferire gli Excel precedenti. "
            "Le righe già presenti, riconosciute tramite session_uuid o participant_index, "
            "non vengono duplicate."
        )
        historical_file = st.file_uploader(
            "Seleziona un file Excel storico",
            type=["xlsx"],
            key="historical_excel_import",
        )
        if historical_file is not None and st.button(
            "Importa nel foglio Risposte",
            key="import_historical_excel_button",
        ):
            try:
                historical_df = pd.read_excel(historical_file, sheet_name="Risposte")
                historical_df = coerce_numeric_response_columns(historical_df)
                required_headers = list(expected_columns().keys())
                missing_headers = [
                    column for column in required_headers
                    if column not in historical_df.columns
                ]
                if missing_headers:
                    raise ValueError(
                        "Il file non è compatibile. Colonne mancanti: "
                        + ", ".join(missing_headers[:15])
                    )

                ws = get_risposte_sheet()
                existing = load_risposte()
                existing_uuids = set(
                    existing.get("session_uuid", pd.Series(dtype=str))
                    .astype(str)
                    .replace("", np.nan)
                    .dropna()
                )
                existing_indices = set(
                    pd.to_numeric(
                        existing.get("participant_index", pd.Series(dtype=float)),
                        errors="coerce",
                    ).dropna().astype(int)
                )

                imported = 0
                skipped = 0
                for _, historical_row in historical_df.iterrows():
                    row_dict = {
                        column: _clean_sheet_value(historical_row.get(column, ""))
                        for column in required_headers
                    }
                    session_uuid = str(row_dict.get("session_uuid", ""))
                    participant_raw = row_dict.get("participant_index", "")
                    try:
                        participant_index = int(float(participant_raw))
                    except (TypeError, ValueError):
                        skipped += 1
                        continue

                    if (
                        (session_uuid and session_uuid in existing_uuids)
                        or participant_index in existing_indices
                    ):
                        skipped += 1
                        continue

                    _append_dict(ws, row_dict, ws.row_values(1))
                    existing_indices.add(participant_index)
                    if session_uuid:
                        existing_uuids.add(session_uuid)
                    imported += 1

                log_event(
                    event_type="importazione_storica",
                    outcome="ok",
                    details=f"Importate {imported} righe; ignorate {skipped} righe.",
                )
                st.success(
                    f"Importazione completata: {imported} risposte aggiunte; "
                    f"{skipped} ignorate perché duplicate o non valide."
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Importazione non completata: {exc}")

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
        try:
            log_event(
                event_type="test_email",
                outcome="ok" if ok else "errore",
                details=message,
            )
        except Exception:
            pass
        (st.success if ok else st.error)(message)
    conferma_reset = st.text_input(
        "Per cancellare tutte le risposte scrivi esattamente: CANCELLA",
        key="conferma_reset",
        help="Questa conferma evita cancellazioni accidentali dei dati.",
    )

    if controls[3].button("🗑️ Reset completo"):
        if conferma_reset != "CANCELLA":
            st.error("Reset annullato: scrivi esattamente CANCELLA per confermare.")
        else:
            try:
                log_event(
                    event_type="reset_database",
                    outcome="ok",
                    details="Reset completo eseguito dal back office.",
                )
            except Exception:
                pass
            reset_database()
            st.success(
                "Database e file di esportazione eliminati. "
                "Il log degli eventi è stato conservato."
            )
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

        st.subheader("Log degli inserimenti")
        logs_df = load_insertion_logs()
        if logs_df.empty:
            st.info("Nessun evento registrato.")
        else:
            st.dataframe(logs_df, hide_index=True, use_container_width=True)
            st.download_button(
                "⬇️ Scarica log inserimenti",
                logs_df.to_csv(index=False).encode("utf-8-sig"),
                "studio2_log_inserimenti.csv",
                "text/csv",
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

if is_closed():
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

    if COND_CONTESTO[t]:
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
    show_llm_output(dominio, t, quality)

    st.subheader("Sezione III — Valutazione finale")
    st.info("""
### Come compilare questa sezione

Dopo aver letto la valutazione dell'AI hai due possibilità:

✅ **Confermare** la tua valutazione iniziale  
(se l'AI non ha modificato il tuo giudizio)

oppure

✅ **Modificare** la tua valutazione iniziale  
(spostando lo slider sul nuovo valore che ritieni corretto).

Per poter proseguire è necessario scegliere una delle due opzioni.
""")

    st.markdown("### Dopo aver letto il parere dell'AI")
    st.markdown("**Indica quale delle seguenti situazioni descrive il tuo caso:**")
    post_choice = st.radio(
        "Scelta relativa alla valutazione finale",
        [
            "Confermo la mia valutazione iniziale",
            "Modifico la valutazione iniziale",
        ],
        index=None,
        key=f"{t}_post_choice",
        label_visibility="collapsed",
    )
    if post_choice == "Confermo la mia valutazione iniziale":
        st.metric("Valutazione finale", f"{pre_saved:.0f}%")
    elif post_choice == "Modifico la valutazione iniziale":
        st.slider(
            "Nuova probabilità stimata (0–100)",
            0,
            100,
            int(pre_saved),
            key=f"{t}_post_slider",
        )
        st.markdown(
            "<p style='color:#c62828; font-weight:700; margin-top:0.25rem;'>"
            "Se hai scelto di modificare la valutazione, sposta lo slider sul nuovo valore."
            "</p>",
            unsafe_allow_html=True,
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
                if choice is None or (
                    choice == "Modifico la valutazione iniziale"
                    and abs(float(st.session_state.get(f"{t}_post_slider", pre_saved)) - pre_saved) < 1e-9
                ):
                    st.error("""
⚠ Prima di continuare:

• se l'AI **NON** ha modificato il tuo giudizio seleziona **Confermo la mia valutazione iniziale**;

• se invece ha modificato il tuo giudizio seleziona **Modifico la valutazione iniziale** e sposta lo slider sul nuovo valore.
""")
                other_errors = [
                    error for error in temp_errors
                    if error not in {
                        "indicare se si conferma o modifica la stima",
                        "modificare effettivamente il valore oppure scegliere conferma",
                    }
                ]
                if other_errors:
                    st.warning(
                        "Completa anche i seguenti campi: " + "; ".join(other_errors) + "."
                    )
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
                log_event(
                    event_type="risposta_salvata",
                    row=row,
                    outcome="ok",
                    details="Risposta inserita correttamente nel database.",
                )
                email_ok, email_message = send_response_email(row)
                log_event(
                    event_type="invio_email",
                    row=row,
                    outcome="ok" if email_ok else "errore",
                    details=email_message,
                )
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
            except (sqlite3.Error, RuntimeError, ValueError, OSError, gspread.GSpreadException) as exc:
                try:
                    log_event(
                        event_type="errore_inserimento",
                        row=locals().get("row", {}),
                        outcome="errore",
                        details=f"{type(exc).__name__}: {exc}",
                    )
                except Exception:
                    pass
                st.error(f"Invio non completato: {exc}")