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

**Fonti:** tecnica interna (buona), OSINT (verificata),
documentazione procedurale (parzialmente disponibile).

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

**Fonti:** documentazione tecnica (verificata), HUMINT (attendibilità
da verificare per indipendenza), SIGINT (parzialmente decifrata).

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

**Fonti:** tecnica (in analisi, parzialmente disponibile),
comparativa (verificata), operativa (in corso).

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

**Fonti:** FIU (verificata), anagrafica giudiziaria (verificata),
struttura di protezione (non consultata).

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

**Fonti:** HUMINT (attendibilità non verificata), SIGINT (verificata),
finanziaria (verificata).

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

**Fonti:** HUMINT (parzialmente verificata su casi precedenti),
finanziaria (verificata), operativa (in corso).

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

**Fonti:** OSINT finanziaria (verificata), registri societari
(parzialmente verificati), contrattuale (non disponibile).

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

**Fonti:** HUMINT (attendibilità parziale), SIGINT (verificata),
contrattuale (parzialmente disponibile).

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

**Fonti:** HUMINT (non verificata), comparativa (verificata),
finanziaria (verificata).

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
