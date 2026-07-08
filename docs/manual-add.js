/*
 * Haber Ekle / Sil — anasayfa (index.html) pop-up'ı.
 *
 * İki işlem:
 *   • Ekle : yeni bir kritik kart ekle (kaynak URL veya rapordaki bir haber).
 *            Opsiyonel: "Çıkarılacak Haber" seçilirse o haber SİLİNMEZ,
 *            gövdeye ('diğer haberler') iner ve yeni haber onun yerine geçer
 *            (kritik sayısı 3'te kalır; eski "Değiştir" işlevi buraya taşındı).
 *            Hiçbiri seçilmezse yeni haber eklenir (kritik 4'e çıkar).
 *   • Sil  : bir haberi tamamen SİL (yerine bir şey konmaz) — kritik kart VEYA
 *            alt listedeki (diğer haberler) bir haber.
 *
 * Tüm asıl iş (URL getirme, LLM, dosya yazma, commit) SUNUCU tarafında
 * (/api/manual_add) çalışır. Bu dosya yalnızca arayüz + uç noktaya istek atar.
 */
(function () {
  "use strict";

  // ── Sunucu uç noktası — Vercel'e deploy ettikten sonra BURAYI doldur ──────
  var MANUAL_ADD_ENDPOINT = "https://siberguvenlik-5hqc.vercel.app/api/manual_add";
  // "Sıfırla & Yeniden Üret" ucu — aynı Vercel host'unda /api/reset_regenerate.
  // Sabit URL uydurmadan, doğrulanmış manual_add host'undan türetilir.
  var RESET_ENDPOINT = MANUAL_ADD_ENDPOINT.replace(/\/manual_add(\/?)$/, "/reset_regenerate");

  // ── Stiller (yalnızca MODAL stilleri; buton stili ana sayfa CSS'inde) ──
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
    ".ma-tag{display:inline-block;font-size:10.5px;font-weight:700;padding:1px 6px;border-radius:5px;",
    "margin-right:6px;vertical-align:middle;letter-spacing:.3px;}",
    ".ma-tag.crit{background:#fee2e2;color:#b91c1c;}",
    ".ma-tag.body{background:#e0e7ff;color:#3730a3;}",
    ".ma-hint{font-size:12px;color:#64748b;margin:4px 0 0;}",
    // İşlem seçici + kaynak sekmeleri (ortak .ma-tab görünümü)
    ".ma-tabs{display:flex;gap:8px;margin:6px 0 0;}",
    ".ma-tab{flex:1;text-align:center;padding:9px 8px;border:1.5px solid #94a3b8;border-radius:8px;",
    "font-size:13px;font-weight:600;cursor:pointer;background:#e8edf5;color:#334155;transition:all .15s;}",
    ".ma-tab:hover{background:#dbe3ef;}",
    ".ma-tab.active{background:#1d4ed8;color:#fff;border-color:#1d4ed8;box-shadow:0 2px 6px rgba(29,78,216,.3);}",
    ".ma-tab:disabled{opacity:.5;cursor:not-allowed;}",
    // "Diğer Haberlerden Seç" sekmesi pasifken amber dolgu + nabız parıltısı
    ".ma-tab-report:not(.active):not(:disabled){background:#f59e0b;border-color:#d97706;color:#fff;",
    "font-weight:700;animation:ma-pulse 1.7s ease-in-out infinite;}",
    ".ma-tab-report:not(.active):not(:disabled):hover{background:#d97706;animation:none;}",
    "@keyframes ma-pulse{0%,100%{box-shadow:0 0 0 0 rgba(245,158,11,.6);}",
    "50%{box-shadow:0 0 0 7px rgba(245,158,11,0);}}",
    "@media (prefers-reduced-motion:reduce){.ma-tab-report{animation:none!important;}}",
    // Sil sekmesi vurgusu (aktifken kırmızı)
    ".ma-op-delete.active{background:#dc2626!important;border-color:#dc2626!important;",
    "box-shadow:0 2px 6px rgba(220,38,38,.3)!important;}",
    // "Raporu Yeniden Üret" sekmesi (aktifken amber/turuncu)
    ".ma-op-reset.active{background:#b45309!important;border-color:#b45309!important;",
    "box-shadow:0 2px 6px rgba(180,83,9,.3)!important;color:#fff!important;}",
    // Reset onay ekranı — uyarı kutusu + ortada yeniden-üret butonu
    ".ma-reset-warn{margin:16px 0 0;padding:14px 16px;border:1.5px solid #fcd34d;",
    "background:#fffbeb;border-radius:10px;font-size:14px;line-height:1.55;color:#92400e;}",
    ".ma-reset-warn b{color:#b45309;}",
    ".ma-reset-actions{margin-top:18px;text-align:center;}",
    ".ma-btn.reset{background:#b45309;color:#fff;border-color:#b45309;padding:12px 22px;font-size:15px;}",
    ".ma-btn.reset:hover{background:#92400e;}",
    ".ma-btn.reset:disabled{background:#94a3b8;border-color:#94a3b8;cursor:not-allowed;}",
    "[data-theme='dark'] .ma-reset-warn{background:#2d2410;border-color:#7c5e10;color:#fcd34d;}",
    "[data-theme='dark'] .ma-reset-warn b{color:#fbbf24;}",
    ".ma-source-block{display:none;}",
    ".ma-source-block.active{display:block;}",
    // İşlem blokları (ekle/sil) — yalnızca aktif olan gösterilir
    ".ma-op-block{display:none;}",
    ".ma-op-block.active{display:block;}",
    // Ekle kaynağı seçildikten SONRA açılan detay (url kutusu / haber listesi)
    ".ma-src-detail{display:none;}",
    ".ma-src-detail.active{display:block;}",
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
    "[data-theme='dark'] .ma-tag.crit{background:#3b1116;color:#fca5a5;}",
    "[data-theme='dark'] .ma-tag.body{background:#1e1b4b;color:#a5b4fc;}",
    "[data-theme='dark'] .ma-tab{background:#21262d;color:#c9d1d9;border-color:#484f58;}",
    "[data-theme='dark'] .ma-tab:hover{background:#2d333b;}",
    "[data-theme='dark'] .ma-tab.active{background:#388bfd;color:#fff;border-color:#388bfd;box-shadow:0 2px 6px rgba(56,139,253,.35);}",
    "[data-theme='dark'] .ma-tab-report:not(.active):not(:disabled){background:#d97706;border-color:#f59e0b;color:#fff;}",
    "[data-theme='dark'] .ma-tab-report:not(.active):not(:disabled):hover{background:#b45309;}",
    "[data-theme='dark'] .ma-actions{border-top-color:#30363d;}",
    "[data-theme='dark'] .ma-btn.cancel{background:#161b22;color:#c9d1d9;border-color:#30363d;}",
    // ── İlerleme katmanı (işlem sürerken) ───────────────────────────────────
    ".ma-progress{position:fixed;inset:0;z-index:10000;display:none;align-items:center;",
    "justify-content:center;padding:16px;background:rgba(15,23,42,.55);}",
    ".ma-progress.show{display:flex;}",
    ".ma-progress-card{background:#fff;border-radius:12px;max-width:430px;width:100%;",
    "padding:30px 26px;box-shadow:0 20px 50px rgba(0,0,0,.35);text-align:center;",
    "font-family:inherit;color:#1e293b;}",
    ".ma-spinner{width:48px;height:48px;margin:0 auto 20px;border:4px solid #dbe3ef;",
    "border-top-color:#1d4ed8;border-radius:50%;animation:ma-spin .8s linear infinite;}",
    "@keyframes ma-spin{to{transform:rotate(360deg);}}",
    ".ma-progress-title{font-size:17px;font-weight:700;margin-bottom:10px;color:#1d4ed8;}",
    ".ma-progress-step{font-size:14.5px;line-height:1.5;color:#334155;min-height:22px;font-weight:600;}",
    ".ma-progress-dots::after{display:inline-block;width:1.2em;text-align:left;",
    "content:'';animation:ma-dots 1.4s steps(1,end) infinite;}",
    "@keyframes ma-dots{0%{content:'';}25%{content:'.';}50%{content:'..';}75%{content:'...';}}",
    ".ma-progress-sub{font-size:12px;color:#64748b;margin-top:14px;line-height:1.5;}",
    "@media (prefers-reduced-motion:reduce){.ma-spinner{animation-duration:2.4s;}",
    ".ma-progress-dots::after{animation:none;content:'…';}}",
    "[data-theme='dark'] .ma-progress-card{background:#161b22;color:#e6edf3;}",
    "[data-theme='dark'] .ma-spinner{border-color:#30363d;border-top-color:#388bfd;}",
    "[data-theme='dark'] .ma-progress-title{color:#79c0ff;}",
    "[data-theme='dark'] .ma-progress-step{color:#c9d1d9;}",
    ".ma-progress-sub b{color:#b45309;}",
    "[data-theme='dark'] .ma-progress-sub b{color:#fbbf24;}",
    ".ma-progress-elapsed{font-size:12.5px;color:#64748b;margin-top:10px;",
    "font-variant-numeric:tabular-nums;font-weight:600;}",
    "[data-theme='dark'] .ma-progress-elapsed{color:#8b949e;}"
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

  function top3Section() {
    return document.querySelector("#onemli-gelismeler-block .top3-section");
  }

  // Raporun alt bölümündeki "diğer haberler" — kritik-3 kartları HARİÇ.
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
    stopProgress();
    var ov = document.getElementById("ma-overlay");
    if (ov) ov.parentNode.removeChild(ov);
  }

  function showMsg(kind, text) {
    var m = document.getElementById("ma-msg");
    if (!m) return;
    m.className = "ma-msg " + kind;
    m.textContent = text;
    scrollModalTop();
  }

  function scrollModalTop() {
    var modal = document.querySelector("#ma-overlay .ma-modal");
    if (modal && typeof modal.scrollTo === "function") modal.scrollTo({ top: 0, behavior: "smooth" });
    else if (modal) modal.scrollTop = 0;
  }

  // ── İşlem ilerleme göstergesi ─────────────────────────────────────────────
  var _progressTimer = null;
  var _elapsedTimer = null;
  function _fmtElapsed(sec) {
    var m = Math.floor(sec / 60), s = sec % 60;
    return m + ":" + (s < 10 ? "0" : "") + s;
  }
  function startProgress(steps) {
    var layer = document.getElementById("ma-progress");
    var stepEl = document.getElementById("ma-progress-step");
    var elapsedEl = document.getElementById("ma-progress-elapsed");
    if (!layer || !stepEl) return;
    var i = 0;
    var loopStart = Math.max(0, steps.length - 2);
    stepEl.textContent = steps[0];
    layer.classList.add("show");
    if (_progressTimer) clearInterval(_progressTimer);
    if (_elapsedTimer) clearInterval(_elapsedTimer);
    _progressTimer = setInterval(function () {
      i = (i < steps.length - 1) ? i + 1 : loopStart;
      stepEl.textContent = steps[i];
    }, 4500);
    var startTs = Date.now();
    if (elapsedEl) {
      elapsedEl.textContent = "Geçen süre: 0:00";
      _elapsedTimer = setInterval(function () {
        elapsedEl.textContent = "Geçen süre: " +
          _fmtElapsed(Math.round((Date.now() - startTs) / 1000));
      }, 1000);
    }
  }
  function stopProgress() {
    if (_progressTimer) { clearInterval(_progressTimer); _progressTimer = null; }
    if (_elapsedTimer) { clearInterval(_elapsedTimer); _elapsedTimer = null; }
    var layer = document.getElementById("ma-progress");
    if (layer) layer.classList.remove("show");
  }

  // Aktif KAYNAK modu ("url" | "report" | null) — Ekle işleminde kullanılır.
  // null verilince kaynak detayı (kutu/liste) gizlenir; yalnızca alt sekmeler kalır.
  function setMode(mode) {
    ["url", "report"].forEach(function (m) {
      var tab = document.getElementById("ma-tab-" + m);
      var blk = document.getElementById("ma-src-" + m);
      if (tab) tab.classList.toggle("active", m === mode);
      if (blk) blk.classList.toggle("active", m === mode);
    });
    // Detay (url kutusu / haber listesi) yalnızca bir kaynak seçilince açılır.
    var detail = document.getElementById("ma-src-detail");
    if (detail) detail.classList.toggle("active", mode === "url" || mode === "report");
  }

  function currentMode() {
    if (document.getElementById("ma-tab-report").classList.contains("active")) return "report";
    if (document.getElementById("ma-tab-url").classList.contains("active")) return "url";
    return null;
  }

  // Aktif İŞLEM ("" | "add" | "delete" | "reset") — blokları gösterir/gizler.
  // Boş ("") = hiçbir işlem seçili değil; yalnızca Ekle/Sil/Yeniden Üret sekmeleri görünür.
  function setOp(op) {
    ["add", "delete", "reset"].forEach(function (o) {
      var tab = document.getElementById("ma-op-" + o);
      if (tab) tab.classList.toggle("active", o === op);
    });
    // Bloklar: ekle → yalnız kaynak; sil → silinecek liste; reset → onay ekranı.
    var b;
    if ((b = document.getElementById("ma-blk-source"))) b.classList.toggle("active", op === "add");
    if ((b = document.getElementById("ma-blk-delete"))) b.classList.toggle("active", op === "delete");
    if ((b = document.getElementById("ma-blk-reset"))) b.classList.toggle("active", op === "reset");
    // Ekle'ye her geçişte kaynak seçimi sıfırlanır → yalnızca alt sekmeler görünür.
    if (op === "add") setMode(null);
    // Reset'in kendi butonu (onay ekranında) var; footer "Tamam" reset'te gizlenir.
    var okBtn = document.getElementById("ma-ok");
    if (okBtn) okBtn.style.display = (op === "reset") ? "none" : "";
    var lbl = document.getElementById("ma-src-label");
    if (lbl) lbl.textContent = "Ne eklensin? (yeni bir kritik kart olarak eklenecek)";
  }

  function currentOp() {
    if (document.getElementById("ma-op-reset").classList.contains("active")) return "reset";
    if (document.getElementById("ma-op-delete").classList.contains("active")) return "delete";
    if (document.getElementById("ma-op-add").classList.contains("active")) return "add";
    return null;
  }

  window.openManualAddModal = function () {
    injectStyles();
    closeModal();

    var cards = topCards();

    var others = otherNewsItems();
    var hasOthers = others.length > 0;

    // Ekle kaynağı: rapordan taşınacak haber listesi.
    var reportOptsHtml = hasOthers
      ? others.map(function (n) {
          return (
            '<label class="opt"><input type="checkbox" name="ma-news" value="' + esc(n.id) + '">' +
            "<span>" + esc(n.title) + "</span></label>"
          );
        }).join("")
      : '<div class="opt"><span style="color:#94a3b8;">Bu raporda taşınabilecek başka haber yok.</span></div>';

    // Ekle: (opsiyonel, ÇOKLU) çıkarılacak haber(ler). Seçilen kart(lar)
    // kritik-3'ten çıkarılıp gövdeye iner; yeni eklenen haber(ler) bunların
    // yerine geçer (net kritik sayısı dengelenir). Hiçbiri seçilmezse düz ekle.
    var replaceOptsHtml = cards.length
      ? cards.map(function (c, i) {
          return (
            '<label class="opt"><input type="checkbox" name="ma-replace" value="' + i + '">' +
            '<span><span class="ma-tag crit">KRİTİK</span>' + esc(cardTitle(c)) + " → çıkarılsın</span></label>"
          );
        }).join("")
      : '<div class="opt"><span style="color:#94a3b8;">Çıkarılacak kritik kart yok.</span></div>';

    // Sil: kritik kartlar + alt liste haberleri (birleşik). value = "crit:i" | "body:id".
    var deleteOptsHtml = cards.map(function (c, i) {
      return (
        '<label class="opt"><input type="checkbox" name="ma-delete" value="crit:' + i + '">' +
        '<span><span class="ma-tag crit">KRİTİK</span>' + esc(cardTitle(c)) + "</span></label>"
      );
    }).join("") + others.map(function (n) {
      return (
        '<label class="opt"><input type="checkbox" name="ma-delete" value="body:' + esc(n.id) + '">' +
        '<span><span class="ma-tag body">HABER</span>' + esc(n.title) + "</span></label>"
      );
    }).join("");
    if (!deleteOptsHtml) {
      deleteOptsHtml = '<div class="opt"><span style="color:#94a3b8;">Silinecek haber yok.</span></div>';
    }

    var overlay = document.createElement("div");
    overlay.className = "ma-overlay";
    overlay.id = "ma-overlay";
    overlay.innerHTML =
      '<div class="ma-modal" role="dialog" aria-modal="true">' +
        "<h3>Haber Ekle / Sil</h3>" +
        '<div class="ma-msg" id="ma-msg"></div>' +
        '<div class="ma-body">' +
          '<label class="fld" for="ma-pass">Şifre</label>' +
          '<input type="password" id="ma-pass" autocomplete="off" placeholder="••••••••">' +

          '<label class="fld">İşlem</label>' +
          '<div class="ma-tabs">' +
            '<button type="button" class="ma-tab" id="ma-op-add">Ekle</button>' +
            '<button type="button" class="ma-tab ma-op-delete" id="ma-op-delete">Sil</button>' +
            '<button type="button" class="ma-tab ma-op-reset" id="ma-op-reset">🔄 Raporu Yeniden Üret</button>' +
          "</div>" +

          // KAYNAK (ekle)
          '<div class="ma-op-block" id="ma-blk-source">' +
            '<label class="fld" id="ma-src-label">Ne eklensin? (yeni bir kritik kart olarak eklenecek)</label>' +
            '<div class="ma-tabs">' +
              '<button type="button" class="ma-tab" id="ma-tab-url">URL ile yeni haber ekle</button>' +
              '<button type="button" class="ma-tab ma-tab-report" id="ma-tab-report"' + (hasOthers ? "" : " disabled") + ">Diğer Haberlerden Seç</button>" +
            "</div>" +
            // Kaynak seçildikten SONRA açılan detay — url kutusu / haber listesi
            '<div class="ma-src-detail" id="ma-src-detail">' +
              '<div class="ma-source-block" id="ma-src-url">' +
                '<label class="fld" for="ma-url">Eklenecek haberin URL\'si</label>' +
                '<input type="url" id="ma-url" placeholder="https://...">' +
                '<p class="ma-hint">URL\'den üretilen yeni haber kritik bölüme eklenir.</p>' +
              "</div>" +
              '<div class="ma-source-block" id="ma-src-report">' +
                '<label class="fld">Eklenecek haberleri seçin (birden fazla seçebilirsiniz)</label>' +
                '<div class="ma-remove-list">' + reportOptsHtml + "</div>" +
                '<p class="ma-hint">Seçilen haber(ler) alt listeden çıkarılıp (taşınıp) kritik bölüme eklenir.</p>' +
              "</div>" +
              // Opsiyonel (ÇOKLU): çıkarılacak haber(ler) — seçilenler kritik-3'ten
              // çıkarılıp gövdeye iner, yeni eklenen(ler) onların yerine geçer.
              '<label class="fld" style="margin-top:12px;">Çıkarılacak Haber(ler) (opsiyonel, birden fazla seçebilirsiniz)</label>' +
              '<div class="ma-remove-list">' + replaceOptsHtml + "</div>" +
              '<p class="ma-hint">Seçtiğin kritik haber(ler) SİLİNMEZ; alttaki "diğer haberler" ' +
              'listesine iner, yeni eklenen(ler) onların yerine geçer. Hiçbirini seçmezsen ' +
              'yeni haber(ler) mevcutlara EK olarak eklenir (kritik sayısı artar).</p>' +
            "</div>" +
          "</div>" +

          // SİL: kritik + alt liste birleşik
          '<div class="ma-op-block" id="ma-blk-delete">' +
            '<label class="fld">Silinecek haberleri seçin (birden fazla seçebilirsiniz)</label>' +
            '<div class="ma-remove-list">' + deleteOptsHtml + "</div>" +
            '<p class="ma-hint">Seçilen haber(ler) rapordan TAMAMEN silinir (yerine bir şey ' +
            'konmaz). Kritik bir haber silinirse kart sayısı azalır; ertesi günkü otomatik ' +
            'rapor yine 3 üretir. (Silmeden gövdeye indirmek istersen Ekle işlemindeki ' +
            '"Çıkarılacak Haber" seçeneğini kullan.)</p>' +
          "</div>" +

          // RAPORU YENİDEN ÜRET — onay ekranı (uyarı + aynı buton)
          '<div class="ma-op-block" id="ma-blk-reset">' +
            '<div class="ma-reset-warn">' +
              "Bugünün <b>raporu silinecek ve sıfırdan yeniden üretilecek.</b> Emin misiniz?" +
              '<br><br>• Bugünkü ham veri, rapor ve durum işaretleri silinir' +
              '<br>• Haberler yeniden çekilir ve rapor baştan oluşturulur' +
              '<br>• İşlem GitHub Actions\'ta ~10 dakika sürer' +
              '<br>• Eski günlerin raporları <b>etkilenmez</b>' +
            "</div>" +
            '<div class="ma-reset-actions">' +
              '<button type="button" class="ma-btn reset" id="ma-reset">🔄 Raporu Yeniden Üret</button>' +
            "</div>" +
          "</div>" +
        "</div>" +
        '<div class="ma-actions">' +
          '<button class="ma-btn cancel" id="ma-cancel">İptal</button>' +
          '<button class="ma-btn ok" id="ma-ok">Tamam</button>' +
        "</div>" +
      "</div>" +
      '<div class="ma-progress" id="ma-progress" role="status" aria-live="polite">' +
        '<div class="ma-progress-card">' +
          '<div class="ma-spinner"></div>' +
          '<div class="ma-progress-title">İşleminiz sürüyor</div>' +
          '<div class="ma-progress-step">' +
            '<span id="ma-progress-step">Hazırlanıyor</span>' +
            '<span class="ma-progress-dots"></span>' +
          "</div>" +
          '<p class="ma-progress-sub">Lütfen bekleyin; <b>bu işlem 2-3 dakika sürebilir.</b> ' +
          'İşlem tamamlanınca bu pencere kendiliğinden kapanacaktır; lütfen kapatmayın.</p>' +
          '<p class="ma-progress-elapsed" id="ma-progress-elapsed"></p>' +
        "</div>" +
      "</div>";

    document.body.appendChild(overlay);

    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) closeModal();
    });
    document.getElementById("ma-cancel").addEventListener("click", closeModal);
    document.getElementById("ma-ok").addEventListener("click", submit);
    document.getElementById("ma-reset").addEventListener("click", submitReset);
    document.getElementById("ma-op-add").addEventListener("click", function () { setOp("add"); });
    document.getElementById("ma-op-delete").addEventListener("click", function () { setOp("delete"); });
    document.getElementById("ma-op-reset").addEventListener("click", function () { setOp("reset"); });
    document.getElementById("ma-tab-url").addEventListener("click", function () { setMode("url"); });
    var reportTab = document.getElementById("ma-tab-report");
    if (hasOthers) reportTab.addEventListener("click", function () { setMode("report"); });

    // Akordiyon: başta hiçbir işlem seçili değil — yalnızca Ekle/Sil/Yeniden Üret
    // sekmeleri görünür. Kullanıcı seçtikçe alt seviyeler kademeli açılır.
    setOp("");
  };

  function submit() {
    var pass = (document.getElementById("ma-pass").value || "").trim();
    if (!pass) { showMsg("err", "Şifre giriniz."); return; }
    if (!MANUAL_ADD_ENDPOINT) {
      showMsg("err", "Sunucu uç noktası yapılandırılmamış (manual-add.js → MANUAL_ADD_ENDPOINT).");
      return;
    }

    var op = currentOp();
    if (op !== "add" && op !== "delete") {
      showMsg("err", "Önce bir işlem seçiniz (Ekle veya Sil)."); return;
    }
    var payload = { password: pass, action: op };
    var steps;
    // Başarıda istemci-tarafı DOM güncellemesi için bağlam (batchAdd/batchDelete
    // aşağıda doldurulur; ikisi de her zaman set edilir — bkz. applyResult).
    var ctx = {};

    if (op === "delete") {
      // ÇOKLU silme: seçilen tüm kritik/gövde haberleri tek işlemde silinir.
      var delChecked = Array.prototype.slice.call(
        document.querySelectorAll('input[name="ma-delete"]:checked'));
      if (!delChecked.length) { showMsg("err", "Silinecek en az bir haber seçiniz."); return; }
      payload.targets = delChecked.map(function (el) {
        var v = el.value;
        if (v.indexOf("crit:") === 0) return { t: "critical", i: parseInt(v.slice(5), 10) };
        return { t: "body", id: v.slice(5) };
      });
      ctx.batchDelete = true;
      steps = [
        (delChecked.length > 1 ? "Haberler rapordan kaldırılıyor" : "Haber rapordan kaldırılıyor"),
        "Numaralandırma ve indeks tablosu güncelleniyor",
        "Yönetici Özeti yeniden oluşturuluyor (en uzun adım)",
        "Değişiklikler GitHub'a kaydediliyor"
      ];
    } else {
      // add — kaynak (url/report) gerekir. "Çıkarılacak Haber(ler)" (demote_indices)
      // opsiyonel ve ÇOKLU: seçilenler kritik-3'ten çıkarılıp gövdeye iner, yeni
      // eklenen(ler) onların yerine geçer; boşsa düz ekleme (kritik sayısı artar).
      var mode = currentMode();
      if (mode !== "url" && mode !== "report") {
        showMsg("err", "Bir kaynak seçiniz (URL ile yeni haber ekle veya Diğer Haberlerden Seç).");
        return;
      }
      payload.mode = mode;

      var demoteChecked = Array.prototype.slice.call(
        document.querySelectorAll('input[name="ma-replace"]:checked'));
      if (demoteChecked.length) {
        payload.demote_indices = demoteChecked.map(function (el) { return parseInt(el.value, 10); });
      }

      if (mode === "url") {
        var url = (document.getElementById("ma-url").value || "").trim();
        if (!/^https?:\/\//i.test(url)) { showMsg("err", "Geçerli bir URL giriniz (http/https)."); return; }
        payload.url = url;
        ctx.batchAdd = true;
        steps = [
          "Haber kaynağına bağlanılıyor",
          "Makale metni çıkarılıyor",
          "Yapay zekâ ile Türkçe başlık ve özet üretiliyor",
          "Yönetici Özeti yeniden oluşturuluyor (en uzun adım)",
          "Yapay zekâ yanıtı tamamlanıyor, lütfen bekleyin",
          "Değişiklikler GitHub'a kaydediliyor"
        ];
      } else {
        // Rapordan taşıma — çoklu seçim desteklenir; tekli seçim de aynı
        // (tek elemanlı) diziyle gönderilir, sunucuda ayrı bir yol gerekmez.
        var newsChecked = Array.prototype.slice.call(
          document.querySelectorAll('input[name="ma-news"]:checked'));
        if (!newsChecked.length) { showMsg("err", "Eklenecek en az bir haber seçiniz."); return; }
        payload.news_ids = newsChecked.map(function (el) { return el.value; });
        ctx.batchAdd = true;
        steps = [
          "Seçilen haber(ler) kritik bölüme taşınıyor",
          "Yönetici Özeti yeni haberlere göre yeniden oluşturuluyor (en uzun adım)",
          "Yapay zekâ yanıtı tamamlanıyor, lütfen bekleyin",
          "Değişiklikler GitHub'a kaydediliyor"
        ];
      }
    }

    var okBtn = document.getElementById("ma-ok");
    okBtn.disabled = true;
    startProgress(steps);

    var controller = (typeof AbortController !== "undefined") ? new AbortController() : null;
    var failsafe = setTimeout(function () {
      if (controller) controller.abort();
    }, 300000);

    fetch(MANUAL_ADD_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller ? controller.signal : undefined
    })
      .then(function (r) {
        return r.json().then(function (data) { return { status: r.status, data: data }; });
      })
      .then(function (res) {
        clearTimeout(failsafe);
        stopProgress();
        if (res.status === 200 && res.data && res.data.ok) {
          applyResult(ctx, res.data);
          if (res.data.summary_warning) {
            showMsg("err", "İşlem tamamlandı. UYARI: " + res.data.summary_warning);
            okBtn.disabled = false;
          } else {
            showMsg("ok", "İşlem kaydedildi. Sayfada hemen görünür; ancak yeniden " +
              "yüklersen GitHub Pages önbelleği nedeniyle güncel hâlin gelmesi 1-2 dk " +
              "sürebilir (kaybolmadı, kaydedildi).");
            setTimeout(closeModal, 3500);
          }
        } else {
          okBtn.disabled = false;
          var err = (res.data && res.data.error) ? res.data.error : ("Hata (HTTP " + res.status + ")");
          showMsg("err", err);
        }
      })
      .catch(function (e) {
        clearTimeout(failsafe);
        stopProgress();
        okBtn.disabled = false;
        if (e && e.name === "AbortError") {
          showMsg("err", "İşlem beklenenden uzun sürdü ve durduruldu. Değişiklik arka " +
            "planda tamamlanmış OLABİLİR — bu pencereyi kapatıp sayfayı yenileyerek kontrol edin.");
        } else {
          showMsg("err", "Sunucuya ulaşılamadı: " + (e && e.message ? e.message : e));
        }
      });
  }

  // ── SIFIRLA & YENİDEN ÜRET ────────────────────────────────────────────────
  // Bugünün raporunu SIFIRDAN yeniden ürettirir: şifre doğrulanır, sonra
  // Vercel ucu GitHub Actions'ı reset_today=true ile tetikler. Gerçek reset +
  // taze fetch + üretim Actions'ta (~10 dk) olur; bu buton yalnızca tetikler.
  function submitReset() {
    var pass = (document.getElementById("ma-pass").value || "").trim();
    if (!pass) { showMsg("err", "Şifre giriniz."); return; }
    if (!RESET_ENDPOINT) {
      showMsg("err", "Sunucu uç noktası yapılandırılmamış (reset_regenerate)."); return;
    }
    // Onay artık ayrı bir ekranda (ma-blk-reset uyarısı) gösterildiği için
    // ayrıca window.confirm sorulmaz — bu butona basmak onayı ifade eder.

    var resetBtn = document.getElementById("ma-reset");
    var okBtn = document.getElementById("ma-ok");
    resetBtn.disabled = true; okBtn.disabled = true;
    // Bu uç HIZLI döner (sadece tetikler); asıl 10 dk'lık iş Actions'ta.
    startProgress(["GitHub Actions tetikleniyor", "Onay bekleniyor"]);

    var controller = (typeof AbortController !== "undefined") ? new AbortController() : null;
    var failsafe = setTimeout(function () { if (controller) controller.abort(); }, 30000);

    fetch(RESET_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pass, action: "reset_regenerate" }),
      signal: controller ? controller.signal : undefined
    })
      .then(function (r) {
        return r.json().then(function (data) { return { status: r.status, data: data }; });
      })
      .then(function (res) {
        clearTimeout(failsafe);
        stopProgress();
        resetBtn.disabled = false; okBtn.disabled = false;
        if (res.status === 200 && res.data && res.data.ok) {
          showMsg("ok", res.data.message ||
            "Reset tetiklendi. Rapor ~10 dakika içinde güncellenecek; sonra sayfayı sert yenileyin (Ctrl+F5).");
        } else {
          var err = (res.data && res.data.error) ? res.data.error : ("Hata (HTTP " + res.status + ")");
          showMsg("err", err);
        }
      })
      .catch(function (e) {
        clearTimeout(failsafe);
        stopProgress();
        resetBtn.disabled = false; okBtn.disabled = false;
        if (e && e.name === "AbortError") {
          showMsg("err", "Tetikleme yanıtı gecikti. Tetikleme yine de gitmiş OLABİLİR — " +
            "birkaç dakika sonra raporu kontrol edin.");
        } else {
          showMsg("err", "Sunucuya ulaşılamadı: " + (e && e.message ? e.message : e));
        }
      });
  }

  // Sunucu sonucunu sayfaya ANINDA yansıt (işleme göre).
  function applyResult(ctx, data) {
    if (ctx.batchAdd) {
      // Ekle (tekli veya çoklu): önce "Çıkarılacak Haber(ler)" ile demote
      // edilen kritik kartlar DOM'dan AZALAN indeksle silinir (kartların
      // gövdeye taşınması sunucuda zaten yapıldı; burada yalnızca üst
      // kutudaki kartı kaldırıyoruz — gövdeye eklenen hâli sayfa yeniden
      // yüklenince görünür). Sonra yeni kart(lar) sona eklenir, taşınan
      // kaynak haberler gövdeden kaldırılır.
      (data.demoted_indices || []).slice().sort(function (a, b) { return b - a; })
        .forEach(function (i) { deleteCard(i); });
      (data.added_cards || []).forEach(function (h) { appendCard(h); });
      (data.removed_news_ids || []).forEach(function (id) { removeNewsItem(id); });
      return;
    }
    if (ctx.batchDelete) {
      // Çoklu sil: kritik kartları AZALAN indeksle sil (DOM'dan silince kalan
      // kartların indeksi kayar), sonra gövde haberlerini id ile kaldır.
      (data.deleted_indices || []).slice().sort(function (a, b) { return b - a; })
        .forEach(function (i) { deleteCard(i); });
      (data.removed_news_ids || []).forEach(function (id) { removeNewsItem(id); });
      return;
    }
  }

  // Ekle: yeni kritik kartı kartların sonuna ekler. Bölüm yoksa (kartsız/
  // dejenere rapor) top3-section'ı oluşturup Önemli Gelişmeler kutusuna koyar.
  function appendCard(cardHtml) {
    if (!cardHtml) return;
    var tmp = document.createElement("div");
    tmp.innerHTML = cardHtml.trim();
    var newCard = tmp.querySelector(".top3-card") || tmp.firstChild;
    if (!newCard) return;
    var section = top3Section();
    if (section) { section.appendChild(newCard); return; }
    var block = document.getElementById("onemli-gelismeler-block");
    if (!block) return;
    var sec = document.createElement("div");
    sec.className = "top3-section";
    sec.appendChild(newCard);
    var bottom = block.querySelector(".block-actions-bottom");
    if (bottom) block.insertBefore(sec, bottom); else block.appendChild(sec);
  }

  // Sil (kritik): index'inci kritik kartı sayfadan kaldırır.
  function deleteCard(index) {
    var cards = topCards();
    if (index >= 0 && index < cards.length && cards[index].parentNode) {
      cards[index].parentNode.removeChild(cards[index]);
    }
  }

  // Alt listeden bir haberi (ve varsa yönetici tablosundaki satırını) kaldırır.
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
