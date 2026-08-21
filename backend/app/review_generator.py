import random
import requests
import json

TEMPLATES_BY_CATEGORY = {
    "casa_arredamento": {
        "titles": [
            "Ottima qualità e design moderno, pienamente soddisfatto!",
            "Elegante, solido e facile da montare: 5 stelle meritate",
            "Superiore alle aspettative! Robusto e ben rifinito",
            "Perfetto per il soggiorno, fa una splendida figura",
            "Ottimo rapporto qualità/prezzo, esattamente come in foto",
            "Molto pratico e capiente, materiale di ottima fattura"
        ],
        "openings": [
            "Ho acquistato questo prodotto incuriosito dal design e devo dire che la qualità mi ha sorpreso positivamente.",
            "Arrivato puntualissimo grazie alla spedizione rapida, l'imballaggio era impeccabile e protettivo.",
            "Cercavo un articolo con queste caratteristiche da tempo e questo modello ha soddisfatto tutte le mie esigenze.",
            "Prodotto davvero ben realizzato, si nota subito la cura nei dettagli fin dal primo sguardo."
        ],
        "bodies": [
            "I materiali sono resistenti e la finitura è piacevole sia al tatto che alla vista. Si integra alla perfezione con il resto dell'arredamento.",
            "Il montaggio è stato intuitivo e ha richiesto pochissimi minuti. La struttura risulta stabile e robusta, senza scricchiolii.",
            "Molto spazioso e funzionale nell'uso quotidiano. Ha risolto i miei problemi di spazio mantenendo un'estetica pulita e moderna.",
            "Rifinito con precisione in ogni angolo, le dimensioni sono fedeli alla descrizione e rispecchiano le foto dell'annuncio."
        ],
        "closings": [
            "Rapporto qualità-prezzo eccellente. Lo consiglio vivamente a chi cerca qualità e design!",
            "Cinque stelle meritatissime, sicuramente acquisterò ancora da questo venditore.",
            "Molto soddisfatto dell'acquisto, ha superato le aspettative. Consigliatissimo!",
            "Un acquisto azzeccato sotto ogni punto di vista, pienamente promosso a pieni voti."
        ]
    },
    "elettronica_elettrodomestici": {
        "titles": [
            "Potente, silenzioso e maneggevole! Ottimo acquisto",
            "Funziona alla perfezione, fa esattamente ciò che promette",
            "Indispensabile per le pulizie di casa, 5 stelle piene",
            "Eccezionale rapporto qualità-prezzo, facilissimo da usare",
            "Risultati professionali già dal primo utilizzo!",
            "Materiali di qualità e ottima potenza di aspirazione"
        ],
        "openings": [
            "Prodotto arrivato perfettamente imballato e nei tempi previsti. Già messo alla prova su diversi utilizzi.",
            "Dopo qualche giorno di test intensivo posso confermare la bontà di questo dispositivo.",
            "Ero scettico all'inizio ma le prestazioni sono davvero degne di nota, molto soddisfatto.",
            "Ottima dotazione di accessori e manuale chiaro, pronto all'uso in meno di due minuti."
        ],
        "bodies": [
            "La potenza è notevole pur mantenendo un livello di rumorosità contenuto. Pulisce a fondo senza fatica.",
            "I serbatoi sono facili da riempire, svuotare e pulire. Molto comodo anche da riporre grazie alle dimensioni compatte.",
            "La qualità costruttiva delle plastiche e degli innesti è solida e resistente. Si nota la cura ingegneristica.",
            "Ha rimosso macchie e sporco ostinato con grande facilità. I risultati si vedono all'istante."
        ],
        "closings": [
            "Ha cambiato il mio modo di fare le pulizie, fa risparmiare un sacco di tempo. Super consigliato!",
            "Per questa fascia di prezzo è davvero difficile trovare di meglio. 5 stelle senza dubbio!",
            "Pienamente soddisfatto delle prestazioni. Acquisto assolutamente consigliato!",
            "Dispositivo affidabile ed efficiente, lo ricomprerei subito."
        ]
    },
    "generico": {
        "titles": [
            "Ottima qualità, esattamente conforme alla descrizione!",
            "Prodotto eccellente, 5 stelle meritate sotto ogni aspetto",
            "Molto soddisfatto dell'acquisto! Pratico e resistente",
            "Ottimo rapporto qualità/prezzo, spedizione impeccabile",
            "Superiore alle aspettative, consigliatissimo!"
        ],
        "openings": [
            "Pacco arrivato nei tempi previsti, ben protetto e con confezione integra.",
            "Utilizzo questo prodotto da qualche giorno e ne sono davvero entusiasta.",
            "Ho deciso di provare questo articolo e devo dire che la qualità è evidente fin dall'unboxing.",
            "Ottima esperienza d'acquisto: descrizione fedele e prodotto di qualità."
        ],
        "bodies": [
            "I materiali sono resistenti e la funzionalità risponde in pieno alle mie aspettative.",
            "Semplice da utilizzare, comodo e dall'aspetto curato nei minimi dettagli.",
            "Fa esattamente ciò che promette con grande efficienza ed affidabilità.",
            "La qualità costruttiva è notevole e si percepisce la cura nella realizzazione."
        ],
        "closings": [
            "Consiglio sicuramente l'acquisto a chiunque sia interessato. 5 stelle!",
            "Rapporto qualità-prezzo imbattibile, acquisterò sicuramente altri prodotti del brand.",
            "Davvero un ottimo acquisto, pienamente soddisfatto del risultato.",
            "Valutazione massima ampiamente meritata!"
        ]
    }
}

def detect_category(title: str) -> str:
    title_lower = title.lower()
    if any(w in title_lower for w in ["comodino", "tavolo", "sedia", "mobile", "armadio", "divano", "letto", "scaffale", "lampada", "camera"]):
        return "casa_arredamento"
    if any(w in title_lower for w in ["lavatappeti", "aspirapolvere", "pulitore", "motore", "elettrodomestico", "cuffie", "caricatore", "robot", "vapore"]):
        return "elettronica_elettrodomestici"
    return "generico"

def generate_review(product_title: str, gemini_api_key: str = None) -> dict:
    """
    Genera una recensione a 5 stelle realistica e naturale con Titolo e Testo completo.
    Se è fornita una chiave Gemini API, usa il modello AI per personalizzarla al 100%.
    Altrimenti usa i template combinatori intelligenti in italiano.
    """
    if gemini_api_key and gemini_api_key.strip():
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key.strip()}"
            prompt = (
                f"Sei un acquirente italiano entusiasta che ha acquistato su Amazon il seguente prodotto: '{product_title}'. "
                f"Scrivi una recensione a 5 stelle autentica, credibile e dettagliata in perfetto italiano. "
                f"Fornisci la risposta SOLO in formato JSON valido con due chiavi: 'title' (titolo accattivante di 5-10 parole) e 'body' (testo della recensione di 3-5 frasi naturali che elogiano qualità, imballaggio e utilizzo)."
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"}
            }
            resp = requests.post(url, json=payload, timeout=8)
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
            print(f"[Review Generator] Fallback to template generator: {e}")

    # Template-based generator
    category = detect_category(product_title)
    cat_data = TEMPLATES_BY_CATEGORY.get(category, TEMPLATES_BY_CATEGORY["generico"])
    
    title = random.choice(cat_data["titles"])
    opening = random.choice(cat_data["openings"])
    body = random.choice(cat_data["bodies"])
    closing = random.choice(cat_data["closings"])
    
    full_text = f"{opening} {body} {closing}"
    
    return {
        "title": title,
        "body": full_text,
        "source": "Smart Templates (Italiano Naturale)"
    }
