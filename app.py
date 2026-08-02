"""
Script2.py — Studio 2
=====================
Questionario Sistema 3 — Versione estesa con output LLM precompilato.
Tre domini (A: infrastrutture, B: criminalità, C: intelligence economica).
ABM e Monte Carlo integrati nel back office.
Password admin: sasa
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
import smtplib
import io
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

st.set_page_config(
    page_title="Questionario Sistema 3 — Studio 2",
    page_icon="🧠",
    layout="wide"
)

# ============================================================
# CONFIGURAZIONE
# ============================================================

OUTPUT_DIR = Path(r"C:\Users\casti\OneDrive\Desktop\1_SOCIO_FISICA\studio2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH       = OUTPUT_DIR / "studio2_risposte.sqlite"
CSV_RESPONSES = OUTPUT_DIR / "studio2_01_risposte.csv"

AI_COSTANTE   = 65
ADMIN_PWD     = "sasa"
MAX_P         = 90   # 10 team da 9 — 30 per gruppo
N_SYNTH       = 20
N_MC          = 75
BASE_SEED     = 2026

AREE_OPERATIVE = ["Intelligence / sicurezza","Investigativa / law enforcement"]
AREE_CIVILI    = ["Cyber / tecnologia","Economico-finanziaria",
                   "OSINT / analisi fonti aperte","Accademica / ricerca",
                   "Linguistica / area studies"]

ROLE_INFLUENCE = {
    "Team Leader":    1.00,
    "Analista Senior":0.70,
    "Analista Junior":0.45,
    "Analista Civile":0.55,
}

ORDINI = ["T1-T2-T3","T2-T3-T1","T3-T1-T2"]
# Versioni LLM: C=calibrato, S=sovrastimante, U=sottostimante
# Controbilanciamento tra partecipanti
VERSIONI_LLM = ["C","S","U"]

COND_LABEL = {
    "T1":"Configurazione α — Sessione analitica ordinaria",
    "T2":"Configurazione β — Sessione analitica straordinaria",
    "T3":"Configurazione γ — Sessione analitica di crisi",
}

COND_CONTESTO = {
    "T1": "**Sessione analitica — Configurazione α**",
    "T2": "**Sessione analitica — Configurazione β**",
    "T3": "**Sessione analitica — Configurazione γ**",
}

# ── DOMINI ──────────────────────────────────────────────────
DOMINI = {"A":"Infrastrutture critiche",
           "B":"Criminalità organizzata",
           "C":"Intelligence economica"}

DOMANDA = {
    "A": ("Gli elementi disponibili costituiscono evidenza di una minaccia "
          "operativa alle infrastrutture critiche che richieda l'attivazione "
          "immediata delle misure di protezione?"),
    "B": ("Gli elementi disponibili costituiscono evidenza sufficiente per "
          "avviare un'indagine formale coordinata con attivazione delle "
          "misure di contrasto?"),
    "C": ("Gli elementi disponibili costituiscono evidenza di un'operazione "
          "di acquisizione ostile che richieda l'attivazione della procedura "
          "di golden power?"),
}

# ── BRIEFING ────────────────────────────────────────────────
BRIEFING = {

"A":{
"T1":"""**BRIEFING OPERATIVO — RISERVATO**

---

**Contesto operativo.** I sistemi di supervisione di una rete di distribuzione
energetica in un'area portuale hanno registrato accessi non previsti nel
registro degli utenti autorizzati. Il sistema di controllo ha generato
quarantadue segnalazioni nel corso delle ultime tre settimane. Il gestore
dell'impianto riferisce che il personale tecnico interno non ha rilevato
anomalie operative nei flussi di distribuzione.

**Fonte primaria.** Un tecnico con accesso diretto ai log di sistema segnala
connessioni da indirizzi IP non censiti nel registro degli accessi autorizzati.
Lo stesso tecnico precisa che un ciclo di penetration test autorizzato è stato
completato dieci giorni prima delle prime segnalazioni dalla stessa fascia
di indirizzi. Il report finale del test non è ancora stato consegnato
dalla società incaricata.

**Elemento di corroborazione.** Su un forum tecnico specializzato sono comparsi
nelle ultime settimane post con richieste di informazioni sulle vulnerabilità
del protocollo SCADA utilizzato dall'impianto. L'autore usa un profilo anonimo
creato recentemente. I post hanno ricevuto risposte da profili tecnici esperti.

**Elemento anomalo.** Il responsabile della sicurezza dell'impianto ha richiesto
alla società incaricata del penetration test di accelerare la consegna del
report finale. La società ha risposto indicando difficoltà organizzative interne
senza fornire una data certa.

**Lacuna informativa.** Non è disponibile il report del penetration test.
Non è noto se gli indirizzi IP non censiti appartengano alla sottorete
utilizzata dalla società esterna durante il test o a soggetti terzi.

**Fonti:** tecnica interna (attendibilità buona), OSINT (verificata),
documentazione procedurale (parzialmente disponibile).

---""",

"T2":"""**BRIEFING OPERATIVO — RISERVATO**

---

**Contesto operativo.** Le segnalazioni tecniche sull'impianto portuale
si sono intensificate. Si registrano ora tentativi di accesso a sottosistemi
che controllano la distribuzione verso utenze industriali. Il gestore
ha avviato un audit interno ma non ha ancora prodotto risultati definitivi.
Il personale operativo non segnala anomalie nei flussi fisici.

**Fonte primaria.** Il report finale del penetration test è ora disponibile.
Il documento certifica che l'attività è stata condotta su un sottoinsieme
limitato di sistemi e non include i sottosistemi che hanno generato
le segnalazioni recenti. Due fonti con accesso diverso all'impianto
descrivono tentativi sistematici non riconducibili ad attività tecnica
autorizzata. Le due fonti si conoscono tra loro.

**Elemento di corroborazione.** Le comunicazioni intercettate tra soggetti
non identificati contengono termini tecnici specifici dell'impianto.
Il contenuto non è stato completamente decifrato. Un ex tecnico
dell'impianto, che ha lasciato la società sei mesi fa per ragioni
non documentate, risulta in contatto con uno dei soggetti nelle comunicazioni.

**Elemento anomalo.** L'ex tecnico ha contattato il suo ex responsabile
nei giorni successivi all'intensificazione delle segnalazioni,
riferendo di aver ricevuto proposte di consulenza da una società
non identificata. Il responsabile non ha formalizzato la segnalazione.

**Lacuna informativa.** L'identità dei soggetti nelle comunicazioni
intercettate non è stata stabilita. Non è chiaro se le due fonti HUMINT
condividano le stesse informazioni di base attraverso canali informali.

**Fonti:** documentazione tecnica (verificata), HUMINT (attendibilità
da verificare per indipendenza), SIGINT (parzialmente decifrata).

---""",

"T3":"""**BRIEFING OPERATIVO — RISERVATO**

---

**Contesto operativo.** Nelle ultime ore si è verificata un'interruzione
parziale dei sistemi di supervisione dell'impianto portuale. I sistemi
operativi di distribuzione non risultano compromessi. Il gestore
ha dichiarato uno stato di allerta interno e ha isolato i sistemi
di supervisione dalla rete principale. Il personale tecnico esterno
è stato convocato per un'analisi d'emergenza.

**Fonte primaria.** L'analisi tecnica preliminare ha isolato un codice
malevolo nei sistemi di supervisione con caratteristiche riconducibili
a strumenti APT documentati. Lo stesso tipo di codice è stato
osservato in due incidenti analoghi in impianti energetici europei
negli ultimi diciotto mesi, uno dei quali si è risolto senza conseguenze
operative significative dopo l'isolamento dei sistemi.

**Elemento di corroborazione.** I log di accesso mostrano una sequenza
di operazioni avvenuta nelle ore precedenti l'interruzione, compatibile
con una fase di ricognizione dei sistemi di supervisione. Non sono
stati rilevati tentativi di accesso ai sistemi operativi di distribuzione.

**Elemento anomalo.** Un ex tecnico dell'impianto non risponde
alle chiamate dal giorno precedente l'interruzione. Il responsabile
della sicurezza dell'impianto ritiene che questa coincidenza temporale
possa essere non significativa dato il contesto personale dell'ex tecnico.

**Lacuna informativa.** L'analisi forense completa richiede tempi
non compatibili con la necessità di una risposta operativa immediata.
Non è noto se il codice malevolo sia ancora attivo in altri sottosistemi
non ancora analizzati.

**Fonti:** tecnica (in analisi, parzialmente disponibile), comparativa
(verificata), operativa (in corso).

---""",

},

"B":{
"T1":"""**BRIEFING OPERATIVO — RISERVATO**

---

**Contesto operativo.** La Financial Intelligence Unit ha trasmesso
una segnalazione relativa a movimenti finanziari anomali attraverso
una catena di società schermo in tre giurisdizioni. I movimenti
complessivi nell'arco di quattro mesi mostrano una struttura
frammentata con importi sotto le soglie di segnalazione automatica.
Le società terminali della catena sono registrate in giurisdizioni
con regime di controllo doganale differenziato.

**Fonte primaria.** L'analisi della segnalazione FIU evidenzia acquisti
di componenti elettronici attraverso intermediari in un Paese terzo.
La classificazione dual-use di questi componenti dipende dalla
configurazione finale, non determinabile dall'analisi finanziaria.
Uno degli intestatari delle società schermo è un collaboratore
di giustizia con protezione attiva, registrato con identità alternativa.

**Elemento di corroborazione.** Un precedente giudiziario per riciclaggio,
conclusosi con patteggiamento tre anni fa, coinvolge un secondo intestatario
in una transazione distinta ma con struttura societaria analoga.

**Elemento anomalo.** Il collaboratore di giustizia ha regolarmente
dichiarato alla struttura di protezione le sue attività commerciali.
Non è possibile stabilire se la sua presenza nella struttura societaria
attuale sia stata dichiarata o meno.

**Lacuna informativa.** Non è nota la classificazione esatta dei componenti
acquistati né l'identità del destinatario finale della merce.
Non è disponibile la posizione della struttura di protezione
riguardo all'attività commerciale del collaboratore.

**Fonti:** FIU (verificata), anagrafica giudiziaria (verificata),
struttura di protezione (non consultata).

---""",

"T2":"""**BRIEFING OPERATIVO — RISERVATO**

---

**Contesto operativo.** Gli sviluppi investigativi nelle ultime settimane
hanno prodotto nuovi elementi sulla struttura societaria precedentemente
segnalata. Sono stati identificati ulteriori livelli di intermediazione
e nuovi soggetti. L'attività della struttura è aumentata in termini
di volume e frequenza delle transazioni.

**Fonte primaria.** Una fonte con accesso alla struttura riferisce che
i componenti sono destinati a un soggetto in un Paese sotto embargo
internazionale, con transito attraverso un Paese terzo. La fonte
ha richiesto misure di protezione in cambio della collaborazione
e non ha ancora fornito elementi verificabili indipendentemente.
Il collaboratore di giustizia ha contattato il proprio referente
nella struttura di protezione in orari non usuali nelle ultime
quarantotto ore.

**Elemento di corroborazione.** Le comunicazioni intercettate tra
due intestatari contengono riferimenti a tempistiche di consegna
e a un committente indicato con un nome in codice. Il tenor delle
comunicazioni è compatibile sia con una transazione commerciale
lecita sia con la gestione di un'operazione illecita.

**Elemento anomalo.** Un bonifico di importo compatibile con i costi
di trasporto internazionale del tipo di merce indicato è stato
effettuato nelle ultime ventiquattro ore verso un conto riconducibile
a un operatore logistico in un Paese terzo.

**Lacuna informativa.** L'attendibilità della fonte non è ancora
verificata. Non è chiara la natura dei contatti del collaboratore
con la struttura di protezione né se stia operando su mandato
non dichiarato.

**Fonti:** HUMINT (attendibilità non verificata), SIGINT (verificata),
finanziaria (verificata).

---""",

"T3":"""**BRIEFING OPERATIVO — RISERVATO**

---

**Contesto operativo.** La situazione operativa ha registrato
un'evoluzione nelle ultime ore. La fonte ha fornito documentazione
che consente di identificare il committente finale. La consegna
è indicata come imminente secondo le informazioni disponibili.
Il collaboratore di giustizia non risponde ai contatti della struttura
di protezione dall'ora di pranzo di oggi.

**Fonte primaria.** La fonte ha fornito documenti che identificano
il committente come entità riconducibile a un Paese sotto embargo.
La stessa fonte ha fornito in passato informazioni accurate in due
casi separati, ma non è mai stata impiegata in contesti operativi
di questa portata. I documenti forniti non recano elementi
di autenticazione verificabili indipendentemente in tempi brevi.

**Elemento di corroborazione.** L'analisi finanziaria aggiornata
conferma un bonifico verso il conto dell'operatore logistico.
L'importo è nella fascia compatibile con le tariffe di trasporto
internazionale del tipo di merce indicato dalla fonte.

**Elemento anomalo.** Il legale della società terminale della catena
ha contattato nella mattinata il registro delle imprese per una
richiesta di documentazione societaria di routine, compatibile
con un'operazione commerciale ordinaria in fase di chiusura.

**Lacuna informativa.** Il contenuto fisico della merce non è stato
verificato. L'autenticità dei documenti forniti dalla fonte richiede
verifiche non compatibili con i tempi indicati. La posizione
del collaboratore di giustizia è sconosciuta.

**Fonti:** HUMINT (parzialmente verificata su casi precedenti),
finanziaria (verificata), operativa (in corso).

---""",

},

"C":{
"T1":"""**BRIEFING OPERATIVO — RISERVATO**

---

**Contesto operativo.** Il monitoraggio degli investimenti esteri
in settori tecnologici sensibili ha identificato l'acquisizione
di partecipazioni minoritarie in quattro aziende italiane da parte
di un fondo sovrano estero attraverso veicoli societari in cascata.
Le operazioni si sono distribuite nell'arco di diciotto mesi.
Le aziende coinvolte operano in settori ad alta densità brevettuale.

**Fonte primaria.** L'analisi delle strutture societarie intermedie
evidenzia che il fondo sovrano non compare direttamente in nessuna
delle operazioni. La ricostruzione della titolarità effettiva
è basata sull'analisi dei registri societari di tre giurisdizioni
diverse, con lacune documentali in una di esse. Due delle quattro
aziende hanno ottenuto contratti con la difesa nazionale negli ultimi
tre anni per forniture di componenti non classificate.

**Elemento di corroborazione.** Le quattro acquisizioni presentano importi
sistematicamente inferiori alle soglie che avrebbero attivato
la notifica obbligatoria. La probabilità statistica di questa
frammentazione su quattro operazioni indipendenti è bassa,
ma non esclude strategie di ottimizzazione fiscale che producono
lo stesso effetto.

**Elemento anomalo.** Due delle aziende target hanno rifiutato
in passato offerte di acquisizione da operatori nazionali
con valorizzazioni superiori. I motivi del rifiuto non sono
documentati pubblicamente.

**Lacuna informativa.** Non sono disponibili le clausole contrattuali
delle acquisizioni. Non è noto se il fondo abbia ottenuto diritti
di accesso a informazioni tecniche riservate contestualmente
alle acquisizioni.

**Fonti:** OSINT finanziaria (verificata), registri societari
(parzialmente verificati), contrattuale (non disponibile).

---""",

"T2":"""**BRIEFING OPERATIVO — RISERVATO**

---

**Contesto operativo.** L'analisi delle acquisizioni precedentemente
segnalate ha prodotto nuovi elementi. Sono emersi contatti diretti
tra rappresentanti del fondo e personale tecnico delle aziende
target che vanno oltre la normale relazione tra investitore
e partecipata in una quota minoritaria. L'analisi contrattuale
parziale è ora disponibile per due delle quattro aziende.

**Fonte primaria.** Una fonte con accesso a una delle aziende target
riferisce di richieste di documentazione tecnica non prevista
dagli accordi di investimento, relative a brevetti in fase
di registrazione. La richiesta è stata parzialmente evasa
prima che la direzione ne fosse informata. La stessa fonte
ha sollevato in passato segnalazioni interne non accolte dalla
direzione aziendale su questioni non correlate.

**Elemento di corroborazione.** L'analisi dei flussi di comunicazione
tra le aziende e indirizzi riconducibili al fondo mostra
un volume significativamente superiore a quello atteso
per una partecipazione minoritaria di natura finanziaria.
Uno dei rappresentanti del fondo risulta aver ricoperto un incarico
in un'agenzia governativa del Paese di riferimento prima
di passare al settore privato undici anni fa.

**Elemento anomalo.** L'analisi contrattuale delle due aziende
per cui è disponibile non evidenzia clausole anomale
di accesso a informazioni tecniche. Il trasferimento di documentazione
è avvenuto al di fuori dei canali previsti dagli accordi.

**Lacuna informativa.** Non è nota la qualificazione della documentazione
tecnica già trasferita rispetto alle categorie di informazione
sensibile per la sicurezza nazionale. Non è disponibile l'analisi
contrattuale delle altre due aziende.

**Fonti:** HUMINT (attendibilità parziale), SIGINT (verificata),
contrattuale (parzialmente disponibile).

---""",

"T3":"""**BRIEFING OPERATIVO — RISERVATO**

---

**Contesto operativo.** Una quinta azienda italiana, operante in un settore
connesso a sistemi di comunicazione per applicazioni sia civili sia militari,
risulta oggetto di un'offerta di acquisizione da parte di una società
riconducibile alla stessa catena del fondo sovrano. L'offerta è stata
presentata quarantotto ore fa al consiglio di amministrazione.

**Fonte primaria.** Una fonte con accesso alle strutture del fondo
riferisce che le acquisizioni precedenti costituiscono il primo stadio
di un piano articolato in due fasi, di cui la quinta azienda rappresenta
la seconda. La fonte è stata acquisita recentemente e non ha un track
record verificabile. Il piano descritto è compatibile con le operazioni
osservate ma non aggiunge elementi verificabili indipendentemente.

**Elemento di corroborazione.** L'analisi comparativa con operazioni
condotte dallo stesso fondo in altri Paesi europei negli ultimi
dieci anni mostra un pattern ricorrente: acquisizioni minoritarie
in settori tecnologici sensibili, seguite dopo diciotto-ventiquattro
mesi da un'acquisizione in un settore con applicazioni duali.
In tre casi su sei il pattern si è interrotto prima della seconda fase.

**Elemento anomalo.** Il consiglio di amministrazione della quinta azienda
ha espresso disponibilità all'operazione nonostante la valorizzazione
proposta sia inferiore del diciotto percento rispetto alle stime
di mercato degli ultimi sei mesi. L'azienda ha registrato un calo
del fatturato nell'ultimo esercizio.

**Lacuna informativa.** Non è disponibile la valutazione dell'impatto
dell'acquisizione sui contratti con la difesa nazionale. Non è noto
se il calo di fatturato abbia creato una dipendenza finanziaria
che rende l'offerta difficilmente rifiutabile indipendentemente
da altre considerazioni.

**Fonti:** HUMINT (non verificata), comparativa (verificata),
finanziaria (verificata).

---""",

},
}

LLM_TESTI = {
"A": {
"T1": """Il briefing descrive una situazione in cui segnali tecnici e informativi convergono su un possibile interesse ostile verso un impianto energetico portuale, senza che alcun evento concreto si sia ancora verificato.

Gli elementi disponibili presentano una caratteristica comune: ciascuno è spiegabile individualmente con ipotesi benigne. Le anomalie nei log di accesso potrebbero essere residui del penetration test autorizzato. Le discussioni OSINT sulle vulnerabilità SCADA sono diffuse in ambienti tecnici specializzati e non implicano necessariamente un interesse operativo ostile.

La lacuna informativa centrale è l'assenza del report finale del penetration test. Senza di esso non è possibile stabilire se le anomalie siano già documentate e attribuibili all'attività autorizzata, oppure richiedano una spiegazione diversa.

Il mio giudizio è che gli elementi disponibili non siano sufficienti per attivare misure operative immediate, ma siano sufficienti per giustificare l'acquisizione urgente del report e l'avvio di un monitoraggio rafforzato.""",

"T2": """Il briefing presenta uno sviluppo significativo: due fonti HUMINT indipendenti convergono nel descrivere tentativi sistematici di accesso non riconducibili al penetration test, e il report di quest'ultimo — ora disponibile — non documenta le anomalie rilevate. Le anomalie non hanno una spiegazione tecnica autorizzata.

Tuttavia l'identità dei soggetti nelle comunicazioni SIGINT è ancora sconosciuta. L'ipotesi del vettore interno — l'ex dipendente congedato — è suggestiva ma non supportata da elementi diretti.

La lacuna critica è l'identificazione dei soggetti nelle comunicazioni SIGINT. Senza di essa non è possibile stabilire se si tratti di un gruppo organizzato o di soggetti opportunistici.

Il mio giudizio è che il quadro si trovi in una zona di confine. La discrepanza tra anomalie rilevate e report del pentest supera la soglia del sospetto ma non raggiunge quella della certezza operativa. Raccomando misure di contenimento tecnico immediate mentre l'identificazione dei soggetti SIGINT procede in parallelo.""",

"T3": """Il briefing descrive un evento che ha già prodotto conseguenze operative concrete: l'interruzione parziale dei sistemi di supervisione. Non si tratta più di segnali o indicatori — si tratta di un incidente in corso.

L'analisi tecnica del codice malevolo è l'elemento più significativo. Le caratteristiche APT e la coerenza con attacchi documentati in altri Paesi europei indicano un livello di sofisticazione incompatibile con un attaccante opportunistico.

L'elemento anomalo — il codice ha colpito solo i sistemi di supervisione — potrebbe indicare un obiettivo di ricognizione preparatorio a un'azione più ampia. Il fatto che l'analisi forense completa non sia compatibile con i tempi operativi è una condizione normale nella gestione di incidenti cyber critici, non una ragione per rinviare la decisione.

Il mio giudizio è che gli elementi disponibili siano sufficienti per attivare le misure operative immediate. L'attesa di certezze analitiche complete in questa situazione aumenta il rischio, non lo riduce.""",
},

"B": {
"T1": """Il briefing descrive una struttura finanziaria anomala con caratteristiche tipiche del riciclaggio internazionale. Questi elementi, presi singolarmente, non sono infrequenti nelle segnalazioni FIU di routine.

Ciò che distingue questa segnalazione è la presenza di un collaboratore di giustizia sotto protezione attiva tra gli intestatari. Questa circostanza può avere tre spiegazioni: una coincidenza non intenzionale, un errore operativo della struttura di protezione, oppure una partecipazione consapevole in violazione degli accordi.

La lacuna informativa centrale è la natura del materiale dual-use e l'identità del destinatario finale. Senza questi elementi non è possibile valutare la gravità operativa della segnalazione.

Il mio giudizio è che gli elementi disponibili non siano ancora sufficienti per avviare un'indagine formale, ma richiedano due approfondimenti urgenti: la verifica della consapevolezza della struttura di protezione riguardo al collaboratore, e l'identificazione del destinatario finale del materiale.""",

"T2": """Il quadro si è evoluto in modo significativo. La fonte HUMINT indica un destinatario finale in un Paese sotto embargo — se confermato, questo trasforma la segnalazione da riciclaggio a elusione delle sanzioni internazionali.

Ci sono però due complicazioni. L'attendibilità della fonte non è ancora verificata: una fonte che chiede protezione ha incentivi propri che possono distorcere i dati forniti. Il comportamento del collaboratore di giustizia rimane ambiguo.

Il bonifico al trasportatore nelle ultime ventiquattro ore cambia i termini della decisione. Non si tratta più di valutare un rischio futuro — si tratta di decidere se intervenire su una transazione in corso.

Il mio giudizio è che gli elementi disponibili siano sufficienti per avviare misure di contrasto immediate. La finestra temporale non consente di attendere la verifica completa della fonte senza rischiare di perdere la possibilità di intervento.""",

"T3": """Il briefing descrive una situazione in cui la maggior parte delle lacune precedenti è stata colmata. Il committente finale è identificato come ente parastatale sotto embargo. L'attendibilità della fonte è parzialmente verificata. Il bonifico è confermato.

Rimangono due elementi non risolti. Il contenuto esatto del materiale non è stato verificato fisicamente. La scomparsa del collaboratore di giustizia introduce una variabile operativa non controllata: potrebbe essere in pericolo, potrebbe aver abbandonato la protezione, potrebbe operare su mandato non dichiarato.

La scomparsa del collaboratore non modifica la valutazione principale sulla natura della transazione, ma introduce un rischio aggiuntivo per l'intervento.

Il mio giudizio è che gli elementi disponibili siano sufficienti per attivare immediatamente le misure di contrasto. L'incertezza sul collaboratore è un elemento da gestire operativamente, non una ragione per rinviare la decisione principale.""",
},

"C": {
"T1": """Il briefing descrive un pattern di acquisizioni con una caratteristica statisticamente significativa: quattro operazioni distinte, tutte con importi appena al di sotto delle soglie di notifica obbligatoria. La probabilità che questa frammentazione sia casuale su quattro operazioni indipendenti è bassa.

Le aziende target includono due con contratti difesa attivi. Questo rafforza il sospetto che la selezione non sia stata guidata esclusivamente da considerazioni finanziarie.

La lacuna critica è l'analisi delle clausole contrattuali. In un'operazione di intelligence economica il valore non sta nella quota azionaria — sta nei diritti di accesso a informazioni tecniche, brevetti e processi produttivi che possono essere negoziati contestualmente all'acquisizione.

Il mio giudizio è che gli elementi disponibili non siano sufficienti per attivare la procedura di golden power, ma richiedano un'analisi immediata delle clausole contrattuali e un monitoraggio rafforzato dei contatti tra il fondo sovrano e il management delle aziende target.""",

"T2": """Il quadro è cambiato in modo sostanziale. Non si tratta più di inferire l'intenzione del fondo sovrano dalla struttura delle acquisizioni — ci sono ora elementi diretti di comportamento anomalo: richieste di documentazione tecnica non prevista dagli accordi, volume di comunicazioni incompatibile con una partecipazione puramente finanziaria, documentazione già parzialmente trasferita.

L'elemento più significativo è il profilo del rappresentante con background in un'agenzia di intelligence, che ha deliberatamente modificato il proprio profilo pubblico rimuovendo questo riferimento dopo l'avvio dell'analisi.

La lacuna che rimane è la qualificazione del materiale tecnico già trasferito: se include informazioni rilevanti per la sicurezza nazionale, il danno si è già in parte prodotto.

Il mio giudizio è che gli elementi disponibili siano sufficienti per attivare la procedura di golden power e bloccare ulteriori trasferimenti di documentazione. La valutazione del materiale già trasferito deve procedere in parallelo.""",

"T3": """Il briefing descrive la fase conclusiva di un'operazione strutturata nel tempo. La fonte HUMINT ad alta attendibilità indica che l'acquisizione della quinta azienda — settore comunicazioni militari — è l'elemento finale di un piano preordinato. Il pattern comparativo con operazioni analoghe in altri Paesi europei conferisce a questa valutazione una base empirica solida.

La disponibilità del consiglio di amministrazione ad accettare una valutazione sotto mercato è anomala e non spiegata. Potrebbe indicare difficoltà finanziarie non pubbliche, pressioni esterne o accordi paralleli.

La lacuna sulla valutazione di impatto sui contratti difesa in essere è rilevante per calibrare la risposta, non per decidere se rispondere. L'operazione deve essere bloccata indipendentemente dall'esito di quella valutazione.

Il mio giudizio è che gli elementi disponibili siano pienamente sufficienti per attivare immediatamente la procedura di golden power sull'offerta sulla quinta azienda e per avviare una revisione delle acquisizioni già completate.""",
},
}



SCALA_ORDINALE = [
    "— seleziona —",
    "No — nessuna evidenza",
    "Probabilmente no — segnali deboli",
    "Incerto — elementi contrastanti",
    "Probabilmente sì — convergenza significativa",
    "Sì — evidenza solida",
]

# ============================================================
# DATABASE
# ============================================================

def get_conn():
    return sqlite3.connect(str(DB_PATH))

def init_db():
    con = get_conn()
    # Migrazione automatica: aggiunge colonne mancanti se il DB esiste già
    try:
        cur = con.cursor()
        cur.execute("PRAGMA table_info(risposte)")
        cols_esistenti = {row[1] for row in cur.fetchall()}
        colonne_nuove = {
            "gruppo": "TEXT",
            "team_id": "INTEGER",
            "posizione_team": "INTEGER",
            "T1_suffic_cat": "TEXT",
            "T2_suffic_cat": "TEXT",
            "T3_suffic_cat": "TEXT",
            "ai_llm_use": "INTEGER",
            "ai_llm_trust": "INTEGER",
        }
        for col, tipo in colonne_nuove.items():
            if col not in cols_esistenti:
                try:
                    con.execute(f"ALTER TABLE risposte ADD COLUMN {col} {tipo}")
                    con.commit()
                except Exception:
                    pass
    except Exception:
        pass
    con.execute("""
    CREATE TABLE IF NOT EXISTS risposte (
        session_uuid TEXT PRIMARY KEY,
        timestamp TEXT, ruolo TEXT,
        team_id INTEGER, posizione_team INTEGER,
        gruppo TEXT, experience TEXT,
        coordination INTEGER, specialist_area TEXT,
        ai_use INTEGER, ai_critical INTEGER,
        ai_llm_use INTEGER, ai_llm_trust INTEGER,
        ordine TEXT,
        T1_pre_ai INTEGER, T1_pre_ordinale TEXT,
        T1_conf_pre INTEGER, T1_llm_utile INTEGER,
        T1_suffic_cat TEXT,
        T1_post_ai INTEGER, T1_post_ordinale TEXT,
        T1_motivo TEXT, T1_trust_ai INTEGER,
        T1_confidence INTEGER, T1_leader_acceptance INTEGER,
        T1_need_group INTEGER, T1_gravity INTEGER,
        T1_uncertainty INTEGER, T1_strategic INTEGER,
        T1_pressione_1 INTEGER, T1_pressione_2 INTEGER,
        T1_pressione_3 INTEGER,
        T2_pre_ai INTEGER, T2_pre_ordinale TEXT,
        T2_conf_pre INTEGER, T2_llm_utile INTEGER,
        T2_suffic_cat TEXT,
        T2_post_ai INTEGER, T2_post_ordinale TEXT,
        T2_motivo TEXT, T2_trust_ai INTEGER,
        T2_confidence INTEGER, T2_leader_acceptance INTEGER,
        T2_need_group INTEGER, T2_gravity INTEGER,
        T2_uncertainty INTEGER, T2_strategic INTEGER,
        T2_pressione_1 INTEGER, T2_pressione_2 INTEGER,
        T2_pressione_3 INTEGER,
        T3_pre_ai INTEGER, T3_pre_ordinale TEXT,
        T3_conf_pre INTEGER, T3_llm_utile INTEGER,
        T3_suffic_cat TEXT,
        T3_post_ai INTEGER, T3_post_ordinale TEXT,
        T3_motivo TEXT, T3_trust_ai INTEGER,
        T3_confidence INTEGER, T3_leader_acceptance INTEGER,
        T3_need_group INTEGER, T3_gravity INTEGER,
        T3_uncertainty INTEGER, T3_strategic INTEGER,
        T3_pressione_1 INTEGER, T3_pressione_2 INTEGER,
        T3_pressione_3 INTEGER
    )""")
    con.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    con.execute("INSERT OR IGNORE INTO settings VALUES ('closed','0')")
    con.commit(); con.close()

def load_risposte():
    try:
        con = get_conn()
        df = pd.read_sql_query("SELECT * FROM risposte ORDER BY timestamp", con)
        con.close()
        return df
    except:
        return pd.DataFrame()

def save_risposta(row):
    con = get_conn()
    cols = list(row.keys())
    sql = (f"INSERT OR REPLACE INTO risposte ({','.join(cols)}) "
           f"VALUES ({','.join(['?']*len(cols))})")
    con.execute(sql, [row[c] for c in cols])
    con.commit(); con.close()
    df = load_risposte()
    # Esporta CSV
    try:
        df.to_csv(str(CSV_RESPONSES), index=False, encoding="utf-8-sig")
    except:
        pass
    # Esporta Excel
    try:
        excel_path = OUTPUT_DIR / "studio2_02_risposte.xlsx"
        df.to_excel(str(excel_path), index=False, engine="openpyxl")
    except:
        pass
    invia_email(row)

def is_closed():
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT value FROM settings WHERE key='closed'")
    r = cur.fetchone(); con.close()
    return r and r[0] == "1"

def set_closed(v):
    con = get_conn()
    con.execute("UPDATE settings SET value=? WHERE key='closed'", ("1" if v else "0",))
    con.commit(); con.close()

def reset_db():
    con = get_conn()
    con.execute("DELETE FROM risposte")
    con.execute("UPDATE settings SET value='0' WHERE key='closed'")
    con.commit(); con.close()

# ============================================================
# ASSEGNAZIONE AUTOMATICA
# ============================================================

def n_risposte_totali():
    df = load_risposte()
    return 0 if df.empty else len(df)

def assegna_gruppo(n):
    """Primo terzo → A, secondo → B, terzo → C."""
    if n < 30:   return "A"
    elif n < 60: return "B"
    else:        return "C"

def posizione_nel_team(n):
    return n % 9

def team_id(n):
    return n // 9

def assegna_ruolo(experience, specialist_area, pos):
    if pos == 0:
        return "Team Leader"
    if specialist_area in AREE_CIVILI:
        return "Analista Civile"
    anni = {"Meno di 5 anni":2,"5-10 anni":7,"11-20 anni":15,"Oltre 20 anni":25}.get(experience,7)
    return "Analista Junior" if anni <= 10 else "Analista Senior"

# ============================================================
# EMAIL
# ============================================================

def get_email_config():
    try:
        cfg = st.secrets["email"]
        return {"mittente":cfg["mittente"],"password":cfg["password"],
                "destinatario":"castiello.mauro@gmail.com"}
    except:
        return None

def invia_email(row):
    cfg = get_email_config()
    if not cfg: return
    try:
        msg = MIMEMultipart()
        msg["From"]    = cfg["mittente"]
        msg["To"]      = cfg["destinatario"]
        msg["Subject"] = (f"Studio 2 — {row.get('ruolo','?')} "
                          f"Gruppo {row.get('gruppo','?')} "
                          f"[{row.get('timestamp','')[:10]}]")
        corpo = (f"Studio 2 — nuova risposta\n\n"
                 f"Ruolo: {row.get('ruolo','?')}\n"
                 f"Gruppo: {row.get('gruppo','?')} ({DOMINI.get(row.get('gruppo','?'),'')})\n"
                 f"Team: {row.get('team_id','?')}\n"
                 f"Timestamp: {row.get('timestamp','?')}")
        msg.attach(MIMEText(corpo,"plain","utf-8"))
        df = load_risposte()
        if not df.empty:
            buf = io.StringIO()
            df.to_csv(buf, index=False)
            part = MIMEBase("application","octet-stream")
            part.set_payload(buf.getvalue().encode("utf-8"))
            encoders.encode_base64(part)
            part.add_header("Content-Disposition",
                            "attachment; filename=studio2_risposte.csv")
            msg.attach(part)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(cfg["mittente"], cfg["password"])
            s.sendmail(cfg["mittente"], cfg["destinatario"], msg.as_string())
    except:
        pass

# ============================================================
# ABM — compatibile con Studio 1
# ============================================================

def likert01(x):
    return float(np.clip((float(x)-1)/6, 0, 1))

def compute_G(row, T):
    return float(np.clip(
        (np.mean([row[f"{T}_gravity"],row[f"{T}_uncertainty"],row[f"{T}_strategic"]])-1)/6,0,1))

def compute_H_i(row, T):
    la = row[f"{T}_leader_acceptance"]
    ng = row[f"{T}_need_group"]
    return float(la/(la+ng+1e-6))

def compute_F_i(row, T):
    delta = row[f"{T}_post_ai"] - row[f"{T}_pre_ai"]
    sign  = 1.0 if delta >= 0 else -1.0
    try:
        cp = float(row[f"{T}_conf_pre"])
    except:
        cp = 4.0
    return float(sign * abs(delta)/100 * (cp/7))

def compute_stability(row):
    return float(np.clip(
        1-np.mean([abs(row[f"T{i}_post_ai"]-row[f"T{i}_pre_ai"])
                   for i in [1,2,3]])/100,0,1))

def experience_score(x):
    return {"Meno di 5 anni":0.20,"5-10 anni":0.45,
            "11-20 anni":0.75,"Oltre 20 anni":1.00}.get(x,0.50)

def infer_roles_df(df):
    df = df.copy()
    df["role"] = df.apply(
        lambda r: assegna_ruolo(r["experience"], r["specialist_area"],
                                int(r.get("posizione_team",0))), axis=1)
    df["role_influence"] = df["role"].map(ROLE_INFLUENCE).fillna(0.45)
    df["E"] = df["experience"].apply(experience_score)
    df["S"] = df.apply(compute_stability, axis=1)
    return df

def build_network_abm(team, T):
    H_val = np.mean([compute_H_i(row, T) for _,row in team.iterrows()])
    G = nx.Graph()
    roles = {}
    for _,row in team.iterrows():
        code = row["session_uuid"][:6]
        roles[code] = row["role"]
        G.add_node(code, role=row["role"])
    codes = list(roles.keys())
    leader = next((c for c,r in roles.items() if r=="Team Leader"), codes[0])
    seniors = [c for c,r in roles.items() if r=="Analista Senior"]
    juniors = [c for c,r in roles.items() if r=="Analista Junior"]
    for n in codes:
        if n != leader:
            G.add_edge(leader, n, weight=0.30+0.60*H_val)
    hor = 0.80*(1-H_val)+0.05
    for i in range(len(seniors)):
        for j in range(i+1,len(seniors)):
            G.add_edge(seniors[i],seniors[j],weight=hor)
    return G, roles, H_val

def simulate_abm(team, T, seed):
    rng = np.random.default_rng(seed)
    G, roles, H_val = build_network_abm(team, T)
    P = np.mean([compute_G(row,T) for _,row in team.iterrows()])
    sigma_P = 0.05 + 0.15*P
    codes = list(roles.keys())
    id2i  = {c:i for i,c in enumerate(codes)}
    beliefs = np.array([team.iloc[i][f"{T}_post_ai"] for i in range(len(team))],
                        dtype=float)
    initial = beliefs.copy()
    trust   = np.array([likert01(team.iloc[i][f"{T}_trust_ai"]) for i in range(len(team))])
    conf    = np.array([likert01(team.iloc[i][f"{T}_confidence"]) for i in range(len(team))])
    F_arr   = np.array([compute_F_i(team.iloc[i], T) for i in range(len(team))])
    H_arr   = np.array([compute_H_i(team.iloc[i], T) for i in range(len(team))])
    G_arr   = np.array([compute_G(team.iloc[i], T) for i in range(len(team))])
    li      = next((i for i,c in enumerate(codes) if roles[c]=="Team Leader"), 0)
    steps   = 6 if P < 0.35 else (5 if P < 0.65 else 4)
    history = []
    for step in range(steps+1):
        lb = float(beliefs[li])
        consensus   = float(np.clip(1-np.std(beliefs)/50,0,1))
        dist_ai0    = np.mean(np.abs(initial-AI_COSTANTE))+1e-6
        deleg_ai    = float(np.clip(1-np.mean(np.abs(beliefs-AI_COSTANTE))/dist_ai0,0,1))
        dist_l0     = np.mean(np.abs(initial-initial[li]))+1e-6
        hier_idx    = float(np.clip(1-np.mean(np.abs(beliefs-lb))/dist_l0,0,1))
        deliberation= float(np.clip((1-P)*(1-H_val)*np.mean(np.abs(F_arr))*0.85,0,1))
        Gm          = float(np.mean(G_arr))
        mediation   = float(np.clip(
            0.40*consensus+0.30*deliberation+0.20*(1-deleg_ai)+0.10*(1-Gm),0,1))
        history.append({"condition":T,"step":step,
                         "group_mean":float(np.mean(beliefs)),
                         "consensus":consensus,"delegation_ai":deleg_ai,
                         "hierarchy_index":hier_idx,"deliberation":deliberation,
                         "mediation_system3":mediation,"P":P,"H":H_val})
        if step == steps: break
        new = beliefs.copy()
        for i,c in enumerate(codes):
            ai_sal = float(np.clip(AI_COSTANTE*(1+rng.normal(0,sigma_P)),0,100))
            nb_v,nb_w = [],[]
            for nb in G.neighbors(c):
                j = id2i[nb]
                nb_v.append(beliefs[j])
                nb_w.append(G[c][nb]["weight"])
            local = np.average(nb_v,weights=nb_w) if nb_v else beliefs[i]
            w_ai   = np.clip(0.08+0.25*trust[i]+0.18*P+0.14*G_arr[i],0,0.80)
            w_lead = np.clip(0.05+0.38*H_val*H_arr[i]+0.08*G_arr[i],0,0.80)
            w_net  = np.clip(0.40*(1-P)*(1-H_val)*abs(F_arr[i]),0,0.70)
            w_self = max(0.05,1-(w_ai+w_lead+w_net))
            tot    = w_self+w_ai+w_lead+w_net
            w_self,w_ai,w_lead,w_net = [x/tot for x in (w_self,w_ai,w_lead,w_net)]
            target = w_self*beliefs[i]+w_ai*ai_sal+w_lead*lb+w_net*local
            new[i] = float(np.clip(
                beliefs[i]+(1-0.45*conf[i])*(target-beliefs[i])+rng.normal(0,2.5+3.5*P),
                0,100))
        beliefs = new
    return pd.DataFrame(history)

def run_abm_single(team):
    return pd.concat([simulate_abm(team,T,BASE_SEED+3000) for T in ["T1","T2","T3"]],
                     ignore_index=True)

def perturb_team(team, seed, noise=0.08):
    rng = np.random.default_rng(seed)
    t = team.copy()
    for T in ["T1","T2","T3"]:
        for col in [f"{T}_pre_ai",f"{T}_post_ai"]:
            if col in t.columns:
                t[col] = np.clip(t[col].astype(float)*rng.normal(1,noise,len(t)),0,100).round().astype(int)
        for col in [f"{T}_trust_ai",f"{T}_confidence",f"{T}_leader_acceptance",
                    f"{T}_need_group",f"{T}_gravity",f"{T}_uncertainty",f"{T}_strategic"]:
            if col in t.columns:
                t[col] = np.clip(t[col].astype(float)*rng.normal(1,noise,len(t)),1,7).round().astype(int)
    return t

def run_montecarlo(team):
    finals = []
    for synth in range(N_SYNTH):
        st_team = perturb_team(team, BASE_SEED+synth)
        for run in range(N_MC):
            for T in ["T1","T2","T3"]:
                sim = simulate_abm(st_team, T, BASE_SEED+synth*10000+run)
                last = sim.iloc[-1].to_dict()
                last["synthetic_team"] = synth
                last["run"] = run
                finals.append(last)
    mc = pd.DataFrame(finals)
    summary = mc.groupby("condition").agg(
        mediation_mean=("mediation_system3","mean"),
        mediation_ci95=("mediation_system3",lambda x: 1.96*x.std()/np.sqrt(len(x))),
        delegation_mean=("delegation_ai","mean"),
        delegation_ci95=("delegation_ai",lambda x: 1.96*x.std()/np.sqrt(len(x))),
        consensus_mean=("consensus","mean"),
        P=("P","mean"), H=("H","mean")
    ).reset_index()
    return mc, summary.set_index("condition").loc[["T1","T2","T3"]].reset_index()

def plot_abm(abm, summary):
    fig, axes = plt.subplots(1,2,figsize=(12,5))
    x = np.arange(3)
    colori = {"T1":"#2E7D32","T2":"#E65100","T3":"#C62828"}
    for T in ["T1","T2","T3"]:
        d = abm[abm["condition"]==T]
        axes[0].plot(d["step"],d["mediation_system3"],
                     color=colori[T],lw=2,label=f"{T} — Mediazione S3")
        axes[0].plot(d["step"],d["delegation_ai"],
                     color=colori[T],lw=1.5,linestyle="--")
    axes[0].set_xlabel("Step"); axes[0].set_ylabel("Indice")
    axes[0].set_ylim(0,1.05); axes[0].legend(fontsize=8)
    axes[0].set_title("ABM singolo — Mediazione S3 (—) e Delega AI (--)")
    axes[0].grid(alpha=0.25)
    axes[1].errorbar(x,summary["mediation_mean"],yerr=summary["mediation_ci95"],
                     fmt="o-",lw=2,capsize=6,label="Mediazione S3")
    axes[1].errorbar(x,summary["delegation_mean"],yerr=summary["delegation_ci95"],
                     fmt="s-",lw=2,capsize=6,label="Delega AI")
    axes[1].set_xticks(x); axes[1].set_xticklabels(["T1","T2","T3"])
    axes[1].set_ylim(0,1.05)
    axes[1].set_title(f"Monte Carlo — N={N_SYNTH}×{N_MC} run")
    axes[1].legend(fontsize=9); axes[1].grid(alpha=0.25)
    plt.tight_layout()
    try:
        plt.savefig(str(OUTPUT_DIR/"studio2_abm.png"),dpi=200,bbox_inches="tight")
    except:
        pass
    return fig

# ============================================================
# RENDERING OUTPUT LLM
# ============================================================

def mostra_output_llm(gruppo, T, versione="C"):
    testo = LLM_TESTI[gruppo][T][versione]
    st.info(
        "**Sistema di supporto analitico — Analisi del modello linguistico**\n\n"
        "Il modello linguistico ha elaborato le stesse informazioni contenute "
        "nel briefing e produce la seguente analisi argomentata. "
        "Sulla base di questa analisi ti viene chiesto di valutare se le "
        "informazioni disponibili siano sufficienti per attivare le misure operative."
    )
    for paragrafo in testo.strip().split("\n\n"):
        st.markdown(paragrafo)
    st.caption("Il giudizio analitico finale spetta a te.")

# ============================================================
# UI
# ============================================================

init_db()
st.title("Questionario Sistema 3 — Studio 2")
st.markdown("Raccolta dati individuali — Analisi decisionale con supporto LLM")

admin = st.sidebar.text_input("Password back office", type="password")

# ── BACK OFFICE ──────────────────────────────────────────────
if admin == ADMIN_PWD:
    st.sidebar.success("Back office attivo")
    st.header("Back Office — Studio 2")
    df = load_risposte()
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Risposte totali", len(df))
    c2.metric("Rilevazione", "Chiusa" if is_closed() else "Aperta")
    c3.metric("Team completati", len(df)//9 if len(df)>0 else 0)
    cfg = get_email_config()
    c4.metric("Email", "🟢" if cfg else "🔴")

    if not df.empty and "gruppo" in df.columns:
        st.subheader("Distribuzione per gruppo")
        for g,nome in DOMINI.items():
            n = int((df["gruppo"]==g).sum())
            st.progress(min(n/30,1.0), text=f"Gruppo {g} — {nome}: {n}/30")

    col1,col2,col3 = st.columns(3)
    with col1:
        if st.button("Chiudi rilevazione"): set_closed(True); st.rerun()
    with col2:
        if st.button("🗑️ Reset completo"):
            reset_db()
            # Elimina anche CSV ed Excel di prova
            for f_path in [CSV_RESPONSES,
                           OUTPUT_DIR / "studio2_02_risposte.xlsx",
                           OUTPUT_DIR / "studio2_montecarlo.csv"]:
                try:
                    Path(f_path).unlink(missing_ok=True)
                except:
                    pass
            st.success("Database, CSV ed Excel eliminati. Rilevazione riaperta.")
            st.rerun()
    with col3:
        if cfg and st.button("Test email"):
            invia_email({"ruolo":"TEST","gruppo":"A",
                          "team_id":0,"timestamp":datetime.now().isoformat()})
            st.success("Email inviata.")

    st.divider()

    # Tabella risposte
    if not df.empty:
        st.subheader("Tabella risposte")
        st.dataframe(df, hide_index=True, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Scarica CSV", csv,
                           "studio2_risposte.csv","text/csv")
        # Download Excel in memoria
        try:
            import io as _io
            buf = _io.BytesIO()
            df.to_excel(buf, index=False, engine="openpyxl")
            buf.seek(0)
            st.download_button("⬇️ Scarica Excel", buf.getvalue(),
                               "studio2_risposte.xlsx",
                               "application/vnd.openxmlformats-officedocument"
                               ".spreadsheetml.sheet")
        except Exception as _e:
            st.caption(f"Excel non disponibile: {_e}")

    # ABM e Monte Carlo
    st.divider()
    st.subheader("Analisi ABM e Monte Carlo")
    if len(df) >= 9:
        if st.button("▶ Esegui analisi ABM + Monte Carlo",type="primary"):
            with st.spinner(f"ABM singolo + Monte Carlo {N_SYNTH}×{N_MC}..."):
                # Usa il primo team completo disponibile (9 partecipanti)
                n_team = len(df) // 9
                st.caption(f"Team completi disponibili: {n_team} — "
                           f"analisi sul primo team ({min(9,len(df))} partecipanti)")
                team = infer_roles_df(df.head(9))
                abm  = run_abm_single(team)
                mc, summary = run_montecarlo(team)
                fig  = plot_abm(abm, summary)
                st.pyplot(fig)
                st.subheader("Sintesi Monte Carlo")
                st.dataframe(summary.round(3), hide_index=True)
                mc_csv = mc.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Scarica risultati MC", mc_csv,
                                   "studio2_montecarlo.csv","text/csv")
    else:
        st.info(f"Servono almeno 9 risposte per l'ABM. "
                f"Disponibili: {len(df)}/{MAX_P}")
    st.stop()

# ── QUESTIONARIO ─────────────────────────────────────────────
if is_closed():
    st.info("La rilevazione è terminata. Grazie per la partecipazione.")
    st.stop()

n_tot      = n_risposte_totali()
gruppo     = assegna_gruppo(n_tot)
pos        = posizione_nel_team(n_tot)
tid        = team_id(n_tot)
ordine_str = ORDINI[n_tot % 3]
ordine     = ordine_str.split("-")

st.progress(min(n_tot/MAX_P,1.0),
            text=f"Risposte completate: {n_tot}/{MAX_P}")
st.caption(f"Sessione {n_tot+1} di {MAX_P}")

with st.expander("Istruzioni operative", expanded=True):
    st.markdown(f"""
Il presente questionario riproduce tre sessioni di analisi individuale
in condizioni operative distinte relative al dominio **{DOMINI[gruppo]}**.

1. **Leggi il briefing operativo** nella sua interezza.
2. **Formula una stima autonoma** e indica il livello di sicurezza analitica.
   Clicca **Conferma** per procedere.
3. **Consulta la valutazione del modello linguistico** che ha analizzato
   le stesse informazioni.
4. **Aggiorna o conferma la tua stima** alla luce dell'analisi del modello.
5. **Rispondi alle domande di contesto**.

Non esistono risposte corrette o scorrette.
""")

st.subheader("Profilo professionale")
experience = st.selectbox("Anni di esperienza nel settore",
    ["— seleziona —","Meno di 5 anni","5-10 anni","11-20 anni","Oltre 20 anni"])
coordination = st.slider("Esperienza nel coordinamento di gruppi", 1,7,4,
    help="1 = nessuna  |  7 = consolidata")
specialist_area = st.selectbox("Area operativa prevalente",
    ["— seleziona —",
     "Intelligence / sicurezza",
     "Investigativa / law enforcement",
     "Cyber / tecnologia",
     "Economico-finanziaria",
     "OSINT / analisi fonti aperte",
     "Accademica / ricerca",
     "Linguistica / area studies",
     "Comunicazione e media",
     "Settore privato della sicurezza",
     "Affari legali",
     "Marketing",
     "Altro"])
ai_use = st.slider("Frequenza utilizzo strumenti analisi automatizzata", 1,7,4,
    help="1 = mai  |  7 = quotidianamente")
ai_critical = st.slider("Capacità di valutare criticamente output automatizzati", 1,7,4)
ai_llm_use  = st.slider("Frequenza utilizzo modelli linguistici (LLM)", 1,7,4)
ai_llm_trust= st.slider("Fiducia negli output LLM in contesti analitici", 1,7,4)

profilo_ok = (experience != "— seleziona —" and specialist_area != "— seleziona —")
if not profilo_ok:
    st.warning("Completa il profilo professionale per procedere.")
    st.stop()

ruolo = assegna_ruolo(experience, specialist_area, pos)

for T in ordine:
    for k in ["confirmed","pre_val","conf_pre_saved"]:
        if f"{T}_{k}" not in st.session_state:
            st.session_state[f"{T}_{k}"] = (False if k=="confirmed" else 50)

responses = {}
st.divider()

for T in ordine:
    idx_scenario = ordine.index(T) + 1
    st.header(f"Scenario {idx_scenario} di 3")
    idx_T = ordine.index(T)
    if not all(st.session_state.get(f"{c}_confirmed",False) for c in ordine[:idx_T]):
        st.info("🔒 Completa lo scenario precedente per sbloccare questo.")
        st.divider(); continue

    with st.expander("📄 Leggi il briefing operativo",
                     expanded=not st.session_state[f"{T}_confirmed"]):
        st.markdown(BRIEFING[gruppo][T])

    if not st.session_state[f"{T}_confirmed"]:
        st.subheader("Sezione I — Valutazione analitica individuale")
        st.markdown(f"**{DOMANDA[gruppo]}**")
        st.caption("Formula la tua stima prima di consultare il modello linguistico.")

        pre_ai = st.slider("Probabilità stimata (0–100)",0,100,50,
                           key=f"{T}_pre_slider")
        pre_ord = st.selectbox("Valutazione qualitativa",SCALA_ORDINALE,
                               key=f"{T}_pre_ord")
        conf_pre = st.slider("Livello di sicurezza analitica",1,7,4,
                             key=f"{T}_conf_pre",
                             help="1 = molto incerto  |  7 = molto sicuro")

        if st.button(f"✅ Conferma e consulta il modello linguistico",
                     key=f"{T}_confirm_btn",type="primary"):
            if pre_ord == "— seleziona —":
                st.error("Seleziona la valutazione qualitativa prima di procedere.")
            else:
                st.session_state[f"{T}_confirmed"]      = True
                st.session_state[f"{T}_pre_val"]        = pre_ai
                st.session_state[f"{T}_pre_ord_val"]    = pre_ord
                st.session_state[f"{T}_conf_pre_saved"] = conf_pre
                st.rerun()
        st.warning("⚠️ Conferma la valutazione per accedere all'analisi del modello.")
        st.divider(); continue

    pre_ai   = st.session_state[f"{T}_pre_val"]
    pre_ord  = st.session_state.get(f"{T}_pre_ord_val","—")
    conf_pre = st.session_state.get(f"{T}_conf_pre_saved",4)
    responses[f"{T}_pre_ai"]      = pre_ai
    responses[f"{T}_pre_ordinale"] = pre_ord
    responses[f"{T}_conf_pre"]    = conf_pre
    st.success(f"✅ Scenario {T} — Sezione I completata.")

    st.subheader("Sezione II — Analisi del modello linguistico")
    st.markdown("Hai formulato la tua valutazione autonoma. "
                "Consulti ora l'analisi prodotta dal modello linguistico "
                "che ha elaborato le stesse informazioni del briefing:")
    mostra_output_llm(gruppo, T, versione_llm)

    st.divider()
    st.markdown("**Dopo aver letto l'analisi del modello, rispondi alle seguenti domande:**")

    # Domanda categoriale — sufficienza informativa × conferma/modifica
    suffic_opt = [
        "— seleziona —",
        "Le informazioni sono sufficienti — confermo la mia valutazione iniziale",
        "Le informazioni sono sufficienti — modifico la mia valutazione alla luce dell'analisi",
        "Le informazioni non sono sufficienti — confermo la mia valutazione iniziale",
        "Le informazioni non sono sufficienti — modifico la mia valutazione alla luce dell'analisi",
    ]
    responses[f"{T}_suffic_cat"] = st.selectbox(
        "Valuta la sufficienza delle informazioni disponibili e il tuo aggiornamento:",
        suffic_opt, key=f"{T}_suffic")

    # Slider aggiornato — compatibile con Studio 1
    st.markdown(f"**{DOMANDA[gruppo]}**")
    responses[f"{T}_post_ai"] = st.slider(
        "Aggiorna la tua stima di probabilità (0–100)",
        0, 100, pre_ai, key=f"{T}_post",
        help="Puoi confermare o modificare la stima iniziale")
    responses[f"{T}_post_ordinale"] = st.selectbox(
        "Esprimi la stessa valutazione sulla scala qualitativa",
        SCALA_ORDINALE, key=f"{T}_post_ord")
    responses[f"{T}_llm_utile"] = st.slider(
        "Quanto è stata utile l'analisi del modello per la tua decisione?",
        1, 7, 4, key=f"{T}_llm_u",
        help="1 = per nulla utile  |  7 = molto utile")

    st.subheader("Sezione III — Motivazione")
    responses[f"{T}_motivo"] = st.selectbox(
        "Fattore principale che ha determinato la tua valutazione finale:",
        ["— seleziona —",
         "La valutazione del modello ha modificato la mia interpretazione",
         "Ho rivalutato autonomamente le informazioni del briefing",
         "Ho scelto di allinearmi al modello per coerenza",
         "La mia valutazione non ha subito modifiche significative",
         "Altro"],
        key=f"{T}_motivo")

    st.subheader("Sezione IV — Contesto operativo")
    responses[f"{T}_gravity"]           = st.slider("Gravità operativa del quadro",1,7,4,key=f"{T}_grav")
    responses[f"{T}_uncertainty"]       = st.slider("Incertezza informativa dello scenario",1,7,4,key=f"{T}_unc")
    responses[f"{T}_strategic"]         = st.slider("Rilevanza strategica della decisione",1,7,4,key=f"{T}_str")
    responses[f"{T}_trust_ai"]          = st.slider("Attendibilità del modello in questo scenario",1,7,4,key=f"{T}_tr")
    responses[f"{T}_confidence"]        = st.slider("Sicurezza della tua valutazione finale",1,7,4,key=f"{T}_conf")
    responses[f"{T}_leader_acceptance"] = st.slider("Disponibilità ad accettare sintesi del Team Leader",1,7,4,key=f"{T}_la")
    responses[f"{T}_need_group"]        = st.slider("Necessità di confronto con gli altri analisti",1,7,4,key=f"{T}_ng")
    responses[f"{T}_pressione_1"]       = st.slider("Ho percepito pressione a decidere rapidamente",1,7,4,key=f"{T}_p1")
    responses[f"{T}_pressione_2"]       = st.slider("Il tempo disponibile era adeguato alla complessità",1,7,4,key=f"{T}_p2")
    responses[f"{T}_pressione_3"]       = st.slider("Ho dovuto rispondere prima di completare l'analisi",1,7,4,key=f"{T}_p3")

    if idx_T < len(ordine)-1:
        if st.button(f"▶ Vai allo scenario successivo",
                     key=f"{T}_next"):
            st.rerun()
    st.divider()

# ── PAGINA COMPLETAMENTO ─────────────────────────────────────
if st.session_state.get("completato", False):
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; padding:60px 0'>"
        "<h1>✅ Questionario concluso con successo</h1>"
        "<p style='font-size:1.2em; color:#555'>La tua risposta è stata registrata "
        "e trasmessa al sistema.<br>"
        "Puoi chiudere questa finestra.</p>"
        "<p style='font-size:0.9em; color:#aaa; margin-top:40px'>"
        "Studio Sistema 3 — Scuola di Perfezionamento per le Forze di Polizia</p>"
        "</div>",
        unsafe_allow_html=True)
    st.stop()

# ── INVIO ─────────────────────────────────────────────────────
tutti_confermati = all(
    st.session_state.get(f"{T}_confirmed",False) for T in ordine)

if tutti_confermati:
    if st.button("📨 Invia questionario",type="primary"):
        incompleti = [T for T in ordine
                      if responses.get(f"{T}_motivo","— seleziona —")=="— seleziona —"
                      or responses.get(f"{T}_post_ordinale","— seleziona —")=="— seleziona —"
                      or responses.get(f"{T}_suffic_cat","— seleziona —")=="— seleziona —"]
        if incompleti:
            st.warning(f"Completa motivazione e valutazione qualitativa per: "
                       f"{', '.join(incompleti)}")
        else:
            row = {
                "session_uuid":   str(uuid.uuid4()),
                "timestamp":      datetime.now().isoformat(timespec="seconds"),
                "ruolo":          ruolo,
                "team_id":        tid,
                "posizione_team": pos,
                "gruppo":         gruppo,
                "versione_llm":   versione_llm,
                "experience":     experience,
                "coordination":   coordination,
                "specialist_area":specialist_area,
                "ai_use":         ai_use,
                "ai_critical":    ai_critical,
                "ai_llm_use":     ai_llm_use,
                "ai_llm_trust":   ai_llm_trust,
                "ordine":         ordine_str,
            }
            row.update(responses)
            save_risposta(row)
            if n_risposte_totali() >= MAX_P:
                set_closed(True)
            st.session_state["completato"] = True
            st.rerun()
else:
    st.info("Completa e conferma tutti e tre gli scenari per procedere all'invio.")# ── TESTI LLM PRECOMPILATI — 27 TESTI (3 domini × 3 condizioni × 3 versioni) ──
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
completa delle comunicazioni SIGINT è il passo prioritario prima
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
"C":"""Dal briefing emerge uno sviluppo significativo: la fonte HUMINT indica
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
