// ============================================================
// COPE AESTHETIC CUSTOMS — ADMIN NAVBAR (navbar.js)
// ============================================================
// renderAdminNav() dynamically builds and injects the top navigation bar
// into every admin page. Calling it from a <script> tag at the bottom of
// each admin page means we only define the nav HTML once here — any change
// to the nav automatically applies to all admin pages.
//
// HOW TO USE:
//   Call renderAdminNav('admin-dashboard.html') at the bottom of each page,
//   passing the current page's filename so the correct link gets the
//   "active" highlight style.
// ============================================================

function renderAdminNav(active) {
  // Read the logged-in admin's info from localStorage to show their initial
  // in the avatar circle. Set by admin-login.html on successful login.
  const user = JSON.parse(localStorage.getItem('admin_user') || '{}');
  const init = (user.name || user.email || 'A')[0].toUpperCase();

  // Define all nav links in one place — add new admin pages here
  const links = [
    { href:'admin-dashboard.html', label:'Dashboard' },
    { href:'admin-orders.html',    label:'Orders'    },
    { href:'admin-queue.html',     label:'Queue'     },
    { href:'admin-reports.html',   label:'Reports'   },
    { href:'admin-settings.html',  label:'Settings'  },
  ];

  // Build and prepend the <nav> element to the top of the page
  const nav = document.createElement('nav');
  nav.className = 'nav';
  nav.innerHTML = `
    <div class="nav-logo">
      <img src="logo.png" alt="Cope Aesthetic Customs" />
    </div>
    <div class="nav-links">
      <!-- Loop over links and add "active" class to the current page -->
      ${links.map(l => `<a href="${l.href}" class="nav-a${active === l.href ? ' active' : ''}">${l.label}</a>`).join('')}
    </div>
    <div class="nav-right">
      <span class="nav-chip">Admin</span>
      <!-- Avatar circle shows the user's initial — click opens the dropdown -->
      <div class="nav-avatar" id="navAv" title="${user.email || ''}">${init}</div>
    </div>`;
  document.body.prepend(nav);

  // Build the user dropdown menu that appears when the avatar is clicked
  const drop = document.createElement('div');
  drop.id = 'navDrop';
  drop.style.cssText = 'display:none;position:fixed;top:70px;right:18px;background:var(--s1);border:1px solid var(--b1);border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,0.4);z-index:300;min-width:200px;overflow:hidden;font-family:var(--fd);';
  drop.innerHTML = `
    <!-- Show the logged-in email at the top of the dropdown (read-only) -->
    <div style="padding:10px 16px;font-size:11px;color:var(--txt-m);border-bottom:1px solid var(--b1);">${user.email || 'Admin'}</div>
    <a href="admin-settings.html" style="display:block;padding:11px 16px;font-size:13px;color:var(--txt);text-decoration:none;">⚙️ Settings</a>
    <!-- logout() is defined in core.js — clears tokens and redirects to landing -->
    <button onclick="logout()" style="width:100%;text-align:left;padding:11px 16px;font-size:13px;color:var(--err);background:none;border:none;cursor:pointer;font-family:var(--fd);border-top:1px solid var(--b1);">🚪 Log Out</button>`;
  document.body.appendChild(drop);

  // Toggle dropdown open/closed when avatar is clicked
  document.getElementById('navAv').onclick = () =>
    drop.style.display = drop.style.display === 'none' ? 'block' : 'none';

  // Close dropdown when clicking anywhere else on the page
  document.addEventListener('click', e => {
    if (!e.target.closest('#navAv') && !e.target.closest('#navDrop'))
      drop.style.display = 'none';
  });
}
