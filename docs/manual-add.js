/*
 * Haber Ekle / Değiştir — anasayfa (index.html) pop-up'ı.
 *
 * Akış:
 *   1. Anasayfada sağ üstteki "Haber ekle/değiştir" butonu bu pop-up'ı açar.
 *   2. Kullanıcı: şifre girer, 3 kritik haberden çıkarılacak olanı işaretler ve
 *      o boşluğu doldurmak için KAYNAK seçer:
 *        (a) URL ile yeni haber  → bir URL girilir (sunucu çeker + LLM ile üretir).
 *        (b) Rapordan haber seç  → raporun alt bölümündeki diğer haberlerden biri
 *            (yalnızca BAŞLIKLARI listelenir) seçilir. Bu seçenek URL/LLM gerektirmez;
 *            içerik zaten raporda vardır. Seçilen haber alt listeden ÇIKARILIP
 *            (taşınıp) kritik karta dönüştürülür.
 *   3. "Tamam" → sunucudaki /api/manual_add uç noktasına POST gider.
 *      Sunucu YALNIZCA ilgili kritik kartı (ve rapor modunda taşınan haberi)
 *      docs/index.html + o günün arşiv raporunda değiştirip main'e commit eder ve
 *      üretilen kartı geri döner.
 *   4. Dönen kart, sayfadaki ilgili kart ile ANINDA değiştirilir; rapor modunda
 *      taşınan haber alt listeden ANINDA kaldırılır.
 *
 * NOT: Tüm asıl iş (URL getirme, LLM, dosya yazma, commit) SUNUCU tarafında
 * çalışır. Bu dosya yalnızca arayüz + uç noktaya istek atar.
 */
(function () {
  "use strict";

  // ── Sunucu uç noktası — Vercel'e deploy ettikten sonra BURAYI doldur ──────
  // Dosya api/manual_add.py olduğundan yol /api/manual_add olur:
  var MANUAL_ADD_ENDPOINT = "https://siberguvenlik-5hqc.vercel.app/api/manual_add";

  // ── Stiller (yalnızca MODAL stilleri; buton stili artık ana sayfa CSS'inde) ──
  var CSS = [
    ".ma-overlay{position:fixed;inset:0;background:rgba(15,23,42,.55);display:flex;",
    "align-items:center;justify-content:center;z-index:9999;padding:16px;}",
    ".ma-modal{background:#fff;border-radius:12px;max-width:540px;width:100%;",
    "max-height:90vh;overflow:auto;box-shadow:0 20px 50px rgba(0,0,0,.3);",
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1e293b;}",
    ".ma-modal h3{margin:0;padding:20px 24px;border-bottom:1px solid #e2e8f0;font-size:18px;",
    "background:linear-gradient(90deg,#1d4ed8,#6366f1);color:#fff;border-radius:12px 12px 0 0;}",
    ".ma-body{padding:20px 24px;}",
    ".ma-body label.fld{display:block;font-weight:600;font-size:13px;margin:14px 0 6px;}",
    ".ma-body input[type=text],.ma-body input[type=password],.ma-body input[type=url]{",
    "width:100%;padding:10px 12px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px;",
    "box-sizing:border-box;font-family:inherit;}",
    ".ma-body input:focus{outline:none;border-color:#1d4ed8;}",
    ".ma-remove-list{margin:6px 0 0;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;}",
    ".ma-remove-list .opt{display:flex;align-items:flex-start;gap:10px;padding:11px 12px;",
    "cursor:pointer;border-bottom:1px solid #eef2f7;font-size:13.5px;line-height:1.45;}",
    ".ma-remove-list .opt:last-child{border-bottom:none;}",
    ".ma-remove-list .opt:hover{background:#f8fafc;}",
    ".ma-remove-list .opt input{margin-top:3px;}",
    ".ma-hint{font-size:12px;color:#64748b;margin:4px 0 0;}",
    // Kaynak seçici sekmeleri
    ".ma-tabs{display:flex;gap:8px;margin:6px 0 0;}",
    // Pasif sekmeler artık arka planla aynı DEĞİL: dolgulu zemin + belirgin kenarlık.
    ".ma-tab{flex:1;text-align:center;padding:9px 8px;border:1.5px solid #94a3b8;border-radius:8px;",
    "font-size:13px;font-weight:600;cursor:pointer;background:#e8edf5;color:#334155;transition:all .15s;}",
    ".ma-tab:hover{background:#dbe3ef;}",
    ".ma-tab.active{background:#1d4ed8;color:#fff;border-color:#1d4ed8;box-shadow:0 2px 6px rgba(29,78,216,.3);}",
    ".ma-tab:disabled{opacity:.5;cursor:not-allowed;}",
    // "Diğer Haberlerden Seç" sekmesi pasifken amber dolgu + nabız parıltısıyla
    // gözü ANINDA çeker; üzerine gelince/aktifken animasyon durur.
    ".ma-tab-report:not(.active):not(:disabled){background:#f59e0b;border-color:#d97706;color:#fff;",
    "font-weight:700;animation:ma-pulse 1.7s ease-in-out infinite;}",
    ".ma-tab-report:not(.active):not(:disabled):hover{background:#d97706;animation:none;}",
    "@keyframes ma-pulse{0%,100%{box-shadow:0 0 0 0 rgba(245,158,11,.6);}",
    "50%{box-shadow:0 0 0 7px rgba(245,158,11,0);}}",
    "@media (prefers-reduced-motion:reduce){.ma-tab-report{animation:none!important;}}",
    ".ma-source-block{display:none;}",
    ".ma-source-block.active{display:block;}",
    ".ma-actions{padding:16px 24px;border-top:1px solid #e2e8f0;display:flex;justify-content:flex-end;gap:10px;}",
    ".ma-btn{padding:9px 18px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;",
    "border:1px solid transparent;font-family:inherit;}",
    ".ma-btn.ok{background:#1d4ed8;color:#fff;}",
    ".ma-btn.ok:hover{background:#1e40af;}",
    ".ma-btn.ok:disabled{background:#94a3b8;cursor:not-allowed;}",
    ".ma-btn.cancel{background:#fff;color:#475569;border-color:#cbd5e1;}",
    ".ma-btn.cancel:hover{background:#f1f5f9;}",
    ".ma-msg{margin:14px 24px 0;padding:10px 12px;border-radius:8px;font-size:13px;display:none;}",
    ".ma-msg.err{background:#fef2f2;color:#b91c1c;border:1px solid #fecaca;display:block;}",
    ".ma-msg.ok{background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;display:block;}",
    ".ma-msg.info{background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;display:block;}",
    "[data-theme='dark'] .ma-modal{background:#161b22;color:#e6edf3;}",
    "[data-theme='dark'] .ma-modal h3{border-bottom-color:#30363d;}",
    "[data-theme='dark'] .ma-body input{background:#0d1117;border-color:#30363d;color:#e6edf3;}",
    "[data-theme='dark'] .ma-remove-list{border-color:#30363d;}",
    "[data-theme='dark'] .ma-remove-list .opt{border-bottom-color:#21262d;}",
    "[data-theme='dark'] .ma-remove-list .opt:hover{background:#21262d;}",
    "[data-theme='dark'] .ma-tab{background:#21262d;color:#c9d1d9;border-color:#484f58;}",
    "[data-theme='dark'] .ma-tab:hover{background:#2d333b;}",
    "[data-theme='dark'] .ma-tab.active{background:#388bfd;color:#fff;border-color:#388bfd;box-shadow:0 2px 6px rgba(56,139,253,.35);}",
    "[data-theme='dark'] .ma-tab-report:not(.active):not(:disabled){background:#d97706;border-color:#f59e0b;color:#fff;}",
    "[data-theme='dark'] .ma-tab-report:not(.active):not(:disabled):hover{background:#b45309;}",
    "[data-theme='dark'] .ma-actions{border-top-color:#30363d;}",
    "[data-theme='dark'] .ma-btn.cancel{background:#161b22;color:#c9d1d9;border-color:#30363d;}"
  ].join("");

  function injectStyles() {
    if (document.getElementById("ma-styles")) return;
    var s = document.createElement("style");
    s.id = "ma-styles";
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  function topCards() {
    return Array.prototype.slice.call(
      document.querySelectorAll("#onemli-gelismeler-block .top3-card")
    );
  }

  // Raporun alt bölümündeki "diğer haberler" — kritik-3 kartları HARİÇ.
  // Her birinin başlığı + sabit kimliği (id="haber-N") döner.
  function otherNewsItems() {
    var items = Array.prototype.slice.call(
      document.querySelectorAll(".news-section .news-item[id]")
    );
    return items
      .filter(function (el) { return /^haber-\d+$/.test(el.id); })
      .map(function (el) {
        var t = el.querySelector(".news-title");
        return { id: el.id, title: t ? t.textContent.trim() : "(başlık okunamadı)" };
      });
  }

  function cardTitle(card) {
    var a = card.querySelector(".top3-card-title a") || card.querySelector(".top3-card-title");
    return a ? a.textContent.trim() : "(başlık okunamadı)";
  }

  function esc(str) {
    var d = document.createElement("div");
    d.textContent = str == null ? "" : String(str);
    return d.innerHTML;
  }

  function closeModal() {
    var ov = document.getElementById("ma-overlay");
    if (ov) ov.parentNode.removeChild(ov);
  }

  function showMsg(kind, text) {
    var m = document.getElementById("ma-msg");
    if (!m) return;
    m.className = "ma-msg " + kind;
    m.textContent = text;
  }

  // Aktif kaynak modu ("url" | "report") — sekmeleri ve blokları senkronlar.
  function setMode(mode) {
    ["url", "report"].forEach(function (m) {
      var tab = document.getElementById("ma-tab-" + m);
      var blk = document.getElementById("ma-src-" + m);
      if (tab) tab.classList.toggle("active", m === mode);
      if (blk) blk.classList.toggle("active", m === mode);
    });
  }

  window.openManualAddModal = function () {
    injectStyles();
    closeModal();

    var cards = topCards();
    if (cards.length === 0) {
      alert("Kritik haber kartları bulunamadı.");
      return;
    }

    var optsHtml = cards.map(function (c, i) {
      return (
        '<label class="opt"><input type="radio" name="ma-remove" value="' + i + '">' +
        "<span>" + esc(cardTitle(c)) + "</span></label>"
      );
    }).join("");

    var others = otherNewsItems();
    var hasOthers = others.length > 0;
    var reportOptsHtml = hasOthers
      ? others.map(function (n) {
          return (
            '<label class="opt"><input type="radio" name="ma-news" value="' + esc(n.id) + '">' +
            "<span>" + esc(n.title) + "</span></label>"
          );
        }).join("")
      : '<div class="opt"><span style="color:#94a3b8;">Bu raporda taşınabilecek başka haber yok.</span></div>';

    var overlay = document.createElement("div");
    overlay.className = "ma-overlay";
    overlay.id = "ma-overlay";
    overlay.innerHTML =
      '<div class="ma-modal" role="dialog" aria-modal="true">' +
        "<h3>Haber Ekle / Değiştir</h3>" +
        '<div class="ma-msg" id="ma-msg"></div>' +
        '<div class="ma-body">' +
          '<label class="fld" for="ma-pass">Şifre</label>' +
          '<input type="password" id="ma-pass" autocomplete="off" placeholder="••••••••">' +
          '<label class="fld">Çıkarılacak haberi işaretleyin</label>' +
          '<div class="ma-remove-list">' + optsHtml + "</div>" +
          '<label class="fld">Yerine ne eklensin?</label>' +
          '<div class="ma-tabs">' +
            '<button type="button" class="ma-tab" id="ma-tab-url">URL ile yeni haber ekle</button>' +
            '<button type="button" class="ma-tab ma-tab-report" id="ma-tab-report"' + (hasOthers ? "" : " disabled") + ">Diğer Haberlerden Seç</button>" +
          "</div>" +
          '<div class="ma-source-block" id="ma-src-url">' +
            '<label class="fld" for="ma-url">Eklenecek haberin URL\'si</label>' +
            '<input type="url" id="ma-url" placeholder="https://...">' +
            '<p class="ma-hint">URL\'den üretilen yeni haber, işaretlenen kritik haberle değiştirilecek.</p>' +
          "</div>" +
          '<div class="ma-source-block" id="ma-src-report">' +
            '<label class="fld">Eklenecek haberi seçin</label>' +
            '<div class="ma-remove-list">' + reportOptsHtml + "</div>" +
            '<p class="ma-hint">Seçilen haber alt listeden çıkarılıp (taşınıp) işaretlenen kritik haberin yerine eklenecek.</p>' +
          "</div>" +
        "</div>" +
        '<div class="ma-actions">' +
          '<button class="ma-btn cancel" id="ma-cancel">İptal</button>' +
          '<button class="ma-btn ok" id="ma-ok">Tamam</button>' +
        "</div>" +
      "</div>";

    document.body.appendChild(overlay);

    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) closeModal();
    });
    document.getElementById("ma-cancel").addEventListener("click", closeModal);
    document.getElementById("ma-ok").addEventListener("click", submit);
    document.getElementById("ma-tab-url").addEventListener("click", function () { setMode("url"); });
    var reportTab = document.getElementById("ma-tab-report");
    if (hasOthers) reportTab.addEventListener("click", function () { setMode("report"); });

    setMode("url");  // varsayılan: URL ile yeni haber
  };

  function currentMode() {
    var rt = document.getElementById("ma-tab-report");
    return (rt && rt.classList.contains("active")) ? "report" : "url";
  }

  function submit() {
    var pass = (document.getElementById("ma-pass").value || "").trim();
    var checked = document.querySelector('input[name="ma-remove"]:checked');
    var mode = currentMode();

    if (!pass) { showMsg("err", "Şifre giriniz."); return; }
    if (!checked) { showMsg("err", "Çıkarılacak haberi işaretleyiniz."); return; }
    if (!MANUAL_ADD_ENDPOINT) {
      showMsg("err", "Sunucu uç noktası yapılandırılmamış (manual-add.js → MANUAL_ADD_ENDPOINT).");
      return;
    }

    var removeIndex = parseInt(checked.value, 10);
    var payload = { password: pass, mode: mode, remove_index: removeIndex };
    var waitMsg;

    if (mode === "url") {
      var url = (document.getElementById("ma-url").value || "").trim();
      if (!/^https?:\/\//i.test(url)) { showMsg("err", "Geçerli bir URL giriniz (http/https)."); return; }
      payload.url = url;
      waitMsg = "Haber çekiliyor ve sistem formatında hazırlanıyor… (bu işlem biraz sürebilir)";
    } else {
      var newsChecked = document.querySelector('input[name="ma-news"]:checked');
      if (!newsChecked) { showMsg("err", "Eklenecek haberi seçiniz."); return; }
      payload.news_id = newsChecked.value;
      waitMsg = "Seçilen haber kritik bölüme taşınıyor…";
    }

    var okBtn = document.getElementById("ma-ok");
    okBtn.disabled = true;
    showMsg("info", waitMsg);

    fetch(MANUAL_ADD_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(function (r) {
        return r.json().then(function (data) { return { status: r.status, data: data }; });
      })
      .then(function (res) {
        if (res.status === 200 && res.data && res.data.ok) {
          applyCard(removeIndex, res.data.card_html);
          if (res.data.removed_news_id) removeNewsItem(res.data.removed_news_id);
          showMsg("ok", "Haber eklendi ve rapor güncellendi.");
          setTimeout(closeModal, 1200);
        } else {
          okBtn.disabled = false;
          var err = (res.data && res.data.error) ? res.data.error : ("Hata (HTTP " + res.status + ")");
          showMsg("err", err);
        }
      })
      .catch(function (e) {
        okBtn.disabled = false;
        showMsg("err", "Sunucuya ulaşılamadı: " + e.message);
      });
  }

  // Sayfadaki ilgili kritik kartı, sunucudan dönen kartla anında değiştirir.
  function applyCard(index, cardHtml) {
    var cards = topCards();
    if (!cardHtml || index < 0 || index >= cards.length) return;
    var tmp = document.createElement("div");
    tmp.innerHTML = cardHtml.trim();
    var newCard = tmp.querySelector(".top3-card") || tmp.firstChild;
    if (newCard) cards[index].parentNode.replaceChild(newCard, cards[index]);
  }

  // Rapor modunda: taşınan haberi (ve varsa yönetici tablosundaki satırını) anında kaldırır.
  function removeNewsItem(newsId) {
    var item = document.getElementById(newsId);
    if (item && item.parentNode) item.parentNode.removeChild(item);
    var link = document.querySelector('.executive-table a[href="#' + newsId + '"]');
    if (link) {
      var row = link.closest ? link.closest("tr") : null;
      if (row && row.parentNode) row.parentNode.removeChild(row);
    }
  }
})();
