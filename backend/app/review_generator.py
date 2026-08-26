import random
import re
import requests
import json

# =====================================================================
# MOTORE GENERATORE RECENSIONI 5 STELLE ULTRA-SPECIALIZZATE
# REGOLA: Tassativamente MAI generiche. Devono citare l'articolo e
# valorizzarne i dettagli d'uso, tecnici, ergonomici e prestazionali.
# =====================================================================

def clean_product_subject(title: str) -> str:
    """Pulisce il titolo rimuovendo parole di marketing o promozionali per estrarre il nome reale dell'oggetto."""
    if not title:
        return "articolo"
    
    # Rimuove emoji
    t = re.sub(r'[\U00010000-\U0010ffff]', '', title)
    t = re.sub(r'[🔥💥⚡⭐🎁🏷️✨📦🛒🚨📢👉✅❗‼️]', '', t)
    
    # Rimuove parole di vendita / telegram
    stop_words = [
        r'\b100%\s*rimborso\b', r'\brimborso\s*totale\b', r'\bgratis\b', r'\bofferta\b',
        r'\bprezzo\s*speciale\b', r'\bcoupon\b', r'\bprime\b', r'\bamazon\b', r'\bnuovo\b',
        r'\bspedizione\s*gratis\b', r'\brecensione\s*5\s*stelle\b', r'\bpp\s*refund\b',
        r'\bafter\s*review\b', r'\bcover\s*pp\b', r'\bcover\s*tax\b', r'\bno\s*fees\b'
    ]
    for pattern in stop_words:
        t = re.sub(pattern, '', t, flags=re.IGNORECASE)
    
    # Prende la parte principale del titolo (fino a 6-8 parole significative)
    words = [w for w in t.split() if len(w) > 1 and not w.startswith(('http', '@', '#'))]
    if not words:
        return "questo articolo"
    
    clean_subj = " ".join(words[:6]).strip(' -,:;()[]')
    return clean_subj if clean_subj else "questo articolo"


def extract_features(title: str) -> dict:
    """Estrae parametri tecnici e attributi specifici dal titolo."""
    t = title.lower()
    features = {
        "has_battery": bool(re.search(r'\b(batteria|ricaricabile|autonomia|mah|usb-c|type-c|cordless|senza fili)\b', t)),
        "has_led": bool(re.search(r'\b(display|schermo|led|amoled|lcd|digitale|touch)\b', t)),
        "has_bluetooth": bool(re.search(r'\b(bluetooth|wireless|wi-fi|wifi|app|smart|connessione)\b', t)),
        "has_waterproof": bool(re.search(r'\b(impermeabile|ip6[5-8]|ipx[5-8]|resistente all\'acqua|lavabile)\b', t)),
        "has_power": bool(re.search(r'\b(\d+\s*w|\d+\s*watt|\d+\s*v|\d+\s*volt|\d+\s*kpa|\d+\s*bar|\d+\s*rpm)\b', t)),
        "has_capacity": bool(re.search(r'\b(\d+\s*l|\d+\s*litr[io]|\d+\s*ml|\d+\s*kg|\d+\s*g|set\s*da\s*\d+|\d+\s*pezzi)\b', t))
    }
    return features


# =====================================================================
# DATABASE CATEGORIE E TEMPLATE ULTRA-SPECIFICI (50+ AMBITI PRECISI)
# =====================================================================
CATEGORIES = {
    # --- 1. IGIENE ORALE & DENTALE (IDROPULSORI, IRRIGATORI, SPAZZOLINI) ---
    "idropulsore_igiene_orale": {
        "keywords": [
            "idropulsore dentale", "idropulsore portatile", "idropulsore senza fili", "idropulsore", 
            "irrigatore orale", "irrigatore dentale", "irrigatore", "idropulitrice dentale", 
            "idropulitore dentale", "idrogetto dentale", "doccia dentale", "spazzolino elettrico", 
            "spazzolino sonico", "spazzolino rotante", "spazzolino", "filo interdentale elettrico", 
            "filo interdentale", "sbiancamento denti", "sbiancante denti", "testine spazzolino", 
            "pulizia dentale", "beccucci idropulsore", "ugelli idropulsore", "flosser", "water flosser"
        ],
        "titles": [
            "Pressione del getto d'acqua perfetta e pulizia interdentale impeccabile!",
            "Gengive sane e placca rimossa in profondità: serbatoio capiente e testine comodissime",
            "Idropulsore fantastico: getto modulabile, zero sanguinamento e batteria duratura",
            "Igiene orale professionale a casa: getto potente, compatto e facilissimo da riempire",
            "Spazzolamento e idrogetto impeccabili: sensazione di freschezza e pulizia duratura!"
        ],
        "openings": [
            "Utilizzo questo dispositivo per l'igiene orale ogni giorno dopo i pasti e ha trasformato completamente la mia routine di pulizia dentale.",
            "Arrivato in una confezione completa di molteplici beccucci/ugelli intercambiabili per ogni esigenza, cavo di ricarica rapida e comoda custodia.",
            "L'impugnatura è ergonomica e antiscivolo, con un serbatoio comodo da riempire ed estrarre per il risciacquo quotidiano."
        ],
        "bodies": [
            "I diversi livelli di pressione selezionabili (dalla modalità delicata/soft per gengive sensibili a quella a impulsi profondi) permettono di rimuovere ogni traccia di cibo e placca negli spazi interdentali più stretti e attorno all'apparecchio ortodontico.",
            "Il micro-getto d'acqua mirato ad alta frequenza massaggia le gengive senza irritarle o provocare sanguinamenti, garantendo un'igiene profonda superiore al tradizionale filo interdentale.",
            "La certificazione di impermeabilità IPX7 ne consente l'uso sicuro anche sotto la doccia o lavandolo sotto il rubinetto, mentre la batteria ricaricabile Type-C offre settimane di autonomia con una singola carica."
        ],
        "closings": [
            "Un acquisto fondamentale per la salute di denti e gengive che consiglio caldamente a tutti. 5 stelle meritate!",
            "Rapporto qualità-prezzo eccellente, molto più pratico, delicato e veloce del filo interdentale tradizionale.",
            "Bocca pulitissima, gengive sfiammate e sensazione di freschezza duratura. Pienamente soddisfatto!"
        ]
    },

    # --- 2. CURA DEI CAPELLI & STYLING (ASCIUGACAPELLI, PHON, PIASTRE, ARRICCIACAPELLI) ---
    "asciugacapelli_piastre_hairstyling": {
        "keywords": [
            "asciugacapelli professionale", "asciugacapelli", "phon professionale", "phon", 
            "piastra per capelli", "piastra capelli", "arricciacapelli", "spazzola asciugacapelli", 
            "spazzola lisciante", "spazzola ad aria calda", "diffusore capelli", "ferro arricciacapelli", 
            "styler capelli", "diffusore phon"
        ],
        "titles": [
            "Asciugatura ultra-rapida con ioni negativi: capelli morbidi, luminosi e zero crespo!",
            "Controllo intelligente del calore, flusso d'aria potente e rispetto totale della fibra capillare",
            "Piega perfetta da salone a casa: leggero, maneggevole e con beccucci/diffusore eccellenti",
            "Piastra scorrevole in ceramica: riscaldamento istantaneo e liscio perfetto in una sola passata!"
        ],
        "openings": [
            "Utilizzo questo styler per capelli costantemente dopo lo shampoo e i risultati sono paragonabili a una piega dal parrucchiere.",
            "Arrivato perfettamente imballato con beccucci concentratori magnetici/a incastro, diffusore per ricci e cavo girevole a 360° antipiega.",
            "Fin dal primo utilizzo si apprezza la leggerezza del corpo motore e il perfetto bilanciamento dei pesi che non affatica il braccio."
        ],
        "bodies": [
            "Il motore ad alta velocità eroga un flusso d'aria potente e concentrato che asciuga la chioma in tempi record senza bruciare o inaridire le punte.",
            "La tecnologia a ioni negativi contrasta l'elettricità statica e sigilla le cuticole, lasciando i capelli straordinariamente disciplinati, lucenti e morbidi al tatto.",
            "I vari livelli di calore e velocità, uniti al getto d'aria fredda istantaneo, permettono di modellare e fissare la piega a lungo con la massima precisione."
        ],
        "closings": [
            "Un accessorio di bellezza professionale che fa risparmiare tantissimo tempo ogni giorno. 5 stelle piene!",
            "Rapporto qualità-prezzo eccellente rispetto ai marchi più pubblicizzati. Consigliatissimo!",
            "Capelli morbidi, sani e luminosi senza alcun danno da calore. Pienamente soddisfatta!"
        ]
    },

    # --- 3. RASATURA & REGOLAZIONE BARBA/CORPO ---
    "rasoi_regolabarba_tagliacapelli": {
        "keywords": [
            "rasoio elettrico", "rasoio da barba", "tagliacapelli", "tagliabarba", "regolabarba", 
            "rifinitore barba", "epilatore", "depilatore", "lamette da barba", "rasoio corpo", 
            "rifinitore naso", "shaver", "trimmer", "rasoio"
        ],
        "titles": [
            "Lame affilate di precisione e zero irritazioni: taglio perfetto e scorrevole!",
            "Motore potente, impugnatura ergonomica e batteria che dura settimane con una carica",
            "Rifinitura millimetrica, testine lavabili sotto l'acqua e accessori completi per ogni esigenza",
            "Rasatura confortevole a secco o con schiuma: pelle liscia e zero arrossamenti!"
        ],
        "openings": [
            "Utilizzo questo dispositivo regolarmente per la cura quotidiana e ha reso la rasatura rapida e priva di fastidi.",
            "Arrivato perfettamente imballato con una dotazione ricca di pettini distanziatori, cavo di ricarica rapida e custodia protettiva.",
            "L'impugnatura offre un bilanciamento ideale e un grip antiscivolo anche a mani umide."
        ],
        "bodies": [
            "Le lame in acciaio inossidabile o ceramica autoaffilanti scorrono con estrema dolcezza tagliando i peli alla prima passata senza impuntamenti o tiraggi.",
            "Il motore ad alti giri garantisce un taglio omogeneo e costante anche sulla barba più folta o dura, senza surriscaldare la testina.",
            "La testina impermeabile permette l'uso a secco o sotto la doccia e si risciacqua in un secondo sotto il rubinetto per una pulizia impeccabile."
        ],
        "closings": [
            "Uno strumento affidabile, robusto e preciso in ogni dettaglio. Consigliatissimo!",
            "Ottimo investimento per chi cerca qualità professionale e risparmio di tempo. 5 stelle!",
            "Superiore alle aspettative: pelle liscia, zero tagli e massima comodità d'uso."
        ]
    },

    # --- 4. IDROPULITRICI ESTERNE & ALTA PRESSIONE (AUTO, GIARDINO, PATIO) ---
    "idropulitrici_esterni_alta_pressione": {
        "keywords": [
            "idropulitrice alta pressione", "idropulitrice a scoppio", "idropulitrice elettrica", 
            "idropulitrice da giardino", "idropulitrice per auto", "idropulitrice a batteria", 
            "idropulitrice", "pressure washer", "lancia idropulitrice"
        ],
        "titles": [
            "Pressione vigorosa e getto concentrato: elimina lo sporco ostinato in pochissimi minuti!",
            "Idropulitrice potente e compatta: lancia regolabile, serbatoio schiuma e tubi robusti",
            "Pulizia impeccabile di pavimentazioni esterne, terrazzi, recinzioni e carrozzeria auto!"
        ],
        "openings": [
            "Ho messo subito alla prova questa idropulitrice per la pulizia del piazzale, dei vialetti e dell'auto con risultati eccezionali.",
            "Arrivata con kit completo di lancia regolabile, ugello rotante turbo, serbatoio per detergente e raccordi rapidi.",
            "Montaggio rapido e intuitivo: pronta all'uso in meno di 5 minuti senza perdite d'acqua dai raccordi."
        ],
        "bodies": [
            "La pompa ad alta pressione sviluppa una potenza notevole capace di rimuovere muschio, fango secco e incrostazioni ostinate da pietra, cemento e veicoli.",
            "La lancia regolabile consente di passare con facilità da un getto a ventaglio delicato per il lavaggio auto a un getto mirato ad alta pressione per pavimenti duri.",
            "La struttura compatta su ruote e il lungo tubo ad alta pressione offrono un ampio raggio d'azione senza dover spostare continuamente il corpo macchina."
        ],
        "closings": [
            "Uno strumento potentissimo che fa risparmiare fatica e litri d'acqua. 5 stelle meritatissime!",
            "Rapporto qualità-prezzo eccellente per potenza ed efficacia di lavaggio. Consigliatissima!",
            "Pulizia profonda senza sforzo: superfici esterne tornate come nuove!"
        ]
    },

    # --- 5. SKINCARE & COSMETICA ---
    "skincare_cosmetica": {
        "keywords": [
            "siero viso", "siero", "crema viso", "acido ialuronico", "vitamina c", "retinolo", 
            "fondotinta", "antiage", "antirughe", "skincare", "lifting", "maschera viso", 
            "esfoliante", "tonico viso", "olio viso", "struccante", "bava di lumaca", "contorno occhi", 
            "crema idratante", "crema corpo", "crema solare", "balsamo labbra", "peeling"
        ],
        "titles": [
            "Texture setosa a rapido assorbimento: idratazione profonda e pelle luminosa fin da subito!",
            "Formula ricca e delicatissima anche sulle pelli sensibili: risultati visibili in pochi giorni",
            "Non unge, lascia il viso disteso, compatto e vellutato. Qualità cosmetica eccellente!",
            "Profumazione delicata ed effetto rimpolpante immediato: un must-have per la routine viso"
        ],
        "openings": [
            "Ho integrato questo cosmetico nella mia routine mattutina e serale di cura del viso e i benefici sono evidenti.",
            "Flacone elegante con erogatore dosatore che protegge la purezza della formula ed evita qualsiasi spreco di prodotto.",
            "Fin dalla primissima applicazione si apprezza la finezza degli ingredienti e l'assenza di alcool aggressivo."
        ],
        "bodies": [
            "La consistenza fluida penetra istantaneamente negli strati epidermici senza lasciare residui appiccicosi o effetto lucido, rendendola ideale anche come base trucco.",
            "La pelle appare visibilmente più tonica, nutrita ed elastica, con una grana affinata e una distensione evidente delle linee d'espressione.",
            "Nessun arrossamento, bruciore o reazione allergica: tollerabilità cutanea impeccabile anche per pelli delicate e reattive."
        ],
        "closings": [
            "Rapporto qualità-prezzo eccellente per un cosmetico di questa resa dermatologica. 5 stelle!",
            "Mantiene tutte le promesse con risultati reali e duraturi. Lo ricomprerò sicuramente!",
            "Pienamente soddisfatta della sensazione di freschezza e idratazione che regala ogni giorno."
        ]
    },

    # --- 6. MANICURE, PEDICURE & UNGHIE ---
    "manicure_pedicure_unghie": {
        "keywords": [
            "fresa per unghie", "fresa unghie", "lampada uv unghie", "fornetto unghie", "fornetto uv", 
            "lampada led unghie", "smalto semipermanente", "kit unghie", "tagliaunghie", 
            "aspiratore unghie", "lime unghie", "pedicure", "manicure", "ricostruzione unghie"
        ],
        "titles": [
            "Polimerizzazione rapida e uniforme: manicure e pedicure perfette come dall'estetista!",
            "Fresa potente, silenziosa e priva di vibrazioni: punte precise e velocità regolabile",
            "Risultati professionali a casa: smalto brillante, resistente e senza sbeccature!"
        ],
        "openings": [
            "Utilizzo questo set per la cura e la ricostruzione delle unghie a casa e la comodità d'uso è eccezionale.",
            "Arrivato con set completo di punte diamantate, cilindri abrasivi e alimentatore dedicato in una pratica custodia."
        ],
        "bodies": [
            "La potenza dei LED/UV distribuisce la luce in modo uniforme su tutte le dita, asciugando gel e semipermanenti in pochissimi secondi grazie ai sensori intelligenti di inserimento mano.",
            "Il manipolo della fresa ha un'impugnatura bilanciata priva di vibrazioni, con velocità regolabile e doppio senso di rotazione per trattare cuticole e callosità con la massima precisione."
        ],
        "closings": [
            "Uno strumento di qualità professionale che fa risparmiare tempo e denaro. 5 stelle meritate!",
            "Unghie curate, resistenti e brillanti per settimane. Consigliatissimo!"
        ]
    },

    # --- 7. DISPOSITIVI MEDICI & SALUTE (PRESSIONE, SATURIMETRI, TERMOMETRI, AEROSOL) ---
    "dispositivi_medici_salute": {
        "keywords": [
            "misuratore di pressione", "misuratore pressione", "sfigmomanometro", "saturimetro", 
            "pulsossimetro", "termometro a infrarossi", "termometro digitale", "termometro", 
            "aerosol", "nebulizzatore", "misuratore glicemia", "elettrostimolatore", "tens", 
            "fascia posturale", "tutore", "correttore postura"
        ],
        "titles": [
            "Misurazione rapida e precisa al millimetro: display grande, chiaro e facilissimo da leggere!",
            "Dispositivo medico affidabile e certificato: funzionamento immediato a un solo tasto",
            "Silenzioso, compatto e con memoria storica delle letture: fondamentale per la salute in famiglia"
        ],
        "openings": [
            "Ho acquistato questo dispositivo per monitorare i parametri di salute a casa e si è dimostrato impeccabile per precisione e semplicità.",
            "Confezionato con bracciale ergonomico regolabile, batterie, custodia da viaggio e manuale illustrato in italiano."
        ],
        "bodies": [
            "I sensori ad alta sensibilità rilevano i dati in pochissimi secondi, fornendo letture coerenti e conformi ai parametri di riferimento con indicatori visivi chiari.",
            "Lo schermo retroilluminato a grandi cifre rende i valori immediatamente comprensibili anche per persone anziane, con memoria per archiviare le misurazioni di più utenti.",
            "La pompa/nebulizzatore lavora con una silenziosità esemplare, rendendo l'utilizzo confortevole in qualsiasi momento."
        ],
        "closings": [
            "Un presidio sanitario domestico affidabile e indispensabile per tutta la famiglia. 5 stelle!",
            "Rapporto qualità-prezzo eccellente, paragonabile ai dispositivi da studio medico."
        ]
    },

    # --- 8. UMIDIFICATORI, DIFFUSORI & PURIFICATORI D'ARIA ---
    "diffusori_umidificatori_purificatori": {
        "keywords": [
            "diffusore di aromi", "diffusore oli essenziali", "diffusore aromi", "umidificatore ultrasuoni", 
            "umidificatore", "purificatore d'aria", "purificatore aria", "filtro hepa", 
            "deumidificatore portatile", "deumidificatore", "ozonizzatore"
        ],
        "titles": [
            "Nebulizzazione a ultrasuoni finissima e silenziosissima: aria fresca e profumo avvolgente!",
            "Purificazione efficace con filtro HEPA: elimina polvere, pollini e cattivi odori in un attimo",
            "Serbatoio capiente, luci LED rilassanti e spegnimento automatico di sicurezza: fantastico!"
        ],
        "openings": [
            "Ho posizionato questo dispositivo nella zona giorno/notte e la qualità dell'aria nella stanza è migliorata immediatamente.",
            "Design moderno ed elegante con finiture effetto legno/minimal che si integrano con grazia nell'arredamento."
        ],
        "bodies": [
            "La tecnologia ultrasonica diffonde una nebbia fresca e leggera che idrata l'aria negli ambienti secchi diffondendo gli oli essenziali in modo uniforme.",
            "Il sistema di filtrazione trattiene microparticelle e allergeni lasciando l'ambiente salubre, mentre la rumorosità è talmente bassa da non disturbare minimamente il riposo notturno.",
            "La funzione di spegnimento automatico a esaurimento acqua e i timer programmabili garantiscono massima sicurezza e serenità."
        ],
        "closings": [
            "Un acquisto eccellente per il benessere e il relax quotidiano in casa. 5 stelle piene!",
            "Profumazione gradevole, silenziosità assoluta e consumi irrisori. Consigliatissimo!"
        ]
    },

    # --- 9. ASPIRAPOLVERE & LAVAPAVIMENTI ---
    "aspirapolvere_lavapavimenti": {
        "keywords": [
            "aspirapolvere senza fili", "aspirapolvere", "lavapavimenti", "scopa elettrica", 
            "robot aspirapolvere", "lavatappeti", "mocio autolavante", "aspirabriciole", "aspiratore liquidi"
        ],
        "titles": [
            "Potenza di aspirazione straordinaria e pavimenti puliti in una sola passata!",
            "Leggera, maneggevole e con un'ottima autonomia: rivoluziona le pulizie di casa",
            "Aspirazione profonda contro peli di animali e briciole, doppi serbatoi impeccabili",
            "Rullo autopulente fantastico e asciugatura rapida senza aloni su parquet e gres"
        ],
        "openings": [
            "Questo elettrodomestico ha letteralmente dimezzato il tempo che dedicavo alla pulizia dei pavimenti.",
            "Messo subito alla prova su gres porcellanato, piastrelle e parquet con sporco ostinato: risultato impeccabile!",
            "Consegnato in tempi rapidi con un imballaggio protettivo e accessori pronti all'uso in un attimo."
        ],
        "bodies": [
            "La divisione netta tra serbatoio dell'acqua pulita e quello di recupero garantisce di non trascinare lo sporco, lasciando le superfici igienizzate e lucide. La testina snodabile scivola attorno ai battiscopa e sotto i mobili con fluidità.",
            "Il motore sviluppa una depressione potente che cattura istantaneamente polvere sottile, briciole e peli di animali, mentre il rullo motorizzato elimina anche le macchie secche asciugando in pochi secondi.",
            "La base di ricarica con programma di autopulizia lava il rullo ed evita cattivi odori premendo un solo pulsante. Ottima anche l'autonomia della batteria che permette di coprire l'intero appartamento con una sola carica."
        ],
        "closings": [
            "Un investimento fondamentale per la casa che fa risparmiare fatica ogni giorno. Consigliatissimo!",
            "Prestazioni paragonabili a modelli top di gamma dal costo doppio. 5 stelle piene!",
            "Efficiente, silenziosa e robusta. Pienamente soddisfatto dell'acquisto!"
        ]
    },

    # --- 10. BARATTOLI & CONTENITORI ERMETICI CAFFÈ ---
    "barattoli_contenitori_caffe": {
        "keywords": [
            "barattolo per caffè", "barattolo caffè", "contenitore caffè", "barattolo ermetico", 
            "contenitore ermetico", "valvola co2", "valvola rilascio co2", "barattolo acciaio inox", 
            "chicchi di caffè", "barattolo chicchi", "contenitore ermetico per caffè", "barattolo ermetico caffè"
        ],
        "titles": [
            "Barattolo ermetico eccezionale: acciaio inox robusto, valvola CO2 perfetta e aroma sempre al top!",
            "La miglior soluzione per conservare il caffè: tenuta stagna al 100%, ghiera datario e cucchiaio comodissimo",
            "Qualità costruttiva impeccabile: valvola di sfiato unidirezionale e guarnizione in silicone a tenuta perfetta",
            "Capiente (1.2L), elegante e utilissimo: mantiene i chicchi fragranti e freschi come appena tostati"
        ],
        "openings": [
            "Da appassionato di caffè cercavo un contenitore ermetico che preservasse davvero la fragranza e gli oli essenziali dei chicchi.",
            "Arrivato perfettamente imballato, senza il minimo graffio, con il cucchiaio dosatore in acciaio inox e le valvole di ricambio incluse.",
            "Fin dal primo contatto si percepisce la solidità dell'acciaio inossidabile alimentare di alto spessore, igienico e facile da pulire."
        ],
        "bodies": [
            "La valvola di rilascio unidirezionale per la CO2 funziona in modo impeccabile: permette ai gas naturali della tostatura di fuoriuscire evitando che l'ossigeno e l'umidità entrino a contatto con i chicchi o il macinato, mantenendo intatto l'aroma.",
            "La chiusura a leva in metallo esercita una pressione costante sulla guarnizione in silicone alimentare, garantendo un isolamento ermetico a tenuta stagna. Molto utile la ghiera con datario integrata sul coperchio per impostare il giorno del riempimento o della scadenza.",
            "La capienza da 1.2 Litri è ideale per ospitare comodamente un pacco standard di caffè in grani o polvere. Il cucchiaio dosatore agganciato lateralmente è praticissimo e permette di dosare con precisione senza sporcare."
        ],
        "closings": [
            "Un accessorio indispensabile per la cucina di chi ama il buon caffè e la freschezza degli alimenti. 5 stelle strameritate!",
            "Rapporto qualità-prezzo eccellente per finiture e tenuta ermetica. Consiglio l'acquisto senza riserve!",
            "Elegante sul piano di lavoro e funzionale al 100%. Pienamente soddisfatto!"
        ]
    },

    # --- 11. FRIGGITRICI AD ARIA & ELETTRODOMESTICI CUCINA ---
    "friggitrice_cucina_elettro": {
        "keywords": [
            "friggitrice ad aria", "friggitrice", "air fryer", "frullatore", "robot da cucina", 
            "macchina caffe", "macchina caffè", "caffettiera", "bollitore elettrico", "bollitore", 
            "tostapane", "forno elettrico", "fornetto", "impastatrice planetaria", "impastatrice", 
            "microonde", "slow cooker", "cuociriso", "estrattore di succo", "sigillatrice sottovuoto"
        ],
        "titles": [
            "Cottura perfetta e croccante senza olio: cestello capiente e programmi facilissimi!",
            "Prestazioni professionali in cucina: riscaldamento rapido e pulizia immediata",
            "Compatto, potente ed elegante sul piano di lavoro: un aiuto indispensabile per cucinare",
            "Materiali antiaderenti di prima scelta, consumi ridotti e risultati da chef!"
        ],
        "openings": [
            "Da quando ho inserito questo elettrodomestico in cucina lo utilizzo quotidianamente per preparare ogni tipo di pietanza.",
            "Arrivato con imballo robusto, manuale chiaro con ricettario e accessori pronti all'uso.",
            "Esteticamente moderno ed elegante, si sposa alla perfezione con l'arredamento della cucina."
        ],
        "bodies": [
            "Il flusso di calore e la resistenza ad alta potenza garantiscono una doratura uniforme e croccante all'esterno mantenendo le pietanze morbide e succose all'interno con pochissimo condimento.",
            "I comandi digitali touch screen permettono di selezionare i programmi preimpostati o di regolare temperatura e timer con estrema precisione e feedback sonoro chiaro.",
            "Il rivestimento antiaderente è di altissima qualità: il cibo non si attacca minimamente e il cestello estraibile si lava in lavastoviglie o sotto il rubinetto in meno di un minuto."
        ],
        "closings": [
            "Un acquisto azzeccatissimo che fa risparmiare tempo ed energia elettrica. 5 stelle meritate!",
            "Superiore alle aspettative per versatilità e qualità dei piatti. Consigliatissimo a tutti!",
            "Cottura impeccabile e salutare ogni giorno. Promosso a pieni voti!"
        ]
    },

    # --- 12. PENTOLE, PADELLE & UTENSILI DA CUCINA ---
    "utensili_cucina_accessori": {
        "keywords": [
            "pentola a pressione", "pentola", "padella antiaderente", "padella", "set coltelli", 
            "coltello cucina", "tagliere", "bilancia da cucina", "borraccia termica", "thermos", 
            "portaspezie", "organizer cucina", "scolapiatti", "tagliapasta", "stampo silicone", "posate"
        ],
        "titles": [
            "Materiali per uso alimentare di prima scelta, guarnizioni ermetiche e zero perdite!",
            "Solido, funzionale ed esteticamente bellissimo: un tocco di ordine ed eleganza in cucina",
            "Mantiene la freschezza e le temperature inalterate a lungo. 5 stelle piene!"
        ],
        "openings": [
            "Utilizzo questo accessorio quotidianamente in cucina e ha dimostrato una qualità costruttiva notevole.",
            "Confezione accurata che ha protetto ogni singolo elemento da graffi durante la spedizione."
        ],
        "bodies": [
            "La tenuta ermetica delle guarnizioni sigilla perfettamente contro aria e umidità preservando aroma, croccantezza e freschezza degli ingredienti.",
            "I materiali (vetro spesso / acciaio alimentare) non assorbono odori né rilasciano sostanze, risultando igienici e facilissimi da igienizzare sia a mano che in lavastoviglie.",
            "Il design compatto e curato permette di ottimizzare lo spazio nei pensili e sui ripiani mantenendo tutto a portata di mano."
        ],
        "closings": [
            "Un prodotto curato nei dettagli che dura nel tempo. Consigliatissimo!",
            "Rapporto qualità-prezzo davvero ottimo. 5 stelle meritate!"
        ]
    },

    # --- 13. COMPUTER, NOTEBOOK & MINI PC ---
    "computer_notebook_pc": {
        "keywords": [
            "mini pc", "notebook", "laptop", "computer desktop", "all-in-one", "macbook", 
            "chromebook", "workstation", "portatile", "ultrabook", "i3", "i5", "i7", "i9", 
            "ryzen", "n100", "n95", "n5105", "intel core", "amd ryzen", "computer", "pc"
        ],
        "titles": [
            "PC fluido, velocissimo e silenzioso: processore potente e ottima dissipazione termica!",
            "Prestazioni eccellenti, avvio in pochi secondi con SSD e reattività totale in multitasking",
            "Display nitido dai colori brillanti, memoria capiente e batteria duratura. 5 stelle piene!",
            "Rapporto qualità/prezzo imbattibile per studio, smart working e produttività quotidiana!"
        ],
        "openings": [
            "Utilizzo questo computer quotidianamente per lavoro, navigazione e streaming e si è dimostrato straordinariamente fluido e scattante.",
            "Arrivato perfettamente imballato con alimentatore originale e sistema operativo già configurato e pronto all'uso fin dalla prima accensione.",
            "Messo subito alla prova aprendo molteplici software e schede del browser in contemporanea: reattività impeccabile senza alcun rallentamento."
        ],
        "bodies": [
            "La combinazione tra il processore veloce e la memoria SSD NVMe garantisce tempi di caricamento istantanei all'avvio e nell'apertura di qualsiasi applicazione, con una gestione della RAM eccellente.",
            "Lo schermo offre una risoluzione definita con ottimi angoli di visione, neri profondi e trattamento antiriflesso che non affatica la vista anche dopo molte ore consecutive di lavoro.",
            "La ventola di raffreddamento è sorprendentemente silenziosa e mantiene le temperature costantemente basse anche sotto carico prolungato. La dotazione di porte (USB 3.0, Type-C, HDMI) è completa e comodissima."
        ],
        "closings": [
            "Una macchina affidabile, elegante e performante che consiglio senza riserve. 5 stelle meritatissime!",
            "Superiore alle aspettative rispetto al prezzo di acquisto: hardware scattante e ottima qualità costruttiva.",
            "Pienamente soddisfatto, perfetto per chi cerca produttività e velocità senza spendere cifre esorbitanti."
        ]
    },

    # --- 14. MONITOR, SCHERMI & PROIETTORI ---
    "monitor_schermi": {
        "keywords": [
            "monitor gaming", "monitor pc", "schermo pc", "display gaming", "display curvo", 
            "144hz", "165hz", "240hz", "proiettore portatile", "videoproiettore", "smart tv", 
            "monitor 4k", "monitor 2k", "monitor ips", "monitor", "schermo"
        ],
        "titles": [
            "Colori brillanti, neri profondi e frequenza di aggiornamento fluidissima!",
            "Monitor eccezionale: cornici sottili, zero affaticamento visivo e resa visiva spettacolare",
            "Luminosità uniforme e tempi di risposta istantanei: perfetto sia per lavoro che per gaming"
        ],
        "openings": [
            "Ho collegato questo monitor alla mia postazione di lavoro e la qualità visiva è sbalorditiva fin dalla prima accensione.",
            "Pannello privo di pixel difettosi o aloni di luce, con base solida e inclinazione regolabile."
        ],
        "bodies": [
            "La tecnologia del pannello garantisce angoli di visione ampi e una fedeltà cromatica impeccabile con colori vividi e contrasti definiti.",
            "L'elevato refresh rate rende lo scorrimento dei testi, delle finestre e dei giochi incredibilmente fluido senza scie o sfarfallii.",
            "Le tecnologie di protezione visiva (antiriflesso e filtro luce blu) permettono di lavorare per ore senza mai stancare la vista."
        ],
        "closings": [
            "Un monitor di fascia alta a un prezzo eccezionale. 5 stelle meritate!",
            "Consigliatissimo a chiunque cerchi nitidezza, fluidità e comfort visivo."
        ]
    },

    # --- 15. TABLET & E-READER ---
    "tablet_e_ipad": {
        "keywords": ["tablet android", "tablet", "ipad", "fire hd", "tab", "display touch", "e-reader", "kindle", "lettore ebook"],
        "titles": [
            "Touch screen reattivo, display brillante e fluidità assoluta con tutte le app!",
            "Leggero, compatto e con una batteria infinita: perfetto per streaming, studio e lettura",
            "Ottimo tablet: audio stereo coinvolgente e prestazioni fluide senza lag. 5 stelle!"
        ],
        "openings": [
            "Utilizzo questo tablet ogni giorno per guardare video, leggere documenti e navigare sul web con grandissima soddisfazione.",
            "Arrivato in una confezione protettiva con cavo di ricarica rapida e accessori completi."
        ],
        "bodies": [
            "Il display touch risponde istantaneamente al tocco con immagini limpide e colori saturi, ideale per godersi film e serie TV.",
            "Il processore gestisce la riproduzione multimediale e le applicazioni con fluidità senza impuntamenti o surriscaldamenti.",
            "La batteria garantisce molte ore continuative di utilizzo e gli altoparlanti integrati offrono un suono chiaro e corposo."
        ],
        "closings": [
            "Un dispositivo versatile ed affidabile per tutta la famiglia. Consigliatissimo!",
            "Rapporto qualità-prezzo imbattibile, super consigliato a studenti e professionisti."
        ]
    },

    # --- 16. MOUSE, TASTIERE & PERIFERICHE ---
    "mouse_tastiere_gaming": {
        "keywords": [
            "mouse wireless", "mouse gaming", "mouse ergonomico", "mouse verticale", 
            "tastiera meccanica", "tastiera wireless", "tastiera bluetooth", "tappetino mouse", 
            "mousepad xxl", "mousepad", "mouse", "tastiera"
        ],
        "titles": [
            "Digitazione confortevole e silenziosa, switch reattivi e precisione assoluta!",
            "Ergonomia perfetta che non affatica il polso, connessione wireless stabile e zero ritardi",
            "Sensore ottico millimetrico, tasti precisi e materiali piacevoli al tatto. 5 stelle!"
        ],
        "openings": [
            "Ho acquistato questa periferica per la mia scrivania e la comodità d'uso è notevole fin dai primi minuti.",
            "Packaging curato con ricevitore USB e cavo inclusi, riconosciuto all'istante dal computer senza driver complessi."
        ],
        "bodies": [
            "I tasti offrono una corsa precisa e una risposta tattile piacevole, garantendo una digitazione rapida e priva di errori.",
            "Il sensore e la connessione lavorano con latenza impercettibile e precisione millimetrica su qualsiasi superficie.",
            "L'impugnatura e il profilo anatomico supportano la mano in posizione naturale riducendo l'affaticamento articolare."
        ],
        "closings": [
            "Una periferica indispensabile per lavorare o giocare al massimo del comfort. 5 stelle!",
            "Costruzione solida e grande piacevolezza d'uso quotidiana."
        ]
    },

    # --- 17. AUDIO, CUFFIE & CASSE BLUETOOTH ---
    "cuffie_auricolari_audio": {
        "keywords": [
            "auricolari bluetooth", "auricolari wireless", "auricolari", "cuffie bluetooth", 
            "cuffie wireless", "cuffie", "earbuds", "tws", "soundbar", "altoparlante bluetooth", 
            "speaker bluetooth", "cassa bluetooth", "microfono wireless", "cuffie anc", "cancellazione rumore"
        ],
        "titles": [
            "Audio cristallino con bassi potenti e cancellazione del rumore attiva davvero efficace!",
            "Connessione Bluetooth 5.3 istantanea, microfoni nitidi in chiamata e batteria infinita",
            "Comodità assoluta nell'orecchio, controlli touch reattivi e display LED sulla custodia",
            "Qualità sonora di livello superiore, isolamento acustico top e custodia compatta"
        ],
        "openings": [
            "Utilizzo queste cuffie quotidianamente per ascoltare musica, podcast e per lunghe chiamate di lavoro.",
            "Packaging molto curato con gommini di ricambio in silicone di varie taglie e cavo di ricarica rapida.",
            "Accoppiamento immediato allo smartphone appena si apre la custodia di ricarica."
        ],
        "bodies": [
            "La resa acustica è straordinariamente dettagliata, con alti limpidi e bassi corposi che non distorcono neppure al massimo volume. La riduzione del rumore attenua i suoni ambientali garantendo un ascolto immersivo.",
            "I microfoni integrati con tecnologia di filtraggio catturano la voce in modo pulito e chiaro, consentendo conversazioni impeccabili anche all'aperto con vento o traffico.",
            "L'ergonomia garantisce una vestibilità stabile che non scivola durante la corsa o gli allenamenti e la custodia ricarica più volte gli auricolari per giorni di autonomia."
        ],
        "closings": [
            "Nella loro categoria sono senza dubbio tra le migliori per qualità e prezzo. 5 stelle piene!",
            "Prestazioni audio favolose e comodità totale. Acquisto consigliatissimo!",
            "Pienamente promosso sotto ogni aspetto tecnico e di design."
        ]
    },

    # --- 18. SMARTWATCH & FITNESS TRACKER ---
    "smartwatch_fitness_tracker": {
        "keywords": [
            "smartwatch", "smart watch", "smartband", "smart band", "orologio fitness", 
            "fitness tracker", "activity tracker", "cardiofrequenzimetro da polso", 
            "cardiofrequenzimetro", "sportwatch", "orologio smart", "orologio da polso smart"
        ],
        "titles": [
            "Display AMOLED brillante e reattivo, monitoraggio parametri salute accurato e puntuale!",
            "Smartwatch completo ed elegante: notifiche fulminee e batteria che dura moltissimi giorni",
            "Leggero al polso, ricco di modalità sportive e impermeabile: rapporto qualità/prezzo imbattibile",
            "Sensori cardio e sonno precisi, cinturino comodo e applicazione ricca di statistiche"
        ],
        "openings": [
            "Indosso questo smartwatch costantemente sia durante gli allenamenti che nella vita quotidiana.",
            "Arrivato in confezione curata con cavo di ricarica magnetico rapido e guida in italiano.",
            "Lo schermo si legge benissimo anche sotto la luce solare diretta grazie all'ottima luminosità e ai colori vivaci."
        ],
        "bodies": [
            "I sensori ottici rilevano frequenza cardiaca, livelli di ossigeno SpO2, stress e fasi del sonno con grande coerenza, fornendo report chiari sull'applicazione.",
            "La sincronizzazione Bluetooth non perde mai un colpo: chiamate, messaggi e notifiche delle app arrivano all'istante con vibrazione personalizzabile.",
            "L'autonomia è eccellente e permette di dimenticarsi del caricatore per vari giorni consecutivi. La resistenza all'acqua garantisce tranquillità anche sotto la doccia o con la pioggia."
        ],
        "closings": [
            "Un dispositivo completo e affidabile che non ha nulla da invidiare a modelli ben più costosi. 5 stelle!",
            "Esteticamente gradevole e funzionalmente impeccabile. Consigliatissimo!",
            "Ottimo compagno per monitorare la salute e le notifiche al polso."
        ]
    },

    # --- 19. POWERBANK & BATTERIE PORTATILI ---
    "powerbank_batterie_portatili": {
        "keywords": [
            "power bank", "powerbank", "batteria portatile", "caricatore portatile", 
            "caricabatterie portatile", "batteria esterna", "20000mah", "10000mah", "30000mah", 
            "pd3.0", "qc4.0", "quick charge", "power delivery"
        ],
        "titles": [
            "Power Bank 20000mAh potentissimo: ricarica rapida PD 22.5W, display percentuale e autonomia infinita!",
            "Capienza reale da 20000mAh, ricarica ultra-veloce PD 3.0/QC 4.0 e zero surriscaldamento",
            "Indispensabile per viaggi e lavoro: ricarica smartphone e tablet più volte a piena velocità",
            "Materiali solidi, porte multiple USB-C/USB-A e protocolli di ricarica rapida 22.5W impeccabili"
        ],
        "openings": [
            "Utilizzo quotidianamente questo Power Bank per alimentare smartphone, cuffie e tablet fuori casa e le prestazioni sono eccezionali.",
            "Arrivato perfettamente imballato, pre-caricato e corredato di cavo di ricarica ad alta velocità.",
            "Fin dal primo utilizzo si nota l'elevata densità energetica e la cura costruttiva nei dettagli e nelle porte di connessione."
        ],
        "bodies": [
            "La capacità da 20000mAh è reale ed eroga una riserva di carica abbondante, permettendo di ricaricare completamente un moderno smartphone per 4-5 volte consecutive senza cali di tensione.",
            "I protocolli di ricarica rapida Power Delivery 3.0 e Quick Charge 4.0 a 22.5W riconoscono all'istante il dispositivo collegato erogando la massima potenza disponibile per una carica dal 20% all'80% in circa mezz'ora.",
            "Le porte di uscita multiple (USB-C bidirezionale e USB-A) consentono di ricaricare più dispositivi contemporaneamente, mentre i circuiti di protezione intelligente evitano surriscaldamenti e sbalzi di tensione mantenendo il corpo fresco al tatto."
        ],
        "closings": [
            "Un Power Bank affidabile, capiente e compatto da portare sempre nello zaino o in valigia. 5 stelle strameritate!",
            "Rapporto qualità-prezzo imbattibile per capacità reale e velocità di ricarica rapida. Consigliatissimo!",
            "Mai più con la batteria a terra: prodotto eccellente e indispensabile."
        ]
    },

    # --- 20. CAVI, HUB & ACCESSORI SMARTPHONE ---
    "accessori_smartphone_cavi": {
        "keywords": [
            "caricatore usb-c", "caricabatterie gan", "caricatore", "caricabatterie", "cavo usb-c", 
            "cavo type-c", "cavo lightning", "cavo hdmi", "cover iphone", "cover", "pellicola vetro", 
            "vetro temperato", "supporto smartphone", "supporto tablet", "hub usb-c", "hub usb", 
            "docking station", "chiavetta usb", "ssd esterno", "scheda sd"
        ],
        "titles": [
            "Ricarica ultra-rapida, materiali robusti e connettività impeccabile!",
            "Compatto, resistente e affidabile: risolve ogni esigenza di ricarica e connessione",
            "Perfetta compatibilità, finiture solide e prestazioni costanti senza surriscaldamenti"
        ],
        "openings": [
            "Ho preso questo accessorio per completare la mia dotazione tecnologica e ne sono pienamente soddisfatto.",
            "Costruzione solida che trasmette immediatamente una sensazione di affidabilità e sicurezza elettrica."
        ],
        "bodies": [
            "I connettori si innestano saldamente senza giochi meccanici e i protocolli di ricarica/trasmissione dati lavorano a piena velocità senza dispersioni.",
            "I sistemi di protezione integrati evitano sovratensioni e mantengono le temperature perfettamente nella norma anche sotto carico prolungato."
        ],
        "closings": [
            "Un accessorio indispensabile da avere sempre a portata di mano. 5 stelle!",
            "Qualità eccellente a un prezzo conveniente. Consigliatissimo!"
        ]
    },

    # --- 21. VIDEOSORVEGLIANZA & SICUREZZA ---
    "sicurezza_telecamere": {
        "keywords": [
            "telecamera wifi", "telecamera da esterno", "telecamera da interno", "telecamera", 
            "videocamera sorveglianza", "videosorveglianza", "ip camera", "wifi camera", 
            "pannello solare telecamera", "telecamera solare", "visione notturna", "sensore pir", 
            "campanello wireless", "videocitofono"
        ],
        "titles": [
            "Risoluzione video 2K nitidissima, visione notturna a colori e rilevamento di movimento fulmineo!",
            "Installazione wireless semplicissima, pannello solare sempre carico e app intuitiva",
            "Sorveglianza affidabile con audio bidirezionale chiaro e zero falsi allarmi. 5 stelle!"
        ],
        "openings": [
            "Ho installato questa videocamera per monitorare l'esterno della casa e ha superato le mie aspettative.",
            "Kit completo di staffe, viti e dima di foratura per un montaggio veloce e sicuro."
        ],
        "bodies": [
            "Il sensore ottico cattura immagini definite e ricche di dettagli sia di giorno che di notte grazie ai potenti faretti integrati e agli infrarossi.",
            "Il sensore PIR con intelligenza artificiale distingue persone da animali inviando notifiche istantanee sullo smartphone con registrazione su scheda SD/cloud.",
            "L'impermeabilità alle intemperie e l'alimentazione autonoma assicurano un funzionamento continuo 24/7 senza manutenzione."
        ],
        "closings": [
            "Garantisce sicurezza e serenità a tutta la famiglia. Consigliatissima!",
            "Ottima qualità costruttiva e software reattivo. 5 stelle meritate!"
        ]
    },

    # --- 22. VENTILATORI, CLIMATIZZAZIONE & RAFFREDDAMENTO LETTO ---
    "ventilatori_raffreddamento_letto": {
        "keywords": [
            "raffreddamento per letto", "raffreddamento letto", "sotto le lenzuola", "ventilatore letto", 
            "ventilatore da letto", "ventilatore sotto lenzuola", "ventilatore a piantana", "ventilatore a torre", 
            "ventilatore da tavolo", "ventilatore usb", "ventilatore portatile", "condizionatore portatile", 
            "rinfrescatore d'aria", "ventilatore silenzioso", "ventilatore", "bed fan", "cooling fan", "raffrescatore"
        ],
        "titles": [
            "Flusso d'aria fresco e costante sotto le lenzuola: notti estive fresche e sonno rigenerante!",
            "Ventilatore ultra-silenzioso con velocità regolabili: fresco immediato nel letto senza rumori fastidiosi",
            "Sistema di raffreddamento per letto formidabile: consumi ridottissimi, montaggio rapido e freschezza totale",
            "Addio afa notturna: 5 velocità comodissime, getto d'aria omogeneo e massima silenziosità!"
        ],
        "openings": [
            "Ho acquistato questo sistema di ventilazione e raffreddamento per affrontare le notti calde e afose ed è stata la migliore decisione per il mio riposo.",
            "Arrivato perfettamente imballato con tutti gli accessori, il tubo/diffusore d'aria flessibile per posizionamento sotto le lenzuola e il pratico controller di velocità.",
            "L'installazione a bordo letto è facilissima e immediata: si adatta a qualsiasi materasso e lenzuolo senza creare ingombro."
        ],
        "bodies": [
            "Il motore eroga un flusso d'aria fresca e piacevole che circola in modo uniforme sotto le coperte allontanando subito l'umidità e il calore corporeo.",
            "Le 5 velocità selezionabili permettono di calibrare l'intensità perfetta: le prime marce sono così silenziose da poter dormire senza alcun disturbo, mentre le marce superiori rinfrescano il letto in pochi minuti prima di coricarsi.",
            "La costruzione è solida, i consumi elettrici sono minimi e il sistema evita il getto diretto d'aria fredda sul corpo, garantendo un comfort ideale senza rischiare malanni."
        ],
        "closings": [
            "Un dispositivo geniale che ha migliorato drasticamente la qualità del mio sonno estivo. 5 stelle meritate!",
            "Efficacissimo, silenzioso e dai consumi irrisori rispetto a un condizionatore. Consigliatissimo!",
            "Letto fresco e sonno profondo tutta la notte. Pienamente soddisfatto dell'acquisto!"
        ]
    },

    # --- 23. MOBILI & ARREDAMENTO ---
    "mobili_arredamento": {
        "keywords": [
            "comodino", "tavolino", "tavolo", "sedia ergonomica", "sedia da ufficio", "poltrona", "scaffale", 
            "libreria", "armadietto", "mobiletto", "cassettiera", "mobile tv", "divano", "struttura letto", 
            "giroletto", "telaio letto", "testiera letto", "scrivania", "mensola", "appendiabiti", "scarpiera"
        ],
        "titles": [
            "Design moderno ed elegante: solido, capiente e facilissimo da montare!",
            "Finiture impeccabili e materiali robusti: fa una splendida figura nella stanza",
            "Perfetta stabilità, dimensioni conformi al millimetro e ottima ottimizzazione dello spazio",
            "Superiore alle aspettative: elegante, resistente e curato nei minimi dettagli"
        ],
        "openings": [
            "Cercavo un complemento d'arredo per valorizzare la stanza e questo articolo ha soddisfatto tutte le mie aspettative.",
            "Imballaggio esemplare con protezioni in polistirolo e angolari rigidi per proteggere le superfici da qualsiasi urto.",
            "La ferramenta inclusa è completa di pezzi di scorta e le istruzioni illustrate rendono l'assemblaggio rapido anche da soli."
        ],
        "bodies": [
            "I pannelli e la struttura sono spessi e stabili, la verniciatura è uniforme e piacevole sia al tatto che alla vista, integrandosi con armonia nell'ambiente.",
            "Gli scomparti e i ripiani offrono un volume utile notevole per riporre oggetti, vestiti o documenti mantenendo l'ordine con grande praticità.",
            "La base poggia in modo saldo a terra senza oscillazioni, e le guide/cerniere scorrono con fluidità e silenziosità."
        ],
        "closings": [
            "Un acquisto di grande impatto estetico e funzionale per la casa. 5 stelle meritate!",
            "Rapporto qualità-prezzo ottimo rispetto ai negozi di arredamento. Consigliatissimo!",
            "Solido, bello da vedere e pratico da vivere ogni giorno."
        ]
    },

    # --- 23. ILLUMINAZIONE & LAMPADE LED ---
    "illuminazione_lampade": {
        "keywords": [
            "lampada da tavolo", "lampada scrivania", "plafoniera led", "lampadario", 
            "luce led", "striscia led rgb", "striscia led", "faretto led", "faretto", 
            "applique", "luce solare esterno", "lampadina smart", "lampada"
        ],
        "titles": [
            "Luce potente e omogenea, tonalità dimmerabili e zero sfarfallio!",
            "Design moderno e minimale: illumina l'intera stanza con bassi consumi energetici",
            "Facilissima da installare, telecomando/app comodo e resa cromatica eccellente"
        ],
        "openings": [
            "Ho montato questo punto luce per rinnovare l'illuminazione dell'ambiente e il risultato visivo è spettacolare.",
            "Pacco consegnato integro con tutti i tasselli e morsetti necessari all'installazione rapida."
        ],
        "bodies": [
            "I LED ad alta efficienza erogano un fascio luminoso brillante e diffuso senza creare zone d'ombra o affaticamento visivo.",
            "La regolazione dell'intensità e del calore della luce (da calda a fredda) consente di creare sempre l'atmosfera perfetta per ogni momento della giornata.",
            "I consumi elettrici sono minimi e la struttura disperde il calore in modo efficiente per una lunga durata."
        ],
        "closings": [
            "Un'ottima scelta per valorizzare gli ambienti domestici con eleganza. 5 stelle!",
            "Rapporto qualità-prezzo imbattibile, illumina alla perfezione!"
        ]
    },

    # --- 24. AUTO & ACCESSORI MOTO ---
    "auto_diagnostica_accessori": {
        "keywords": [
            "scanner obd2", "diagnosi auto", "obd2", "obd", "dashcam auto", "dashcam", 
            "supporto auto", "portacellulare auto", "trasmettitore fm", "tappetini auto", 
            "coprisedili auto", "lucidatrice auto", "cavi batteria auto"
        ],
        "titles": [
            "Strumento indispensabile per l'auto: lettura rapida, precisa e facilissimo da usare!",
            "Compatto, potente e robusto: risolve all'istante le emergenze e fa risparmiare tempo e denaro",
            "Connessione immediata, display retroilluminato chiaro e costruzione solida a prova d'urto"
        ],
        "openings": [
            "Ho acquistato questo dispositivo per la manutenzione e la sicurezza della mia auto e ha funzionato alla perfezione al primo colpo.",
            "Arrivato in custodia protettiva con cavi resistenti e manuale d'istruzioni chiaro."
        ],
        "bodies": [
            "Il collegamento è immediato e la risposta del software/hardware è rapida e affidabile nel leggere parametri, codici o erogare la potenza richiesta.",
            "Lo schermo retroilluminato garantisce un'ottima visibilità anche in condizioni di scarsa luce o in garage.",
            "I materiali sono resistenti agli urti, agli oli e agli sbalzi termici, ideali da tenere sempre nel bagagliaio o nel vano portaoggetti."
        ],
        "closings": [
            "Un accessorio che ogni automobilista dovrebbe possedere. Consigliatissimo!",
            "Si ripaga da solo fin dal primissimo utilizzo. 5 stelle meritate!",
            "Affidabile e robusto in ogni situazione."
        ]
    },

    # --- 25. COMPRESSORI PORTATILI & GONFIATORI ---
    "compressore_portatile_auto": {
        "keywords": [
            "compressore portatile", "compressore auto", "gonfiatore portatile", "gonfiatore auto", 
            "gonfiatore pneumatici", "gonfiatore", "avviatore auto", "avviatore portatile", 
            "jump starter", "booster auto", "manometro digitale", "150psi", "150 psi", "pompa bici elettrica"
        ],
        "titles": [
            "Pressione PSI precisa e gonfiaggio fulmineo: salva da ogni emergenza!",
            "Autonomia eccellente, display digitale chiaro e spegnimento automatico a pressione raggiunta",
            "Compatto, potente e robusto: gonfia pneumatici e ruote in pochissimi minuti senza sforzo!"
        ],
        "openings": [
            "Ho acquistato questo compressore/avviatore portatile per tenerlo sempre in auto ed è già stato provvidenziale.",
            "Valigetta/sacca completa di adattatori per valvole auto, moto, bici e palloni, con cavo di ricarica rapida e luce LED di emergenza."
        ],
        "bodies": [
            "Il manometro digitale legge la pressione con assoluta precisione e la funzione di auto-stop arresta l'erogazione esattamente al valore impostato.",
            "Il motore interno sviluppa una pressione notevole gonfiando uno pneumatico sgonfio in tempi record senza surriscaldamenti eccessivi.",
            "La batteria integrata funge anche da powerbank di emergenza e la torcia LED incorporata è comodissima per interventi notturni sul ciglio della strada."
        ],
        "closings": [
            "Uno strumento di emergenza indispensabile per ogni automobilista e motociclista. 5 stelle meritatissime!",
            "Qualità costruttiva al top, preciso, affidabile e compatto. Consigliatissimo!"
        ]
    },

    # --- 26. ATTREZZI FAI DA TE & BRICOLAGE ---
    "faidate_attrezzi": {
        "keywords": [
            "trapano a percussione", "avvitatore a batteria", "trapano avvitatore", "trapano", 
            "avvitatore", "flessibile", "smerigliatrice angolare", "smerigliatrice", "seghetto alternativo", 
            "set chiavi a bussola", "set cacciaviti", "cacciavite", "valigetta attrezzi", 
            "saldatore a stagno", "multimetro digitale", "metro laser", "morsa da banco"
        ],
        "titles": [
            "Coppia di serraggio vigorosa, doppia batteria al litio e mandrino preciso!",
            "Valigetta completa e attrezzi robusti: indispensabile per tutti i lavori di casa e bricolage",
            "Motore potente, impugnatura gommata bilanciata e accessori di qualità. 5 stelle piene!"
        ],
        "openings": [
            "Utilizzo questo elettroutensile per vari lavori di bricolage e manutenzione domestica e si è dimostrato un vero cavallo di battaglia.",
            "Valigetta rigida comoda e resistente, con ogni inserto e accessorio alloggiato al proprio posto."
        ],
        "bodies": [
            "Il motore sviluppa una forza notevole permettendo di forare e avvitare su legno, metallo e muratura senza sforzo e con regolazioni di frizione precise.",
            "Le batterie al litio hanno un'ottima tenuta di carica e il caricatore rapido consente di lavorare ininterrottamente alternandole.",
            "La luce LED integrata illumina la zona di lavoro e il mandrino autoserrante blocca le punte senza slittamenti."
        ],
        "closings": [
            "Uno strumento semiprofessionale a una frazione del costo di marche famose. 5 stelle!",
            "Robusto, maneggevole e potente: acquisto super consigliato!"
        ]
    },

    # --- 27. GIARDINAGGIO & CURA ESTERNI ---
    "giardinaggio_esterni": {
        "keywords": [
            "tagliaerba a batteria", "tagliaerba", "decespugliatore", "soffiatore foglie", 
            "soffiatore", "motosega a batteria", "motosega", "forbici da potatura", "forbici potatura", 
            "tubo irrigazione estensibile", "tubo irrigazione", "irrigatore giardino", "centralina irrigazione", 
            "telo pacciamatura", "serra da giardino"
        ],
        "titles": [
            "Taglio netto e potente, leggero da maneggiare e con ottima autonomia!",
            "Rende la cura del giardino rapida e senza fatica: materiali resistenti alle intemperie",
            "Perfetto per prato e siepi: silenzioso, bilanciato e facilissimo da avviare"
        ],
        "openings": [
            "Ho messo subito alla prova questo attrezzo per la manutenzione del giardino e sono rimasto colpito dall'efficienza.",
            "Confezione solida con tutti i dispositivi di protezione, lame di ricambio e accessori montabili in pochi minuti."
        ],
        "bodies": [
            "Le lame affilate recidono erba e rami con precisione e fluidità senza strappare le fibre vegetali.",
            "La leggerezza della struttura e l'asta telescopica regolabile evitano affaticamento a schiena e braccia anche dopo sessioni prolungate.",
            "L'assenza di cavi ingombranti e la silenziosità del motore permettono di lavorare ovunque in totale libertà."
        ],
        "closings": [
            "Un valido aiuto per avere un giardino sempre curato e in ordine. 5 stelle!",
            "Qualità costruttiva al top e grande praticità d'uso. Consigliatissimo!"
        ]
    },

    # --- 28. COLLARI, PETTORINE & GUINZAGLI CANI E GATTI ---
    "collari_pettorine_guinzagli_cani": {
        "keywords": [
            "collare per cani", "collare per cane", "collare cane", "collare cani", "collare antiabbaio", 
            "collare addestramento", "collare gps", "collare led", "collare luminoso", "collare gatto", 
            "collare gatti", "collare seresto", "collare scalibor", "collare", "pettorina per cani", 
            "pettorina cane", "pettorina cani", "pettorina ad h", "pettorina antifuga", "pettorina no pull", 
            "pettorina gatto", "pettorina", "guinzaglio per cani", "guinzaglio cane", "guinzaglio cani", 
            "guinzaglio retrattile", "guinzaglio doppio", "guinzaglio addestramento", "guinzaglio", 
            "museruola cane", "museruola", "targhetta cane", "targhetta gatto"
        ],
        "titles": [
            "Collare resistente, imbottitura morbida e chiusura di massima sicurezza per il mio cane!",
            "Materiali robusti, cuciture riflettenti per la notte e regolazione perfetta: il cane è comodissimo",
            "Non stringe, non irrita il collo e regge benissimo le trazioni anche con cani vivaci. 5 stelle!",
            "Qualità costruttiva al top: fibbia solida a scatto rapido, tessuto traspirante e tenuta impeccabile",
            "Addestramento e controllo ottimali durante le passeggiate: sicuro, elegante e durevole"
        ],
        "openings": [
            "Ho acquistato questo collare per il mio cane e fin dalla prima passeggiata la differenza si è notata subito.",
            "Arrivato in una confezione curata con sistema di regolazione rapido e gancio di sicurezza solido in metallo.",
            "I materiali al tatto trasmettono immediatamente un'ottima sensazione di robustezza e morbidezza interna."
        ],
        "bodies": [
            "L'imbottitura interna traspirante evita qualsiasi sfregamento o perdita di pelo sul collo del cane anche dopo lunghe corse, mentre la fibbia di bloccaggio a scatto rapido è solidissima e non si apre accidentalmente sotto forte trazione.",
            "Le cuciture rinforzate e gli inserti riflettenti ad alta visibilità aumentano notevolmente la sicurezza durante le passeggiate serali o con scarsa illuminazione.",
            "La regolazione millimetrica della circonferenza consente di adattarlo perfettamente alla taglia del cane senza stringere o sfilarsi.",
            "Il gancio ad anello in lega resistente permette di agganciare il guinzaglio o la medaglietta in modo rapido e stabile senza rischio di rotture."
        ],
        "closings": [
            "Il mio cane lo indossa volentieri e io mi sento sicuro a ogni uscita. Prodotto eccellente, 5 stelle meritate!",
            "Rapporto qualità-prezzo imbattibile per robustezza e comfort. Consigliatissimo a tutti i proprietari di cani e gatti!",
            "Passeggiate serene e controllo ottimale: mai più problemi al guinzaglio. Pienamente soddisfatto!"
        ]
    },

    # --- 28b. ALTRI ACCESSORI ANIMALI & PET CARE ---
    "animali_pet": {
        "keywords": [
            "cuccia per cani", "cuccia per cane", "cuccia cane", "cuccia per gatti", "cuccia gatto", "cuccia", 
            "tiragraffi per gatti", "tiragraffi", "tosatrice per cani", "tosatrice per gatti", "tosatrice animali", 
            "spazzola per cani", "spazzola cane", "spazzola gatto", "guanto togli peli", "fontanella per gatti", 
            "fontanella gatto", "distributore cibo automatico", "mangiatoia automatica", "ciotola cane", 
            "ciotola gatto", "ciotola rialzata", "ciotola anti ingozzamento", "lettiera per gatti", "lettiera gatto", 
            "trasportino per cani", "trasportino cane", "trasportino gatto", "borsa cane", "passeggino per cani", 
            "gioco cane", "giocattolo cane", "tiragraffi", "tappetino igienico", "traversine cani", "antiparassitario", 
            "crocchette cane", "snack cane", "cani", "cane", "gatti", "gatto", "cucciolo", "cuccioli", "pet"
        ],
        "titles": [
            "Materiali morbidi e atossici, amatissimo dal mio animale fin dal primo giorno!",
            "Robusto, sicuro e facilissimo da pulire: il miglior acquisto per il nostro cucciolo",
            "Ottima stabilità, rifiniture curate e comfort totale per cani e gatti. 5 stelle!"
        ],
        "openings": [
            "Ho acquistato questo prodotto per il mio animale domestico ed è stato un successo immediato.",
            "Arrivato perfettamente imballato, privo di qualsiasi odore sgradevole e subito pronto all'uso."
        ],
        "bodies": [
            "I tessuti e i componenti sono resistenti a graffi, morsi e usura quotidiana, garantendo la massima sicurezza per l'animale.",
            "La pulizia e il lavaggio sono semplicissimi, consentendo di mantenere l'ambiente igienico e privo di peli accumulati.",
            "La struttura è ergonomica e solida, offrendo al cucciolo comfort, stabilità e benessere prolungato."
        ],
        "closings": [
            "Approvato al 100% dal mio cucciolo e da me! Consigliatissimo a tutti i proprietari di animali. 5 stelle!",
            "Qualità eccellente a un prezzo conveniente. Pienamente soddisfatto!"
        ]
    },

    # --- 29. SPORT & FITNESS ---
    "sport_fitness_outdoor": {
        "keywords": [
            "manubri pesi", "manubri regolabili", "manubri", "elastici fitness", "bande di resistenza", 
            "tappetino yoga", "tappetino fitness", "panca pesi", "panca palestra", "cyclette da camera", 
            "cyclette", "tapis roulant", "corda per saltare", "corda salto", "fasce resistenza", 
            "zaino trekking", "tenda campeggio", "sacco a pelo", "guanti palestra"
        ],
        "titles": [
            "Materiali tecnici resistenti e grip perfetto: ideale per allenarsi al meglio!",
            "Robusto, ergonomico e compatto: qualità da palestra comodamente a casa",
            "Superiore alle aspettative: supporta carichi intensi con massima stabilità e comfort"
        ],
        "openings": [
            "Utilizzo questa attrezzatura nei miei allenamenti quotidiani e la resa è impeccabile.",
            "Spedizione rapidissima con imballo compatto e istruzioni per gli esercizi incluse."
        ],
        "bodies": [
            "I materiali antiscivolo garantiscono una presa sicura e salda anche con mani sudate, prevenendo infortuni o scivolamenti.",
            "La robustezza strutturale regge sollecitazioni continuative senza cedere o deformarsi, dimostrando grande longevità.",
            "Facile da riporre e trasportare per allenarsi sia in casa che all'aperto con la massima versatilità."
        ],
        "closings": [
            "Un compagno di allenamento fondamentale per raggiungere i propri obiettivi di fitness. 5 stelle!",
            "Rapporto qualità-prezzo imbattibile, consigliatissimo a sportivi di ogni livello!"
        ]
    },

    # --- 30. ABBIGLIAMENTO, ZAINI & VALIGIE ---
    "abbigliamento_valigie_borse": {
        "keywords": [
            "zaino porta pc", "zaino trekking", "zaino viaggio", "zaino", "valigia rigida", 
            "valigia", "trolley cabina", "trolley", "borsa da viaggio", "borsa donna", "borsa", 
            "marsupio", "portafoglio uomo", "portafoglio", "cintura pelle", "occhiali da sole", 
            "giacca impermeabile", "scarpe da ginnastica", "sneakers", "pantofole", "ciabatte", "pigiama"
        ],
        "titles": [
            "Cuciture rinforzate, tessuti impermeabili e scomparti super organizzati!",
            "Trolley leggero e maneggevole con ruote a 360° e chiusura di sicurezza: perfetto per viaggiare",
            "Design elegante e vestibilità impeccabile: materiali di prima scelta e rifiniture perfette"
        ],
        "openings": [
            "Ho acquistato questo articolo e sono rimasto piacevolmente colpito dalla cura sartoriale e dalla scelta dei tessuti.",
            "Consegnato in confezione protettiva antigraffio con tutte le etichette originali."
        ],
        "bodies": [
            "Le cerniere scorrono con fluidità senza incastrarsi e le cuciture nei punti di maggior trazione sono doppie e resistenti.",
            "Gli scomparti interni imbottiti proteggono dispositivi elettronici e oggetti personali, offrendo una capienza sorprendente.",
            "Il materiale è piacevole al tatto, traspirante e resistente alla pioggia e allo sfregamento."
        ],
        "closings": [
            "Un acquisto di grande stile e praticità che consiglio vivamente. 5 stelle piene!",
            "Ottimo rapporto qualità-prezzo, supera molti prodotti di marche note!"
        ]
    },

    # --- 31. RIPOSO, CUSCINI & MATERASSI ---
    "cuscini_materassi_riposo": {
        "keywords": [
            "cuscino cervicale", "cuscino memory foam", "cuscino memory", "cuscino ortopedico", 
            "guanciale memory", "guanciale ortopedico", "guanciale", "topper memory", "materasso ortopedico", 
            "materasso", "memory foam", "topper", "federa traspirante"
        ],
        "titles": [
            "Sostegno cervicale perfetto: niente più dolori al collo e sonno finalmente riposante!",
            "Memory foam ad alta densità a lento ritorno: comfort ortopedico eccezionale",
            "Traspirante, ergonomico e con federa lavabile: una vera svolta per la qualità del sonno!"
        ],
        "openings": [
            "Soffrivo spesso di risvegli con rigidità al collo e alle spalle, ma con questo supporto per il riposo la situazione è cambiata radicalmente fin dalla prima notte.",
            "Arrivato sottovuoto perfettamente sigillato, ha ripreso la sua forma corretta in poche ore senza rilasciare alcun odore chimico."
        ],
        "bodies": [
            "La schiuma memory accoglie la testa e allinea la colonna vertebrale in modo naturale sia dormendo supini che sul fianco, distribuendo la pressione in modo uniforme.",
            "La sagomatura ergonomica sostiene la zona cervicale senza affossarsi eccessivamente e mantiene la sua elasticità e densità nel tempo.",
            "La fodera esterna in tessuto traspirante è fresca, ipoallergenica e facilmente sfoderabile con cerniera per il lavaggio in lavatrice."
        ],
        "closings": [
            "Un toccasana per la salute cervicale e il riposo notturno. Consigliatissimo a tutti!",
            "Rapporto qualità-prezzo imbattibile rispetto ai negozi di ortopedia. 5 stelle piene!"
        ]
    },

    # --- 32. INTEGRATORI & SALUTE ---
    "integratori_salute": {
        "keywords": [
            "integratore alimentare", "integratore", "capsule", "compresse", "magnesio supremo", 
            "magnesio", "collagene idrolizzato", "collagene", "vitamina d3 k2", "vitamina d3", 
            "vitamina c pura", "omega 3 alto dosaggio", "omega 3", "probiotici fermenti", 
            "fermenti lattici", "creatina monoidrato", "proteine whey", "multivitaminico completo", 
            "melatonina sonno", "zinco"
        ],
        "titles": [
            "Alta concentrazione di principi attivi, facile da deglutire e ottima digeribilità!",
            "Formula pura e certificata: benefici tangibili su energia e benessere in pochi giorni",
            "Nessun retrogusto, ottimo dosaggio giornaliero e flacone sigillato a regola d'arte. 5 stelle!"
        ],
        "openings": [
            "Assumo questo integratore regolarmente ogni giorno come supporto nutrizionale e ne apprezzo particolarmente la qualità degli ingredienti.",
            "Flacone sigillato con sigillo di garanzia integro e data di scadenza generosa."
        ],
        "bodies": [
            "Le capsule sono di dimensioni ottimali e facili da assumere con un bicchiere d'acqua, senza causare alcuna pesantezza gastrica o retrogusto sgradevole.",
            "La titolazione dei principi attivi rispetta i più elevati standard nutrizionali fornendo il giusto fabbisogno giornaliero per sostenere vitalità e difese.",
            "Composizione pulita priva di glutine, lattosio o additivi superflui, garanzia di elevata purezza e massima biodisponibilità."
        ],
        "closings": [
            "Un integratore di qualità farmaceutica a un prezzo conveniente. Lo ricomprerò sicuramente!",
            "Pienamente soddisfatto dei benefici riscontrati. 5 stelle meritate!"
        ]
    },

    # --- 33. MASSAGGIATORI & BENESSERE CORPOREO ---
    "massaggiatori_benessere": {
        "keywords": [
            "pistola massaggiante", "massaggiatore cervicale", "massaggiatore collo", 
            "cuscino massaggiante", "pressoterapia gambe", "massaggiatore piedi", "idromassaggio piedi", 
            "pediluvio", "massaggiatore", "cervicale massaggiante"
        ],
        "titles": [
            "Sollievo muscolare immediato! Percussione profonda, 6 testine e motore ultra silenzioso",
            "Scioglie contratture e tensioni muscolari con grande efficacia: robusto e facilissimo da usare",
            "Potenza regolabile con precisione e batteria di lunghissima durata: un toccasana quotidiano!"
        ],
        "openings": [
            "Ho acquistato questo dispositivo per alleviare le tensioni muscolari dopo l'attività fisica e il lavoro ed è diventato irrinunciabile.",
            "Valigetta rigida elegante e ben organizzata con tutti gli accessori di ricambio inclusi."
        ],
        "bodies": [
            "La profondità di percussione raggiunge i tessuti profondi sciogliendo nodi e rigidità su schiena, collo e gambe con diversi livelli di intensità selezionabili dal display.",
            "Il motore brushless eroga una coppia vigorosa senza bloccarsi alla pressione, mantenendo un livello acustico molto basso e discreto.",
            "La batteria agli ioni di litio assicura giorni di trattamenti con una sola ricarica rapida Type-C."
        ],
        "closings": [
            "Un acquisto che vale ogni centesimo per il benessere corporeo quotidiano. 5 stelle!",
            "Rapporto qualità-prezzo eccellente, costruzione solida e risultati tangibili fin da subito!"
        ]
    },

    # --- 34. MATERNITÀ & INFANZIA (TIRALATTE, BIBERON, PRIMA INFANZIA) ---
    "maternita_infanzia": {
        "keywords": [
            "tiralatte elettrico", "tiralatte indossabile", "tiralatte", "allattamento", 
            "latte materno", "scaldabiberon", "sterilizzatore biberon", "biberon anticolica", 
            "biberon", "ciuccio neonato", "ciuccio", "cuscino allattamento", "fasciatoio", 
            "bavaglino", "seggiolone", "passeggino", "culla neonato", "culla", "neonato"
        ],
        "titles": [
            "Materiali di altissima qualità senza BPA, sicuro e praticissimo per mamma e bebè!",
            "Delicato, silenzioso e facilissimo da sterilizzare: indispensabile per la routine quotidiana",
            "Massimo comfort, ergonomia studiata per i neonati e zero perdite. 5 stelle piene!"
        ],
        "openings": [
            "Ho scelto questo articolo per il mio bimbo e sono rimasto estremamente soddisfatto della qualità costruttiva.",
            "Confezione perfettamente sigillata nel rispetto delle più rigide norme igieniche per la prima infanzia."
        ],
        "bodies": [
            "Le finiture e i componenti a contatto con il bambino sono al 100% privi di BPA e atossici, con guarnizioni a tenuta impeccabile.",
            "L'ergonomia è studiata appositamente per una presa comoda e un utilizzo naturale, e ogni elemento si lava e sterilizza con la massima facilità."
        ],
        "closings": [
            "Un supporto fondamentale che dona serenità a ogni genitore. Consigliatissimo!",
            "Rapporto qualità-prezzo eccellente, promosso a pieni voti!"
        ]
    },

    # --- 35. FOTOGRAFIA, VIDEO & CREATOR ---
    "fotografia_video_creator": {
        "keywords": [
            "ring light", "luce ad anello", "treppiede smartphone", "treppiede reflex", 
            "treppiede", "gimbal stabilizzatore", "gimbal", "softbox", "fondale fotografico", 
            "microfono lavalier", "telecomando bluetooth foto"
        ],
        "titles": [
            "Illuminazione uniforme e naturale, zero ombre e temperatura colore regolabile!",
            "Stabilità perfetta, testa orientabile fluida e telecomando scatto comodissimo",
            "Kit completo indispensabile per video, streaming e foto professionali. 5 stelle!"
        ],
        "openings": [
            "Utilizzo questo set fotografico per riprese video, foto e videoconferenze con una resa visiva nettamente superiore.",
            "Arrivato con custodia imbottita, staffe orientabili e cavi di collegamento completi."
        ],
        "bodies": [
            "La struttura in alluminio è leggera ma stabilissima, con chiusure a sgancio rapido che permettono di regolare l'altezza in pochi secondi.",
            "L'erogazione luminosa o la stabilizzazione sui tre assi eliminano qualsiasi oscillazione o sfarfallio, garantendo scatti e riprese sempre nitidi e professionali."
        ],
        "closings": [
            "Un accessorio essenziale per chiunque realizzi contenuti multimediali. 5 stelle!",
            "Qualità costruttiva al top a un prezzo accessibile. Consigliatissimo!"
        ]
    }
}


def detect_specific_category(title: str) -> tuple:
    """
    Trova la categoria specifica più adatta dando priorità alle parole chiave composte
    e più tecniche (es. 'idropulsore dentale' batte qualsiasi keyword generica).
    """
    if not title:
        return None, None

    t = title.lower()
    matches = []
    
    for cat_name, cat_data in CATEGORIES.items():
        for kw in cat_data["keywords"]:
            kw_clean = kw.lower()
            pattern = r'(?<!\w)' + re.escape(kw_clean) + r'(?!\w)'
            if re.search(pattern, t):
                # Peso calcolato: numero di parole * 100 + lunghezza caratteri
                # Assicura che espressioni a più parole (es. 'idropulsore dentale', 'friggitrice ad aria')
                # abbiano priorità assoluta rispetto a singole parole isolate.
                word_count = len(kw_clean.split())
                score = word_count * 100 + len(kw_clean)
                matches.append((score, cat_name, cat_data, kw))
    
    if matches:
        matches.sort(key=lambda x: x[0], reverse=True)
        best_match = matches[0]
        return best_match[1], best_match[2]
        
    return None, None


def extract_deep_technical_specs(title: str) -> list:
    """Estrae e analizza le specifiche tecniche concrete dal titolo dell'articolo."""
    t = title.lower()
    specs = []
    
    # 1. Wattaggio / Potenza
    w_match = re.search(r'\b(\d+\s*(?:w|watt|kw|kpa|bar))\b', t)
    if w_match:
        val = w_match.group(1).upper().replace(" ", "")
        specs.append(f"L'erogazione di potenza ({val}) è vigorosa e costante, garantendo prestazioni elevate senza cali di rendimento sotto sforzo.")
    
    # 2. Batteria & Autonomia
    mah_match = re.search(r'\b(\d+\s*(?:mah|ah))\b', t)
    if mah_match:
        val = mah_match.group(1).upper().replace(" ", "")
        specs.append(f"La batteria ad alta densità da {val} assicura un'autonomia davvero generosa, consentendo utilizzi prolungati senza l'ansia di ricaricare.")
        
    # 3. Risoluzione, Frequenza & Display
    res_match = re.search(r'\b(4k|2k|1080p|fhd|qhd|amoled|oled|ips|144hz|165hz|240hz|hdr)\b', t)
    if res_match:
        val = res_match.group(1).upper()
        specs.append(f"La qualità visiva con standard {val} offre una nitidezza eccellente, colori vivaci e un'ottima fluidità priva di scie o sfarfallio.")
        
    # 4. Standard Connettività & Porte
    conn_match = re.search(r'\b(bluetooth\s*5\.[0-4]|bt\s*5\.[0-4]|wi-fi\s*6|wifi\s*6|type-c|usb-c|hdmi\s*2\.[01])\b', t)
    if conn_match:
        val = conn_match.group(1).title()
        specs.append(f"La connettività {val} garantisce un accoppiamento istantaneo, latenza impercettibile e massima stabilità di trasmissione.")
        
    # 5. Materiali di costruzione
    mat_match = re.search(r'\b(acciaio\s*inox|alluminio|silicone|vetro\s*temperato|legno\s*massello|carbonio|ecopelle|cotone|abs)\b', t)
    if mat_match:
        val = mat_match.group(1)
        specs.append(f"La struttura realizzata in {val} trasmette una sensazione di notevole solidità e resistenza all'usura, con finiture curate al millimetro.")

    # 6. Dimensioni, Capacità & Volumi
    cap_match = re.search(r'\b(\d+(?:[.,]\d+)?\s*(?:l|litri|ml|kg|g|pollici|cm|mm))\b', t)
    if cap_match:
        val = cap_match.group(1)
        specs.append(f"Il formato/capacità da {val} rispetta scrupolosamente le specifiche tecniche, risultando perfettamente proporzionato e funzionale all'uso quotidiano.")

    # 7. Funzionalità specifiche (impermeabile, silenzioso, etc.)
    if re.search(r'\b(impermeabile|ip6[5-8]|ipx[5-8]|waterproof)\b', t):
        specs.append("La certificazione di impermeabilità protegge i componenti interni da schizzi, acqua e umidità offrendo totale affidabilità.")
    if re.search(r'\b(brushless|inverter|silenzioso|low noise)\b', t):
        specs.append("Il motore ad alta efficienza lavora con una silenziosità esemplare e vibrazioni minime.")

    return specs


def synthesize_custom_review(product_title: str) -> dict:
    """
    Sintetizza una recensione tecnica ultra-specifica analizzando minuziosamente
    i parametri tecnici, costruttivi ed ergonomici del prodotto.
    """
    subject = clean_product_subject(product_title)
    tech_specs = extract_deep_technical_specs(product_title)
    
    # Titoli tecnici contestuali
    titles = [
        f"Prestazioni tecniche eccellenti e dettagli costruttivi impeccabili per {subject}!",
        f"{subject.capitalize()}: caratteristiche tecniche conformi alle aspettative e resa al top",
        f"Ottima efficienza, materiali di prima scelta e funzionamento impeccabile per {subject}",
        f"Superiore alle aspettative: {subject} offre grande affidabilità e precisione tecnica"
    ]
    
    # Aperture tecniche
    openings = [
        f"Sto utilizzando questo {subject} da diversi giorni e ha dimostrato una qualità tecnica e costruttiva notevole in ogni scenario d'uso.",
        f"Ricevuto perfettamente imballato e conforme al 100% alla scheda tecnica: {subject} risponde con precisione a quanto dichiarato.",
        f"Messo subito sotto test per valutarne le specifiche: questo {subject} si distingue per affidabilità e cura nei dettagli tecnici."
    ]
    
    # Corpo con specifiche concrete
    if tech_specs:
        body_text = " ".join(tech_specs[:3])
    else:
        body_text = f"La costruzione di {subject} si distingue per l'assemblaggio solido privo di giochi meccanici, un'eccellente risposta funzionale e un'ottimizzazione ideale per l'utilizzo quotidiano intensivo."
    
    # Chiusure
    closings = [
        f"Un prodotto tecnicamente valido e affidabile che soddisfa appieno le aspettative. 5 stelle meritatissime per {subject}!",
        f"Rapporto qualità-prezzo eccellente in rapporto alle prestazioni offerte. Consigliatissimo!",
        f"Pienamente soddisfatto delle prestazioni e dell'affidabilità dimostrata nel tempo."
    ]
    
    return {
        "title": random.choice(titles),
        "body": f"{random.choice(openings)} {body_text} {random.choice(closings)}",
        "source": "Deep Technical Synthesizer"
    }


def generate_review(product_title: str, gemini_api_key: str = None) -> dict:
    """
    Genera una recensione a 5 stelle autentica, tecnica, dettagliata e categoricamente NON generica.
    1. Se è configurata una chiave Gemini AI, genera una recensione analitica al 100%.
    2. Altrimenti usa il database categoriale specifico (50+ settori tecnici).
    3. In subordine sintetizza dinamicamente la recensione estraendo le caratteristiche tecniche dal titolo.
    """
    clean_title = (product_title or "Articolo Amazon").strip()
    
    # 1. TENTATIVO CON INTELLIGENZA ARTIFICIALE GEMINI (ANALISI TECNICA APPROFONDITA)
    if gemini_api_key and gemini_api_key.strip():
        candidate_models = ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-2.5-flash-lite", "gemini-flash-latest"]
        for mod in candidate_models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={gemini_api_key.strip()}"
                prompt = (
                    f"Sei un acquirente italiano competente ed esperto che ha acquistato e testato a fondo su Amazon il seguente articolo: '{clean_title}'.\n"
                    f"Scrivi una recensione a 5 stelle autentica, ricca di dettagli d'uso, ergonomici, tecnici e funzionali in perfetto italiano.\n"
                    f"REGOLA TASSATIVA ASSOLUTA:\n"
                    f"- È SEVERAMENTE VIETATO scrivere frasi generiche o scambiare la tipologia di prodotto.\n"
                    f"- Devi leggere ATTENTAMENTE il titolo e attenerti fedelmente alla funzione d'uso del prodotto.\n"
                    f"- Rispondi ESCLUSIVAMENTE in formato JSON con due chiavi: 'title' (titolo specifico e accattivante di 5-10 parole) e 'body' (testo della recensione di 3-4 frasi articolate e tecniche)."
                )
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.7
                    }
                }
                resp = requests.post(url, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if raw_text.startswith("```"):
                        raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
                        raw_text = re.sub(r'\s*```$', '', raw_text)
                    parsed = json.loads(raw_text)
                    if parsed.get("title") and parsed.get("body"):
                        return {
                            "title": parsed.get("title").strip(),
                            "body": parsed.get("body").strip(),
                            "source": f"AI (Gemini {mod})"
                        }
            except Exception as e:
                print(f"[Review Generator AI Error with {mod}] {e}")

    # 2. RICONOSCIMENTO CATEGORIALE ULTRA-SPECIFICO
    cat_name, cat_data = detect_specific_category(clean_title)
    if cat_data:
        title = random.choice(cat_data["titles"])
        opening = random.choice(cat_data["openings"])
        body = random.choice(cat_data["bodies"])
        closing = random.choice(cat_data["closings"])
        return {
            "title": title,
            "body": f"{opening} {body} {closing}",
            "source": f"Specialized Category ({cat_name})"
        }

    # 3. MOTORE PARAMETRICO TECNICO ZERO-GENERIC
    return synthesize_custom_review(clean_title)
