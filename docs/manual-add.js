/*
 * Manuel Haber Ekle — anasayfa (index.html) pop-up'ı.
 *
 * Akış:
 *   1. Anasayfada sağ üstteki "Manuel Haber Ekle" butonu bu pop-up'ı açar.
 *   2. Kullanıcı: şifre + eklenecek haberin URL'si girer, 3 kritik haberden
 *      çıkarılacak olanı işaretler.
 *   3. "Tamam" → sunucudaki /api/manual-add uç noktasına POST gider.
 *      Sunucu URL'yi çeker, BİZİM sistemin promptu/formatıyla paragraf üretir,
 *      docs/index.html + o günün arşiv raporundaki YALNIZCA ilgili kritik
 *      kartı değiştirip main'e commit eder ve üretilen kartı geri döner.
 *   4. Dönen kart, sayfadaki ilgili kart ile ANINDA değiştirilir.
 *
 * NOT: Tüm asıl iş (URL getirme, LLM, dosya yazma, commit) SUNUCU tarafında
 * çalışır. Bu dosya yalnızca arayüz + uç noktaya istek atar.
 */
(function () {
  "use strict";

  // ── Sunucu uç noktası — Vercel'e deploy ettikten sonra BURAYI doldur ──────
  // Dosya api/manual_add.py olduğundan yol /api/manual_add olur:
  // Örn: "https://siberguvenlik-xxxx.vercel.app/api/manual_add"
  var MANUAL_ADD_ENDPOINT = "";

  // ── Stiller (kendi içine enjekte eder, ayrı CSS dosyası gerekmez) ─────────
  var CSS = [
    ".manual-add-btn{position:absolute;top:50%;right:150px;transform:translateY(-50%);",
    "background:#1d4ed8;color:#fff;border:none;border-radius:20px;padding:7px 14px;",
    "cursor:pointer;font-size:12px;font-weight:600;display:flex;align-items:center;gap:6px;",
    "z-index:10;transition:background .2s;font-family:inherit;}",
    ".manual-add-btn:hover{background:#1e40af;}",
    "@media (max-width:760px){.manual-add-btn{position:static;transform:none;margin:10px auto 0;}}",
    "[data-theme='dark'] .manual-add-btn{background:#388bfd;}",
    "[data-theme='dark'] .manual-add-btn:hover{background:#58a6ff;}",
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

    var overlay = document.createElement("div");
    overlay.className = "ma-overlay";
    overlay.id = "ma-overlay";
    overlay.innerHTML =
      '<div class="ma-modal" role="dialog" aria-modal="true">' +
        "<h3>Manuel Haber Ekle</h3>" +
        '<div class="ma-msg" id="ma-msg"></div>' +
        '<div class="ma-body">' +
          '<label class="fld" for="ma-pass">Şifre</label>' +
          '<input type="password" id="ma-pass" autocomplete="off" placeholder="••••••••">' +
          '<label class="fld" for="ma-url">Eklenecek haberin URL\'si</label>' +
          '<input type="url" id="ma-url" placeholder="https://...">' +
          '<label class="fld">Çıkarılacak haberi işaretleyin</label>' +
          '<div class="ma-remove-list">' + optsHtml + "</div>" +
          '<p class="ma-hint">İşaretlenen kritik haber, URL\'den üretilecek yeni haberle değiştirilecek. Raporda başka hiçbir şey değişmez.</p>' +
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
  };

  function submit() {
    var pass = (document.getElementById("ma-pass").value || "").trim();
    var url = (document.getElementById("ma-url").value || "").trim();
    var checked = document.querySelector('input[name="ma-remove"]:checked');

    if (!pass) { showMsg("err", "Şifre giriniz."); return; }
    if (!/^https?:\/\//i.test(url)) { showMsg("err", "Geçerli bir URL giriniz (http/https)."); return; }
    if (!checked) { showMsg("err", "Çıkarılacak haberi işaretleyiniz."); return; }
    if (!MANUAL_ADD_ENDPOINT) {
      showMsg("err", "Sunucu uç noktası yapılandırılmamış (manual-add.js → MANUAL_ADD_ENDPOINT).");
      return;
    }

    var removeIndex = parseInt(checked.value, 10);
    var okBtn = document.getElementById("ma-ok");
    okBtn.disabled = true;
    showMsg("info", "Haber çekiliyor ve sistem formatında hazırlanıyor… (bu işlem biraz sürebilir)");

    fetch(MANUAL_ADD_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pass, url: url, remove_index: removeIndex })
    })
      .then(function (r) {
        return r.json().then(function (data) { return { status: r.status, data: data }; });
      })
      .then(function (res) {
        if (res.status === 200 && res.data && res.data.ok) {
          applyCard(removeIndex, res.data.card_html);
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
})();
