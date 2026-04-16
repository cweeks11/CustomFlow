// ============================================================
// COPE AESTHETIC CUSTOMS — NAVBAR (navbar.js)
// ============================================================

function renderAdminNav(active) {
  const user  = JSON.parse(localStorage.getItem('admin_user') || '{}');
  const init  = (user.name || user.email || 'A')[0].toUpperCase();

  const links = [
    { href:'admin-dashboard.html', label:'Dashboard', icon:'📊' },
    { href:'admin-orders.html',    label:'Orders',    icon:'📋' },
    { href:'admin-queue.html',     label:'Queue',     icon:'🎨' },
    { href:'admin-reports.html',   label:'Reports',   icon:'📈' },
    { href:'admin-settings.html',  label:'Settings',  icon:'⚙️' },
  ];

  const nav = document.createElement('nav');
  nav.className = 'nav';
  nav.innerHTML = `
    <div class="nav-logo">
      <img src="logo_gold_transparent.png" alt="Cope Aesthetic Customs" style="height:36px;width:auto;" />
    </div>
    <div class="nav-links">
      ${links.map(l => `<a href="${l.href}" class="nav-a${active === l.href ? ' active' : ''}">${l.label}</a>`).join('')}
    </div>
    <div class="nav-right">
      <span class="nav-chip">Admin</span>
      <div class="nav-avatar" id="navAv" title="${user.email || ''}">${init}</div>
    </div>`;
  document.body.prepend(nav);

  const drop = document.createElement('div');
  drop.id = 'navDrop';
  drop.style.cssText = 'display:none;position:fixed;top:70px;right:18px;background:var(--s1);border:1px solid var(--b1);border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,0.4);z-index:300;min-width:220px;overflow:hidden;font-family:var(--fd);';
  drop.innerHTML = `
    <div style="padding:10px 16px;font-size:11px;color:var(--txt-m);border-bottom:1px solid var(--b1);">${user.email || 'Admin'}</div>
    ${links.map(l => `
      <a href="${l.href}" class="nav-drop-link${active === l.href ? ' nav-drop-active' : ''}"
         style="display:none;padding:11px 16px;font-size:13px;color:var(--txt);text-decoration:none;align-items:center;gap:10px;">
        <span>${l.icon}</span> ${l.label}
      </a>`).join('')}
    <div class="nav-drop-mobile-divider" style="display:none;height:1px;background:var(--b1);"></div>
    <a href="admin-settings.html" class="nav-drop-desktop-only" style="display:flex;padding:11px 16px;font-size:13px;color:var(--txt);text-decoration:none;align-items:center;gap:10px;">⚙️ Settings</a>
    <button onclick="logout()" style="width:100%;text-align:left;padding:11px 16px;font-size:13px;color:var(--err);background:none;border:none;cursor:pointer;font-family:var(--fd);border-top:1px solid var(--b1);display:flex;align-items:center;gap:10px;">🚪 Log Out</button>`;
  document.body.appendChild(drop);

  // Show nav links in dropdown on mobile
  function updateDropdownForMobile() {
    const isMobile = window.innerWidth <= 900;
    drop.querySelectorAll('.nav-drop-link').forEach(el => {
      el.style.display = isMobile ? 'flex' : 'none';
    });
    drop.querySelectorAll('.nav-drop-mobile-divider').forEach(el => {
      el.style.display = isMobile ? 'block' : 'none';
    });
    drop.querySelectorAll('.nav-drop-desktop-only').forEach(el => {
      el.style.display = isMobile ? 'none' : 'flex';
    });
  }
  updateDropdownForMobile();
  window.addEventListener('resize', updateDropdownForMobile);

  document.getElementById('navAv').onclick = () =>
    drop.style.display = drop.style.display === 'none' ? 'block' : 'none';

  document.addEventListener('click', e => {
    if (!e.target.closest('#navAv') && !e.target.closest('#navDrop'))
      drop.style.display = 'none';
  });
}


function renderCustomerNav(active) {
  const user = JSON.parse(localStorage.getItem('customer_user') || '{}');
  const name = user.name || '';
  const init = (name || user.email || 'C')[0].toUpperCase();

  const links = [
    { href:'customer-portal.html',     label:'My Orders', icon:'📦' },
    { href:'customer-order-form.html', label:'New Order',  icon:'✨' },
    { href:'customer-track.html',      label:'Track',      icon:'🔍' },
    { href:'customer-settings.html',   label:'Settings',   icon:'⚙️' },
  ];

  const nav = document.createElement('nav');
  nav.className = 'nav';
  nav.innerHTML = `
    <div class="nav-logo">
      <img src="logo_white_transparent.png" alt="Cope Aesthetic Customs" style="height:36px;width:auto;" />
    </div>
    <div class="nav-links">
      ${links.map(l => `<a href="${l.href}" class="nav-a${active === l.href ? ' active' : ''}">${l.label}</a>`).join('')}
    </div>
    <div class="nav-right">
      <div class="nav-avatar" id="navAv" title="${user.email || ''}">${init}</div>
    </div>`;
  document.body.prepend(nav);

  // Dropdown — always shows all links on both desktop and mobile
  const drop = document.createElement('div');
  drop.id = 'navDrop';
  drop.style.cssText = 'display:none;position:fixed;top:70px;right:18px;background:var(--s1);border:1px solid var(--b1);border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,0.4);z-index:300;min-width:220px;overflow:hidden;font-family:var(--fd);';
  drop.innerHTML = `
    <div style="padding:12px 16px;border-bottom:1px solid var(--b1);">
      <div style="font-size:13px;font-weight:700;color:var(--txt);">${name || 'My Account'}</div>
      <div style="font-size:11px;color:var(--txt-m);margin-top:2px;">${user.email || ''}</div>
    </div>
    ${links.map(l => `
      <a href="${l.href}"
         style="display:flex;padding:11px 16px;font-size:13px;color:${active === l.href ? 'var(--mg)' : 'var(--txt)'};text-decoration:none;align-items:center;gap:10px;${active === l.href ? 'background:rgba(242,23,165,0.06);font-weight:700;' : ''}">
        <span>${l.icon}</span> ${l.label}
      </a>`).join('')}
    <div style="height:1px;background:var(--b1);"></div>
    <button onclick="logoutCustomer()" style="width:100%;text-align:left;padding:11px 16px;font-size:13px;color:var(--err);background:none;border:none;cursor:pointer;font-family:var(--fd);display:flex;align-items:center;gap:10px;">🚪 Log Out</button>`;
  document.body.appendChild(drop);

  document.getElementById('navAv').onclick = () =>
    drop.style.display = drop.style.display === 'none' ? 'block' : 'none';

  document.addEventListener('click', e => {
    if (!e.target.closest('#navAv') && !e.target.closest('#navDrop'))
      drop.style.display = 'none';
  });
}

function logoutCustomer() {
  localStorage.removeItem('customer_token');
  localStorage.removeItem('customer_user');
  window.location.href = 'customer-login.html';
}
