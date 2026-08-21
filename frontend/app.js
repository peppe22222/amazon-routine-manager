// Amazon Routine Manager - Frontend Controller
// Versione con Zoom Lightbox Interattivo e Lettura ad Alto Contrasto

let currentTab = 'offers';
let currentActiveOrderId = null;

// Lightbox state
let lightboxState = {
  scale: 1,
  translateX: 0,
  translateY: 0,
  isDragging: false,
  startX: 0,
  startY: 0,
  currentSrc: ''
};

document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  loadOffers();
  loadOrders();
  loadLogs();
  loadSettings();
  loadActiveChannel();
  initLightboxEvents();
  
  // Auto refresh ogni 15 secondi
  setInterval(() => {
    loadStats();
    if (currentTab === 'offers') loadOffers();
    if (currentTab === 'confirmations' || currentTab === 'reviews' || currentTab === 'refunds') loadOrders();
    if (currentTab === 'logs') loadLogs();
  }, 15000);
});

// ----------------- TAB SWITCHING -----------------

function switchTab(tabId) {
  currentTab = tabId;
  
  // Nascondi tutti i tab content
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  const target = document.getElementById(`tab-${tabId}`);
  if (target) target.classList.remove('hidden');

  // Aggiorna stile bottoni desktop
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.className = 'tab-btn px-4 py-2.5 rounded-xl text-sm font-semibold text-slate-300 hover:text-white flex items-center gap-2 hover:bg-brand-surface border border-transparent transition-all';
  });
  const activeBtn = document.getElementById(`tab-btn-${tabId}`);
  if (activeBtn) {
    activeBtn.className = 'tab-btn px-4 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm';
  }

  // Aggiorna stile bottoni mobile
  const mobTabs = ['offers', 'confirmations', 'reviews', 'refunds'];
  mobTabs.forEach(t => {
    const mBtn = document.getElementById(`mob-btn-${t}`);
    if (mBtn) {
      if (t === tabId) {
        mBtn.classList.remove('text-slate-400');
        mBtn.classList.add('text-emerald-400');
      } else {
        mBtn.classList.remove('text-emerald-400');
        mBtn.classList.add('text-slate-400');
      }
    }
  });

  // Carica i dati specifici
  if (tabId === 'offers') loadOffers();
  else if (tabId === 'confirmations' || tabId === 'reviews' || tabId === 'refunds') loadOrders();
  else if (tabId === 'logs') loadLogs();
}

// ----------------- DATA FETCHING -----------------

async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('stat-total-spent').innerText = `€${data.total_spent.toFixed(2)}`;
    document.getElementById('stat-pending-refund').innerText = `€${data.pending_refund.toFixed(2)}`;
    document.getElementById('stat-reimbursed').innerText = `€${data.reimbursed_total.toFixed(2)}`;
    document.getElementById('stat-active-count').innerText = data.active_orders_count;

    document.getElementById('badge-offers-count').innerText = data.new_offers_count;
    document.getElementById('badge-confirm-count').innerText = data.pending_confirmation_count;

    const mobBadge = document.getElementById('mob-badge-confirm');
    if (data.pending_confirmation_count > 0) {
      mobBadge.classList.remove('hidden');
    } else {
      mobBadge.classList.add('hidden');
    }
  } catch (err) {
    console.error('Errore caricamento statistiche:', err);
  }
}

// ----------------- OFFERS RENDERING -----------------

async function loadOffers() {
  try {
    const res = await fetch('/api/offers');
    if (!res.ok) return;
    const offers = await res.json();
    const container = document.getElementById('offers-grid');

    if (offers.length === 0) {
      container.innerHTML = `
        <div class="col-span-full py-16 text-center text-slate-400 glass-card rounded-2xl p-8 border border-dashed border-slate-700">
          <div class="w-16 h-16 rounded-2xl bg-slate-800/80 mx-auto flex items-center justify-center text-3xl text-emerald-400/80 mb-3 shadow-inner">
            <i class="fa-solid fa-inbox"></i>
          </div>
          <h3 class="text-base font-bold text-white">Nessuna nuova offerta dal canale Telegram</h3>
          <p class="text-xs text-slate-300 mt-1 max-w-sm mx-auto">Non appena un'offerta viene pubblicata sul canale Telegram, comparirà qui con la foto zoomabile e le condizioni.</p>
          <button onclick="openSimulatorModal()" class="mt-4 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-900/30 inline-flex items-center gap-2">
            <i class="fa-solid fa-wand-magic-sparkles"></i> Simula Offerta di Prova
          </button>
        </div>
      `;
      return;
    }

    container.innerHTML = offers.map(o => {
      const imgUrl = o.image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80';
      const isRequested = o.status === 'requested';

      return `
        <div class="glass-card rounded-2xl overflow-hidden flex flex-col justify-between transition-all duration-200 hover:-translate-y-1 hover:shadow-xl hover:border-emerald-500/50">
          
          <!-- Product Image Container with Complete Visibility (No Cropping) -->
          <div class="relative w-full h-64 bg-slate-950 flex items-center justify-center overflow-hidden group cursor-pointer border-b border-slate-800" onclick="openLightboxFromSrc('${imgUrl}', '${escapeHtml(o.title)}', 'Condizioni: ${escapeHtml(o.price_info || '')}')">
            <img src="${imgUrl}" alt="${escapeHtml(o.title)}" class="max-h-full max-w-full w-auto h-auto object-contain p-2 group-hover:scale-105 transition-transform duration-300">
            
            <!-- Badges top -->
            <div class="absolute top-2.5 left-2.5 right-2.5 flex items-center justify-between pointer-events-none">
              <span class="text-[11px] font-extrabold px-2.5 py-0.5 rounded-full bg-emerald-500 text-slate-950 shadow-md flex items-center gap-1">
                <i class="fa-solid fa-check"></i> ${o.refund_pct || 100}% RIMBORSO
              </span>
              <span class="text-[11px] font-bold px-2 py-0.5 rounded-md bg-slate-900/90 backdrop-blur-md text-blue-300 border border-blue-500/30 flex items-center gap-1 shadow">
                <i class="fa-brands fa-telegram text-blue-400"></i> ${o.seller_contact || '@venditore'}
              </span>
            </div>

            <!-- Zoom Prompt Overlay -->
            <div class="absolute bottom-2.5 right-2.5 px-2.5 py-1 rounded-lg bg-slate-900/90 backdrop-blur-md text-white text-[11px] font-bold border border-slate-700 flex items-center gap-1 shadow-lg group-hover:bg-emerald-600 transition-colors">
              <i class="fa-solid fa-magnifying-glass-plus text-emerald-400 group-hover:text-white"></i>
              <span>Ingrandisci Foto</span>
            </div>
          </div>

          <!-- Card Content Body -->
          <div class="p-4 flex-1 flex flex-col justify-between space-y-3">
            <div>
              <!-- Titolo Prodotto -->
              <h3 class="text-sm md:text-base font-extrabold text-white leading-snug line-clamp-2">
                ${escapeHtml(o.title)}
              </h3>

              <!-- Griglia Condizioni & Spesa (Alto Contrasto) -->
              <div class="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div class="p-2.5 rounded-xl bg-slate-900/90 border border-slate-700/80">
                  <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Condizioni Spesa:</span>
                  <span class="font-extrabold text-emerald-300 text-xs mt-0.5 block truncate">${o.price_info || '100% rimborso'}</span>
                </div>
                <div class="p-2.5 rounded-xl bg-slate-900/90 border border-slate-700/80">
                  <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Copertura Tasse:</span>
                  <span class="font-extrabold ${o.taxes_covered ? 'text-emerald-400' : 'text-amber-300'} text-xs mt-0.5 block flex items-center gap-1">
                    ${o.taxes_covered ? '<i class="fa-solid fa-shield-check"></i> Coperte' : '<i class="fa-solid fa-triangle-exclamation"></i> Da verificare'}
                  </span>
                </div>
              </div>
            </div>

            <!-- Bottoni Azione -->
            <div class="pt-3 border-t border-brand-border flex items-center gap-2">
              ${isRequested
                ? `
                  <div class="flex-1 flex items-center gap-1.5">
                    <button disabled class="flex-1 py-2.5 px-2.5 rounded-xl bg-blue-600/20 text-blue-300 border border-blue-500/40 text-xs font-bold flex items-center justify-center gap-1.5 truncate">
                      <i class="fa-solid fa-check-double text-blue-400"></i> Richiesta Inviata
                    </button>
                    <button onclick="resetOffer(${o.id})" title="Reimposta e riabilita tasto richiesta" class="px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-xs font-bold flex items-center gap-1 transition-all shrink-0">
                      <i class="fa-solid fa-rotate-left"></i> Reset
                    </button>
                  </div>
                `
                : `<button onclick="requestOffer(${o.id})" class="flex-1 py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white text-xs font-extrabold shadow-lg shadow-emerald-900/40 flex items-center justify-center gap-2 transition-all">
                    <i class="fa-solid fa-paper-plane"></i> Richiedi Disponibilità
                  </button>`
              }
              <button onclick="dismissOffer(${o.id})" title="Rimuovi offerta" class="w-10 h-10 rounded-xl bg-slate-900 hover:bg-red-500/20 text-slate-400 hover:text-red-400 border border-slate-700/80 flex items-center justify-center transition-all shrink-0">
                <i class="fa-regular fa-trash-can text-sm"></i>
              </button>
            </div>

          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Errore caricamento offerte:', err);
  }
}

// ----------------- ORDERS / CONFIRMATIONS / REVIEWS -----------------

async function loadOrders() {
  try {
    const res = await fetch('/api/orders');
    if (!res.ok) return;
    const orders = await res.json();

    renderConfirmations(orders);
    renderReviews(orders);
    renderRefunds(orders);
  } catch (err) {
    console.error('Errore caricamento ordini:', err);
  }
}

function renderConfirmations(orders) {
  const container = document.getElementById('confirmations-list');
  const pendingOrders = orders.filter(o => o.status === 'pending_confirmation');

  if (pendingOrders.length === 0) {
    container.innerHTML = `
      <div class="py-16 text-center text-slate-400 glass-card rounded-2xl p-8 border border-dashed border-slate-700">
        <div class="w-16 h-16 rounded-2xl bg-slate-800/80 mx-auto flex items-center justify-center text-3xl text-amber-400/80 mb-3 shadow-inner">
          <i class="fa-solid fa-camera"></i>
        </div>
        <h3 class="text-base font-bold text-white">Nessuna schermata ordine in attesa di conferma</h3>
        <p class="text-xs text-slate-300 mt-1 max-w-md mx-auto">Non appena acquisti su Amazon, il sistema genera in automatico lo screenshot e preleva il numero d'ordine, che comparirà qui pronto per essere inviato con un solo tocco.</p>
        <button onclick="simulateOrder('Comodino Moderno Cilindrico', 8.00, '@venditore_arredo')" class="mt-4 px-4 py-2.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-300 text-xs font-bold inline-flex items-center gap-2">
          <i class="fa-solid fa-cart-shopping"></i> Crea Ordine di Prova
        </button>
      </div>
    `;
    return;
  }

  container.innerHTML = pendingOrders.map(o => {
    const prodImg = o.product_image || 'https://images.unsplash.com/photo-1532372320572-cda25653a26d?auto=format&fit=crop&w=800&q=80';
    
    return `
      <div class="glass-card rounded-2xl p-5 border-amber-500/40 flex flex-col lg:flex-row lg:items-center justify-between gap-5 shadow-lg">
        
        <!-- Sinistra: Foto Prodotto + Dati Ordine -->
        <div class="flex items-start gap-4 flex-1">
          <!-- Thumbnail Prodotto Zoomabile -->
          <div onclick="openLightboxFromSrc('${prodImg}', '${escapeHtml(o.product_title)}', 'Numero Ordine: ${o.order_number}')" class="cursor-pointer relative w-24 h-24 rounded-2xl overflow-hidden border border-slate-700 bg-slate-950 flex items-center justify-center shrink-0 group shadow-md" title="Clicca per zoomare la foto">
            <img src="${prodImg}" alt="Foto Prodotto" class="max-w-full max-h-full object-contain p-1 group-hover:scale-110 transition-transform">
            <div class="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-white text-xs">
              <i class="fa-solid fa-magnifying-glass-plus text-base"></i>
            </div>
            <span class="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/80 text-[10px] text-white font-bold">Foto</span>
          </div>

          <!-- Dettagli Ordine & Venditore -->
          <div class="flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-xs font-mono font-extrabold px-2.5 py-1 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/40">
                ${o.order_number}
              </span>
              <button onclick="copyToClipboard('${o.order_number}', 'N° Ordine copiato!')" class="px-2 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1">
                <i class="fa-regular fa-copy"></i> Copia N°
              </button>
            </div>

            <h3 class="text-sm md:text-base font-extrabold text-white mt-2 leading-snug">${escapeHtml(o.product_title)}</h3>
            
            <div class="mt-2 flex flex-wrap items-center gap-3 text-xs">
              <span class="text-slate-300">Venditore Telegram: <strong class="text-blue-400 font-bold">${o.seller_contact}</strong></span>
              <span class="text-slate-500">•</span>
              <span class="text-slate-300">Spesa: <strong class="text-white font-bold">€${o.price_paid.toFixed(2)}</strong></span>
              <span class="text-slate-500">•</span>
              <span class="text-emerald-400 font-bold">Rimborso: 100%</span>
            </div>
          </div>
        </div>

        <!-- Destra: Azioni Tasto di Conferma & Anteprima Screen -->
        <div class="flex flex-wrap items-center gap-2 shrink-0 border-t lg:border-t-0 pt-3 lg:pt-0 border-brand-border">
          <button onclick="openIPhoneUploadModal(${o.id})" class="px-3.5 py-2.5 rounded-xl bg-gradient-to-r from-purple-600/30 to-indigo-600/30 hover:from-purple-600/50 hover:to-indigo-600/50 border border-purple-500/50 text-purple-200 text-xs font-bold flex items-center gap-1.5 shadow-md transition-all" title="Incolla dagli appunti iPhone, scegli da Rullino o carica file">
            <i class="fa-solid fa-mobile-screen-button text-purple-300"></i> Screen iPhone / Incolla
          </button>

          <button onclick="showScreenshot('${o.confirmation_screen_url}', '${o.order_number}')" class="px-3 py-2.5 rounded-xl bg-brand-surface hover:bg-brand-card border border-brand-border text-slate-200 text-xs font-bold flex items-center gap-1.5 shadow-md">
            <i class="fa-solid fa-receipt text-amber-400"></i> Ricevuta
          </button>
          
          <button onclick="confirmAndSendOrder(${o.id})" class="px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white text-xs font-extrabold shadow-lg shadow-emerald-900/40 flex items-center gap-1.5 transition-all">
            <i class="fa-solid fa-paper-plane"></i> Conferma e Invia
          </button>
        </div>

      </div>
    `;
  }).join('');
}

function renderReviews(orders) {
  const container = document.getElementById('reviews-list');
  const reviewOrders = orders.filter(o => o.status !== 'cancelled' && o.status !== 'pending_confirmation');

  if (reviewOrders.length === 0) {
    container.innerHTML = `
      <div class="col-span-full py-16 text-center text-slate-400 glass-card rounded-2xl p-8 border border-dashed border-slate-700">
        <div class="w-16 h-16 rounded-2xl bg-slate-800/80 mx-auto flex items-center justify-center text-3xl text-purple-400/80 mb-3 shadow-inner">
          <i class="fa-solid fa-star"></i>
        </div>
        <h3 class="text-base font-bold text-white">Nessuna recensione attiva al momento</h3>
        <p class="text-xs text-slate-300 mt-1 max-w-md mx-auto">Dopo aver confermato l'ordine, si avvierà il conto alla rovescia di 10 giorni con il testo a 5 stelle pre-generato pronto da incollare su Amazon.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = reviewOrders.map(o => {
    const isReady = o.days_until_review === 0;
    const progressPct = Math.min(100, Math.max(0, ((10 - o.days_until_review) / 10) * 100));
    const prodImg = o.product_image || 'https://images.unsplash.com/photo-1558317374-067fb5f30001?auto=format&fit=crop&w=800&q=80';

    return `
      <div class="glass-card rounded-2xl p-5 flex flex-col justify-between space-y-4 shadow-lg">
        <div>
          <!-- Header Card con Immagine & Timer -->
          <div class="flex items-start justify-between gap-3">
            <div class="flex items-center gap-3">
              <div onclick="openLightboxFromSrc('${prodImg}', '${escapeHtml(o.product_title)}', 'Ordine: ${o.order_number}')" class="cursor-pointer relative w-12 h-12 rounded-xl overflow-hidden border border-slate-700 bg-slate-950 flex items-center justify-center shrink-0 group">
                <img src="${prodImg}" alt="Foto" class="max-w-full max-h-full object-contain p-0.5 group-hover:scale-110 transition-transform">
                <div class="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 text-white text-[10px]">
                  <i class="fa-solid fa-magnifying-glass-plus"></i>
                </div>
              </div>
              <div>
                <span class="text-xs font-mono text-slate-400 font-bold">${o.order_number}</span>
                <h3 class="text-sm font-extrabold text-white line-clamp-1 mt-0.5">${escapeHtml(o.product_title)}</h3>
              </div>
            </div>
            
            <span class="text-xs font-extrabold px-2.5 py-1 rounded-lg ${isReady ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 animate-pulse' : 'bg-purple-500/20 text-purple-300 border border-purple-500/40'} shrink-0">
              ${isReady ? '⭐ RECENSIONE PRONTA!' : `Giorno ${10 - o.days_until_review}/10`}
            </span>
          </div>

          <!-- Barra di Progresso Timer 10 Giorni -->
          <div class="mt-4 p-3 rounded-xl bg-brand-bg border border-brand-border">
            <div class="flex justify-between text-xs text-slate-300 mb-1.5 font-bold">
              <span>Conto alla Rovescia Recensione (10gg)</span>
              <span class="${isReady ? 'text-emerald-400 font-extrabold' : 'text-purple-300'}">
                ${isReady ? 'Scadenza raggiunta: pubblica ora!' : `${o.days_until_review} giorni rimanenti`}
              </span>
            </div>
            <div class="w-full h-2.5 bg-slate-900 rounded-full overflow-hidden border border-slate-700">
              <div class="h-full ${isReady ? 'bg-emerald-500' : 'bg-gradient-to-r from-purple-500 to-indigo-500'} transition-all duration-500" style="width: ${progressPct}%"></div>
            </div>
          </div>

          <!-- Anteprima Recensione 5 Stelle Generata -->
          <div class="mt-4 p-3.5 rounded-xl bg-brand-bg border border-brand-border space-y-2">
            <div class="flex items-center justify-between text-amber-400 text-xs">
              <div class="flex text-sm">
                <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i>
              </div>
              <span class="text-xs text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">Testo Generato Pronto</span>
            </div>
            <p class="text-xs font-extrabold text-white line-clamp-1">"${escapeHtml(o.review_title || 'Ottimo prodotto, spedizione impeccabile')}"</p>
            <p class="text-xs text-slate-300 line-clamp-2 leading-relaxed font-medium">${escapeHtml(o.review_body || 'Arrivato puntuale, ben imballato. Qualità dei materiali ottima e facilissimo da utilizzare. Pienamente soddisfatto!')}</p>
          </div>
        </div>

        <!-- Bottoni Azione Recensione -->
        <div class="pt-3 border-t border-brand-border flex flex-wrap items-center gap-2">
          <!-- Tasto Visualizza Testo: sempre consultabile -->
          <button onclick="openReviewModal(${o.id})" class="flex-1 py-2.5 px-3 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/40 text-xs font-bold flex items-center justify-center gap-1.5 transition-all shadow-md">
            <i class="fa-solid fa-copy"></i> Testo Recensione
          </button>
          
          <!-- Tasto Screen iPhone: Attivo SOLO al 10° giorno -->
          ${isReady ? `
            <button onclick="openIPhoneUploadModal(${o.id}, 'review')" class="py-2.5 px-3.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 border border-purple-400 text-white text-xs font-extrabold flex items-center gap-1.5 shadow-md shadow-purple-900/30 transition-all animate-pulse" title="Incolla o carica screenshot della recensione pubblicata">
              <i class="fa-solid fa-mobile-screen-button"></i> Screen iPhone / Incolla
            </button>
          ` : `
            <button disabled class="py-2.5 px-3.5 rounded-xl bg-slate-800/50 border border-slate-700 text-slate-500 text-xs font-bold flex items-center gap-1.5 opacity-50 cursor-not-allowed" title="Disponibile allo scadere dei 10 giorni (Giorno ${10 - o.days_until_review}/10)">
              <i class="fa-solid fa-lock text-[10px]"></i> Screen iPhone
            </button>
          `}
          
          <!-- Tasto Invia a Venditore: Attivo SOLO al 10° giorno -->
          ${isReady ? `
            <button onclick="sendReviewToSeller(${o.id})" class="py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white border border-emerald-400 text-xs font-extrabold flex items-center gap-1.5 transition-all shadow-lg shadow-emerald-900/40" title="Invia conferma screen recensione al venditore Telegram">
              <i class="fa-solid fa-paper-plane"></i> Invia a Venditore
            </button>
          ` : `
            <button disabled class="py-2.5 px-4 rounded-xl bg-slate-800/50 border border-slate-700 text-slate-500 text-xs font-bold flex items-center gap-1.5 opacity-50 cursor-not-allowed" title="Invio bloccato: attendi la scadenza dei 10 giorni per pubblicare la recensione">
              <i class="fa-solid fa-lock text-[10px]"></i> Invia a Venditore
            </button>
          `}
        </div>
      </div>
    `;
  }).join('');
}

function renderRefunds(orders) {
  const container = document.getElementById('refunds-list');
  const eligibleOrders = orders.filter(o => o.status !== 'cancelled' && o.status !== 'pending_confirmation');

  if (eligibleOrders.length === 0) {
    container.innerHTML = `
      <div class="py-16 text-center text-slate-400 glass-card rounded-2xl p-8 border border-dashed border-slate-700">
        <div class="w-16 h-16 rounded-2xl bg-slate-800/80 mx-auto flex items-center justify-center text-3xl text-blue-400/80 mb-3 shadow-inner">
          <i class="fa-brands fa-paypal"></i>
        </div>
        <h3 class="text-base font-bold text-white">Nessun rimborso da gestire</h3>
        <p class="text-xs text-slate-300 mt-1 max-w-md mx-auto">Le pratiche per le quali hai inviato la recensione appariranno qui per tracciare l'accredito PayPal del 100%.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = eligibleOrders.map(o => {
    const isReimbursed = o.status === 'reimbursed';
    const prodImg = o.product_image || 'https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?auto=format&fit=crop&w=800&q=80';

    return `
      <div class="glass-card rounded-2xl p-4 md:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-lg border ${isReimbursed ? 'border-emerald-500/30' : 'border-blue-500/30'}">
        
        <div class="flex items-center gap-4">
          <!-- Thumbnail Prodotto Zoomabile -->
          <div onclick="openLightboxFromSrc('${prodImg}', '${escapeHtml(o.product_title)}', 'Rimborso €${o.refund_amount.toFixed(2)}')" class="cursor-pointer relative w-14 h-14 rounded-xl overflow-hidden border border-slate-700 bg-slate-900 shrink-0 group">
            <img src="${prodImg}" alt="Foto" class="w-full h-full object-cover group-hover:scale-110 transition-transform">
            <div class="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 text-white text-xs">
              <i class="fa-solid fa-magnifying-glass-plus"></i>
            </div>
          </div>

          <div>
            <div class="flex items-center gap-2">
              <span class="text-xs font-mono text-slate-300 font-bold">${o.order_number}</span>
              <span class="text-[11px] px-2.5 py-0.5 rounded-md ${isReimbursed ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'} font-extrabold uppercase">
                ${isReimbursed ? '✓ Rimborso Saldato' : '⏳ In Attesa PayPal'}
              </span>
            </div>
            <p class="text-sm font-extrabold text-white mt-1">${escapeHtml(o.product_title)}</p>
            <p class="text-xs text-slate-300 mt-0.5">Venditore: <strong class="text-blue-400 font-bold">${o.seller_contact}</strong></p>
          </div>
        </div>

        <div class="flex items-center justify-between md:justify-end gap-5 shrink-0 border-t md:border-t-0 pt-3 md:pt-0 border-brand-border">
          <div class="text-right">
            <p class="text-xs font-bold text-slate-400 uppercase">Importo Rimborso</p>
            <p class="text-xl font-extrabold ${isReimbursed ? 'text-emerald-400' : 'text-amber-300'}">€${o.refund_amount.toFixed(2)}</p>
          </div>

          ${isReimbursed
            ? `<span class="px-4 py-2.5 rounded-xl bg-emerald-500/10 text-emerald-300 text-xs font-extrabold flex items-center gap-1.5 border border-emerald-500/30">
                <i class="fa-solid fa-check"></i> Accreditato
              </span>`
            : `<button onclick="markRefunded(${o.id})" class="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-extrabold shadow-lg shadow-emerald-900/30 flex items-center gap-1.5 transition-all">
                <i class="fa-solid fa-check"></i> Segna Ricevuto
              </button>`
          }
        </div>
      </div>
    `;
  }).join('');
}

// ----------------- LOGS RENDERING -----------------

async function loadLogs() {
  try {
    const res = await fetch('/api/logs');
    if (!res.ok) return;
    const logs = await res.json();
    const container = document.getElementById('logs-container');

    if (logs.length === 0) {
      container.innerHTML = `<p class="text-xs text-slate-400 text-center py-6">Nessuna attività registrata finora.</p>`;
      return;
    }

    container.innerHTML = logs.map(l => `
      <div class="p-3 rounded-xl bg-brand-bg border border-brand-border flex items-start justify-between gap-3 text-xs">
        <div class="space-y-0.5">
          <div class="flex items-center gap-2">
            <span class="font-bold text-white">${escapeHtml(l.title)}</span>
            <span class="text-[10px] px-2 py-0.5 rounded bg-brand-surface text-slate-300 font-mono">${escapeHtml(l.action_type)}</span>
          </div>
          <p class="text-slate-300 text-[11px] leading-relaxed">${escapeHtml(l.details || '')}</p>
        </div>
        <span class="text-[10px] text-slate-400 font-mono shrink-0">${formatDate(l.timestamp || l.created_at)}</span>
      </div>
    `).join('');
  } catch (err) {
    console.error('Errore caricamento log:', err);
  }
}

// ----------------- LIGHTBOX ZOOM SYSTEM -----------------

function initLightboxEvents() {
  const container = document.getElementById('lightbox-container');
  const img = document.getElementById('lightbox-img');

  if (!container || !img) return;

  // Mouse wheel zoom
  container.addEventListener('wheel', (e) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.2 : -0.2;
    zoomLightbox(delta);
  }, { passive: false });

  // Mouse Drag / Pan
  container.addEventListener('mousedown', (e) => {
    if (lightboxState.scale <= 1) return;
    lightboxState.isDragging = true;
    lightboxState.startX = e.clientX - lightboxState.translateX;
    lightboxState.startY = e.clientY - lightboxState.translateY;
    container.classList.add('is-dragging');
  });

  window.addEventListener('mousemove', (e) => {
    if (!lightboxState.isDragging) return;
    lightboxState.translateX = e.clientX - lightboxState.startX;
    lightboxState.translateY = e.clientY - lightboxState.startY;
    applyLightboxTransform();
  });

  window.addEventListener('mouseup', () => {
    lightboxState.isDragging = false;
    if (container) container.classList.remove('is-dragging');
  });

  // Touch Events for Mobile / iPhone
  let touchStartDist = 0;
  container.addEventListener('touchstart', (e) => {
    if (e.touches.length === 1 && lightboxState.scale > 1) {
      lightboxState.isDragging = true;
      lightboxState.startX = e.touches[0].clientX - lightboxState.translateX;
      lightboxState.startY = e.touches[0].clientY - lightboxState.translateY;
    } else if (e.touches.length === 2) {
      touchStartDist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
    }
  });

  container.addEventListener('touchmove', (e) => {
    if (e.touches.length === 1 && lightboxState.isDragging) {
      e.preventDefault();
      lightboxState.translateX = e.touches[0].clientX - lightboxState.startX;
      lightboxState.translateY = e.touches[0].clientY - lightboxState.startY;
      applyLightboxTransform();
    } else if (e.touches.length === 2) {
      e.preventDefault();
      const dist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      const factor = (dist - touchStartDist) * 0.01;
      zoomLightbox(factor);
      touchStartDist = dist;
    }
  }, { passive: false });

  container.addEventListener('touchend', () => {
    lightboxState.isDragging = false;
  });

  // Keyboard navigation
  window.addEventListener('keydown', (e) => {
    const modal = document.getElementById('modal-lightbox');
    if (!modal || modal.classList.contains('hidden')) return;

    if (e.key === 'Escape') closeLightbox();
    else if (e.key === '+' || e.key === '=') zoomLightbox(0.25);
    else if (e.key === '-' || e.key === '_') zoomLightbox(-0.25);
    else if (e.key === '0') resetLightboxZoom();
  });
}

function openLightboxFromSrc(src, title, subtitle) {
  lightboxState.currentSrc = src;
  lightboxState.scale = 1;
  lightboxState.translateX = 0;
  lightboxState.translateY = 0;

  const modal = document.getElementById('modal-lightbox');
  const img = document.getElementById('lightbox-img');
  const titleEl = document.getElementById('lightbox-title');
  const subEl = document.getElementById('lightbox-subtitle');

  if (img) img.src = src;
  if (titleEl) titleEl.innerText = title || 'Foto Prodotto';
  if (subEl) subEl.innerText = subtitle || 'Visualizzatore ad alta risoluzione';

  updateZoomBadge();
  applyLightboxTransform();

  if (modal) modal.classList.remove('hidden');
}

function closeLightbox() {
  const modal = document.getElementById('modal-lightbox');
  if (modal) modal.classList.add('hidden');
  resetLightboxZoom();
}

function zoomLightbox(delta) {
  lightboxState.scale = Math.min(4.0, Math.max(0.5, lightboxState.scale + delta));
  if (lightboxState.scale <= 1) {
    lightboxState.translateX = 0;
    lightboxState.translateY = 0;
  }
  updateZoomBadge();
  applyLightboxTransform();
}

function resetLightboxZoom() {
  lightboxState.scale = 1;
  lightboxState.translateX = 0;
  lightboxState.translateY = 0;
  updateZoomBadge();
  applyLightboxTransform();
}

function updateZoomBadge() {
  const badge = document.getElementById('lightbox-zoom-badge');
  if (badge) {
    badge.innerText = `${Math.round(lightboxState.scale * 100)}%`;
  }
}

function applyLightboxTransform() {
  const img = document.getElementById('lightbox-img');
  if (img) {
    img.style.transform = `translate(${lightboxState.translateX}px, ${lightboxState.translateY}px) scale(${lightboxState.scale})`;
  }
}

function openLightboxImageOriginal() {
  if (lightboxState.currentSrc) {
    window.open(lightboxState.currentSrc, '_blank');
  }
}

// ----------------- ACTIONS & HANDLERS -----------------

async function requestOffer(offerId) {
  try {
    const res = await fetch(`/api/offers/${offerId}/request`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast('Richiesta inviata al venditore Telegram!');
      loadOffers();
      loadStats();
    } else {
      showToast(data.detail || 'Errore durante la richiesta', true);
    }
  } catch (err) {
    showToast('Errore di connessione', true);
  }
}

async function resetOffer(offerId) {
  try {
    const res = await fetch(`/api/offers/${offerId}/reset`, { method: 'POST' });
    if (res.ok) {
      showToast('Stato offerta reimpostato a Nuovo!');
      loadOffers();
      loadStats();
    }
  } catch (err) {
    showToast('Errore di rete', true);
  }
}

async function resetAllRequests() {
  try {
    const res = await fetch('/api/offers/reset-all', { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || 'Tutte le richieste reimpostate!');
      loadOffers();
      loadStats();
    }
  } catch (err) {
    showToast('Errore di rete', true);
  }
}

async function dismissOffer(offerId) {
  try {
    const res = await fetch(`/api/offers/${offerId}`, { method: 'DELETE' });
    if (res.ok) {
      showToast('Offerta rimossa');
      loadOffers();
      loadStats();
    }
  } catch (err) {
    showToast('Errore di rete', true);
  }
}

async function confirmAndSendOrder(orderId) {
  try {
    const res = await fetch(`/api/orders/${orderId}/confirm-and-send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Screenshot e Numero Ordine inviati al venditore!');
      loadOrders();
      loadStats();
    } else {
      showToast(data.detail || "Errore durante l'invio", true);
    }
  } catch (err) {
    showToast('Errore di connessione', true);
  }
}

async function sendReviewToSeller(orderId) {
  try {
    const res = await fetch(`/api/orders/${orderId}/send-review`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast('Conferma recensione inviata al venditore!');
      loadOrders();
      loadStats();
    } else {
      showToast(data.detail || 'Errore invio', true);
    }
  } catch (err) {
    showToast('Errore di rete', true);
  }
}

async function markRefunded(orderId) {
  try {
    const res = await fetch(`/api/orders/${orderId}/mark-refunded`, { method: 'POST' });
    if (res.ok) {
      showToast('Rimborso registrato con successo!');
      loadOrders();
      loadStats();
    }
  } catch (err) {
    showToast('Errore di rete', true);
  }
}

// ----------------- MODALS -----------------

let currentUploadOrderId = null;
let currentUploadType = 'order'; // 'order' oppure 'review'

function openIPhoneUploadModal(orderId, type = 'order') {
  currentUploadOrderId = orderId;
  currentUploadType = type;
  
  const titleEl = document.getElementById('modal-iphone-ord-title');
  if (titleEl) {
    if (type === 'review') {
      titleEl.innerText = 'Scegli come inserire lo screenshot della Recensione 5★ da iPhone';
    } else {
      titleEl.innerText = 'Scegli come inserire la ricevuta dell\'ordine Amazon da iPhone';
    }
  }

  const modal = document.getElementById('modal-iphone-upload');
  if (modal) modal.classList.remove('hidden');
}

async function pasteFromIPhoneClipboard() {
  if (!currentUploadOrderId) return;
  const endpoint = currentUploadType === 'review' 
    ? `/api/orders/${currentUploadOrderId}/upload-review-screenshot` 
    : `/api/orders/${currentUploadOrderId}/upload-screenshot`;

  try {
    if (!navigator.clipboard || !navigator.clipboard.read) {
      showToast('Tocca e tieni premuto l\'Area Tocco per incollare la foto.', true);
      return;
    }
    const items = await navigator.clipboard.read();
    let foundImage = false;
    for (const item of items) {
      for (const type of item.types) {
        if (type.startsWith('image/')) {
          const blob = await item.getType(type);
          const reader = new FileReader();
          reader.onload = async (event) => {
            const base64 = event.target.result;
            const res = await fetch(endpoint, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ image_base64: base64 })
            });
            if (res.ok) {
              showToast(currentUploadType === 'review' ? '⭐ Screenshot Recensione incollato da iPhone!' : '📦 Screenshot Ordine incollato da iPhone!');
              closeModal('modal-iphone-upload');
              loadOrders();
            } else {
              showToast('Errore durante l\'inserimento dell\'immagine', true);
            }
          };
          reader.readAsDataURL(blob);
          foundImage = true;
          break;
        }
      }
      if (foundImage) break;
    }
    if (!foundImage) {
      showToast('Nessuna immagine copiata negli appunti di iPhone.', true);
    }
  } catch (err) {
    console.error('Clipboard read error:', err);
    showToast('Consenti l\'accesso agli appunti o usa l\'opzione Rullino Foto.', true);
  }
}

function triggerIPhonePhotoLibrary() {
  let fileInput = document.getElementById('iphone-photo-input');
  if (!fileInput) {
    fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.id = 'iphone-photo-input';
    fileInput.accept = 'image/*';
    fileInput.className = 'hidden';
    document.body.appendChild(fileInput);

    fileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file || !currentUploadOrderId) return;
      const endpoint = currentUploadType === 'review' 
        ? `/api/orders/${currentUploadOrderId}/upload-review-screenshot` 
        : `/api/orders/${currentUploadOrderId}/upload-screenshot`;

      const reader = new FileReader();
      reader.onload = async (event) => {
        const base64 = event.target.result;
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_base64: base64 })
        });
        if (res.ok) {
          showToast(currentUploadType === 'review' ? '⭐ Screenshot Recensione caricato dal Rullino!' : '📦 Screenshot Ordine caricato dal Rullino!');
          closeModal('modal-iphone-upload');
          loadOrders();
        }
      };
      reader.readAsDataURL(file);
      fileInput.value = '';
    });
  }
  fileInput.click();
}

function triggerIPhoneCamera() {
  let camInput = document.getElementById('iphone-camera-input');
  if (!camInput) {
    camInput = document.createElement('input');
    camInput.type = 'file';
    camInput.id = 'iphone-camera-input';
    camInput.accept = 'image/*';
    camInput.capture = 'environment';
    camInput.className = 'hidden';
    document.body.appendChild(camInput);

    camInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file || !currentUploadOrderId) return;
      const endpoint = currentUploadType === 'review' 
        ? `/api/orders/${currentUploadOrderId}/upload-review-screenshot` 
        : `/api/orders/${currentUploadOrderId}/upload-screenshot`;

      const reader = new FileReader();
      reader.onload = async (event) => {
        const base64 = event.target.result;
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_base64: base64 })
        });
        if (res.ok) {
          showToast('📷 Foto scattata e collegata con successo!');
          closeModal('modal-iphone-upload');
          loadOrders();
        }
      };
      reader.readAsDataURL(file);
      camInput.value = '';
    });
  }
  camInput.click();
}

function focusIPhonePasteBox() {
  const input = document.getElementById('iphone-hidden-paste-input');
  if (input) {
    input.focus();
    showToast('Tieni premuto e tocca "Incolla" nel menu di iPhone');
  }
}

async function grabLatestPCScreenshot(orderId) {
  try {
    const res = await fetch(`/api/orders/${orderId}/grab-latest-pc-screenshot`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || 'Screenshot catturato e collegato con successo!');
      loadOrders();
    } else {
      showToast(data.detail || 'Nessuno screenshot recente trovato sul PC.', true);
    }
  } catch (err) {
    showToast('Errore durante la cattura automatica', true);
  }
}

// Supporto Incolla Immediata (Ctrl + V) da qualsiasi schermata
window.addEventListener('paste', async (e) => {
  const items = (e.clipboardData || e.originalEvent.clipboardData).items;
  for (let item of items) {
    if (item.type.indexOf('image') === 0) {
      const blob = item.getAsFile();
      const reader = new FileReader();
      reader.onload = async (event) => {
        const base64 = event.target.result;
        try {
          const resOrders = await fetch('/api/orders');
          const orders = await resOrders.json();
          const targetOrder = orders.find(o => o.status === 'pending_confirmation');

          if (targetOrder) {
            const res = await fetch(`/api/orders/${targetOrder.id}/upload-screenshot`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ image_base64: base64 })
            });
            if (res.ok) {
              showToast(`📋 Screenshot incollato con successo all'ordine ${targetOrder.order_number}!`);
              loadOrders();
            }
          } else {
            showToast('📋 Screenshot copiato negli appunti! Seleziona una pratica per associarlo.');
          }
        } catch (err) {
          console.error(err);
        }
      };
      reader.readAsDataURL(blob);
      break;
    }
  }
});

function showScreenshot(url, orderNum) {
  document.getElementById('modal-screen-img').src = url;
  document.getElementById('modal-screen-ord-num').innerText = orderNum;
  document.getElementById('modal-screenshot').classList.remove('hidden');
}

async function previewReviewScreenshot(orderId) {
  try {
    const res = await fetch(`/api/orders/${orderId}/review-screen`);
    const data = await res.json();
    if (data.review_screen_url) {
      showScreenshot(data.review_screen_url, `Recensione 5★ (Ordine #${orderId})`);
    } else {
      showToast('Impossibile generare lo screenshot della recensione', true);
    }
  } catch (err) {
    showToast('Errore di rete', true);
  }
}

async function openReviewModal(orderId) {
  currentActiveOrderId = orderId;
  try {
    const res = await fetch('/api/orders');
    const orders = await res.json();
    const order = orders.find(o => o.id === orderId);
    if (!order) return;

    document.getElementById('modal-review-title').value = order.review_title || '';
    document.getElementById('modal-review-body').value = order.review_body || '';

    const isReady = order.days_until_review <= 0;
    const iphoneBtn = document.getElementById('modal-review-iphone-btn');
    if (iphoneBtn) {
      if (isReady) {
        iphoneBtn.disabled = false;
        iphoneBtn.className = 'px-3.5 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white border border-purple-400 text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all';
        iphoneBtn.title = 'Incolla o carica screenshot della recensione pubblicata';
      } else {
        iphoneBtn.disabled = true;
        iphoneBtn.className = 'px-3.5 py-2 rounded-xl bg-slate-800/50 border border-slate-700 text-slate-500 text-xs font-bold flex items-center gap-1.5 opacity-50 cursor-not-allowed';
        iphoneBtn.title = `Disponibile allo scadere dei 10 giorni (Giorno ${10 - order.days_until_review}/10)`;
      }
    }
    
    document.getElementById('btn-regenerate-review').onclick = async () => {
      const regRes = await fetch(`/api/orders/${orderId}/regenerate-review`);
      const rev = await regRes.json();
      document.getElementById('modal-review-title').value = rev.title;
      document.getElementById('modal-review-body').value = rev.body;
      showToast('Nuova variante recensione generata!');
    };

    document.getElementById('modal-review').classList.remove('hidden');
  } catch (err) {
    console.error(err);
  }
}

function openSimulatorModal() {
  document.getElementById('modal-simulator').classList.remove('hidden');
}

function openSettingsModal() {
  document.getElementById('modal-settings').classList.remove('hidden');
}

function closeModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.add('hidden');
}

// ----------------- SIMULATOR HELPERS -----------------

async function resetFullDemo() {
  try {
    const res = await fetch('/api/simulator/reset-demo', { method: 'POST' });
    if (res.ok) {
      showToast('Set demo HD ripristinato con successo!');
      closeModal('modal-simulator');
      loadStats();
      loadOffers();
      loadOrders();
      loadLogs();
    }
  } catch (err) {
    showToast('Errore nel ripristino demo', true);
  }
}

async function simulateOffer(title, priceInfo, contact, imgUrl) {
  try {
    const res = await fetch('/api/simulator/new-offer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: title,
        price_info: priceInfo,
        seller_contact: contact,
        image_url: imgUrl
      })
    });
    if (res.ok) {
      showToast('Nuova offerta simulata aggiunta!');
      closeModal('modal-simulator');
      loadOffers();
      loadStats();
    }
  } catch (err) {
    showToast('Errore simulazione offerta', true);
  }
}

async function simulateOrder(title, price, contact, imgUrl) {
  try {
    const res = await fetch('/api/simulator/new-order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_title: title,
        price: price,
        seller_contact: contact,
        product_image: imgUrl
      })
    });
    if (res.ok) {
      showToast('Ordine Amazon creato con screenshot pronto!');
      closeModal('modal-simulator');
      loadOrders();
      loadStats();
      switchTab('confirmations');
    }
  } catch (err) {
    showToast('Errore simulazione ordine', true);
  }
}

// ----------------- SETTINGS & UTILS -----------------

async function loadSettings() {
  try {
    const res = await fetch('/api/settings');
    if (!res.ok) return;
    const s = await res.json();

    if (s.test_mode !== undefined) {
      document.getElementById('set_test_mode').checked = s.test_mode === 'true';
    }
    if (s.telegram_api_id) document.getElementById('set_telegram_api_id').value = s.telegram_api_id;
    if (s.telegram_api_hash) document.getElementById('set_telegram_api_hash').value = s.telegram_api_hash;
    if (s.test_recipient) document.getElementById('set_test_recipient').value = s.test_recipient;
    if (s.email_user) document.getElementById('set_email_user').value = s.email_user;
    if (s.email_password) document.getElementById('set_email_password').value = s.email_password;
    if (s.review_days_wait) document.getElementById('set_review_days_wait').value = s.review_days_wait;
    if (s.gemini_api_key) document.getElementById('set_gemini_api_key').value = s.gemini_api_key;
  } catch (err) {
    console.error('Errore caricamento impostazioni:', err);
  }
}

async function saveSettings() {
  const items = [
    { key: 'test_mode', value: document.getElementById('set_test_mode').checked ? 'true' : 'false' },
    { key: 'telegram_api_id', value: document.getElementById('set_telegram_api_id').value },
    { key: 'telegram_api_hash', value: document.getElementById('set_telegram_api_hash').value },
    { key: 'test_recipient', value: document.getElementById('set_test_recipient').value },
    { key: 'email_user', value: document.getElementById('set_email_user').value },
    { key: 'email_password', value: document.getElementById('set_email_password').value },
    { key: 'review_days_wait', value: document.getElementById('set_review_days_wait').value },
    { key: 'gemini_api_key', value: document.getElementById('set_gemini_api_key').value }
  ];

  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(items)
    });
    if (res.ok) {
      showToast('Configurazione salvata con successo!');
      closeModal('modal-settings');
    }
  } catch (err) {
    showToast('Errore nel salvataggio impostazioni', true);
  }
}

function copyToClipboard(text, msg) {
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    showToast(msg || 'Copiato negli appunti!');
  }).catch(() => {
    const t = document.createElement('textarea');
    t.value = text;
    document.body.appendChild(t);
    t.select();
    document.execCommand('copy');
    document.body.removeChild(t);
    showToast(msg || 'Copiato negli appunti!');
  });
}

function showToast(msg, isError = false) {
  const t = document.getElementById('toast');
  const m = document.getElementById('toast-msg');
  if (!t || !m) return;

  m.innerText = msg;
  if (isError) {
    t.className = 'fixed top-5 right-5 z-50 bg-red-600 text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-2.5 text-xs font-extrabold transform transition-all duration-300 opacity-100 translate-y-0 border border-red-400';
  } else {
    t.className = 'fixed top-5 right-5 z-50 bg-emerald-600 text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-2.5 text-xs font-extrabold transform transition-all duration-300 opacity-100 translate-y-0 border border-emerald-400';
  }

  setTimeout(() => {
    t.classList.add('opacity-0', 'translate-y-[-20px]');
  }, 3500);
}

function formatDate(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' ' + d.toLocaleDateString([], { day: '2-digit', month: '2-digit' });
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ----------------- ACTIVE CHANNEL & SMART POST PARSER -----------------

async function loadActiveChannel() {
  try {
    const res = await fetch('/api/telegram/channel');
    if (!res.ok) return;
    const data = await res.json();
    const badge = document.getElementById('active-channel-badge');
    const input = document.getElementById('input-channel-name');
    if (badge) badge.innerText = data.channel_name;
    if (input) input.value = data.channel_name;
  } catch (err) {
    console.error('Errore caricamento canale:', err);
  }
}

function openChangeChannelModal() {
  const badge = document.getElementById('active-channel-badge');
  const input = document.getElementById('input-channel-name');
  if (badge && input) input.value = badge.innerText;
  document.getElementById('modal-change-channel').classList.remove('hidden');
}

async function saveActiveChannel() {
  const input = document.getElementById('input-channel-name');
  const val = input ? input.value.trim() : '';
  if (!val) {
    showToast('Inserisci un nome canale valido', true);
    return;
  }

  try {
    const res = await fetch('/api/telegram/channel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channel_name: val })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(`Canale ${data.channel_name} attivato!`);
      closeModal('modal-change-channel');
      loadActiveChannel();
      loadLogs();
    } else {
      showToast(data.detail || 'Errore salvataggio canale', true);
    }
  } catch (err) {
    showToast('Errore di connessione', true);
  }
}

function openPastePostModal() {
  document.getElementById('paste-post-text').value = '';
  document.getElementById('paste-post-image').value = '';
  document.getElementById('modal-paste-post').classList.remove('hidden');
}

async function submitParsedPost() {
  const text = document.getElementById('paste-post-text').value.trim();
  const img = document.getElementById('paste-post-image').value.trim();

  if (!text) {
    showToast('Incolla il testo del post Telegram', true);
    return;
  }

  try {
    const res = await fetch('/api/telegram/parse-post', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        raw_text: text,
        image_url: img || null
      })
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Offerta analizzata e aggiunta con successo!');
      closeModal('modal-paste-post');
      loadOffers();
      loadStats();
      loadLogs();
    } else {
      showToast(data.detail || "Errore durante l'analisi del post", true);
    }
  } catch (err) {
    showToast("Errore durante l'invio del post", true);
  }
}

async function syncActiveChannel() {
  const btn = document.getElementById('btn-sync-channel');
  if (btn) {
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Download in corso...';
    btn.disabled = true;
  }

  try {
    const res = await fetch('/api/telegram/sync-channel', { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message || 'Sincronizzazione completata!');
      loadOffers();
      loadStats();
      loadLogs();
    } else {
      showToast(data.message || 'Nessun post scaricato. Usa "Incolla Post"', true);
    }
  } catch (err) {
    showToast('Errore di sincronizzazione canale', true);
  } finally {
    if (btn) {
      btn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> Sincronizza Canale Live';
      btn.disabled = false;
    }
  }
}
