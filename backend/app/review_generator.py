import random
import re
import requests
import json

TEMPLATES_BY_CATEGORY = {
    "tiralatte_maternita": {
        "titles": [
            "Indispensabile per l'allattamento: delicato, silenzioso ed efficiente!",
            "Massimo comfort e ottima aspirazione: la vera salvezza per le neo mamme",
            "Silenziosissimo e facile da pulire, batteria di lunga durata!",
            "Estrazione naturale e indolore, materiali sicuri senza BPA",
            "Comodissimo da portare in borsa: leggero, compatto e performante"
        ],
        "openings": [
            "Sto utilizzando questo tiralatte quotidianamente e posso confermare che ha migliorato tantissimo la mia routine di allattamento.",
            "Dopo aver provato diversi modelli, questo si è rivelato di gran lunga il più confortevole ed efficace fin dal primo utilizzo.",
            "Arrivato perfettamente sigillato e con una dotazione di accessori davvero completa e curata nei dettagli."
        ],
        "bodies": [
            "Le coppe in silicone morbido sono estremamente delicate sulla pelle e non provocano alcun fastidio o arrossamento. Le diverse modalità di massaggio e stimolazione consentono un'estrazione del latte naturale, fluida e veloce.",
            "Il motore è sorprendentemente silenzioso, perfetto per le sessioni notturne senza disturbare il riposo del bambino. Lo smontaggio è immediato e tutti i componenti a contatto con il latte si lavano e sterilizzano in pochi minuti.",
            "La batteria ricaricabile Type-C dura per molteplici sessioni senza dover stare vincolati a una presa a muro. Il display è chiaro e permette di regolare con precisione i livelli di intensità desiderati."
        ],
        "closings": [
            "Un acquisto fondamentale che consiglio con il cuore a tutte le mamme in cerca di praticità e benessere. 5 stelle meritatissime!",
            "Rapporto qualità-prezzo eccellente rispetto a marchi ben più costosi. Pienamente soddisfatta!",
            "Affidabile, igienico e facile da usare ovunque. Non potrei più farne a meno!"
        ]
    },
    "aspirapolvere_lavapavimenti": {
        "titles": [
            "Potenza di aspirazione eccellente e lavaggio pavimenti impeccabile!",
            "Pulisce e lava in una sola passata: addio per sempre a secchio e mocio!",
            "Leggero, maneggevole e con un'autonomia della batteria straordinaria",
            "Aspirazione profonda anche per peli di animali e briciole ostinate",
            "I doppi serbatoi e la funzione autopulente del rullo sono una vera svolta!"
        ],
        "openings": [
            "Questo elettrodomestico ha letteralmente dimezzato il tempo che dedicavo alle pulizie dei pavimenti di casa.",
            "Ricevuto con spedizione velocissima e imballaggio protettivo, pronto all'uso in meno di due minuti.",
            "Messo subito alla prova su gres porcellanato e parquet con sporco secco e liquido: superato a pieni voti!"
        ],
        "bodies": [
            "La divisione tra serbatoio dell'acqua pulita e quello di recupero garantisce di lavare sempre con acqua fresca e senza lasciare aloni. La testina snodabile scivola facilmente attorno ai mobili e negli angoli difficili.",
            "Il motore ad alta aspirazione rimuove briciole, polvere e peli di animali in un attimo, mentre il rullo motorizzato strofina le macchie asciugando la superficie quasi istantaneamente.",
            "La funzione di autopulizia sulla base di ricarica è comodissima: pulisce il rullo ed evita cattivi odori premendo un solo tasto. Ottima anche la silenziosità rapportata all'elevata potenza."
        ],
        "closings": [
            "Un investimento fantastico per la casa, fa risparmiare fatica e regala pavimenti splendenti ogni giorno. Consigliatissimo!",
            "Qualità costruttiva al top e prestazioni da fascia premium a un prezzo competitivo. 5 stelle piene!",
            "Superiore a ogni aspettativa, mai più senza per le pulizie quotidiane."
        ]
    },
    "skincare_cosmetici": {
        "titles": [
            "Qualità eccellente: risultati visibili già dalle prime applicazioni!",
            "Texture leggera, assorbimento immediato e profumazione delicata",
            "Formula ricca, idratante e molto delicata anche sulle pelli sensibili",
            "Dona freschezza, compattezza e luminosità immediata al viso!",
            "Non unge, si assorbe subito e lascia la pelle morbida e vellutata"
        ],
        "openings": [
            "Ho inserito questo prodotto nella mia routine quotidiana di cura del viso e i risultati sono davvero evidenti.",
            "Confezione elegante, sigillata ermeticamente e dosatore pratico che permette di non sprecare neanche una goccia.",
            "Fin dalla prima applicazione si percepisce l'elevata qualità della formula e la cura nelle materie prime."
        ],
        "bodies": [
            "La texture è leggera e setosa, si assorbe in pochi secondi senza ungere o lasciare residui lucidi, lasciando una sensazione di freschezza e idratazione profonda.",
            "La pelle appare visibilmente più distesa, elastica e nutrita dopo pochi giorni di utilizzo costante. Ottima anche come base prima del trucco.",
            "La profumazione è delicatissima e gradevole, assolutamente non invasiva. Nessun arrossamento o reazione, adatta anche a pelli reattive."
        ],
        "closings": [
            "Rapporto qualità-prezzo eccellente per un prodotto di questa resa. Lo ricomprerò sicuramente!",
            "Davvero soddisfatta, mantiene tutte le promesse e lascia una sensazione di benessere prolungata.",
            "Cinque stelle piene, super consigliato a chi cerca qualità ed efficacia!"
        ]
    },
    "rasoi_cura_persona": {
        "titles": [
            "Rasatura perfetta a zero senza alcuna irritazione o rossore!",
            "Lame affilatissime, testine snodate e comfort eccezionale sulla pelle",
            "Pratico, maneggevole e con un'ottima autonomia della batteria",
            "Rifinitura precisa e veloce, facile da pulire sotto l'acqua"
        ],
        "openings": [
            "Utilizzo questo dispositivo regolarmente e ha reso la rasatura molto più rapida e confortevole.",
            "Arrivato perfettamente imballato con tutti gli accessori di ricambio e cavo di ricarica rapida.",
            "L'impugnatura ergonomica garantisce una presa salda e sicura anche con le mani bagnate."
        ],
        "bodies": [
            "Le testine e le lame flessibili seguono i contorni con grande fluidità, tagliando i peli alla radice senza strappi o pizzicotti.",
            "Il motore è potente ma silenzioso, non scalda durante l'uso prolungato e la batteria dura settimane con una sola carica.",
            "Comodissimo da sciacquare direttamente sotto il rubinetto per una pulizia igienica e rapida in pochi secondi."
        ],
        "closings": [
            "Un acquisto azzeccato, addio irritazioni post-rasatura. 5 stelle meritate!",
            "Rapporto qualità-prezzo eccellente, robusto ed efficiente come i modelli professionali.",
            "Consigliatissimo a chi cerca precisione, velocità e comfort quotidiano."
        ]
    },
    "comodini_arredamento": {
        "titles": [
            "Design moderno ed elegante: solido, capiente e facile da montare!",
            "Superiore alle aspettative! Finiture impeccabili e vani molto funzionali",
            "Perfetto per la stanza, fa una splendida figura e ottimizza lo spazio",
            "Materiali robusti, stabilità perfetta e montaggio in pochissimi minuti",
            "Ottimo rapporto qualità/prezzo, esattamente come nelle foto dell'annuncio"
        ],
        "openings": [
            "Cercavo un complemento d'arredo moderno e salvaspazio per la stanza e questo modello ha centrato in pieno le mie aspettative.",
            "Pacco consegnato integro con tutti i componenti protetti da polistirolo e pellicole antigraffio.",
            "Si monta con grande facilità grazie alle istruzioni chiare e alla ferramenta completa inclusa nella scatola."
        ],
        "bodies": [
            "I materiali sono solidi e resistenti, la finitura è curata nei minimi particolari e piacevole sia alla vista che al tatto. Si abbina con naturalezza al resto dell'arredamento.",
            "I ripiani e i vani nascosti offrono un'ottima capienza per riporre libri, accessori e dispositivi, mantenendo sempre l'ambiente ordinato e pulito.",
            "La struttura risulta perfettamente stabile senza oscillazioni o scricchiolii. Le dimensioni corrispondono al millimetro alla descrizione."
        ],
        "closings": [
            "Un acquisto azzeccato che dona un tocco di classe ed eleganza alla casa. Consigliatissimo!",
            "Ottima qualità costruttiva a un prezzo davvero onesto. 5 stelle meritate!",
            "Pienamente soddisfatto, è bello da vedere e praticissimo da usare ogni giorno."
        ]
    },
    "cuffie_audio": {
        "titles": [
            "Suono limpido, bassi profondi e cancellazione del rumore eccellente!",
            "Connessione Bluetooth istantanea, stabilità perfetta e comodità totale",
            "Autonomia infinita e microfono nitidissimo per chiamate e meeting",
            "Display LED sulla custodia comodissimo, qualità audio da fascia alta",
            "Isolamento acustico top e vestibilità salda anche durante lo sport"
        ],
        "openings": [
            "Utilizzo queste cuffie da giorni per musica, video e telefonate di lavoro e ne sono rimasto davvero colpito.",
            "Packaging curato con gommini di varie misure e cavo di ricarica rapida Type-C incluso.",
            "Accoppiamento immediato allo smartphone fin dalla prima apertura della custodia."
        ],
        "bodies": [
            "La resa sonora è bilanciata con alti cristallini e bassi corposi che non distorcono neanche ad alto volume. L'isolamento acustico attivo attenua efficacemente i rumori esterni.",
            "I gommini ergonomici offrono una tenuta confortevole e salda nell'orecchio senza dare fastidio anche dopo molte ore consecutive di utilizzo.",
            "I comandi touch rispondono con precisione al tocco e i microfoni integrati catturano la voce in modo pulito anche all'aperto o in ambienti rumorosi."
        ],
        "closings": [
            "Per questa fascia di prezzo è difficile trovare di meglio sul mercato. 5 stelle senza esitazione!",
            "Qualità audio eccellente e batteria che dura giorni. Acquisto super consigliato!",
            "Pienamente promosso, perfetto per chi cerca affidabilità sonora e comodità."
        ]
    },
    "smartwatch_fitness": {
        "titles": [
            "Display AMOLED brillante e reattivo, monitoraggio salute preciso e completo!",
            "Ottimo smartwatch: notifiche puntuali e batteria che dura molti giorni",
            "Design leggero ed elegante, tantissime modalità sportive e cinturino comodo",
            "Rilevazione battito, ossigenazione e sonno impeccabile. Rapporto qualità/prezzo top!"
        ],
        "openings": [
            "Indosso questo smartwatch 24 ore su 24 e si è rivelato un compagno utilissimo sia per il fitness che per la vita quotidiana.",
            "Arrivato perfettamente imballato, configurazione con l'applicazione intuitiva e rapida.",
            "Lo schermo è visibile chiaramente anche sotto la luce diretta del sole con colori vividi e touch reattivo."
        ],
        "bodies": [
            "I sensori rilevano costantemente frequenza cardiaca, livelli di stress, ossigeno nel sangue e la qualità del sonno con grande attendibilità.",
            "Le notifiche di messaggi, chiamate e app arrivano istantaneamente senza perdite di sincronizzazione Bluetooth. Il cinturino è morbido e traspirante.",
            "La batteria garantisce diversi giorni di autonomia con uso intensivo senza l'ansia di dover ricaricare ogni sera. Ottima anche l'impermeabilità."
        ],
        "closings": [
            "Un orologio smart completo e affidabile che non ha nulla da invidiare a modelli molto più costosi. 5 stelle!",
            "Molto soddisfatto dell'acquisto, elegante al polso e ricco di funzionalità pratiche.",
            "Consigliato sia agli appassionati di sport che a chi vuole gestire le notifiche al volo."
        ]
    },
    "auto_diagnostica": {
        "titles": [
            "Strumento indispensabile: diagnostica immediata e lettura codici accurata!",
            "Facilissimo da collegare alla porta OBD2, mi ha fatto risparmiare tempo e soldi",
            "Compatto, robusto e intuitivo: visualizza tutti i parametri dell'auto in tempo reale",
            "Ottimo scanner diagnostico: display chiaro, cavo resistente e istruzioni complete"
        ],
        "openings": [
            "Ho acquistato questo dispositivo per verificare lo stato della centralina dell'auto ed ha funzionato alla perfezione al primo tentativo.",
            "Plug and play reale: basta inserirlo nella presa OBD dell'auto e si accende all'istante senza bisogno di batterie aggiuntive.",
            "Arrivato nei tempi prestabiliti in una confezione protettiva con manuale dettagliato."
        ],
        "bodies": [
            "Legge e cancella i codici di errore DTC della spia motore con rapidità, fornendo la descrizione testuale del guasto in modo chiaro e comprensibile.",
            "Lo schermo retroilluminato garantisce un'ottima leggibilità anche in garage o al buio, con pulsanti fisici ben distanziati e reattivi.",
            "Permette di monitorare i dati in tempo reale dei sensori (giri motore, temperatura liquido refrigerante, emissioni) con fluidità."
        ],
        "closings": [
            "Uno strumento che ogni automobilista dovrebbe tenere nel cruscotto. Consigliatissimo!",
            "Rapporto qualità-prezzo imbattibile, si ripaga da solo già al primo utilizzo. 5 stelle!",
            "Affidabile e preciso, promosso a pieni voti."
        ]
    },
    "cucina_accessori": {
        "titles": [
            "Chiusura ermetica salvafreschezza e materiali resistenti di prima scelta!",
            "Mantiene gli alimenti fragranti a lungo, solido ed esteticamente bellissimo",
            "Pratico, capiente e facile da pulire: 5 stelle piene per la cucina!",
            "Materiali per uso alimentare certificati, guarnizioni perfette senza perdite"
        ],
        "openings": [
            "Utilizzo questo accessorio ogni giorno in cucina e si è dimostrato praticissimo e robusto.",
            "Confezionato con grande cura per evitare graffi o ammaccature durante il trasporto.",
            "Design minimale ed elegante che fa una splendida figura sul piano di lavoro o in dispensa."
        ],
        "bodies": [
            "La guarnizione in silicone e il sistema di chiusura garantiscono una tenuta ermetica impeccabile contro umidità e aria, preservando aroma e freschezza.",
            "I materiali non assorbono odori né rilasciano residui, risultando estremamente igienici e veloci da lavare a mano o in lavastoviglie.",
            "Le dimensioni sono ideali per ottimizzare lo spazio sugli scaffali mantenendo tutto a portata di mano e in perfetto ordine."
        ],
        "closings": [
            "Ottima qualità costruttiva a un prezzo davvero conveniente. Lo consiglio a tutti!",
            "Pienamente soddisfatto, un prodotto utile e ben fatto che dura nel tempo.",
            "Cinque stelle meritatissime per estetica e funzionalità."
        ]
    },
    "generico": {
        "titles": [
            "Ottima qualità, esattamente conforme alla descrizione e alle foto!",
            "Prodotto eccellente, 5 stelle meritate sotto ogni aspetto",
            "Molto soddisfatto dell'acquisto! Pratico, resistente e ben fatto",
            "Ottimo rapporto qualità/prezzo, spedizione impeccabile e imballo sicuro",
            "Superiore alle aspettative, materiali robusti e cura nei dettagli"
        ],
        "openings": [
            "Pacco arrivato nei tempi previsti, ben protetto e con confezione integra.",
            "Utilizzo questo prodotto da qualche giorno e ne sono davvero entusiasta.",
            "Ho deciso di provare questo articolo e devo dire che la qualità è evidente fin dall'unboxing.",
            "Ottima esperienza d'acquisto: descrizione fedele e prodotto affidabile."
        ],
        "bodies": [
            "I materiali impiegati sono resistenti e piacevoli al tatto, rispondendo in pieno a tutte le aspettative dichiarate nell'annuncio.",
            "Semplice e intuitivo da utilizzare nella vita di tutti i giorni, con finiture curate e senza alcuna imperfezione visibile.",
            "Fa esattamente ciò per cui è stato progettato con grande efficienza ed affidabilità costante.",
            "La qualità costruttiva è notevole e si percepisce la solidità della struttura."
        ],
        "closings": [
            "Consiglio sicuramente l'acquisto a chiunque sia interessato. 5 stelle piene!",
            "Rapporto qualità-prezzo imbattibile, acquisterò sicuramente altri prodotti di questo brand.",
            "Davvero un ottimo acquisto, pienamente soddisfatto del risultato.",
            "Valutazione massima ampiamente meritata!"
        ]
    }
}

def detect_category(title: str) -> str:
    t = title.lower()
    if any(w in t for w in ["tiralatte", "biberon", "allattamento", "ciuccio", "neonato", "fasciatoio", "scaldabiberon", "sterilizzatore", "maternità"]):
        return "tiralatte_maternita"
    if any(w in t for w in ["aspirapolvere", "lavapavimenti", "scopa elettrica", "robot aspirapolvere", "lavatappeti", "mocio", "idropulitrice", "pulitore vapore", "aspirabriciole"]):
        return "aspirapolvere_lavapavimenti"
    if any(w in t for w in ["crema", "siero", "fondotinta", "rossetto", "lifting", "skincare", "trucco", "cosmetico", "antiage", "rughe", "vene", "shampoo", "balsamo", "maschera viso"]):
        return "skincare_cosmetici"
    if any(w in t for w in ["rasoio", "tagliacapelli", "epilatore", "spazzolino", "asciugacapelli", "phon", "piastra", "tagliabarba", "barba"]):
        return "rasoi_cura_persona"
    if any(w in t for w in ["comodino", "tavolo", "sedia", "mobile", "armadio", "divano", "letto", "scaffale", "mensola", "lampada", "specchio", "appendiabiti", "organizer", "arredo", "cilindrico"]):
        return "comodini_arredamento"
    if any(w in t for w in ["auricolari", "cuffie", "bluetooth", "auricolare", "soundbar", "altoparlante", "speaker", "anc", "tws", "earbuds", "cassa"]):
        return "cuffie_audio"
    if any(w in t for w in ["smartwatch", "fitness", "orologio", "tracker", "activity tracker", "cardiofrequenzimetro", "smartband", "contapassi"]):
        return "smartwatch_fitness"
    if any(w in t for w in ["obd", "diagnosi", "scanner", "compressore", "dashcam", "supporto auto", "auto", "avviatore", "batteria auto"]):
        return "auto_diagnostica"
    if any(w in t for w in ["barattolo", "caffè", "pentola", "padella", "coltello", "friggitrice", "bilancia", "borraccia", "thermos", "contenitore", "cucina"]):
        return "cucina_accessori"
    return "generico"

def generate_review(product_title: str, gemini_api_key: str = None) -> dict:
    """
    Genera una recensione a 5 stelle realistica e specifica con Titolo e Testo completo.
    Se è fornita una chiave Gemini API, usa il modello AI per personalizzarla al 100%.
    Altrimenti usa i template categorizzati intelligenti che esaltano le caratteristiche dell'oggetto.
    """
    clean_title = (product_title or "Prodotto").strip()
    
    if gemini_api_key and gemini_api_key.strip():
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key.strip()}"
            prompt = (
                f"Sei un acquirente italiano entusiasta che ha acquistato su Amazon il seguente prodotto: '{clean_title}'. "
                f"Scrivi una recensione a 5 stelle autentica, credibile e dettagliata in perfetto italiano. "
                f"IMPORTANTE: Elenca ed elogia specificamente le caratteristiche, i materiali e i punti di forza tipici di questo specifico articolo (es. se è un tiralatte parla di coppe, silenziosità, batteria; se è un aspirapolvere parla di potenza, serbatoi, lavaggio; se è un mobile parla di montaggio e stabilità). "
                f"Fornisci la risposta SOLO in formato JSON valido con due chiavi: 'title' (titolo accattivante di 5-10 parole) e 'body' (testo della recensione di 3-4 frasi naturali e specifiche)."
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"}
            }
            resp = requests.post(url, json=payload, timeout=7)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text)
                return {
                    "title": parsed.get("title", "Ottimo acquisto, qualità eccellente!"),
                    "body": parsed.get("body", "Prodotto eccellente e spedizione rapida. Consigliatissimo!"),
                    "source": "AI (Gemini)"
                }
        except Exception as e:
            print(f"[Review Generator AI Fallback] {e}")

    category = detect_category(clean_title)
    cat_data = TEMPLATES_BY_CATEGORY.get(category, TEMPLATES_BY_CATEGORY["generico"])
    
    title = random.choice(cat_data["titles"])
    opening = random.choice(cat_data["openings"])
    body = random.choice(cat_data["bodies"])
    closing = random.choice(cat_data["closings"])
    
    full_text = f"{opening} {body} {closing}"
    
    return {
        "title": title,
        "body": full_text,
        "source": f"Smart Specialized Engine ({category})"
    }
