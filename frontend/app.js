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

function loadAllData() {
  loadStats();
  loadOffers();
  loadOrders();
  loadLogs();
  loadSettings();
  loadActiveChannel();
  loadTelegramStatus();
  // Auto-sync live Telegram channel in background
  syncActiveChannel(true);
}

document.addEventListener('DOMContentLoaded', async () => {
  initLightboxEvents();
  handleIncomingSharedLink();
  initPullToRefresh();
  const isAuth = await checkAuth();
  if (isAuth) {
    loadAllData();
  }
  
  // Timer live per conto alla rovescia recensioni (aggiorna solo i numeri dei secondi senza ricaricare la pagina)
  setInterval(updateReviewLiveTimers, 1000);

  // Controllo automatico in background risposte e link di Alex ogni 20 secondi
  setInterval(async () => {
    const token = localStorage.getItem('amz_auth_token');
    if (token && document.visibilityState === 'visible') {
      await syncTelegramReplies(true);
    }
  }, 20000);

  // Gestione comparsa pulsante 'Torna all'inizio' allo scroll
  window.addEventListener('scroll', () => {
    const btn = document.getElementById('btn-scroll-top');
    if (!btn) return;
    if (window.scrollY > 300) {
      btn.classList.remove('translate-y-20', 'opacity-0', 'pointer-events-none');
      btn.classList.add('translate-y-0', 'opacity-100', 'pointer-events-auto');
    } else {
      btn.classList.add('translate-y-20', 'opacity-0', 'pointer-events-none');
      btn.classList.remove('translate-y-0', 'opacity-100', 'pointer-events-auto');
    }
  }, { passive: true });
});

async function triggerManualFullSync(btn) {
  const icon = btn ? btn.querySelector('i') : null;
  if (icon) icon.classList.add('fa-spin');
  showToast('Sincronizzazione in corso...');
  try {
    await Promise.all([
      loadAllData(),
      syncTelegramReplies(true),
      syncActiveChannel(true)
    ]);
    showToast('Sincronizzazione completata!');
  } catch (err) {
    showToast('Sincronizzazione terminata');
  } finally {
    if (icon) {
      setTimeout(() => {
        icon.classList.remove('fa-spin');
      }, 500);
    }
  }
}

// ----------------- PULL TO REFRESH (SWIPE IN BASSO SU IPHONE / MOBILE) -----------------

function initPullToRefresh() {
  const ptrIndicator = document.getElementById('ptr-indicator');
  const ptrIcon = document.getElementById('ptr-icon');
  if (!ptrIndicator || !ptrIcon) return;

  let startY = 0;
  let currentY = 0;
  let isPulling = false;
  let isRefreshing = false;
  let thresholdVibrated = false;
  const triggerThreshold = 55;

  window.addEventListener('touchstart', (e) => {
    const hasOpenModal = !!document.querySelector('.modal:not(.hidden), #modal-lightbox:not(.hidden), #auth-lock-screen:not(.hidden)');
    if (window.scrollY <= 2 && !isRefreshing && !hasOpenModal && e.touches.length === 1) {
      startY = e.touches[0].clientY;
      isPulling = true;
      thresholdVibrated = false;
    }
  }, { passive: true });

  window.addEventListener('touchmove', (e) => {
    if (!isPulling || isRefreshing || e.touches.length !== 1) return;
    currentY = e.touches[0].clientY;
    const deltaY = currentY - startY;

    if (deltaY > 0 && window.scrollY <= 2) {
      const pullDistance = Math.min(deltaY * 0.42, 80);
      ptrIndicator.style.transition = 'none';
      ptrIndicator.style.transform = `translateY(${pullDistance + 10}px)`;

      // Rotazione dinamica proporzionale al trascinamento (stile Apple iOS)
      const rotation = pullDistance * 4.5;
      ptrIcon.className = 'fa-solid fa-circle-notch text-lg text-emerald-400';
      ptrIcon.style.transform = `rotate(${rotation}deg)`;

      if (pullDistance >= triggerThreshold && !thresholdVibrated) {
        thresholdVibrated = true;
        if (navigator.vibrate) navigator.vibrate(15);
      }
    } else {
      ptrIndicator.style.transform = 'translateY(-100%)';
    }
  }, { passive: true });

  window.addEventListener('touchend', async () => {
    if (!isPulling || isRefreshing) {
      isPulling = false;
      return;
    }
    isPulling = false;
    const deltaY = currentY - startY;
    const pullDistance = Math.min(deltaY * 0.42, 80);

    if (pullDistance >= triggerThreshold && window.scrollY <= 2) {
      isRefreshing = true;
      ptrIndicator.style.transition = 'transform 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
      ptrIndicator.style.transform = 'translateY(48px)';
      
      // Animazione rotellina continua stile iOS
      ptrIcon.className = 'fa-solid fa-circle-notch fa-spin text-lg text-emerald-400';
      ptrIcon.style.transform = '';
      if (navigator.vibrate) navigator.vibrate(25);

      try {
        await Promise.all([
          loadAllData(),
          syncTelegramReplies(true),
          syncActiveChannel(true)
        ]);
        ptrIcon.className = 'fa-solid fa-check text-base text-emerald-400';
        if (navigator.vibrate) navigator.vibrate([15, 30]);
      } catch (err) {
        // Silently complete
      }

      setTimeout(() => {
        ptrIndicator.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        ptrIndicator.style.transform = 'translateY(-100%)';
        setTimeout(() => {
          ptrIcon.className = 'fa-solid fa-circle-notch text-lg text-emerald-400';
          ptrIcon.style.transform = 'rotate(0deg)';
          isRefreshing = false;
        }, 300);
      }, 500);
    } else {
      ptrIndicator.style.transition = 'transform 0.25s ease-out';
      ptrIndicator.style.transform = 'translateY(-100%)';
    }
  });
}

function scrollToTop() {
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });
}

// ----------------- AUTHENTICATION & ACCESS CONTROL -----------------

async function checkAuth() {
  const token = localStorage.getItem('amz_auth_token');
  const lockScreen = document.getElementById('auth-lock-screen');
  if (!token) {
    if (lockScreen) lockScreen.classList.remove('hidden');
    return false;
  }

  try {
    const res = await fetch(`/api/auth/status?token=${encodeURIComponent(token)}`);
    const data = await res.json();
    if (data.authenticated) {
      if (lockScreen) lockScreen.classList.add('hidden');
      return true;
    } else {
      localStorage.removeItem('amz_auth_token');
      if (lockScreen) lockScreen.classList.remove('hidden');
      return false;
    }
  } catch (err) {
    if (lockScreen) lockScreen.classList.add('hidden');
    return true;
  }
}

async function handleAuthLogin(e) {
  if (e) e.preventDefault();
  const input = document.getElementById('auth-password-input');
  const errorMsg = document.getElementById('auth-error-msg');
  const password = input ? input.value.trim() : '';

  if (!password) {
    if (errorMsg) {
      errorMsg.innerText = 'Inserisci la password di sicurezza';
      errorMsg.classList.remove('hidden');
    }
    return;
  }

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: password })
    });
    let data = {};
    try { data = await res.json(); } catch(e) {}

    if (res.ok && data.token) {
      localStorage.setItem('amz_auth_token', data.token);
      const lockScreen = document.getElementById('auth-lock-screen');
      if (lockScreen) lockScreen.classList.add('hidden');
      if (errorMsg) errorMsg.classList.add('hidden');
      showToast('Accesso autorizzato!');
      loadAllData();
    } else {
      if (errorMsg) {
        errorMsg.innerText = data.detail || 'Password errata. Riprova.';
        errorMsg.classList.remove('hidden');
      }
      if (input) {
        input.value = '';
        input.focus();
      }
    }
  } catch (err) {
    if (errorMsg) {
      errorMsg.innerText = 'Server in riavvio (deploy in corso). Riprova tra qualche istante...';
      errorMsg.classList.remove('hidden');
    }
  }
}

function handleAuthLogout() {
  localStorage.removeItem('amz_auth_token');
  const lockScreen = document.getElementById('auth-lock-screen');
  if (lockScreen) lockScreen.classList.remove('hidden');
  const input = document.getElementById('auth-password-input');
  if (input) {
    input.value = '';
    input.focus();
  }
  showToast('Sessione bloccata');
}

function togglePasswordVisibility(inputId, iconId) {
  const input = document.getElementById(inputId);
  const icon = document.getElementById(iconId);
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    if (icon) icon.className = 'fa-regular fa-eye-slash';
  } else {
    input.type = 'password';
    if (icon) icon.className = 'fa-regular fa-eye';
  }
}

async function changeAdminPassword() {
  const oldPwd = document.getElementById('set_old_password').value.trim() || '123456';
  const newPwd = document.getElementById('set_new_password').value.trim();

  if (!newPwd) {
    showToast('Inserisci la nuova password desiderata', true);
    return false;
  }

  try {
    const res = await fetch('/api/auth/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_password: oldPwd, new_password: newPwd })
    });
    const data = await res.json();
    if (res.ok && data.token) {
      localStorage.setItem('amz_auth_token', data.token);
      showToast('Password di sicurezza aggiornata con successo!');
      document.getElementById('set_old_password').value = '';
      document.getElementById('set_new_password').value = '';
      return true;
    } else {
      showToast(data.detail || 'Errore durante il cambio password', true);
      return false;
    }
  } catch (err) {
    showToast('Errore di rete', true);
    return false;
  }
}

// ----------------- TAB SWITCHING -----------------

function switchTab(tabId) {
  currentTab = tabId;
  
  // Nascondi tutti i tab content
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  const target = document.getElementById(`tab-${tabId}`);
  if (target) target.classList.remove('hidden');

  // Aggiorna stile bottoni pillole
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.className = 'tab-btn whitespace-nowrap shrink-0 px-3.5 py-2 md:px-4 md:py-2.5 rounded-xl text-xs md:text-sm font-semibold text-slate-300 hover:text-white flex items-center gap-2 hover:bg-brand-surface border border-transparent transition-all active:scale-95';
  });
  const activeBtn = document.getElementById(`tab-btn-${tabId}`);
  if (activeBtn) {
    activeBtn.className = 'tab-btn whitespace-nowrap shrink-0 px-3.5 py-2 md:px-4 md:py-2.5 rounded-xl text-xs md:text-sm font-bold flex items-center gap-2 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm transition-all active:scale-95';
  }

  // Aggiorna stile bottoni mobile
  const mobTabs = ['offers', 'approved_links', 'confirmations', 'reviews', 'refunds'];
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
  if (tabId === 'offers') {
    loadOffers();
    syncActiveChannel(true);
  }
  else if (tabId === 'approved_links') {
    loadOrders();
    syncTelegramReplies(true);
  }
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
    
    const badgeLinks = document.getElementById('badge-links-count');
    if (badgeLinks) badgeLinks.innerText = data.links_count || 0;

    const mobBadgeLinks = document.getElementById('mob-badge-links');
    if (mobBadgeLinks) {
      if ((data.links_count || 0) > 0) mobBadgeLinks.classList.remove('hidden');
      else mobBadgeLinks.classList.add('hidden');
    }

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
    const rawOffers = await res.json();
    const container = document.getElementById('offers-grid');
    if (!container) return;

    // Visualizzazione di tutte le offerte sincronizzate (elimina solo copie identiche dello stesso messaggio Telegram)
    const seenMap = new Map();
    for (const o of (rawOffers || [])) {
      if (o.status === 'dismissed') continue;
      
      const key = o.message_id ? `msg_${String(o.message_id).trim()}` : `title_${(o.title || '').trim().toLowerCase()}`;
      
      if (seenMap.has(key)) {
        const existing = seenMap.get(key);
        if (o.is_purchased && !existing.is_purchased) {
          seenMap.set(key, o);
        }
      } else {
        seenMap.set(key, o);
      }
    }
    const offers = Array.from(seenMap.values());

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
      const isPurchased = (o.is_purchased === true || o.status === 'purchased' || ['waiting_review', 'review_ready', 'review_submitted', 'reimbursed', 'pending_confirmation', 'confirmed_sent'].includes(o.order_status));

      return `
        <div class="glass-card rounded-2xl overflow-hidden flex flex-col justify-between transition-all duration-200 hover:-translate-y-1 hover:shadow-xl ${
          isPurchased 
            ? 'border-2 border-emerald-500/80 shadow-lg shadow-emerald-950/60 bg-gradient-to-b from-emerald-950/30 via-slate-900/90 to-slate-900 ring-1 ring-emerald-400/40' 
            : 'hover:border-emerald-500/50'
        }">
          
          <!-- Product Image Container with Complete Visibility (No Cropping) -->
          <div class="relative w-full h-64 bg-slate-950 flex items-center justify-center overflow-hidden group cursor-pointer border-b border-slate-800" onclick="openLightboxFromSrc('${imgUrl}', '${escapeHtml(o.title)}', 'Condizioni: ${escapeHtml(o.price_info || '')}')">
            <img src="${imgUrl}" alt="${escapeHtml(o.title)}" class="max-h-full max-w-full w-auto h-auto object-contain p-2 group-hover:scale-105 transition-transform duration-300">
            
            <!-- Badges top -->
            <div class="absolute top-2.5 left-2.5 right-2.5 flex items-center justify-between pointer-events-none gap-1.5 flex-wrap">
              ${isPurchased ? `
                <span class="text-[11px] md:text-xs font-black px-3 py-1 rounded-full bg-gradient-to-r from-emerald-400 to-teal-400 text-slate-950 shadow-lg flex items-center gap-1.5 ring-2 ring-emerald-300/40 tracking-wide animate-pulse">
                  <i class="fa-solid fa-circle-check text-slate-950"></i> GIÀ ACQUISTATO
                </span>
                <span class="text-[10px] md:text-[11px] font-black px-2.5 py-1 rounded-full bg-slate-900/95 backdrop-blur-md text-emerald-300 border border-emerald-500/60 shadow flex items-center gap-1">
                  <i class="fa-solid fa-percent text-emerald-400"></i> ${o.refund_pct || 100}% RIMBORSO
                </span>
              ` : `
                <span class="text-[11px] font-black px-2.5 py-1 rounded-full bg-emerald-500 text-slate-950 shadow flex items-center gap-1">
                  <i class="fa-solid fa-percent"></i> ${o.refund_pct || 100}% RIMBORSO
                </span>
                <span class="text-[10px] font-extrabold px-2 py-0.5 rounded-full ${o.taxes_covered ? 'bg-slate-900/90 text-emerald-300 border border-emerald-500/40' : 'bg-slate-900/90 text-amber-300 border border-amber-500/40'} shadow">
                  ${o.taxes_covered ? '✓ Tasse Coperte' : 'Tasse da Verificare'}
                </span>
              `}
            </div>

            <!-- Zoom Prompt Overlay -->
            <div class="absolute bottom-2.5 right-2.5 px-2.5 py-1 rounded-lg bg-slate-900/90 backdrop-blur-md text-white text-[11px] font-bold border border-slate-700 flex items-center gap-1 shadow-lg group-hover:bg-emerald-600 transition-colors">
              <i class="fa-solid fa-magnifying-glass-plus text-emerald-400 group-hover:text-white"></i>
              <span>Ingrandisci Foto</span>
            </div>
          </div>

          <!-- Card Content Body -->
          <div class="p-4 flex-1 flex flex-col justify-between space-y-3">
              <!-- Banner Già Acquistato se presente -->
              ${isPurchased ? `
                <div class="p-2.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-between gap-2 text-xs">
                  <div class="flex items-center gap-2 text-emerald-300 font-bold min-w-0">
                    <i class="fa-solid fa-bag-shopping text-emerald-400 shrink-0"></i>
                    <span class="truncate">Hai già comprato questo articolo (${escapeHtml(o.order_status_label || 'In Recensioni')})</span>
                  </div>
                  ${o.order_id ? `<button onclick="goToOrderDetails(${o.order_id}, '${o.order_target_tab || 'reviews'}')" class="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold text-[11px] shadow transition-all flex items-center gap-1 shrink-0"><i class="fa-solid fa-arrow-right"></i> Apri</button>` : ''}
                </div>
              ` : ''}

              <!-- Titolo Prodotto con tasto Modifica Rapida -->
              <div class="flex items-start justify-between gap-2">
                <h3 class="text-sm md:text-base font-extrabold text-white leading-snug flex-1">
                  ${escapeHtml(o.title)}
                </h3>
                <button onclick="quickEditOfferTitle(${o.id}, '${escapeHtml(o.title).replace(/'/g, "\\'")}')" title="Modifica Nome Articolo" class="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-emerald-400 border border-slate-700 text-xs transition-colors shrink-0">
                  <i class="fa-solid fa-pen-to-square"></i>
                </button>
              </div>

              <!-- Riquadro Condizioni Spesa & Copertura Tasse (Testo Completo Multiriga con Percentuale) -->
              <div class="mt-3 space-y-2 text-xs">
                <div class="p-3 rounded-xl bg-slate-900/90 border border-slate-700/80">
                  <div class="flex items-center justify-between mb-1.5 flex-wrap gap-1">
                    <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                      <i class="fa-solid fa-coins text-emerald-400"></i> Condizioni Spesa & Rimborso:
                    </span>
                    <span class="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                      <i class="fa-solid fa-calculator"></i> Rimborso al ${o.refund_pct || 100}%
                    </span>
                  </div>
                  <p class="font-extrabold text-emerald-300 text-xs md:text-sm leading-relaxed break-words whitespace-normal">
                    ${escapeHtml(o.price_info || (o.refund_pct ? (o.refund_pct + '% rimborso dopo recensione') : '100% rimborso'))}
                  </p>
                </div>
              </div>
            </div>

            <!-- Bottoni Azione -->
            <div class="pt-3 border-t border-brand-border flex items-center gap-2 p-4 pt-0">
              ${isPurchased ? `
                <div class="flex-1 flex items-center gap-1.5">
                  <button onclick="goToOrderDetails(${o.order_id || 0}, '${o.order_target_tab || 'reviews'}')" class="flex-1 py-2.5 px-3 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/50 text-xs font-black flex items-center justify-center gap-2 shadow-sm transition-all active:scale-[0.98] cursor-pointer">
                    <i class="fa-solid fa-circle-check text-emerald-400 text-sm"></i>
                    <span>Già Comprato (${escapeHtml(o.order_status_label || 'In Recensioni')})</span>
                    <i class="fa-solid fa-arrow-right text-[10px] opacity-70"></i>
                  </button>
                  <button onclick="resetOffer(${o.id})" title="Reimposta e riabilita tasto richiesta" class="px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-xs font-bold flex items-center gap-1 transition-all shrink-0">
                    <i class="fa-solid fa-rotate-left"></i> Reset
                  </button>
                </div>
              ` : (isRequested || o.status === 'link_received') ? `
                <div class="flex-1 flex items-center gap-1.5">
                  <button disabled class="flex-1 py-2.5 px-2.5 rounded-xl ${
                    o.status === 'link_received' ? 'bg-cyan-600/20 text-cyan-300 border border-cyan-500/40' : 'bg-blue-600/20 text-blue-300 border border-blue-500/40'
                  } text-xs font-extrabold flex items-center justify-center gap-1.5 truncate shadow-sm">
                    <i class="fa-solid ${
                      o.status === 'link_received' ? 'fa-cart-arrow-down text-cyan-400' : 'fa-check-double text-blue-400'
                    }"></i> ${
                      o.status === 'link_received' ? 'Link Ricevuto / Da Comprare' : 'Richiesta Inviata'
                    }
                  </button>
                  <button onclick="resetOffer(${o.id})" title="Reimposta e riabilita tasto richiesta" class="px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-xs font-bold flex items-center gap-1 transition-all shrink-0">
                    <i class="fa-solid fa-rotate-left"></i> Reset
                  </button>
                </div>
              ` : `
                <button data-hold-id="${o.id}" 
                        class="hold-to-confirm-btn relative overflow-hidden select-none flex-1 py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-extrabold shadow-lg shadow-emerald-950/40 flex items-center justify-center gap-2 transition-all active:scale-[0.98] cursor-pointer"
                        style="touch-action: pan-y; -webkit-touch-callout: none; -webkit-user-select: none; user-select: none;">
                  <div class="hold-bar absolute inset-y-0 left-0 bg-emerald-300/40 w-0 pointer-events-none rounded-xl"></div>
                  <span class="hold-label relative z-10 flex items-center gap-1.5 pointer-events-none">
                    <i class="fa-solid fa-fingerprint text-emerald-200 text-sm"></i> Tieni premuto per inviare
                  </span>
                </button>
              `}
              <button onclick="dismissOffer(${o.id})" title="Rimuovi offerta" class="w-10 h-10 rounded-xl bg-slate-900 hover:bg-red-500/20 text-slate-400 hover:text-red-400 border border-slate-700/80 flex items-center justify-center transition-all shrink-0">
                <i class="fa-regular fa-trash-can text-sm"></i>
              </button>
            </div>

          </div>
        </div>
      `;
    }).join('');

    // Inizializza i listener sui pulsanti di pressione prolungata
    bindHoldButtons();

  } catch (err) {
    console.error('Errore caricamento offerte:', err);
  }
}

function goToOrderDetails(orderId, targetTab = 'reviews') {
  switchTab(targetTab);
  if (!orderId) return;
  setTimeout(() => {
    const el = document.querySelector(`[data-order-id="${orderId}"]`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.add('ring-4', 'ring-emerald-400', 'shadow-2xl', 'transition-all', 'duration-500');
      setTimeout(() => {
        el.classList.remove('ring-4', 'ring-emerald-400', 'shadow-2xl');
      }, 3000);
    }
  }, 250);
}

// ----------------- ENHANCED HOLD TO CONFIRM (1.5s + Dynamic Color Glow) -----------------
let currentHoldState = {
  offerId: null,
  btn: null,
  bar: null,
  label: null,
  timer: null,
  startTime: 0,
  startX: 0,
  startY: 0
};

function bindHoldButtons() {
  document.querySelectorAll('.hold-to-confirm-btn').forEach(btn => {
    const offerId = btn.dataset.holdId;
    const bar = btn.querySelector('.hold-bar');
    const label = btn.querySelector('.hold-label');

    btn.onpointerdown = (e) => {
      abortHold();

      currentHoldState = {
        offerId: offerId,
        btn: btn,
        bar: bar,
        label: label,
        startX: e.clientX,
        startY: e.clientY,
        startTime: Date.now(),
        timer: null
      };

      // Cambio colore dinamico e barra di caricamento (1.5 secondi)
      btn.classList.add('border-amber-400', 'shadow-amber-500/30');
      if (bar) {
        bar.className = 'hold-bar absolute inset-y-0 left-0 bg-gradient-to-r from-amber-500 via-yellow-400 to-amber-300 w-0 pointer-events-none rounded-xl shadow-[0_0_15px_rgba(251,191,36,0.8)]';
        bar.style.transition = 'width 1.5s linear';
        bar.style.width = '100%';
      }
      if (label) {
        label.innerHTML = '<i class="fa-solid fa-bolt text-yellow-300 animate-pulse"></i> <span class="text-amber-200 font-extrabold tracking-wide">CONFERMA IN CORSO...</span>';
      }

      currentHoldState.timer = setTimeout(() => {
        if (currentHoldState.offerId === offerId) {
          if (navigator.vibrate) {
            try { navigator.vibrate([60, 40, 60]); } catch (err) {}
          }
          if (label) {
            label.innerHTML = '<i class="fa-solid fa-check text-emerald-300"></i> <span class="text-emerald-300 font-black">RICHIESTA INVIATA!</span>';
          }
          requestOffer(offerId);
          abortHold(true);
        }
      }, 1500);
    };

    btn.onpointermove = (e) => {
      if (!currentHoldState.timer) return;
      const dist = Math.hypot(e.clientX - currentHoldState.startX, e.clientY - currentHoldState.startY);
      if (dist > 18) {
        // Movimento scroll: annulla
        abortHold();
      }
    };

    btn.onpointerup = (e) => {
      const duration = Date.now() - (currentHoldState.startTime || 0);
      if (duration < 1300 && currentHoldState.offerId === offerId) {
        showToast('💡 Tieni premuto 1.5 secondi per confermare');
      }
      abortHold();
    };

    btn.onpointercancel = () => abortHold();
    btn.onpointerleave = () => abortHold();
  });
}

function abortHold(completed = false) {
  if (currentHoldState.timer) {
    clearTimeout(currentHoldState.timer);
    currentHoldState.timer = null;
  }
  if (currentHoldState.btn && !completed) {
    currentHoldState.btn.classList.remove('border-amber-400', 'shadow-amber-500/30');
  }
  if (currentHoldState.bar && !completed) {
    currentHoldState.bar.style.transition = 'width 0.2s ease-out';
    currentHoldState.bar.style.width = '0%';
  }
  if (currentHoldState.label && !completed) {
    currentHoldState.label.innerHTML = '<i class="fa-solid fa-fingerprint text-emerald-200 text-sm"></i> Tieni premuto per inviare';
  }
}

async function quickEditOfferTitle(offerId, currentTitle) {
  const newTitle = prompt('Modifica il nome di questo articolo:', currentTitle || '');
  if (newTitle === null) return;
  if (!newTitle.trim()) {
    showToast('Il nome articolo non può essere vuoto', true);
    return;
  }

  try {
    const res = await fetch(`/api/offers/${offerId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: newTitle.trim() })
    });
    if (res.ok) {
      showToast('Nome articolo aggiornato!');
      loadOffers();
    } else {
      showToast('Errore durante l\'aggiornamento', true);
    }
  } catch (err) {
    showToast('Errore di connessione', true);
  }
}

// ----------------- ORDERS / CONFIRMATIONS / REVIEWS -----------------

let currentManualLinkId = null;

async function loadOrders() {
  try {
    const res = await fetch('/api/orders');
    if (!res.ok) return;
    let orders = await res.json();

    // Schermatura di sicurezza client-side:
    // Se il server ha perso gli ordini durante un riavvio ma il browser ha una copia memorizzata, ripristina all'istante
    const localBackupStr = localStorage.getItem('amz_shielded_orders');
    let localBackup = [];
    try { localBackup = JSON.parse(localBackupStr) || []; } catch(e) {}

    if ((!orders || orders.length === 0) && localBackup && localBackup.length > 0) {
      console.log('[Shield] Ripristino automatico ordini dal browser al server...');
      await fetch('/api/orders/client-sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ orders: localBackup })
      });
      const refreshRes = await fetch('/api/orders');
      if (refreshRes.ok) {
        orders = await refreshRes.json();
      }
    } else if (orders && orders.length > 0) {
      localStorage.setItem('amz_shielded_orders', JSON.stringify(orders));
    }

    renderApprovedLinks(orders);
    renderConfirmations(orders);
    renderReviews(orders);
    renderRefunds(orders);
  } catch (err) {
    console.error('Errore caricamento ordini:', err);
  }
}

function renderApprovedLinks(orders) {
  const container = document.getElementById('approved-links-list');
  if (!container) return;
  
  const linkOrders = (orders || []).filter(o => o.status === 'waiting_link' || o.status === 'link_approved');

  if (linkOrders.length === 0) {
    container.innerHTML = `
      <div class="py-16 text-center text-slate-400 glass-card rounded-2xl p-8 border border-dashed border-slate-700">
        <div class="w-16 h-16 rounded-2xl bg-slate-800/80 mx-auto flex items-center justify-center text-3xl text-cyan-400/80 mb-3 shadow-inner">
          <i class="fa-solid fa-cart-shopping"></i>
        </div>
        <h3 class="text-base font-bold text-white">Nessun link in attesa o approvato</h3>
        <p class="text-xs text-slate-300 mt-1 max-w-md mx-auto">Quando invii una richiesta da "Offerte Telegram", la troverai qui in attesa del link di Alex per procedere all'acquisto.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = linkOrders.map(o => {
    const prodImg = o.product_image || 'https://images.unsplash.com/photo-1532372320572-cda25653a26d?auto=format&fit=crop&w=800&q=80';
    const isApproved = o.status === 'link_approved' && o.amazon_url;
    const seller = o.seller_contact || '@alex8700';

    return `
      <div class="glass-card rounded-2xl p-5 border ${isApproved ? 'border-cyan-500/40 bg-gradient-to-r from-cyan-950/20 via-brand-surface to-brand-card' : 'border-amber-500/30'} flex flex-col lg:flex-row lg:items-center justify-between gap-5 shadow-lg relative z-10 bg-brand-surface">
        <!-- Sinistra: Foto Prodotto + Dati -->
        <div class="flex items-start gap-4 flex-1">
          <div onclick="openLightboxFromSrc('${prodImg}', '${escapeHtml(o.product_title || 'Prodotto')}', 'Contatto: ${seller}')" class="cursor-pointer relative w-24 h-24 rounded-2xl overflow-hidden border border-slate-700 bg-slate-950 flex items-center justify-center shrink-0 group shadow-md" title="Clicca per zoomare la foto">
            <img src="${prodImg}" alt="Foto Prodotto" class="max-w-full max-h-full object-contain p-1 group-hover:scale-110 transition-transform">
            <div class="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-white text-xs">
              <i class="fa-solid fa-magnifying-glass-plus text-base"></i>
            </div>
            <span class="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/80 text-[10px] text-white font-bold">Foto</span>
          </div>

          <div class="flex-1">
            <div class="flex flex-wrap items-center gap-2">
              ${isApproved ? `
                <span class="text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1.5 shadow-sm">
                  <i class="fa-solid fa-circle-check text-emerald-400"></i> Approvato da Alex • Link Disponibile
                </span>
              ` : `
                <span class="text-xs font-bold px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1.5 animate-pulse">
                  <i class="fa-solid fa-hourglass-half text-amber-400"></i> In attesa di risposta da Alex
                </span>
              `}
              <span class="text-xs font-mono px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700">
                ${seller}
              </span>
            </div>

            <h3 class="text-sm md:text-base font-extrabold text-white mt-2 leading-snug">${escapeHtml(o.product_title || 'Articolo in promozione')}</h3>

            ${isApproved && o.amazon_url ? `
              <div class="mt-2.5 flex flex-wrap items-center gap-2">
                <span class="text-[11px] text-slate-400 font-medium">Link Diretto:</span>
                <a href="${o.amazon_url}" target="_blank" class="text-xs text-cyan-300 hover:text-cyan-200 underline font-mono truncate max-w-xs md:max-w-md flex items-center gap-1">
                  <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i> ${o.amazon_url}
                </a>
                <button onclick="copyToClipboard('${o.amazon_url}', 'Link Amazon copiato negli appunti!')" class="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs" title="Copia link">
                  <i class="fa-regular fa-copy"></i>
                </button>
              </div>
            ` : ''}
          </div>
        </div>

        <!-- Destra: Azioni -->
        <div class="flex flex-wrap items-center gap-2 shrink-0 border-t lg:border-t-0 pt-3 lg:pt-0 border-brand-border">
          ${isApproved ? `
            <a href="${o.amazon_url}" target="_blank" class="px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white text-xs font-extrabold flex items-center gap-2 shadow-lg shadow-emerald-950/60 transition-all active:scale-95">
              <i class="fa-solid fa-cart-arrow-down text-sm"></i> Apri & Compra su Amazon
            </a>
            <button onclick="markOrderAsPurchased(${o.id}, '${escapeHtml(o.product_title || '')}')" class="px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-600 hover:from-amber-400 hover:to-yellow-500 text-white text-xs font-extrabold flex items-center gap-2 shadow-lg shadow-amber-950/60 transition-all active:scale-95">
              <i class="fa-solid fa-receipt text-sm"></i> Ho Acquistato
            </button>
            <button onclick="openManualLinkModal(${o.id}, '${escapeHtml(o.product_title || '')}', '${escapeHtml(o.amazon_url || '')}')" title="Modifica Link" class="px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition-all">
              <i class="fa-solid fa-pen text-xs"></i> Modifica Link
            </button>
          ` : `
            <button onclick="pasteAmazonLinkDirectly(${o.id})" class="px-3.5 py-2.5 rounded-xl bg-emerald-600/30 hover:bg-emerald-600/50 border border-emerald-500/50 text-emerald-200 text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all active:scale-95" title="Incolla al volo il link dagli appunti">
              <i class="fa-regular fa-paste text-sm text-emerald-400"></i> Incolla dagli Appunti
            </button>
            <button onclick="openManualLinkModal(${o.id}, '${escapeHtml(o.product_title || '')}', '')" class="px-3.5 py-2.5 rounded-xl bg-cyan-600/30 hover:bg-cyan-600/50 border border-cyan-500/50 text-cyan-200 text-xs font-extrabold flex items-center gap-1.5 shadow-md transition-all active:scale-95">
              <i class="fa-solid fa-link text-sm"></i> Inserisci Link
            </button>
            <button onclick="syncTelegramReplies()" class="px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-cyan-300 text-xs font-bold flex items-center gap-1.5 transition-all" title="Verifica subito se Alex ha inviato il link">
              <i class="fa-brands fa-telegram"></i> Controlla Telegram
            </button>
            <button onclick="markOrderAsPurchased(${o.id}, '${escapeHtml(o.product_title || '')}')" class="px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs font-bold flex items-center gap-1.5 transition-all">
              <i class="fa-solid fa-forward-step text-amber-400"></i> Salta ad Acquisto
            </button>
          `}
          <button onclick="confirmAndDeleteOrder(${o.id})" title="Annulla richiesta / Non disponibile" class="px-3 py-2.5 rounded-xl bg-slate-900 hover:bg-rose-900/30 border border-slate-800 hover:border-rose-500/40 text-slate-400 hover:text-rose-300 text-xs font-bold flex items-center gap-1.5 transition-all">
            <i class="fa-solid fa-xmark"></i> Annulla
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function extractAmazonUrlFromText(text) {
  if (!text) return '';
  const match = text.match(/https?:\/\/[^\s<>"']+/i) || text.match(/(?:(?:www\.)?amazon\.[a-z.]+|amzn\.(?:to|eu))\/[^\s<>"']+/i);
  if (match) {
    let url = match[0].trim().replace(/[.,);!?"'>]+$/, '');
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://' + url;
    }
    return url;
  }
  return '';
}

async function pasteToManualLinkInput() {
  const inputEl = document.getElementById('input-manual-amazon-link');
  if (!inputEl) return;
  try {
    let text = '';
    if (navigator.clipboard && navigator.clipboard.readText) {
      text = await navigator.clipboard.readText();
    }
    if (!text) {
      text = prompt('Incolla qui il testo o il link Amazon ricevuto:');
    }
    if (text) {
      const extracted = extractAmazonUrlFromText(text) || text.trim();
      inputEl.value = extracted;
      showToast('Link inserito negli appunti!');
      inputEl.focus();
    }
  } catch (err) {
    const text = prompt('Incolla qui il testo o il link Amazon ricevuto:');
    if (text) {
      const extracted = extractAmazonUrlFromText(text) || text.trim();
      inputEl.value = extracted;
      inputEl.focus();
    }
  }
}

async function pasteAmazonLinkDirectly(orderId) {
  try {
    let text = '';
    if (navigator.clipboard && navigator.clipboard.readText) {
      text = await navigator.clipboard.readText();
    }
    if (!text) {
      text = prompt('Incolla qui il link o il messaggio ricevuto da Alex:');
    }
    if (!text) return;
    
    const cleanUrl = extractAmazonUrlFromText(text) || text.trim();
    if (!cleanUrl || (!cleanUrl.includes('amazon') && !cleanUrl.includes('amzn'))) {
      showToast('Nessun link Amazon valido trovato nel testo incollato', true);
      return;
    }

    const res = await fetch(`/api/orders/${orderId}/set-amazon-link`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amazon_url: cleanUrl })
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Link Amazon salvato! Articolo pronto per l\'acquisto.');
      loadOrders();
      loadStats();
    } else {
      showToast(data.detail || 'Errore salvataggio link', true);
    }
  } catch (err) {
    const text = prompt('Incolla qui il link o il messaggio ricevuto da Alex:');
    if (text) {
      const cleanUrl = extractAmazonUrlFromText(text) || text.trim();
      if (cleanUrl) {
        const res = await fetch(`/api/orders/${orderId}/set-amazon-link`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ amazon_url: cleanUrl })
        });
        if (res.ok) {
          showToast('Link Amazon salvato!');
          loadOrders();
          loadStats();
        }
      }
    }
  }
}

async function handleIncomingSharedLink() {
  try {
    const params = new URLSearchParams(window.location.search);
    const sharedParam = params.get('url') || params.get('text') || params.get('link') || params.get('title') || '';
    if (sharedParam) {
      const extracted = extractAmazonUrlFromText(sharedParam);
      if (extracted) {
        // Pulisci l'URL del browser
        window.history.replaceState({}, document.title, window.location.pathname);
        
        switchTab('approved_links');
        
        // Attendi che gli ordini siano disponibili
        const res = await fetch('/api/orders');
        if (res.ok) {
          const orders = await res.json();
          const waiting = (orders || []).filter(o => o.status === 'waiting_link');
          if (waiting.length === 1) {
            // Assegna direttamente all'unico ordine in attesa
            const target = waiting[0];
            const setRes = await fetch(`/api/orders/${target.id}/set-amazon-link`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ amazon_url: extracted })
            });
            if (setRes.ok) {
              showToast(`Link Amazon assegnato automaticamente a "${target.product_title.slice(0, 30)}..."!`);
              loadOrders();
              loadStats();
              return;
            }
          } else if (waiting.length > 1) {
            // Più ordini in attesa: apri il modal per il primo
            openManualLinkModal(waiting[0].id, waiting[0].product_title, extracted);
            showToast('Link condiviso intercettato! Clicca Salva per confermare.');
            return;
          }
        }
        showToast('Link Amazon condiviso intercettato!');
      }
    }
  } catch (e) {
    console.error('Shared link handling error:', e);
  }
}

function openManualLinkModal(orderId, productTitle, currentLink = '') {
  currentManualLinkId = orderId;
  const nameEl = document.getElementById('modal-set-link-product-name');
  const inputEl = document.getElementById('input-manual-amazon-link');
  const removeBtn = document.getElementById('btn-remove-manual-link');
  if (nameEl) nameEl.innerText = productTitle || 'Articolo';
  if (inputEl) inputEl.value = currentLink || '';
  if (removeBtn) {
    if (currentLink && currentLink.trim().length > 0) {
      removeBtn.classList.remove('hidden');
    } else {
      removeBtn.classList.add('hidden');
    }
  }
  openModal('modal-set-link');
  if (inputEl) setTimeout(() => inputEl.focus(), 150);
}

async function submitManualAmazonLink() {
  if (!currentManualLinkId) return;
  const inputEl = document.getElementById('input-manual-amazon-link');
  const rawValue = inputEl ? inputEl.value.trim() : '';
  const url = extractAmazonUrlFromText(rawValue) || rawValue;
  if (!url) {
    showToast('Inserisci un URL Amazon valido (oppure usa Rimuovi Link)', true);
    return;
  }

  try {
    const res = await fetch(`/api/orders/${currentManualLinkId}/set-amazon-link`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amazon_url: url })
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Link Amazon salvato con successo! Articolo pronto per l\'acquisto.');
      closeModal('modal-set-link');
      loadOrders();
      loadStats();
    } else {
      showToast(data.detail || 'Errore salvataggio link', true);
    }
  } catch (err) {
    showToast('Errore di connessione', true);
  }
}

async function clearManualAmazonLink() {
  if (!currentManualLinkId) return;
  if (!confirm('Sei sicuro di voler rimuovere il link e rimettere la scheda in attesa di Alex?')) return;
  
  try {
    const res = await fetch(`/api/orders/${currentManualLinkId}/set-amazon-link`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amazon_url: '' })
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Link rimosso! Scheda reimpostata in attesa di Alex.');
      closeModal('modal-set-link');
      loadOrders();
      loadStats();
    } else {
      showToast(data.detail || 'Errore rimozione link', true);
    }
  } catch (err) {
    showToast('Errore di connessione', true);
  }
}

async function markOrderAsPurchased(orderId, productTitle) {
  try {
    const res = await fetch(`/api/orders/${orderId}/mark-purchased`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Acquisto registrato! Spostato in "Da Confermare".');
      loadOrders();
      loadStats();
      switchTab('confirmations');
    } else {
      showToast(data.detail || 'Errore registrazione acquisto', true);
    }
  } catch (err) {
    showToast('Errore di connessione', true);
  }
}

async function syncTelegramReplies(silent = false) {
  try {
    const res = await fetch('/api/telegram/sync-replies', { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.success) {
      if (data.updated_count > 0) {
        showToast(`🎉 Alex ti ha inviato il link Amazon! Pronta per l'acquisto.`);
        loadOrders();
        loadStats();
      } else if (!silent) {
        showToast(data.message || 'Risposte di Alex sincronizzate!');
      }
    } else if (!silent) {
      showToast(data.error || 'Nessun nuovo messaggio da Alex', true);
    }
  } catch (err) {
    if (!silent) console.error('Sync replies error:', err);
  }
}

function renderConfirmations(orders) {
  const container = document.getElementById('confirmations-list');
  const pendingOrders = (orders || []).filter(o => o.status === 'pending_confirmation');

  if (pendingOrders.length === 0) {
    container.innerHTML = `
      <div class="py-16 text-center text-slate-400 glass-card rounded-2xl p-8 border border-dashed border-slate-700">
        <div class="w-16 h-16 rounded-2xl bg-slate-800/80 mx-auto flex items-center justify-center text-3xl text-amber-400/80 mb-3 shadow-inner">
          <i class="fa-solid fa-camera"></i>
        </div>
        <h3 class="text-base font-bold text-white">Nessuna schermata ordine in attesa di conferma</h3>
        <p class="text-xs text-slate-300 mt-1 max-w-md mx-auto">Non appena invii una richiesta ad Alex, la scheda comparirà qui pronta per collegare la ricevuta dell'ordine fatto su Amazon.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = pendingOrders.map(o => {
    const prodImg = o.product_image || 'https://images.unsplash.com/photo-1532372320572-cda25653a26d?auto=format&fit=crop&w=800&q=80';
    const pricePaid = (o.price_paid != null ? Number(o.price_paid) : 0).toFixed(2);
    const screenUrl = o.confirmation_screen_url || '';
    const cleanOrderNum = (o.order_number || '').replace(/_old_\d+$/, '');
    const isRealOrderNumber = cleanOrderNum && !cleanOrderNum.toLowerCase().includes('in attesa') && !cleanOrderNum.toLowerCase().includes('pending');
    
    return `
      <div class="swipe-item-wrapper relative overflow-hidden rounded-2xl mb-4 select-none group" data-order-id="${o.id}" data-item-title="${escapeHtml(o.product_title || 'Articolo')}">
        <!-- Sfondo Rosso di Eliminazione visibile allo Swipe -->
        <div class="swipe-delete-bg absolute inset-0 bg-gradient-to-r from-red-700 to-rose-600 flex items-center justify-end px-5 rounded-2xl text-white font-extrabold text-xs shadow-inner cursor-pointer">
          <button onclick="confirmAndDeleteOrder(${o.id}, this.closest('.swipe-item-wrapper'))" class="flex items-center gap-2 bg-red-800/90 hover:bg-red-900 px-4 py-2.5 rounded-xl border border-red-400/50 shadow-lg text-white">
            <i class="fa-solid fa-trash-can text-sm"></i>
            <span>Elimina</span>
          </button>
        </div>

        <!-- Contenuto Card -->
        <div class="swipe-card-content glass-card rounded-2xl p-5 border-amber-500/40 flex flex-col lg:flex-row lg:items-center justify-between gap-5 shadow-lg relative z-10 bg-brand-surface border border-brand-border">
          <!-- Sinistra: Foto Prodotto + Dati Ordine -->
          <div class="flex items-start gap-4 flex-1">
            <!-- Thumbnail Prodotto Zoomabile -->
            <div onclick="openLightboxFromSrc('${prodImg}', '${escapeHtml(o.product_title || 'Prodotto')}', 'Numero Ordine: ${cleanOrderNum}')" class="cursor-pointer relative w-24 h-24 rounded-2xl overflow-hidden border border-slate-700 bg-slate-950 flex items-center justify-center shrink-0 group shadow-md" title="Clicca per zoomare la foto">
              <img src="${prodImg}" alt="Foto Prodotto" class="max-w-full max-h-full object-contain p-1 group-hover:scale-110 transition-transform">
              <div class="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-white text-xs">
                <i class="fa-solid fa-magnifying-glass-plus text-base"></i>
              </div>
              <span class="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/80 text-[10px] text-white font-bold">Foto</span>
            </div>

            <!-- Dettagli Ordine & Venditore -->
            <div class="flex-1">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-xs font-mono font-extrabold px-2.5 py-1 rounded-lg ${isRealOrderNumber ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'bg-slate-800 text-slate-400 border border-slate-700'} cursor-pointer" onclick="editOrderNumber(${o.id}, '${isRealOrderNumber ? escapeHtml(cleanOrderNum) : ''}')" title="Clicca per inserire o modificare il tuo vero numero d'ordine Amazon">
                  ${isRealOrderNumber ? cleanOrderNum : 'In attesa N° Ordine'}
                </span>
                <button onclick="editOrderNumber(${o.id}, '${isRealOrderNumber ? escapeHtml(cleanOrderNum) : ''}')" title="Modifica Numero Ordine Amazon" class="px-2 py-1 rounded-md bg-amber-500/10 hover:bg-amber-500/25 text-amber-300 text-xs font-semibold flex items-center gap-1 border border-amber-500/30">
                  <i class="fa-solid fa-pen-to-square text-[10px]"></i> ${isRealOrderNumber ? 'Modifica N°' : 'Inserisci N°'}
                </button>
                ${isRealOrderNumber ? `
                  <button onclick="copyToClipboard('${cleanOrderNum}', 'N° Ordine copiato!')" class="px-2 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1">
                    <i class="fa-regular fa-copy"></i> Copia N°
                  </button>
                ` : ''}
                <button onclick="event.stopPropagation(); confirmAndDeleteOrder(${o.id}, this.closest('.swipe-item-wrapper'))" title="Elimina pratica (o fai swipe a sinistra)" class="ml-auto text-slate-500 hover:text-red-400 p-1.5 rounded-lg hover:bg-red-500/10 transition-colors">
                  <i class="fa-solid fa-trash-can text-xs"></i>
                </button>
              </div>

              <h3 class="text-sm md:text-base font-extrabold text-white mt-2 leading-snug">${escapeHtml(o.product_title || 'Articolo in promozione')}</h3>
              
              <div class="mt-2 flex flex-wrap items-center gap-3 text-xs">
                <span class="text-slate-300 cursor-pointer hover:text-white" onclick="editOrderPrice(${o.id}, '${pricePaid}')" title="Clicca per modificare l'importo speso">
                  Spesa: <strong class="text-white font-bold underline decoration-dotted">€${pricePaid}</strong> ✏️
                </span>
                <span class="text-slate-500">•</span>
                <span class="text-emerald-400 font-bold">
                  Rimborso PayPal: €${(o.refund_amount !== undefined && o.refund_amount !== null ? o.refund_amount : o.price_paid || 0).toFixed(2)}
                </span>
              </div>
              ${o.delivery_info ? `
                <div class="mt-2 flex items-center gap-1.5 text-xs text-purple-300 font-semibold bg-purple-500/10 px-2.5 py-1 rounded-lg border border-purple-500/20 w-fit">
                  <i class="fa-solid fa-truck-fast text-purple-400"></i> Consegna stimata: <strong>${escapeHtml(o.delivery_info)}</strong> <span class="text-slate-400 font-normal">(+10gg per recensire)</span>
                </div>
              ` : ''}
            </div>
          </div>

          <!-- Destra: Azioni Tasto di Conferma & Anteprima Screen -->
          <div class="flex flex-wrap items-center gap-2 shrink-0 border-t lg:border-t-0 pt-3 lg:pt-0 border-brand-border">
            <button onclick="openIPhoneUploadModal(${o.id})" class="px-3.5 py-2.5 rounded-xl bg-gradient-to-r from-purple-600/30 to-indigo-600/30 hover:from-purple-600/50 hover:to-indigo-600/50 border border-purple-500/50 text-purple-200 text-xs font-bold flex items-center gap-1.5 shadow-md transition-all" title="Incolla dagli appunti iPhone, scegli da Rullino o carica file">
              <i class="fa-solid fa-mobile-screen-button text-purple-300"></i> Screen iPhone / Incolla
            </button>

            ${screenUrl ? `
              <button onclick="showScreenshot('${screenUrl}', '${o.order_number || ''}')" class="px-3 py-2.5 rounded-xl bg-brand-surface hover:bg-brand-card border border-brand-border text-slate-200 text-xs font-bold flex items-center gap-1.5 shadow-md">
                <i class="fa-solid fa-receipt text-amber-400"></i> Ricevuta
              </button>
            ` : `
              <button onclick="openIPhoneUploadModal(${o.id})" class="px-3 py-2.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs font-bold flex items-center gap-1.5 shadow-md">
                <i class="fa-solid fa-plus text-amber-400"></i> Aggiungi Screen
              </button>
            `}
            
            <button onclick="confirmAndSendOrder(${o.id})" class="px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white text-xs font-extrabold shadow-lg shadow-emerald-900/40 flex items-center gap-1.5 transition-all">
              <i class="fa-solid fa-paper-plane"></i> Conferma e Invia
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');

  initSwipeToDelete('confirmations-list');
}

function renderReviews(orders) {
  const container = document.getElementById('reviews-list');
  const reviewOrders = (orders || []).filter(o => ['waiting_review', 'review_ready', 'review_submitted', 'waiting_refund', 'reimbursed'].includes(o.status));

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
    const prodImg = o.product_image || 'https://images.unsplash.com/photo-1558317374-067fb5f30001?auto=format&fit=crop&w=800&q=80';
    
    // Rileva se il pacco è già stato consegnato (data stimata oggi o passata, oppure stato di consegna)
    const todayMidnight = new Date();
    todayMidnight.setHours(0,0,0,0);
    const estDeliveryMidnight = o.estimated_delivery_date ? new Date(o.estimated_delivery_date) : null;
    if (estDeliveryMidnight) estDeliveryMidnight.setHours(0,0,0,0);
    const isTodayOrPast = estDeliveryMidnight !== null && estDeliveryMidnight.getTime() <= todayMidnight.getTime();
    const isDelivered = (o.delivery_info === 'Consegnato' || isTodayOrPast || o.status === 'waiting_review');
    
    // Il punto di partenza dei 10 giorni esatti è la consegna
    const startIso = o.estimated_delivery_date || o.confirmation_sent_at || o.order_date || new Date().toISOString();
    let targetIso = o.review_target_date;
    if (!targetIso || isDelivered) {
      const baseStartMs = Math.min(Date.now(), new Date(startIso).getTime());
      targetIso = new Date(baseStartMs + 10 * 86400000).toISOString();
    }
    const isSubmitted = o.status === 'review_submitted' || o.status === 'reimbursed';

    return `
      <div class="swipe-item-wrapper relative overflow-hidden rounded-2xl mb-4 select-none group" data-order-id="${o.id}" data-item-title="${escapeHtml(o.product_title || 'Articolo')}">
        <!-- Sfondo Rosso di Eliminazione visibile allo Swipe -->
        <div class="swipe-delete-bg absolute inset-0 bg-gradient-to-r from-red-700 to-rose-600 flex items-center justify-end px-5 rounded-2xl text-white font-extrabold text-xs shadow-inner cursor-pointer">
          <button onclick="confirmAndDeleteOrder(${o.id}, this.closest('.swipe-item-wrapper'))" class="flex items-center gap-2 bg-red-800/90 hover:bg-red-900 px-4 py-2.5 rounded-xl border border-red-400/50 shadow-lg text-white">
            <i class="fa-solid fa-trash-can text-sm"></i>
            <span>Elimina</span>
          </button>
        </div>

        <!-- Contenuto Card Recensione -->
        <div class="swipe-card-content review-timer-card glass-card rounded-2xl p-5 flex flex-col justify-between space-y-4 shadow-lg relative z-10 bg-brand-surface border border-brand-border"
             data-review-order-id="${o.id}"
             data-target-date="${targetIso}"
             data-start-date="${startIso}"
             data-delivery-info="${isDelivered ? 'Consegnato' : escapeHtml(o.delivery_info || '')}"
             data-is-delivered="${isDelivered ? 'true' : 'false'}"
             data-status="${o.status}">
          <div>
            <!-- Header Card con Immagine & Timer Badge -->
            <div class="flex items-start justify-between gap-3">
              <div class="flex items-center gap-3">
                <div onclick="openLightboxFromSrc('${prodImg}', '${escapeHtml(o.product_title || 'Prodotto')}', 'Ordine: ${o.order_number || ''}')" class="cursor-pointer relative w-12 h-12 rounded-xl overflow-hidden border border-slate-700 bg-slate-950 flex items-center justify-center shrink-0 group">
                  <img src="${prodImg}" alt="Foto" class="max-w-full max-h-full object-contain p-0.5 group-hover:scale-110 transition-transform">
                  <div class="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 text-white text-[10px]">
                    <i class="fa-solid fa-magnifying-glass-plus"></i>
                  </div>
                </div>
                <div>
                  <span class="text-xs font-mono text-slate-400 font-bold">${((o.order_number || '').replace(/_old_\d+$/, '') && !o.order_number.toLowerCase().includes('in attesa') && !o.order_number.toLowerCase().includes('pending')) ? (o.order_number || '').replace(/_old_\d+$/, '') : ''}</span>
                  <h3 class="text-sm font-extrabold text-white line-clamp-1 mt-0.5">${escapeHtml(o.product_title || 'Prodotto')}</h3>
                </div>
              </div>
              
              <div class="flex items-center gap-2">
                <span class="review-badge text-xs font-extrabold px-2.5 py-1 rounded-lg shrink-0 ${isSubmitted ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40' : 'bg-purple-500/20 text-purple-300 border border-purple-500/40'}">
                  ${isSubmitted ? '✓ RECENSIONE PUBBLICATA' : 'Calcolo in corso...'}
                </span>
                <button onclick="event.stopPropagation(); confirmAndDeleteOrder(${o.id}, this.closest('.swipe-item-wrapper'))" title="Elimina recensione (o fai swipe a sinistra)" class="text-slate-500 hover:text-red-400 p-1.5 rounded-lg hover:bg-red-500/10 transition-colors">
                  <i class="fa-solid fa-trash-can text-xs"></i>
                </button>
              </div>
            </div>

            <!-- Barra di Progresso Timer con Data Consegna + 10 Giorni -->
            <div class="mt-4 p-3 rounded-xl bg-brand-bg border border-brand-border">
              <div class="flex items-center justify-between text-xs text-slate-300 mb-1.5 font-bold">
                <span class="flex items-center gap-1.5">
                  <i class="fa-solid fa-stopwatch text-purple-400 animate-pulse"></i> ${isDelivered ? 'Conto alla Rovescia (10gg dalla Consegna)' : 'Conto alla Rovescia (Arrivo ' + escapeHtml(o.delivery_info || 'Previsto') + ' + 10gg)'}
                </span>
                <span class="review-countdown-text font-extrabold text-purple-300 font-mono">
                  Calcolo...
                </span>
              </div>
              <div class="w-full h-2.5 bg-slate-900 rounded-full overflow-hidden border border-slate-700">
                <div class="review-progress-bar h-full bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-300" style="width: 10%"></div>
              </div>
              <div class="mt-1.5 flex items-center justify-between text-[11px] text-slate-400 flex-wrap gap-2">
                <span class="review-progress-pct font-bold">0% completato</span>
                <div class="flex items-center gap-3">
                  ${!isDelivered ? `
                    <button onclick="markOrderDelivered(${o.id})" title="Segna il pacco come consegnato oggi per iniziare subito i 10 giorni" class="text-[11px] text-emerald-400 hover:text-emerald-300 font-extrabold flex items-center gap-1 transition-colors">
                      <i class="fa-solid fa-box-open"></i> Pacco Arrivato Oggi
                    </button>
                  ` : `
                    <span class="text-[10px] text-emerald-400 font-bold flex items-center gap-1"><i class="fa-solid fa-circle-check"></i> Consegnato</span>
                  `}
                  <button onclick="resetOrderTimer(${o.id})" title="Reimposta il timer a 10 giorni esatti da adesso" class="text-[10px] text-slate-400 hover:text-slate-200 underline font-semibold transition-colors">
                    🔄 Reset Timer
                  </button>
                </div>
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
              <p class="text-xs font-extrabold text-white line-clamp-1">"${escapeHtml(o.review_title || 'Ottimo acquisto per questo articolo!')}"</p>
              <p class="text-xs text-slate-300 line-clamp-2 leading-relaxed font-medium">${escapeHtml(o.review_body || 'Recensione dettagliata pronta.')}</p>
            </div>
          </div>

          <!-- Bottoni Azione Recensione -->
          <div class="pt-3 border-t border-brand-border flex flex-wrap items-center gap-2">
            <!-- Tasto Visualizza Testo: sempre consultabile -->
            <button onclick="openReviewModal(${o.id})" class="flex-1 py-2.5 px-3 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/40 text-xs font-bold flex items-center justify-center gap-1.5 transition-all shadow-md">
              <i class="fa-solid fa-copy"></i> Testo Recensione
            </button>
            
            <!-- Tasto Screen iPhone: Sbloccato solo a scadenza raggiunta -->
            <button class="review-btn-screen py-2.5 px-3.5 rounded-xl bg-slate-800/50 border border-slate-700 text-slate-500 text-xs font-bold flex items-center gap-1.5 opacity-50 cursor-not-allowed"
                    onclick="openIPhoneUploadModal(${o.id}, 'review')"
                    disabled>
              <i class="fa-solid fa-lock text-[10px]"></i> Screen iPhone
            </button>
            
            <!-- Tasto Invia a Venditore: Sbloccato solo a scadenza raggiunta -->
            <button class="review-btn-send py-2.5 px-4 rounded-xl bg-slate-800/50 border border-slate-700 text-slate-500 text-xs font-bold flex items-center gap-1.5 opacity-50 cursor-not-allowed"
                    onclick="sendReviewToSeller(${o.id})"
                    disabled>
              <i class="fa-solid fa-lock text-[10px]"></i> Invia a Venditore
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');

  // Aggiorna subito i valori del timer e attiva swipe
  updateReviewLiveTimers();
  initSwipeToDelete('reviews-list');
}

// ----------------- REAL-TIME LIVE COUNTDOWN TIMER ENGINE -----------------

function updateReviewLiveTimers() {
  const cards = document.querySelectorAll('.review-timer-card');
  if (cards.length === 0) return;

  const now = Date.now();

  cards.forEach(card => {
    const targetIso = card.dataset.targetDate;
    const startIso = card.dataset.startDate;
    const status = card.dataset.status;
    const deliveryInfo = card.dataset.deliveryInfo;
    const isDelivered = card.dataset.isDelivered === 'true';

    let targetMs = targetIso ? new Date(targetIso).getTime() : now + 10 * 86400000;
    let startMs = startIso ? new Date(startIso).getTime() : targetMs - 10 * 86400000;

    // Se l'articolo è già CONSEGNATO (o è arrivato oggi), il punto di inizio è il momento della consegna
    // e il tempo rimanente parte da un massimo di 10 giorni esatti (quindi oggi sarà 9 giorni e 23h...)
    if (isDelivered) {
      if (startMs > now) {
        startMs = now - 3600000; // Consegnato oggi
      }
      targetMs = startMs + 10 * 86400000;
      if (targetMs > now + 10 * 86400000) {
        targetMs = now + 10 * 86400000 - 3600000;
      }
    }

    const totalDurationMs = 10 * 86400000; // 10 giorni = 240 ore
    const totalDays = 10; // Il conto alla rovescia è sempre e rigorosamente di 10 giorni

    const diffMs = targetMs - now;
    const elapsedMs = Math.max(0, now - startMs);

    const badgeEl = card.querySelector('.review-badge');
    const countdownEl = card.querySelector('.review-countdown-text');
    const progressBarEl = card.querySelector('.review-progress-bar');
    const progressPctEl = card.querySelector('.review-progress-pct');
    const btnScreen = card.querySelector('.review-btn-screen');
    const btnSend = card.querySelector('.review-btn-send');

    const isSubmitted = status === 'review_submitted' || status === 'reimbursed';
    const isReady = diffMs <= 0 || status === 'review_ready' || isSubmitted;

    if (isSubmitted) {
      if (badgeEl) {
        badgeEl.className = 'review-badge text-xs font-extrabold px-2.5 py-1 rounded-lg shrink-0 bg-blue-500/20 text-blue-300 border border-blue-500/40';
        badgeEl.innerText = '✓ RECENSIONE INVIATA';
      }
      if (countdownEl) {
        countdownEl.className = 'review-countdown-text font-extrabold text-blue-400';
        countdownEl.innerText = 'Inviata al venditore';
      }
      if (progressBarEl) {
        progressBarEl.className = 'review-progress-bar h-full bg-blue-500';
        progressBarEl.style.width = '100%';
      }
      if (progressPctEl) progressPctEl.innerText = '100% completato';

      if (btnScreen) {
        btnScreen.disabled = false;
        btnScreen.className = 'review-btn-screen py-2.5 px-3.5 rounded-xl bg-purple-600/30 text-purple-300 border border-purple-500/40 text-xs font-bold flex items-center gap-1.5 cursor-pointer';
        btnScreen.innerHTML = '<i class="fa-solid fa-image"></i> Screen Recensione';
      }
      if (btnSend) {
        btnSend.disabled = true;
        btnSend.className = 'review-btn-send py-2.5 px-4 rounded-xl bg-blue-600/20 text-blue-300 border border-blue-500/40 text-xs font-bold flex items-center gap-1.5 cursor-default';
        btnSend.innerHTML = '<i class="fa-solid fa-check"></i> Inviata';
      }
      return;
    }

    if (isReady) {
      if (badgeEl) {
        badgeEl.className = 'review-badge text-xs font-extrabold px-2.5 py-1 rounded-lg shrink-0 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 animate-pulse';
        badgeEl.innerText = '⭐ RECENSIONE PRONTA!';
      }
      if (countdownEl) {
        countdownEl.className = 'review-countdown-text font-extrabold text-emerald-400';
        countdownEl.innerText = 'Scadenza raggiunta: pubblica ora!';
      }
      if (progressBarEl) {
        progressBarEl.className = 'review-progress-bar h-full bg-emerald-500 transition-all duration-300';
        progressBarEl.style.width = '100%';
      }
      if (progressPctEl) progressPctEl.innerText = `100% (10 giorni trascorsi)`;

      if (btnScreen) {
        btnScreen.disabled = false;
        btnScreen.className = 'review-btn-screen py-2.5 px-3.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 border border-purple-400 text-white text-xs font-extrabold flex items-center gap-1.5 shadow-md shadow-purple-900/30 transition-all animate-pulse cursor-pointer';
        btnScreen.innerHTML = '<i class="fa-solid fa-mobile-screen-button"></i> Screen iPhone / Incolla';
      }
      if (btnSend) {
        btnSend.disabled = false;
        btnSend.className = 'review-btn-send py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white border border-emerald-400 text-xs font-extrabold flex items-center gap-1.5 transition-all shadow-lg shadow-emerald-900/40 cursor-pointer';
        btnSend.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Invia a Venditore';
      }
    } else {
      const totalSec = Math.floor(diffMs / 1000);
      const days = Math.floor(totalSec / 86400);
      const hours = Math.floor((totalSec % 86400) / 3600);
      const minutes = Math.floor((totalSec % 3600) / 60);
      const seconds = totalSec % 60;

      const currentDay = Math.min(10, Math.max(1, Math.floor(elapsedMs / 86400000) + 1));
      const progressPct = Math.min(99.9, Math.max(2, (elapsedMs / totalDurationMs) * 100)).toFixed(1);

      if (badgeEl) {
        badgeEl.className = 'review-badge text-xs font-extrabold px-2.5 py-1 rounded-lg shrink-0 bg-purple-500/20 text-purple-300 border border-purple-500/40';
        badgeEl.innerText = `Giorno ${currentDay}/10`;
      }
      if (countdownEl) {
        countdownEl.className = 'review-countdown-text font-extrabold text-purple-300 font-mono tracking-tight';
        countdownEl.innerText = `${days}g ${String(hours).padStart(2, '0')}h ${String(minutes).padStart(2, '0')}m ${String(seconds).padStart(2, '0')}s`;
      }
      if (progressBarEl) {
        progressBarEl.className = 'review-progress-bar h-full bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-300';
        progressBarEl.style.width = `${progressPct}%`;
      }
      if (progressPctEl) {
        const delivNote = isDelivered ? ' • 📦 Consegnato' : (deliveryInfo && deliveryInfo !== 'Consegnato' ? ` • 🚚 Arrivo: ${deliveryInfo}` : ' • 📦 Consegnato');
        progressPctEl.innerText = `${progressPct}% trascorso (${days} giorni e ${hours}h rimasti${delivNote})`;
      }

      if (btnScreen) {
        btnScreen.disabled = true;
        btnScreen.className = 'review-btn-screen py-2.5 px-3.5 rounded-xl bg-slate-800/50 border border-slate-700 text-slate-500 text-xs font-bold flex items-center gap-1.5 opacity-50 cursor-not-allowed';
        btnScreen.innerHTML = `<i class="fa-solid fa-lock text-[10px]"></i> Screen (Giorno ${currentDay}/10)`;
      }
      if (btnSend) {
        btnSend.disabled = true;
        btnSend.className = 'review-btn-send py-2.5 px-4 rounded-xl bg-slate-800/50 border border-slate-700 text-slate-500 text-xs font-bold flex items-center gap-1.5 opacity-50 cursor-not-allowed';
        btnSend.innerHTML = '<i class="fa-solid fa-lock text-[10px]"></i> Invia a Venditore';
      }
    }
  });
}

async function fastForwardOrderTimer(orderId) {
  try {
    const res = await fetch(`/api/orders/${orderId}/fast-forward-timer`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || 'Timer avanzato! Recensione pronta.');
      loadOrders();
    }
  } catch (err) {
    showToast('Errore durante l\'avanzamento timer', true);
  }
}

async function markOrderDelivered(orderId) {
  try {
    const res = await fetch(`/api/orders/${orderId}/mark-delivered`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || 'Pacco segnato come Consegnato! I 10 giorni partono da oggi.');
      loadOrders();
    }
  } catch (err) {
    showToast('Errore durante l\'aggiornamento consegna', true);
  }
}

async function resetOrderTimer(orderId) {
  try {
    const res = await fetch(`/api/orders/${orderId}/reset-timer`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || 'Timer reimpostato a 10 giorni!');
      loadOrders();
    }
  } catch (err) {
    showToast('Errore durante il reset timer', true);
  }
}

function renderRefunds(orders) {
  const container = document.getElementById('refunds-list');
  const eligibleOrders = (orders || []).filter(o => ['waiting_review', 'review_ready', 'review_submitted', 'waiting_refund', 'reimbursed'].includes(o.status));

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
    const refundAmt = (o.refund_amount != null ? Number(o.refund_amount) : 0).toFixed(2);

    return `
      <div class="swipe-item-wrapper relative overflow-hidden rounded-2xl mb-4 select-none group" data-order-id="${o.id}" data-item-title="${escapeHtml(o.product_title || 'Articolo')}">
        <!-- Sfondo Rosso di Eliminazione visibile allo Swipe -->
        <div class="swipe-delete-bg absolute inset-0 bg-gradient-to-r from-red-700 to-rose-600 flex items-center justify-end px-5 rounded-2xl text-white font-extrabold text-xs shadow-inner cursor-pointer">
          <button onclick="confirmAndDeleteOrder(${o.id}, this.closest('.swipe-item-wrapper'))" class="flex items-center gap-2 bg-red-800/90 hover:bg-red-900 px-4 py-2.5 rounded-xl border border-red-400/50 shadow-lg text-white">
            <i class="fa-solid fa-trash-can text-sm"></i>
            <span>Elimina</span>
          </button>
        </div>

        <!-- Contenuto Card Rimborso -->
        <div class="swipe-card-content glass-card rounded-2xl p-4 md:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-lg border relative z-10 bg-brand-surface ${isReimbursed ? 'border-emerald-500/30' : 'border-blue-500/30'}">
          <div class="flex items-center gap-4">
            <!-- Thumbnail Prodotto Zoomabile -->
            <div onclick="openLightboxFromSrc('${prodImg}', '${escapeHtml(o.product_title || 'Prodotto')}', 'Rimborso €${refundAmt}')" class="cursor-pointer relative w-14 h-14 rounded-xl overflow-hidden border border-slate-700 bg-slate-900 shrink-0 group">
              <img src="${prodImg}" alt="Foto" class="w-full h-full object-cover group-hover:scale-110 transition-transform">
              <div class="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 text-white text-xs">
                <i class="fa-solid fa-magnifying-glass-plus"></i>
              </div>
            </div>

            <div>
              <div class="flex items-center gap-2">
                <span class="text-xs font-mono text-slate-300 font-bold">${(o.order_number && !o.order_number.toLowerCase().includes('in attesa') && !o.order_number.toLowerCase().includes('pending')) ? o.order_number : ''}</span>
                <span class="text-[11px] px-2.5 py-0.5 rounded-md ${isReimbursed ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'} font-extrabold uppercase">
                  ${isReimbursed ? '✓ Rimborso Saldato' : (o.status === 'review_submitted' ? '⏳ In Attesa PayPal' : '⏳ In Attesa di Recensione')}
                </span>
                <button onclick="event.stopPropagation(); confirmAndDeleteOrder(${o.id}, this.closest('.swipe-item-wrapper'))" title="Elimina rimborso (o fai swipe a sinistra)" class="ml-2 text-slate-500 hover:text-red-400 p-1.5 rounded-lg hover:bg-red-500/10 transition-colors">
                  <i class="fa-solid fa-trash-can text-xs"></i>
                </button>
              </div>
              <p class="text-sm font-extrabold text-white mt-1">${escapeHtml(o.product_title || 'Prodotto')}</p>
            </div>
          </div>

          <div class="flex items-center justify-between md:justify-end gap-5 shrink-0 border-t md:border-t-0 pt-3 md:pt-0 border-brand-border">
            <div class="text-right cursor-pointer group" onclick="editOrderPrice(${o.id}, '${refundAmt}')" title="Clicca per modificare l'importo rimborso">
              <p class="text-xs font-bold text-slate-400 uppercase flex items-center justify-end gap-1">
                Importo Rimborso <i class="fa-solid fa-pen text-[10px] text-amber-400"></i>
              </p>
              <p class="text-xl font-extrabold ${isReimbursed ? 'text-emerald-400' : 'text-amber-300'} underline decoration-dotted">€${refundAmt}</p>
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
      </div>
    `;
  }).join('');

  initSwipeToDelete('refunds-list');
}

// ----------------- SWIPE-TO-DELETE GESTURE ENGINE (iOS & PC) -----------------

function initSwipeToDelete(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const wrappers = container.querySelectorAll('.swipe-item-wrapper');
  wrappers.forEach(wrapper => {
    if (wrapper._swipeInitialized) return;
    wrapper._swipeInitialized = true;

    const content = wrapper.querySelector('.swipe-card-content');
    if (!content) return;

    let startX = 0;
    let startY = 0;
    let currentX = 0;
    let isTracking = false;
    let isHorizontalSwipe = false;

    function onTouchStart(e) {
      if (e.target.closest('button') || e.target.closest('input') || e.target.closest('a')) {
        return;
      }
      const touch = e.touches ? e.touches[0] : e;
      startX = touch.clientX;
      startY = touch.clientY;
      currentX = 0;
      isTracking = true;
      isHorizontalSwipe = false;
      content.style.transition = 'none';
    }

    function onTouchMove(e) {
      if (!isTracking) return;
      const touch = e.touches ? e.touches[0] : e;
      const diffX = touch.clientX - startX;
      const diffY = touch.clientY - startY;

      if (!isHorizontalSwipe) {
        if (Math.abs(diffX) > 10 && Math.abs(diffX) > Math.abs(diffY)) {
          isHorizontalSwipe = true;
        } else if (Math.abs(diffY) > 10) {
          isTracking = false;
          return;
        }
      }

      if (isHorizontalSwipe) {
        if (e.cancelable && e.preventDefault) e.preventDefault();
        
        if (diffX < 0) {
          if (diffX < -120) {
            currentX = -120 + (diffX + 120) * 0.2;
          } else {
            currentX = diffX;
          }
          content.style.transform = `translateX(${currentX}px)`;
        } else {
          currentX = Math.min(diffX * 0.2, 20);
          content.style.transform = `translateX(${currentX}px)`;
        }
      }
    }

    function onTouchEnd() {
      if (!isTracking) return;
      isTracking = false;
      content.style.transition = 'transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1)';
      
      if (currentX < -65) {
        content.style.transform = 'translateX(-100px)';
      } else {
        content.style.transform = 'translateX(0px)';
      }
    }

    content.addEventListener('touchstart', onTouchStart, { passive: true });
    content.addEventListener('touchmove', onTouchMove, { passive: false });
    content.addEventListener('touchend', onTouchEnd);
    content.addEventListener('touchcancel', onTouchEnd);

    // Supporto trascinamento mouse per PC
    content.addEventListener('mousedown', onTouchStart);
    window.addEventListener('mousemove', (e) => { if (isTracking) onTouchMove(e); });
    window.addEventListener('mouseup', () => { if (isTracking) onTouchEnd(); });
  });
}

async function confirmAndDeleteOrder(orderId, wrapperElement) {
  if (!confirm('Vuoi davvero eliminare definitivamente questa pratica?')) {
    if (wrapperElement) {
      const content = wrapperElement.querySelector('.swipe-card-content');
      if (content) content.style.transform = 'translateX(0px)';
    }
    return;
  }

  // Animazione immediata di uscita
  if (wrapperElement) {
    wrapperElement.style.transition = 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)';
    wrapperElement.style.transform = 'translateX(-100%)';
    wrapperElement.style.opacity = '0';
    wrapperElement.style.maxHeight = wrapperElement.offsetHeight + 'px';
    setTimeout(() => {
      try { wrapperElement.remove(); } catch(e) {}
    }, 200);
  }

  try {
    const res = await fetch(`/api/orders/${orderId}`, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) {
      // Rimuovi l'ordine anche dal backup del browser
      try {
        const localBackupStr = localStorage.getItem('amz_shielded_orders');
        if (localBackupStr) {
          const arr = JSON.parse(localBackupStr) || [];
          const updated = arr.filter(x => x.id !== orderId);
          localStorage.setItem('amz_shielded_orders', JSON.stringify(updated));
        }
      } catch(e) {}
      showToast(data.message || 'Pratica eliminata definitivamente!');
    } else {
      showToast(data.detail || 'Errore durante l\'eliminazione', true);
    }
  } catch (err) {
    showToast('Errore di connessione durante l\'eliminazione', true);
  } finally {
    loadOrders();
    loadStats();
    loadLogs();
  }
}

async function clearAllReviews() {
  if (!confirm('Vuoi davvero cancellare tutte le recensioni attive?')) return;
  try {
    const res = await fetch('/api/orders?status=reviews', { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) {
      showToast('Tutte le recensioni sono state eliminate!');
      loadOrders();
      loadStats();
      loadLogs();
    } else {
      showToast(data.detail || 'Errore durante l\'eliminazione', true);
    }
  } catch (err) {
    showToast('Errore di connessione', true);
  }
}

async function clearAllRefunds() {
  if (!confirm('Vuoi davvero cancellare tutti i rimborsi PayPal registrati?')) return;
  try {
    const res = await fetch('/api/orders?status=refunds', { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) {
      showToast('Tutti i rimborsi sono stati eliminati!');
      loadOrders();
      loadStats();
      loadLogs();
    } else {
      showToast(data.detail || 'Errore durante l\'eliminazione', true);
    }
  } catch (err) {
    showToast('Errore di connessione', true);
  }
}

// ----------------- LOGS RENDERING & SWIPE-TO-DELETE -----------------

async function loadLogs() {
  try {
    const res = await fetch('/api/logs');
    if (!res.ok) return;
    const logs = await res.json();
    const container = document.getElementById('logs-container');

    if (logs.length === 0) {
      container.innerHTML = `
        <div class="py-12 text-center text-slate-400 glass-card rounded-2xl p-6 border border-dashed border-slate-700">
          <i class="fa-solid fa-list-check text-2xl text-slate-500 mb-2"></i>
          <p class="text-xs font-bold text-white">Nessuna attività registrata nel registro.</p>
          <p class="text-[11px] text-slate-400 mt-0.5">Le operazioni eseguite verranno tracciate qui in automatico.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = logs.map(l => `
      <div class="swipe-item-wrapper relative overflow-hidden rounded-xl select-none group" data-log-id="${l.id}">
        <!-- Sfondo Rosso di Eliminazione visibile allo Swipe -->
        <div class="swipe-delete-bg absolute inset-0 bg-gradient-to-r from-red-700 to-rose-600 flex items-center justify-end px-4 rounded-xl text-white font-extrabold text-xs shadow-inner cursor-pointer">
          <button onclick="confirmAndDeleteLog(${l.id}, this.closest('.swipe-item-wrapper'))" class="flex items-center gap-1.5 bg-red-800/90 hover:bg-red-900 px-3 py-2 rounded-lg border border-red-400/50 shadow-md text-white text-xs font-bold">
            <i class="fa-solid fa-trash-can"></i>
            <span>Elimina</span>
          </button>
        </div>

        <!-- Contenuto Log Card -->
        <div class="swipe-card-content p-3 rounded-xl bg-brand-surface border border-brand-border flex items-start justify-between gap-3 text-xs relative z-10">
          <div class="space-y-0.5 flex-1">
            <div class="flex items-center gap-2">
              <span class="font-bold text-white">${escapeHtml(l.title)}</span>
              <span class="text-[10px] px-2 py-0.5 rounded bg-brand-bg text-slate-300 font-mono border border-slate-700/50">${escapeHtml(l.action_type)}</span>
            </div>
            <p class="text-slate-300 text-[11px] leading-relaxed">${escapeHtml(l.details || '')}</p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <span class="text-[10px] text-slate-400 font-mono">${formatDate(l.timestamp || l.created_at)}</span>
            <button onclick="event.stopPropagation(); confirmAndDeleteLog(${l.id}, this.closest('.swipe-item-wrapper'))" title="Elimina questa voce" class="text-slate-500 hover:text-red-400 p-1 rounded hover:bg-red-500/10 transition-colors">
              <i class="fa-solid fa-trash-can text-xs"></i>
            </button>
          </div>
        </div>
      </div>
    `).join('');

    initSwipeToDelete('logs-container');
  } catch (err) {
    console.error('Errore caricamento log:', err);
  }
}

async function confirmAndDeleteLog(logId, wrapperElement) {
  if (wrapperElement) {
    wrapperElement.style.transition = 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)';
    wrapperElement.style.transform = 'translateX(-100%)';
    wrapperElement.style.opacity = '0';
    wrapperElement.style.maxHeight = wrapperElement.offsetHeight + 'px';
    setTimeout(() => {
      try { wrapperElement.remove(); } catch(e) {}
    }, 150);
  }

  try {
    const res = await fetch(`/api/logs/${logId}`, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) {
      showToast('Voce eliminata dal registro');
      setTimeout(() => loadLogs(), 300);
    } else {
      showToast(data.detail || 'Errore durante l\'eliminazione', true);
      loadLogs();
    }
  } catch (err) {
    showToast('Errore di connessione', true);
    loadLogs();
  }
}

async function confirmAndClearAllLogs() {
  if (!confirm('Vuoi davvero svuotare completamente tutto il registro attività?')) {
    return;
  }

  try {
    const res = await fetch('/api/logs', { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || 'Registro attività svuotato con successo!');
      loadLogs();
    } else {
      showToast(data.detail || 'Errore durante lo svuotamento', true);
    }
  } catch (err) {
    showToast('Errore di connessione', true);
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

async function editOrderNumber(orderId, currentNum) {
  const newNum = prompt('Inserisci il tuo vero Numero Ordine Amazon (es. 408-1234567-8901234):', currentNum || '');
  if (newNum === null) return;
  const clean = newNum.trim();
  if (!clean) {
    showToast('Numero ordine non valido', true);
    return;
  }

  try {
    const res = await fetch(`/api/orders/${orderId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order_number: clean })
    });
    let data = {};
    try { data = await res.json(); } catch(e) {}
    if (res.ok) {
      showToast('Numero ordine Amazon aggiornato!');
      loadOrders();
    } else {
      showToast(data.detail || 'Errore durante l\'aggiornamento', true);
    }
  } catch (err) {
    showToast('Errore di connessione o server in riavvio. Riprova tra qualche istante.', true);
  }
}

async function editOrderPrice(orderId, currentPrice) {
  const enteredPrice = prompt('Inserisci l\'importo reale pagato su Amazon / da rimborsare (€):', currentPrice || '0.00');
  if (enteredPrice === null) return;
  const cleanPrice = parseFloat(enteredPrice.replace(',', '.').trim());
  if (isNaN(cleanPrice) || cleanPrice < 0) {
    showToast('Importo non valido', true);
    return;
  }

  try {
    const res = await fetch(`/api/orders/${orderId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ price_paid: cleanPrice })
    });
    let data = {};
    try { data = await res.json(); } catch(e) {}
    if (res.ok) {
      const refAmt = (data.refund_amount !== undefined && data.refund_amount !== null) ? data.refund_amount.toFixed(2) : cleanPrice.toFixed(2);
      showToast(`Spesa: €${cleanPrice.toFixed(2)} (Rimborso PayPal: €${refAmt})`);
      loadOrders();
      loadStats();
    } else {
      showToast(data.detail || 'Errore durante l\'aggiornamento dell\'importo', true);
    }
  } catch (err) {
    showToast('Errore di connessione', true);
  }
}

async function requestOffer(offerId) {
  try {
    const res = await fetch(`/api/offers/${offerId}/request`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast('Richiesta inviata ad Alex! Apertura sezione "Da Comprare"...');
      loadOffers();
      loadOrders();
      loadStats();
      switchTab('approved_links');
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
  // 1. Controlla se la scheda ha un numero d'ordine reale
  const wrapper = document.querySelector(`.swipe-item-wrapper[data-order-id="${orderId}"]`);
  let orderNumberBadge = wrapper ? wrapper.querySelector('.font-mono') : null;
  let currentNum = orderNumberBadge ? orderNumberBadge.innerText.trim() : '';

  if (!currentNum || currentNum.toLowerCase().includes('in attesa')) {
    const enteredNum = prompt('⚠️ Tassativo: Inserisci il tuo Numero d\'Ordine Amazon reale (es. 404-1867984-8717122):');
    if (enteredNum === null) return; // Annullato dall'utente
    const cleanNum = enteredNum.trim();
    if (!cleanNum) {
      showToast('❌ Invio annullato: Devi inserire il Numero d\'Ordine Amazon reale!', true);
      return;
    }

    // Salva il numero d'ordine prima di procedere
    try {
      const saveRes = await fetch(`/api/orders/${orderId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_number: cleanNum })
      });
      let saveData = {};
      try { saveData = await saveRes.json(); } catch(e) {}
      if (!saveRes.ok) {
        showToast(saveData.detail || 'Errore nel salvataggio del numero ordine', true);
        return;
      }
    } catch (e) {
      showToast('Errore di connessione durante il salvataggio. Riprova tra qualche istante.', true);
      return;
    }
  }

  // 2. Controlla se l'importo di spesa è a 0 o mancante
  let pricePaid = 0;
  if (wrapper) {
    const priceEl = wrapper.querySelector('strong');
    if (priceEl) {
      const priceText = priceEl.innerText.replace('€', '').trim();
      pricePaid = parseFloat(priceText.replace(',', '.')) || 0;
    }
  }

  if (pricePaid <= 0) {
    const enteredPrice = prompt('⚠️ Tassativo: Inserisci l\'importo di acquisto pagato su Amazon (€):');
    if (enteredPrice === null) return; // Annullato dall'utente
    const cleanPrice = parseFloat(enteredPrice.replace(',', '.').trim());
    if (isNaN(cleanPrice) || cleanPrice <= 0) {
      showToast('❌ Invio bloccato: Inserisci l\'importo speso su Amazon!', true);
      return;
    }

    // Salva l'importo prima di procedere
    try {
      const savePriceRes = await fetch(`/api/orders/${orderId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ price_paid: cleanPrice })
      });
      let savePriceData = {};
      try { savePriceData = await savePriceRes.json(); } catch(e) {}
      if (!savePriceRes.ok) {
        showToast(savePriceData.detail || 'Errore nel salvataggio dell\'importo', true);
        return;
      }
    } catch (e) {
      showToast('Errore di connessione durante il salvataggio del prezzo.', true);
      return;
    }
  }

  try {
    const res = await fetch(`/api/orders/${orderId}/confirm-and-send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    let data = {};
    try { data = await res.json(); } catch(e) {}
    if (res.ok) {
      showToast(data.message || 'Screenshot e Numero Ordine inviati ai tuoi Messaggi Salvati!');
      loadOrders();
      loadStats();
    } else {
      showToast(data.detail || "Errore durante l'invio", true);
    }
  } catch (err) {
    showToast('Errore di connessione. Riprova tra qualche istante.', true);
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

      showToast('📤 Caricamento screenshot in corso...');
      const reader = new FileReader();
      reader.onload = async (event) => {
        const base64 = event.target.result;
        try {
          const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_base64: base64 })
          });
          let data = {};
          try { data = await res.json(); } catch(e) {}
          if (res.ok) {
            closeModal('modal-iphone-upload');
            loadOrders();
            loadStats();

            const isRealOrderNum = data.order_number && !data.order_number.toLowerCase().includes('in attesa') && !data.order_number.toLowerCase().includes('pending');
            if (!isRealOrderNum && currentUploadType !== 'review') {
              const enteredNum = prompt('✅ Screenshot collegato!\nInserisci il numero d\'ordine Amazon (es. 404-1867984-8717122):');
              if (enteredNum && enteredNum.trim()) {
                await fetch(`/api/orders/${currentUploadOrderId}`, {
                  method: 'PUT',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ order_number: enteredNum.trim() })
                });
                loadOrders();
                showToast(`N° Ordine ${enteredNum.trim()} impostato con successo!`);
              } else {
                showToast('Screenshot salvato! Puoi inserire il N° Ordine in qualsiasi momento cliccando "Inserisci N°"');
              }
            } else {
              showToast(data.message || '📦 Screenshot caricato con successo!');
            }
          } else {
            showToast(data.detail || 'Errore nel caricamento dello screenshot', true);
          }
        } catch (err) {
          showToast('Errore di connessione durante l\'upload', true);
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

      showToast('📤 Caricamento foto in corso...');
      const reader = new FileReader();
      reader.onload = async (event) => {
        const base64 = event.target.result;
        try {
          const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_base64: base64 })
          });
          let data = {};
          try { data = await res.json(); } catch(e) {}
          if (res.ok) {
            closeModal('modal-iphone-upload');
            loadOrders();
            loadStats();

            const isRealOrderNum = data.order_number && !data.order_number.toLowerCase().includes('in attesa') && !data.order_number.toLowerCase().includes('pending');
            if (!isRealOrderNum && currentUploadType !== 'review') {
              const enteredNum = prompt('✅ Foto collegata!\nInserisci il numero d\'ordine Amazon (es. 404-1867984-8717122):');
              if (enteredNum && enteredNum.trim()) {
                await fetch(`/api/orders/${currentUploadOrderId}`, {
                  method: 'PUT',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ order_number: enteredNum.trim() })
                });
                loadOrders();
                showToast(`N° Ordine ${enteredNum.trim()} impostato!`);
              } else {
                showToast('Foto salvata!');
              }
            } else {
              showToast(data.message || '📷 Foto salvata con successo!');
            }
          } else {
            showToast(data.detail || 'Errore nel salvataggio della foto', true);
          }
        } catch (err) {
          showToast('Errore di connessione', true);
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
            let data = {};
            try { data = await res.json(); } catch(e) {}
            if (res.ok) {
              loadOrders();
              loadStats();
              const isRealOrderNum = data.order_number && !data.order_number.toLowerCase().includes('in attesa') && !data.order_number.toLowerCase().includes('pending');
              if (!isRealOrderNum) {
                const enteredNum = prompt('📋 Screenshot incollato!\nInserisci il numero d\'ordine Amazon (es. 404-1867984-8717122):');
                if (enteredNum && enteredNum.trim()) {
                  await fetch(`/api/orders/${targetOrder.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ order_number: enteredNum.trim() })
                  });
                  loadOrders();
                  showToast(`N° Ordine ${enteredNum.trim()} impostato con successo!`);
                } else {
                  showToast('Screenshot salvato!');
                }
              } else {
                showToast(data.message || `📋 Screenshot incollato con successo all'ordine!`);
              }
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
  loadSettings();
  document.getElementById('modal-settings').classList.remove('hidden');
}

async function toggleSandboxDirect(isChecked) {
  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify([{ key: 'test_mode', value: isChecked ? 'true' : 'false' }])
    });
    if (res.ok) {
      updateSandboxBadge(isChecked);
      const chk = document.getElementById('set_test_mode');
      if (chk) chk.checked = isChecked;
      if (isChecked) {
        showToast('🧪 Modalità SANDBOX Attiva (Zero messaggi reali ad Alex)');
      } else {
        showToast('🟢 Modalità LIVE Attiva (Messaggi reali)');
      }
    }
  } catch (err) {
    showToast('Errore durante il cambio modalità', true);
  }
}

async function toggleSandboxQuick() {
  try {
    const res = await fetch('/api/settings');
    if (!res.ok) return;
    const s = await res.json();
    const currentIsTest = s.test_mode === 'true';
    const newIsTest = !currentIsTest;

    const postRes = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify([{ key: 'test_mode', value: newIsTest ? 'true' : 'false' }])
    });

    if (postRes.ok) {
      updateSandboxBadge(newIsTest);
      const chk = document.getElementById('set_test_mode');
      if (chk) chk.checked = newIsTest;
      if (newIsTest) {
        showToast('🧪 Modalità Sandbox ATTIVA: nessun messaggio verrà inviato ad Alex!');
      } else {
        showToast('🟢 Modalità LIVE ATTIVA: i messaggi verranno inviati realmente ad Alex!');
      }
    }
  } catch (err) {
    showToast('Errore durante il cambio modalità', true);
  }
}

function openModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.remove('hidden');
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

async function loadTelegramStatus() {
  try {
    const res = await fetch('/api/telegram/status');
    if (!res.ok) return;
    const data = await res.json();

    const topBadge = document.getElementById('telegram-connection-status-badge');
    const topDesc = document.getElementById('telegram-channel-status-desc');
    const setTag = document.getElementById('set-tg-status-tag');
    const setConnectedBox = document.getElementById('set-tg-connected-box');
    const setLoginBox = document.getElementById('set-tg-login-box');
    const setUserName = document.getElementById('set-tg-user-name');
    const setUserPhone = document.getElementById('set-tg-user-phone');

    // Modal Status elements
    const modalDot = document.getElementById('tg-auth-status-dot');
    const modalText = document.getElementById('tg-auth-status-text');
    const modalDisconnectBtn = document.getElementById('tg-btn-disconnect');
    const modalPhoneStep = document.getElementById('tg-step-phone');
    const modalCodeStep = document.getElementById('tg-step-code');

    if (data.is_authorized) {
      const u = data.user || {};
      const displayName = u.first_name || u.username || 'Account Telegram';
      const handle = u.username ? `(${u.username})` : (u.phone ? `(${u.phone})` : '');

      if (topBadge) {
        topBadge.className = 'text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1';
        topBadge.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Connesso';
      }
      if (topDesc) {
        topDesc.innerText = `Connesso come ${displayName} ${handle} • Canale sincronizzato.`;
      }
      if (setTag) {
        setTag.className = 'text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
        setTag.innerText = '🟢 Connesso';
      }
      if (setConnectedBox) {
        setConnectedBox.classList.remove('hidden');
        if (setUserName) setUserName.innerText = `Connesso come: ${displayName}`;
        if (setUserPhone) setUserPhone.innerText = `${u.phone || ''} ${u.username || ''}`;
      }
      if (setLoginBox) setLoginBox.classList.add('hidden');

      if (modalDot) modalDot.className = 'w-2.5 h-2.5 rounded-full bg-emerald-400';
      if (modalText) modalText.innerText = `Connesso come ${displayName} ${handle}`;
      if (modalDisconnectBtn) modalDisconnectBtn.classList.remove('hidden');
      if (modalPhoneStep) modalPhoneStep.classList.add('hidden');
      if (modalCodeStep) modalCodeStep.classList.add('hidden');

      const sessionBox = document.getElementById('tg-session-string-box');
      if (data.session_string) {
        window._tg_session_string = data.session_string;
        if (sessionBox) sessionBox.classList.remove('hidden');
      } else {
        if (sessionBox) sessionBox.classList.add('hidden');
      }

    } else {
      if (topBadge) {
        topBadge.className = 'text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1';
        topBadge.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span> Login Richiesto';
      }
      if (topDesc) {
        topDesc.innerText = 'Collega il tuo account Telegram per scaricare automaticamente le offerte con foto HD.';
      }
      if (setTag) {
        setTag.className = 'text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700';
        setTag.innerText = 'Non Connesso';
      }
      if (setConnectedBox) setConnectedBox.classList.add('hidden');
      if (setLoginBox) setLoginBox.classList.remove('hidden');

      if (modalDot) modalDot.className = 'w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse';
      if (modalText) modalText.innerText = 'Nessun account Telegram collegato';
      if (modalDisconnectBtn) modalDisconnectBtn.classList.add('hidden');
      if (modalPhoneStep) modalPhoneStep.classList.remove('hidden');
      if (modalCodeStep) modalCodeStep.classList.add('hidden');

      const sessionBox = document.getElementById('tg-session-string-box');
      if (sessionBox) sessionBox.classList.add('hidden');
    }
  } catch (err) {
    console.error('Errore stato telegram:', err);
  }
}

function copyTelegramSessionString() {
  if (window._tg_session_string) {
    copyToClipboard(window._tg_session_string, 'Chiave di Sessione Permanente copiata negli appunti!');
  } else {
    showToast('Nessuna chiave di sessione attiva', true);
  }
}

function openTelegramAuthModal() {
  loadTelegramStatus();
  document.getElementById('modal-telegram-login').classList.remove('hidden');
}

function resetTelegramAuthStep() {
  const stepPhone = document.getElementById('tg-step-phone');
  const stepCode = document.getElementById('tg-step-code');
  if (stepPhone) stepPhone.classList.remove('hidden');
  if (stepCode) stepCode.classList.add('hidden');
}

async function sendTelegramAuthCode() {
  const input = document.getElementById('tg-input-phone');
  const phone = input ? input.value.trim() : '';
  const btn = document.getElementById('tg-btn-send-code');

  if (!phone) {
    showToast('Inserisci il tuo numero di telefono Telegram (es. +39...)', true);
    return;
  }

  if (btn) {
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Invio in corso...';
    btn.disabled = true;
  }

  try {
    const res = await fetch('/api/telegram/send-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: phone })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message || 'Codice inviato!');
      const stepPhone = document.getElementById('tg-step-phone');
      const stepCode = document.getElementById('tg-step-code');
      if (stepPhone) stepPhone.classList.add('hidden');
      if (stepCode) {
        stepCode.classList.remove('hidden');
        const codeInput = document.getElementById('tg-input-code');
        if (codeInput) codeInput.focus();
      }
    } else {
      showToast(data.detail || data.error || 'Errore invio codice Telegram', true);
    }
  } catch (err) {
    showToast('Errore di connessione con il server', true);
  } finally {
    if (btn) {
      btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Invia Codice di Verifica';
      btn.disabled = false;
    }
  }
}

async function sendTelegramAuthCodeFromSettings() {
  const input = document.getElementById('set_telegram_phone');
  const phone = input ? input.value.trim() : '';
  const btn = document.getElementById('btn-set-send-code');

  if (!phone) {
    showToast('Inserisci il tuo numero di telefono Telegram', true);
    return;
  }

  if (btn) {
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    btn.disabled = true;
  }

  try {
    const res = await fetch('/api/telegram/send-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: phone })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message || 'Codice inviato!');
      const codeBox = document.getElementById('set-tg-code-box');
      if (codeBox) codeBox.classList.remove('hidden');
    } else {
      showToast(data.detail || data.error || 'Errore invio codice', true);
    }
  } catch (err) {
    showToast('Errore di rete', true);
  } finally {
    if (btn) {
      btn.innerHTML = 'Invia Codice';
      btn.disabled = false;
    }
  }
}

async function verifyTelegramAuthCode() {
  const codeInput = document.getElementById('tg-input-code');
  const faInput = document.getElementById('tg-input-2fa');
  const code = codeInput ? codeInput.value.trim() : '';
  const password2fa = faInput ? faInput.value.trim() : null;
  const btn = document.getElementById('tg-btn-verify-code');

  if (!code) {
    showToast('Inserisci il codice di verifica ricevuto', true);
    return;
  }

  if (btn) {
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Verifica in corso...';
    btn.disabled = true;
  }

  try {
    const res = await fetch('/api/telegram/verify-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: code, password_2fa: password2fa || null })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message || 'Account Telegram collegato con successo!');
      closeModal('modal-telegram-login');
      loadTelegramStatus();
      syncActiveChannel();
    } else {
      showToast(data.detail || data.error || 'Codice non valido o errato', true);
    }
  } catch (err) {
    showToast('Errore di rete durante la verifica', true);
  } finally {
    if (btn) {
      btn.innerHTML = '<i class="fa-solid fa-check"></i> Conferma e Collega';
      btn.disabled = false;
    }
  }
}

async function verifyTelegramAuthCodeFromSettings() {
  const codeInput = document.getElementById('set_telegram_code');
  const faInput = document.getElementById('set_telegram_2fa');
  const code = codeInput ? codeInput.value.trim() : '';
  const password2fa = faInput ? faInput.value.trim() : null;

  if (!code) {
    showToast('Inserisci il codice di verifica', true);
    return;
  }

  try {
    const res = await fetch('/api/telegram/verify-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: code, password_2fa: password2fa || null })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message || 'Account Telegram collegato!');
      loadTelegramStatus();
    } else {
      showToast(data.detail || data.error || 'Codice errato', true);
    }
  } catch (err) {
    showToast('Errore di connessione', true);
  }
}

async function telegramLogout() {
  if (!confirm('Vuoi davvero disconnettere l\'account Telegram?')) return;
  try {
    const res = await fetch('/api/telegram/logout', { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast('Account Telegram disconnesso');
      loadTelegramStatus();
    }
  } catch (err) {
    showToast('Errore durante la disconnessione', true);
  }
}

function updateSandboxBadge(isTest) {
  const badge = document.getElementById('sandbox-badge');
  if (!badge) return;
  if (isTest) {
    badge.className = "text-xs px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/50 font-extrabold uppercase tracking-wider cursor-pointer hover:scale-105 active:scale-95 transition-all flex items-center gap-1.5 shadow-sm";
    badge.innerHTML = '<i class="fa-solid fa-flask-vial text-amber-400"></i><span>Sandbox (Test)</span>';
  } else {
    badge.className = "text-xs px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/50 font-extrabold uppercase tracking-wider cursor-pointer hover:scale-105 active:scale-95 transition-all flex items-center gap-1.5 shadow-sm";
    badge.innerHTML = '<i class="fa-solid fa-circle-check text-emerald-400"></i><span>Live Mode</span>';
  }
}

function getInputValue(id, fallback = '') {
  const el = document.getElementById(id);
  return el ? el.value : fallback;
}

async function loadSettings() {
  try {
    const res = await fetch('/api/settings');
    if (!res.ok) return;
    const s = await res.json();

    const isTest = s.test_mode !== 'false';
    const chk = document.getElementById('set_test_mode');
    if (chk) chk.checked = isTest;
    updateSandboxBadge(isTest);

    if (s.telegram_phone) {
      const phoneInput = document.getElementById('set_telegram_phone');
      if (phoneInput) phoneInput.value = s.telegram_phone;
      const modalPhone = document.getElementById('tg-input-phone');
      if (modalPhone) modalPhone.value = s.telegram_phone;
    }
    if (s.telegram_api_id && document.getElementById('set_telegram_api_id')) {
      document.getElementById('set_telegram_api_id').value = s.telegram_api_id;
    }
    if (s.telegram_api_hash && document.getElementById('set_telegram_api_hash')) {
      document.getElementById('set_telegram_api_hash').value = s.telegram_api_hash;
    }
    if (s.email_user && document.getElementById('set_email_user')) {
      document.getElementById('set_email_user').value = s.email_user;
    }
    if (s.email_password && document.getElementById('set_email_password')) {
      document.getElementById('set_email_password').value = s.email_password;
    }
  } catch (err) {
    console.error('Errore caricamento impostazioni:', err);
  }
}

async function saveSettings() {
  const newPwdEl = document.getElementById('set_new_password');
  const newPwd = newPwdEl ? newPwdEl.value.trim() : '';
  if (newPwd) {
    const pwdSuccess = await changeAdminPassword();
    if (!pwdSuccess) return;
  }

  const testModeEl = document.getElementById('set_test_mode');
  const isTest = testModeEl ? testModeEl.checked : true;
  
  const items = [
    { key: 'test_mode', value: isTest ? 'true' : 'false' },
    { key: 'telegram_phone', value: getInputValue('set_telegram_phone') },
    { key: 'telegram_api_id', value: getInputValue('set_telegram_api_id') },
    { key: 'telegram_api_hash', value: getInputValue('set_telegram_api_hash') },
    { key: 'email_user', value: getInputValue('set_email_user') },
    { key: 'email_password', value: getInputValue('set_email_password') }
  ];

  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(items)
    });
    if (res.ok) {
      updateSandboxBadge(isTest);
      showToast(isTest ? '🧪 Modalità Sandbox (Test) salvata!' : '🟢 Modalità Live salvata!');
      closeModal('modal-settings');
    } else {
      showToast('Errore nel salvataggio', true);
    }
  } catch (err) {
    console.error('Errore saveSettings:', err);
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

let toastTimer = null;

function hideToast() {
  const t = document.getElementById('toast');
  if (!t) return;
  t.style.opacity = '0';
  t.style.transform = 'translateY(-20px)';
  t.style.pointerEvents = 'none';
  setTimeout(() => {
    t.style.display = 'none';
  }, 350);
}

function showToast(msg, isError = false) {
  const t = document.getElementById('toast');
  const m = document.getElementById('toast-msg');
  if (!t || !m) return;

  if (toastTimer) {
    clearTimeout(toastTimer);
    toastTimer = null;
  }

  m.innerText = msg;
  
  const icon = t.querySelector('i');
  if (icon) {
    icon.className = isError ? 'fa-solid fa-circle-exclamation text-base' : 'fa-solid fa-circle-check text-base';
  }

  const bgBorder = isError 
    ? 'bg-red-600 border-red-400' 
    : 'bg-emerald-600 border-emerald-400';

  t.className = `fixed top-5 right-5 z-50 ${bgBorder} text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-2.5 text-xs font-extrabold border cursor-pointer`;
  t.style.display = 'flex';
  t.style.transition = 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)';
  t.style.opacity = '1';
  t.style.transform = 'translateY(0)';
  t.style.pointerEvents = 'auto';

  toastTimer = setTimeout(() => {
    hideToast();
  }, 2500);
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
      syncActiveChannel();
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

let isSyncingChannel = false;

async function syncActiveChannel(isSilent = false) {
  if (isSyncingChannel) return;
  isSyncingChannel = true;

  const btn = document.getElementById('btn-sync-channel');
  const syncBadge = document.getElementById('last-sync-time-badge');

  if (!isSilent && btn) {
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Download offerte live...';
    btn.disabled = true;
  }

  try {
    const res = await fetch('/api/telegram/sync-channel', { method: 'POST' });
    const data = await res.json();
    
    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (syncBadge) {
      syncBadge.innerText = `Sinc: ${nowTime}`;
      syncBadge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
    }

    if (res.ok && data.success) {
      if (!isSilent) {
        showToast(data.message || 'Sincronizzazione completata!');
      }
      loadOffers();
      loadStats();
      loadLogs();
    } else if (data.auth_required) {
      if (!isSilent) {
        showToast(data.message || data.error || 'Collega il tuo account Telegram per scaricare dal canale', true);
        openTelegramAuthModal();
      }
    } else {
      if (!isSilent) {
        showToast(data.message || data.error || 'Nessun post scaricato. Usa "Incolla Post"', true);
      }
    }
  } catch (err) {
    if (!isSilent) {
      showToast('Errore di sincronizzazione canale', true);
    }
  } finally {
    isSyncingChannel = false;
    if (btn) {
      btn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> Sincronizza Canale Live';
      btn.disabled = false;
    }
  }
}
