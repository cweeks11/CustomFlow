// ============================================================
// COPE AESTHETIC CUSTOMS — SHARED CORE (core.js)
// ============================================================
// This file is the single source of truth for the entire app.
// Every HTML page loads this file first via <script src="core.js">
// so they all share the same constants, mock data, and helpers.
//
// WHEN CONNECTING THE REAL FLASK BACKEND:
//   - Keep all the constants (STATUSES, ITEM_TYPES, etc.)
//   - Replace MOCK data with real fetch() calls in each page
//   - The apiFetch() helper below is already wired for that
// ============================================================


// ---- BACKEND URL ----
// Base URL for all API calls to the Flask backend.
// During development with mock data this isn't actively used.
// UPDATE THIS when Flask is deployed to Railway or Buffy's domain.
// API_BASE — empty string means calls go to the same server serving the HTML
// Flask serves both the frontend AND the API, so /api/orders works from anywhere
const API_BASE = '';


// ---- ORDER STATUSES ----
// These match the exact status values stored in the PostgreSQL orders table.
// Each status has a label, color, background, and border so every page
// renders badges consistently without duplicating style logic.
// Pipeline order: free_waitlist → paid_waitlist → production_queue
//                 → prep → painting → completed → shipped → closed
// cancelled is a special exit state, not part of the normal pipeline.
const STATUSES = {
  free_waitlist:   { label: 'Free Waitlist',       color: '#858488', bg: 'rgba(133,132,136,0.15)', border: 'rgba(133,132,136,0.3)' },
  paid_waitlist:   { label: 'Paid Waitlist',       color: '#D8BC84', bg: 'rgba(216,188,132,0.15)', border: 'rgba(216,188,132,0.3)' },
  production_queue:{ label: 'Production Queue',    color: '#6B2FBE', bg: 'rgba(107,47,190,0.2)',   border: 'rgba(107,47,190,0.35)' },
  prep:            { label: 'Prep',                color: '#E8A020', bg: 'rgba(232,160,32,0.15)',  border: 'rgba(232,160,32,0.3)'  },
  painting:        { label: 'Painting',            color: '#F217A5', bg: 'rgba(242,23,165,0.15)',  border: 'rgba(242,23,165,0.3)'  },
  completed:       { label: 'Completed',           color: '#2ECC71', bg: 'rgba(46,204,113,0.12)',  border: 'rgba(46,204,113,0.3)'  },
  shipped:         { label: 'Shipped / Picked Up', color: '#3498DB', bg: 'rgba(52,152,219,0.12)',  border: 'rgba(52,152,219,0.3)'  },
  closed:          { label: 'Closed',              color: '#555',    bg: 'rgba(68,68,68,0.2)',     border: 'rgba(68,68,68,0.35)'   },
  cancelled:       { label: 'Cancelled',           color: '#E74C3C', bg: 'rgba(231,76,60,0.12)',   border: 'rgba(231,76,60,0.3)'   },
};

// STATUS_PIPELINE defines the left-to-right order of the progress bar
// shown on order detail pages. Cancelled is excluded because it is a
// dead end, not a forward step in the workflow.
const STATUS_PIPELINE = [
  'free_waitlist','paid_waitlist','production_queue',
  'prep','painting','completed','shipped','closed'
];

// statusBadge() — generates a colored inline HTML badge for any status string.
// Used in every orders table and order detail page to show the current stage.
// Takes a raw status string (e.g. "painting") and returns an HTML <span>.
function statusBadge(s) {
  const k  = (s || '').toLowerCase().replace(/ /g, '_'); // normalize the key
  const st = STATUSES[k] || STATUSES.free_waitlist;       // fallback if unknown
  return `<span style="display:inline-block;padding:3px 10px;border-radius:3px;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;background:${st.bg};color:${st.color};border:1px solid ${st.border};">${st.label}</span>`;
}


// ---- ITEM TYPES ----
// The 10 types of items Buffy customizes. Populates the order form item
// picker and the landing page "Wear Your Story" section.
// Add new types here and they automatically appear everywhere.
const ITEM_TYPES = [
  'Sneakers','Boots','Cleats','Skates','Jacket',
  'Graduation Cap','Helmet','Denim Vest','Bag','Other'
];


// ---- PRICING TIERS ----
// The four pricing options a customer selects when placing an order.
// 'rush' is an add-on applied on top of standard/detailed/premium —
// the rush fee equals 50% of the custom fee (PRD Feature 3).
// Shown on customer-order-form.html step 2 and customer-terms.html.
const PRICING_TIERS = [
  { id: 'standard', label: 'Standard', desc: 'Single color / simple design',           price: '$75+' },
  { id: 'detailed', label: 'Detailed', desc: 'Multi-color / moderate complexity',       price: '$150+' },
  { id: 'premium',  label: 'Premium',  desc: 'Full custom / high detail / large scale', price: '$250+' },
  { id: 'rush',     label: 'Rush',     desc: 'Expedited — subject to approval',         price: '+50% of custom fee' },
];


// ============================================================
// MOCK DATA
// ============================================================
// This entire MOCK object replaces the real PostgreSQL database during
// development and demo. Every table in CustomFlow.sql has a matching
// array here with the same column names so the handoff is a clean swap.
//
// WHEN CONNECTING THE BACKEND — replace direct MOCK reads like:
//   const orders = MOCK.orders
// with real API calls like:
//   const res = await apiFetch('/api/orders')
//   const orders = res.data
// ============================================================
const MOCK = {

  // users table — role: 'owner' | 'employee' | 'customer'
  // notify_email/notify_sms control which notification types they receive
  users: [
    { id:1, name:'Buffy Cope',     email:'admin@copeaesthetic.com',  role:'owner',    phone:'(919) 295-2569', created_at:'2024-01-01' },
    { id:2, name:'James Carter',   email:'customer@email.com',       role:'customer', phone:'(803) 555-1234', created_at:'2026-01-15' },
    { id:3, name:'Aaliyah Monroe', email:'aaliyah@email.com',        role:'customer', phone:'(803) 555-2345', created_at:'2026-02-01' },
    { id:4, name:'Marcus Webb',    email:'marcus@email.com',         role:'customer', phone:'(803) 555-3456', created_at:'2026-02-10' },
  ],

  // orders table — key fields:
  //   pricing_tier:     standard / detailed / premium (customer selects at intake)
  //   is_rush:          true if customer requested rush processing
  //   rush_approved:    true only after Buffy manually approves (PRD Feature 3)
  //   rush_fee:         50% of custom fee — calculated and set by admin
  //   booking_fee_paid: true once the $50 non-refundable booking fee is logged
  //   status:           current pipeline stage (see STATUSES above)
  orders: [
    { id:1047, user_id:2, pricing_tier:'premium',  item_type:'Sneakers',       must_have_by:'2026-04-15', is_rush:false, rush_approved:false, rush_fee:0,   booking_fee_paid:true,  status:'painting',         created_at:'2026-03-01', updated_at:'2026-03-10', admin_notes:'Jordan 1 Bred. Galaxy theme.',       customer_notes:'Deep space purples, blues and pinks. Constellation patterns.' },
    { id:1046, user_id:3, pricing_tier:'detailed', item_type:'Jacket',         must_have_by:'2026-05-01', is_rush:false, rush_approved:false, rush_fee:0,   booking_fee_paid:true,  status:'production_queue', created_at:'2026-03-05', updated_at:'2026-03-08', admin_notes:'',                                   customer_notes:'Colorful lion design on back of jean jacket.' },
    { id:1045, user_id:4, pricing_tier:'premium',  item_type:'Graduation Cap', must_have_by:'2026-05-10', is_rush:true,  rush_approved:true,  rush_fee:125, booking_fee_paid:true,  status:'prep',             created_at:'2026-03-08', updated_at:'2026-03-12', admin_notes:'Grateful Dead theme. Rush approved.', customer_notes:'Grateful Dead themed grad cap — skull with roses.' },
    { id:1044, user_id:2, pricing_tier:'standard', item_type:'Sneakers',       must_have_by:null,         is_rush:false, rush_approved:false, rush_fee:0,   booking_fee_paid:false, status:'free_waitlist',    created_at:'2026-03-15', updated_at:'2026-03-15', admin_notes:'',                                   customer_notes:'Simple custom Vans — Buffy the Vampire Slayer theme.' },
    { id:1043, user_id:3, pricing_tier:'detailed', item_type:'Boots',          must_have_by:'2026-04-30', is_rush:false, rush_approved:false, rush_fee:0,   booking_fee_paid:true,  status:'paid_waitlist',    created_at:'2026-03-12', updated_at:'2026-03-12', admin_notes:'',                                   customer_notes:'Skull and flowers. Dia de los Muertos style.' },
    { id:1042, user_id:4, pricing_tier:'premium',  item_type:'Jacket',         must_have_by:null,         is_rush:false, rush_approved:false, rush_fee:0,   booking_fee_paid:true,  status:'completed',        created_at:'2026-02-01', updated_at:'2026-03-01', admin_notes:'Customer approved final.',            customer_notes:'Picasso Girl Before a Mirror inspired leather jacket.' },
    { id:1041, user_id:2, pricing_tier:'standard', item_type:'Sneakers',       must_have_by:null,         is_rush:false, rush_approved:false, rush_fee:0,   booking_fee_paid:true,  status:'shipped',          created_at:'2026-01-10', updated_at:'2026-02-20', admin_notes:'Shipped USPS.',                       customer_notes:'Deadpool AF1s.' },
    { id:1040, user_id:3, pricing_tier:'detailed', item_type:'Cleats',         must_have_by:null,         is_rush:false, rush_approved:false, rush_fee:0,   booking_fee_paid:true,  status:'closed',           created_at:'2025-12-01', updated_at:'2026-01-15', admin_notes:'',                                   customer_notes:'Football cleats custom painted.' },
  ],

  // payments table — one row per payment transaction.
  // An order can have multiple payments (booking fee first, then custom fee, rush fee etc).
  // type:   'booking' | 'custom' | 'rush' | 'cleaning' | 'revision' | 'addon'
  // method: 'Zelle' | 'Venmo' | 'CashApp' | 'PayPal' | 'Other'
  // status: 'paid' | 'pending' | 'refunded'
  payments: [
    { id:1, order_id:1047, amount:50.00,  type:'booking', method:'Zelle',   status:'paid', recorded_at:'2026-03-01' },
    { id:2, order_id:1047, amount:250.00, type:'custom',  method:'Zelle',   status:'paid', recorded_at:'2026-03-05' },
    { id:3, order_id:1046, amount:50.00,  type:'booking', method:'Venmo',   status:'paid', recorded_at:'2026-03-05' },
    { id:4, order_id:1045, amount:50.00,  type:'booking', method:'CashApp', status:'paid', recorded_at:'2026-03-08' },
    { id:5, order_id:1045, amount:250.00, type:'custom',  method:'CashApp', status:'paid', recorded_at:'2026-03-09' },
    { id:6, order_id:1045, amount:125.00, type:'rush',    method:'CashApp', status:'paid', recorded_at:'2026-03-09' },
  ],

  // mockups table — design preview images uploaded by Buffy before painting.
  // revision_limit: always 3 free revisions per PRD Feature 6.
  // approved: set to true when the customer approves the design.
  // approval_at: timestamp of approval — gates production from starting.
  mockups: [
    { id:1, order_id:1047, image_url:'', created_at:'2026-03-10', approved:true,  approval_at:'2026-03-11', revision_limit:3 },
    { id:2, order_id:1046, image_url:'', created_at:'2026-03-09', approved:false, approval_at:null,         revision_limit:3 },
  ],

  // revisions table — one row per revision request from the customer.
  // revision_number: 1-3 are free, 4+ each cost $20 (PRD Feature 6).
  // charge_amount: 0 for free revisions, $20 for paid ones.
  // mockup_id: links to the specific mockup being revised.
  revisions: [
    { id:1, order_id:1047, mockup_id:1, revision_number:1, notes:'Please make the stars larger', created_at:'2026-03-10', charge_amount:0 },
    { id:2, order_id:1047, mockup_id:1, revision_number:2, notes:'Perfect, approved!',           created_at:'2026-03-11', charge_amount:0 },
  ],

  // order_images table — all images tied to an order, tagged by type:
  //   'base_photo'  — photo of the item as received before any work
  //   'reference'   — inspiration/reference photos uploaded by the customer
  //   'mockup'      — design preview images uploaded by Buffy
  // In production, url will be a Cloudinary or S3 link.
  order_images: [
    { id:1, order_id:1047, url:'', type:'reference',  uploaded_at:'2026-03-01' },
    { id:2, order_id:1047, url:'', type:'base_photo', uploaded_at:'2026-03-01' },
    { id:3, order_id:1047, url:'', type:'mockup',     uploaded_at:'2026-03-10' },
  ],

  // status_history table — every status change appends a new row here.
  // Creates the full timeline shown on admin and customer order detail pages.
  // changed_by: user.id of whoever made the change (admin or customer).
  status_history: [
    { id:1, order_id:1047, from_status:'free_waitlist',    to_status:'paid_waitlist',    changed_by:2, changed_at:'2026-03-02', note:'Booking fee paid' },
    { id:2, order_id:1047, from_status:'paid_waitlist',    to_status:'production_queue', changed_by:1, changed_at:'2026-03-05', note:'Full invoice paid, moved to queue' },
    { id:3, order_id:1047, from_status:'production_queue', to_status:'prep',             changed_by:1, changed_at:'2026-03-08', note:'Started item intake and prep' },
    { id:4, order_id:1047, from_status:'prep',             to_status:'painting',         changed_by:1, changed_at:'2026-03-10', note:'Painting begun' },
  ],

  // consult_calls table — optional calls scheduled per PRD Feature 5.
  // Priority for scheduling: Rush orders first, date-specific, then standard.
  // completed_by: user.id of the employee/owner who ran the call.
  consult_calls: [
    { id:1, order_id:1045, scheduled_at:'2026-03-09T10:00:00', duration_minutes:30, notes:'Discussed Grateful Dead design details and color palette.', completed_by:1 },
  ],

  // add_ons table — optional services added to an order (PRD Feature 8).
  // Currently the only add-on is AI Photography at $35.
  add_ons: [
    { id:1, order_id:1047, name:'AI Product Photography', price:35.00, quantity:1 },
  ],

  // faqs — editable by admin in Settings → FAQ Management.
  // admin-settings.html writes changes back via MOCK.faqs = [...faqs].
  // In production these would come from a GET /api/faqs endpoint.
  faqs: [
    { q:'What is the return policy?',               a:'All custom orders are final sale. Every piece is one-of-one and made specifically for you.' },
    { q:'How long does an order take?',             a:'Typically 2–4 weeks from when Buffy receives your item, depending on complexity. Rush orders available — subject to approval.' },
    { q:'What can Buffy customize?',                a:'Sneakers, boots, cleats, skates, jackets, denim vests, graduation caps, helmets, bags — if you can wear it, she can probably paint it.' },
    { q:'What shipping methods are offered?',       a:'USPS Priority Mail and UPS Ground. All outbound shipments are insured and tracked.' },
    { q:'Can I pay in installments?',               a:'Yes! A booking fee is required to secure your spot. The balance is due before shipping.' },
    { q:'What is the booking fee?',                 a:'The booking fee is $50 and is non-refundable. It moves your order from the Free Waitlist to the Paid Waitlist.' },
    { q:'How many revisions do I get?',             a:'Up to 3 revisions are included at no charge. Additional revisions beyond 3 are available for a fee.' },
    { q:'What is a rush order?',                    a:'A rush order expedites your placement in the production queue. Rush fee is 50% of your custom fee and requires Buffy\'s approval based on schedule availability.' },
    { q:'What if my item is pre-loved (used)?',     a:'A cleaning fee applies to pre-loved items before painting can begin. This is determined at intake.' },
    { q:'How do I send my item to Buffy?',          a:'After approval and deposit, Buffy will provide her shipping address. Use insured, tracked shipping and enter your tracking number in your portal.' },
    { q:'Can I request a consult call?',            a:'Yes! You can request a consult call to discuss your design vision before production begins. Rush orders receive priority scheduling.' },
  ],

  // pricing — displayed on customer-terms.html (PRD Feature 1).
  // Customers must read this before they can create an account.
  // price_from: null means it varies (e.g. rush is percentage-based).
  pricing: [
    { tier:'Standard',              price_from:75,   desc:'Single color, simple designs, minimal detail work. Perfect for lettering, basic patterns.' },
    { tier:'Detailed',              price_from:150,  desc:'Multi-color work, moderate complexity, character art, layered designs.' },
    { tier:'Premium',               price_from:250,  desc:'Full custom, high detail, large-scale pieces, complex scenes or portraiture.' },
    { tier:'Rush Add-On',           price_from:null, desc:'50% of the custom fee. Subject to Buffy\'s approval based on current schedule.' },
    { tier:'Cleaning Fee',          price_from:25,   desc:'Applied to pre-loved items that require cleaning before painting.' },
    { tier:'AI Photography Add-On', price_from:35,   desc:'Professional AI-enhanced product photography of your finished piece.' },
    { tier:'Extra Revision',        price_from:20,   desc:'Each revision beyond the included 3 free revisions.' },
  ],

  // booking — default availability state shown on landing.html.
  // Admin overrides these in Settings → Booking & Availability.
  // Overrides save to localStorage and are read by getBookingStatus() below.
  // In production this would come from a GET /api/settings endpoint.
  booking: {
    status:           'waitlist',              // 'open' | 'waitlist' | 'booked'
    booked_until:     '2026-05-18',
    message:          'Currently booked through May 18, 2026 — Join the waitlist!',
    production_start: 'May 18, 2026',
  },
};


// ============================================================
// API HELPER
// ============================================================
// apiFetch() wraps the native fetch() API with consistent behavior:
//   - Prepends API_BASE so you write '/api/orders' not the full URL
//   - Attaches the auth token from localStorage to every request
//   - Handles 401 Unauthorized by logging the user out and redirecting
//   - Returns { ok, status, data } so every page handles errors the same way
//
// HOW TO USE IT (once backend is live):
//   const result = await apiFetch('/api/orders')
//   if (result && result.ok) { renderOrders(result.data) }
async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('admin_token') || localStorage.getItem('customer_token');
  const isAdmin = !!localStorage.getItem('admin_token');
  const headers = {
    'Content-Type': 'application/json',
    // Attach JWT token as Bearer — Flask reads this to identify the user
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers,
  };
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    // Token expired or invalid — clear storage and redirect to login
    if (res.status === 401) {
      localStorage.removeItem('admin_token');
      localStorage.removeItem('customer_token');
      localStorage.removeItem('admin_user');
      localStorage.removeItem('customer_user');
      // Small delay so any in-flight renders don't flash before redirect
      setTimeout(() => {
        window.location.href = isAdmin ? 'admin-login.html' : 'customer-login.html';
      }, 50);
      return null;
    }
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    // Network error — Flask is down or no internet connection
    console.error('apiFetch error:', err);
    return null;
  }
}


// ============================================================
// AUTH GUARDS
// ============================================================
// Called at the top of every protected page. If the user has no valid
// token they are immediately redirected before any page content renders.
//
// Login flow: on successful login, a token string is saved to localStorage.
// localStorage persists across browser sessions until logout() removes it.
// In production the token will be a real JWT issued by Flask.

// _jwtExpired() — decodes a JWT payload (no crypto — just checks the exp claim)
// Returns true if the token is missing, malformed, or past its expiry time.
// This is a client-side check only — the server always re-validates the signature.
// Purpose: catch stale tokens immediately on page load instead of showing blank UI
// before the 401 redirect fires.
function _jwtExpired(token) {
  if (!token) return true;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    // exp is in seconds; Date.now() is in ms
    return payload.exp && payload.exp < Math.floor(Date.now() / 1000);
  } catch(e) {
    return true; // malformed token — treat as expired
  }
}

// requireAdminAuth() — call at the top of every admin-*.html page
function requireAdminAuth() {
  const token = localStorage.getItem('admin_token');
  if (!token || _jwtExpired(token)) {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    window.location.href = 'admin-login.html';
    return false;
  }
  return true;
}

// requireCustomerAuth() — call at the top of every customer-*.html page
function requireCustomerAuth() {
  const token = localStorage.getItem('customer_token');
  if (!token || _jwtExpired(token)) {
    localStorage.removeItem('customer_token');
    localStorage.removeItem('customer_user');
    window.location.href = 'customer-login.html';
    return false;
  }
  return true;
}

// Alias — some pages use customerApiFetch, others use apiFetch. Both work.
const customerApiFetch = apiFetch;


// ============================================================
// FORMATTERS
// ============================================================

// formatDate() — converts ISO date/timestamp to "Mar 15, 2026, 2:34 PM EDT"
// Always displays in America/New_York (EST/EDT).
// Timestamps from the server are UTC. If the string has no timezone suffix
// (no Z, no +00:00) we append Z so JS parses it as UTC, not local time.
// Date-only strings (no T) get T12:00:00Z so they show the correct calendar day.
function _toUTC(d) {
  if (!d) return null;
  if (!d.includes('T')) return new Date(d + 'T12:00:00Z'); // date-only
  if (/[Zz]$/.test(d) || /[+-]\d{2}:\d{2}$/.test(d)) return new Date(d); // already has tz
  return new Date(d + 'Z'); // naive UTC from server — add Z
}
function formatDate(d) {
  if (!d) return '—';
  return _toUTC(d).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: 'numeric', minute: '2-digit',
    timeZone: 'America/New_York', timeZoneName: 'short'
  });
}

// formatCurrency() — formats a number as "$250.00" with comma separators
function formatCurrency(n) {
  if (n == null || n === '') return '—';
  return '$' + parseFloat(n).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// formatDatetime() — converts ISO timestamp to "Mar 9, 2026, 10:00 AM EDT"
// Used for consult call timestamps and status history entries.
// Same UTC-safe logic as formatDate().
function formatDatetime(d) {
  if (!d) return '—';
  return _toUTC(d).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: 'numeric', minute: '2-digit',
    timeZone: 'America/New_York', timeZoneName: 'short'
  });
}

// timeAgo() — returns "Today", "Yesterday", or "N days ago"
// Used on order cards to show recency without a full date
function timeAgo(d) {
  if (!d) return '';
  const days = Math.floor((Date.now() - new Date(d).getTime()) / 86400000);
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  return `${days} days ago`;
}


// ============================================================
// TOAST NOTIFICATIONS
// ============================================================
// showToast() — shows a dismissing pop-up at the bottom-right corner.
// Creates the DOM element on first call so pages don't need to add it manually.
// type: 'success' (magenta) | 'error' (red) | 'warning' (orange)
// Auto-dismisses after 3.2 seconds.
function showToast(msg, type = 'success') {
  let t = document.getElementById('toast');
  if (!t) { t = document.createElement('div'); t.id = 'toast'; t.className = 'toast'; document.body.appendChild(t); }
  t.textContent = msg;
  t.style.borderLeftColor = type === 'error' ? '#E74C3C' : type === 'warning' ? '#E8A020' : '#F217A5';
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3200);
}


// ============================================================
// LOGOUT
// ============================================================
// Clears all auth tokens and user data from localStorage, then
// redirects to the public landing page.
// In production also call POST /api/logout to invalidate the server-side token.
function logout() {
  localStorage.removeItem('admin_token');
  localStorage.removeItem('customer_token');
  localStorage.removeItem('admin_user');
  localStorage.removeItem('customer_user');
  window.location.href = 'landing.html';
}


// ============================================================
// BOOKING STATUS
// ============================================================
// getBookingStatus() — reads current booking availability.
//
// How it works:
//   1. Admin sets availability in admin-settings.html → Booking & Availability
//   2. Those values save to localStorage via saveBooking()
//   3. This function reads localStorage, falling back to MOCK.booking defaults
//   4. landing.html and customer-terms.html call this to show the right banner
//
// In production: replace with GET /api/settings/booking
function getBookingStatus() {
  return {
    status:     localStorage.getItem('booking_status')  || MOCK.booking.status,
    until:      localStorage.getItem('booked_until')    || MOCK.booking.booked_until,
    message:    localStorage.getItem('booking_message') || MOCK.booking.message,
    prod_start: localStorage.getItem('prod_start')      || MOCK.booking.production_start,
  };
}


// ============================================================
// PRODUCTION QUEUE SORTING
// ============================================================
// buildProductionQueue() — returns all active orders sorted by priority.
//
// PRIORITY RULES (from PRD Feature 7):
//   Tier 1 — Approved rush orders, sorted by must_have_by (soonest first)
//   Tier 2 — Date-specific non-rush orders (has must_have_by), soonest first
//   Tier 3 — Standard FIFO — sorted by booking fee payment date (oldest first)
//
// ACTIVE STATUSES shown in queue: production_queue, prep, painting
// WAITING STATUSES shown separately: paid_waitlist (paid but not yet in queue)
// EXCLUDED: free_waitlist (no booking fee), completed, shipped, closed, cancelled
//
// BACKEND TODO:
//   Replace this with GET /api/queue which runs this same logic
//   in SQL using ORDER BY with CASE WHEN statements for priority tiers.
//
// Returns: { active: [...], waiting: [...] }
//   active  — orders currently in production (sorted by priority)
//   waiting — paid_waitlist orders waiting to enter the queue (same sort)
function buildProductionQueue() {
  const activeStatuses  = ['production_queue', 'prep', 'painting'];
  const waitingStatuses = ['paid_waitlist'];

  // Helper: get the booking fee payment date for an order.
  // Used as the tiebreaker within Tier 3 (standard FIFO).
  // Falls back to order.created_at if no booking payment is found.
  function bookingPaidDate(order) {
    const pmt = MOCK.payments.find(p =>
      p.order_id === order.id && p.type === 'booking' && p.status === 'paid'
    );
    return pmt ? new Date(pmt.recorded_at) : new Date(order.created_at);
  }

  // Helper: assign a numeric priority tier to an order so we can sort.
  //   1 = approved rush (highest priority)
  //   2 = has a must_have_by date but not rush
  //   3 = standard (lowest priority, FIFO within this tier)
  function priorityTier(order) {
    if (order.is_rush && order.rush_approved) return 1;
    if (order.must_have_by)                   return 2;
    return 3;
  }

  // Main sort function — compares two orders across all three priority rules
  function queueSort(a, b) {
    const tierA = priorityTier(a);
    const tierB = priorityTier(b);

    // Rule 1: Higher priority tier always wins
    if (tierA !== tierB) return tierA - tierB;

    // Rule 2 (tiebreaker for Tier 1 & 2): soonest must_have_by date first
    if (tierA <= 2 && a.must_have_by && b.must_have_by) {
      return new Date(a.must_have_by) - new Date(b.must_have_by);
    }

    // Rule 3 (tiebreaker for Tier 3): oldest booking payment date first (FIFO)
    return bookingPaidDate(a) - bookingPaidDate(b);
  }

  // Filter and sort active orders (in production right now)
  const active = MOCK.orders
    .filter(o => activeStatuses.includes(o.status))
    .sort(queueSort);

  // Filter and sort waiting orders (paid but not yet pulled into production)
  const waiting = MOCK.orders
    .filter(o => waitingStatuses.includes(o.status))
    .sort(queueSort);

  return { active, waiting };
}


// ============================================================
// WELCOME EMAIL TEMPLATE
// ============================================================
// WELCOME_EMAIL_TEMPLATE — the full text of the welcome email sent to
// new customers when they create an account.
//
// BACKEND TODO (Flask + SendGrid/Mailgun):
//   In your POST /api/register route, after saving the new user to the DB:
//
//   import sendgrid
//   from sendgrid.helpers.mail import Mail
//
//   def send_welcome_email(to_name, to_email):
//       message = Mail(
//           from_email='CopeAestheticCustoms@gmail.com',
//           to_emails=to_email,
//           subject=WELCOME_EMAIL_TEMPLATE['subject'],
//           html_content=WELCOME_EMAIL_TEMPLATE['html'](to_name)
//       )
//       sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
//       sg.client.mail.send.post(request_body=message.get())
//
// The template below is stored here so the next dev has the exact
// copy ready to paste into Flask without needing to write it from scratch.
const WELCOME_EMAIL_TEMPLATE = {
  subject: 'Welcome to Cope Aesthetic Customs 🎨',

  // Plain text version (fallback for email clients that don't render HTML)
  text: (name) => `
Hey ${name}!

Welcome to Cope Aesthetic Customs — I'm so excited you're here!

You've just taken the first step toward owning a one-of-one piece of wearable art.
Every custom I create is painted by hand, designed around YOUR story, fandom, or vibe.

Here's what happens next:
  1. Browse your portal to track your order status anytime
  2. Once I review your submission, I'll reach out with a quote
  3. Pay your $50 booking fee to lock in your spot on the Paid Waitlist
  4. When it's your turn, we'll kick off the design process together

In the meantime, feel free to upload reference photos or inspiration
directly in your portal — the more I know about your vision, the better.

Questions? I'm always reachable at:
  Email: CopeAestheticCustoms@gmail.com
  Phone: (919) 295-2569

Can't wait to create something special for you.

— Buffy
Cope Aesthetic Customs
customs.copeaesthetic.studio
  `,

  // HTML version — styled email body
  html: (name) => `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"/>
  <style>
    body { margin:0; padding:0; background:#0D0D0D; font-family: 'Helvetica Neue', Arial, sans-serif; }
    .wrap { max-width:560px; margin:0 auto; background:#161616; border:1px solid #2C2C2C; }
    .header { background:#0D0D0D; padding:32px; text-align:center; border-bottom:1px solid #2C2C2C; }
    .header img { max-width:240px; }
    .body { padding:36px 40px; color:#F0EDE8; font-size:15px; line-height:1.7; }
    .greeting { font-size:22px; font-weight:700; letter-spacing:1px; margin-bottom:8px; }
    .sub { color:#858488; font-size:14px; margin-bottom:28px; font-style:italic; }
    .step { display:flex; gap:14px; margin-bottom:16px; align-items:flex-start; }
    .step-n { background:#F217A5; color:#fff; border-radius:50%; width:24px; height:24px;
              display:inline-flex; align-items:center; justify-content:center;
              font-size:11px; font-weight:700; flex-shrink:0; margin-top:2px; }
    .step-txt { color:#F0EDE8; font-size:14px; line-height:1.6; }
    .step-txt strong { color:#D8BC84; }
    .cta { display:block; margin:28px 0; background:#F217A5; color:#fff; text-decoration:none;
           padding:14px 28px; border-radius:4px; font-size:12px; font-weight:700;
           letter-spacing:2px; text-transform:uppercase; text-align:center; }
    .divider { height:1px; background:#2C2C2C; margin:28px 0; }
    .contact { font-size:13px; color:#858488; }
    .contact a { color:#D8BC84; text-decoration:none; }
    .footer { padding:20px 40px; border-top:1px solid #2C2C2C;
              font-size:11px; color:#444; text-align:center; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <!-- Logo will appear here in production when hosted with an absolute URL -->
      <p style="color:#F217A5;font-size:18px;font-weight:700;letter-spacing:3px;text-transform:uppercase;margin:0;">COPE AESTHETIC CUSTOMS</p>
    </div>
    <div class="body">
      <div class="greeting">Hey ${name}! 🎨</div>
      <div class="sub">"I paint one-of-ones that turn your story, fandom, or vibe into wearable art."</div>
      <p>Welcome to the family — I'm so excited you're here. Every piece I create is hand-painted and designed around <em>you</em>. Let's make something incredible together.</p>

      <p style="font-size:13px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#858488;margin-top:28px;margin-bottom:16px;">Here's what happens next</p>

      <div class="step"><span class="step-n">1</span><div class="step-txt"><strong>Check your portal</strong> — track your order status, upload reference photos, and stay updated anytime.</div></div>
      <div class="step"><span class="step-n">2</span><div class="step-txt"><strong>I'll review your submission</strong> and reach out with a custom quote based on your vision and item type.</div></div>
      <div class="step"><span class="step-n">3</span><div class="step-txt"><strong>Pay your $50 booking fee</strong> to lock in your spot and move from the Free Waitlist to the Paid Waitlist.</div></div>
      <div class="step"><span class="step-n">4</span><div class="step-txt"><strong>When it's your turn</strong>, we'll kick off the design process — mockups, revisions, and painting.</div></div>

      <a href="https://customs.copeaesthetic.studio/customer-portal.html" class="cta">Go to My Portal →</a>

      <div class="divider"></div>
      <div class="contact">
        Questions? Reach me anytime:<br/>
        <a href="mailto:CopeAestheticCustoms@gmail.com">CopeAestheticCustoms@gmail.com</a> &nbsp;·&nbsp;
        <a href="tel:9192952569">(919) 295-2569</a>
      </div>
    </div>
    <div class="footer">
      © 2026 Cope Aesthetic Customs · by Buffy<br/>
      <a href="https://customs.copeaesthetic.studio" style="color:#444;">customs.copeaesthetic.studio</a>
    </div>
  </div>
</body>
</html>
  `,
};


// ============================================================
// INVOICES MOCK DATA
// ============================================================
// Each order can have up to 5 invoice types. This array stores
// invoices that Buffy has uploaded per order.
//
// invoice type values:
//   'booking'  — $50 booking fee deposit invoice
//   'custom'   — main custom fee quote invoice
//   'rush'     — rush fee invoice (only if rush approved)
//   'cleaning' — cleaning fee (only if item is pre-loved)
//   'final'    — final balance invoice sent before shipping
//
// status values: 'uploaded' | 'sent'
// sent_at: timestamp of when it was sent to the customer
// file_url: in production this will be a Cloudinary/S3 PDF link
//           in mock/demo it stores a base64 data URL or empty string
//
// BACKEND TODO:
//   GET  /api/orders/:id/invoices   — fetch all invoices for an order
//   POST /api/orders/:id/invoices   — upload a new invoice (multipart PDF)
//   POST /api/invoices/:id/send     — mark as sent + trigger email to customer
MOCK.invoices = [
  { id:1, order_id:1047, type:'booking', label:'Booking Fee Invoice', amount:50.00,  status:'sent',     uploaded_at:'2026-03-01', sent_at:'2026-03-01', file_url:'' },
  { id:2, order_id:1047, type:'custom',  label:'Custom Fee Invoice',  amount:250.00, status:'sent',     uploaded_at:'2026-03-05', sent_at:'2026-03-05', file_url:'' },
  { id:3, order_id:1045, type:'booking', label:'Booking Fee Invoice', amount:50.00,  status:'sent',     uploaded_at:'2026-03-08', sent_at:'2026-03-08', file_url:'' },
  { id:4, order_id:1045, type:'rush',    label:'Rush Fee Invoice',    amount:125.00, status:'sent',     uploaded_at:'2026-03-09', sent_at:'2026-03-09', file_url:'' },
  { id:5, order_id:1046, type:'booking', label:'Booking Fee Invoice', amount:50.00,  status:'uploaded', uploaded_at:'2026-03-05', sent_at:null,         file_url:'' },
];


// ============================================================
// STATUS CHANGE EMAIL TEMPLATES
// ============================================================
// STATUS_EMAIL_TEMPLATES — unique customer-facing email content
// for every stage in the order pipeline.
//
// Each stage has:
//   subject  — email subject line
//   headline — big bold heading inside the email body
//   message  — the body paragraph explaining what this status means
//   cta      — call-to-action button label
//
// BACKEND TODO (Flask):
//   Call send_status_email(order, new_status) inside your
//   PATCH /api/orders/:id route whenever status changes.
//
//   def send_status_email(order, new_status):
//       customer = get_user(order.user_id)
//       template = STATUS_EMAIL_TEMPLATES[new_status]  # same structure below
//       html = render_status_email_html(customer.name, order, template)
//       send_via_sendgrid(
//           to=customer.email,
//           subject=template['subject'],
//           html=html
//       )
//
// The full HTML renderer is buildStatusEmailHtml() below.
const STATUS_EMAIL_TEMPLATES = {

  paid_waitlist: {
    subject:  'Your spot is locked in! 🔒',
    headline: 'You\'re on the Paid Waitlist',
    message:  'Your booking fee has been received and your spot in line is secured. Buffy will be in touch with your full quote and next steps. Keep an eye on your portal for updates.',
    cta:      'View My Order',
    emoji:    '🔒',
  },

  production_queue: {
    subject:  'You\'re in the Production Queue! 🎨',
    headline: 'You\'ve Entered the Production Queue',
    message:  'Your full invoice has been paid and your order is now in the production queue. Buffy will begin working on your piece based on the current schedule. You\'ll hear from her soon!',
    cta:      'Track My Order',
    emoji:    '🎨',
  },

  prep: {
    subject:  'Buffy has your item — prep has started 📦',
    headline: 'Prep Stage Has Begun',
    message:  'Buffy has received your item and prep work has started. This includes cleaning, priming, and any surface preparation needed before painting begins. Almost time for the magic!',
    cta:      'View My Order',
    emoji:    '📦',
  },

  painting: {
    subject:  'Painting has begun on your custom! 🖌️',
    headline: 'The Brush Is Moving',
    message:  'Buffy has started painting your one-of-one. This is where the magic happens. You\'ll receive a mockup or progress update soon. Sit tight — something incredible is being made.',
    cta:      'View My Order',
    emoji:    '🖌️',
  },

  completed: {
    subject:  'Your custom is DONE! 🎉',
    headline: 'Your Piece Is Complete',
    message:  'Buffy has finished your one-of-one — and it looks incredible. Your item is ready. Please make sure your final balance is paid so we can get it shipped out to you ASAP.',
    cta:      'View & Pay Balance',
    emoji:    '🎉',
  },

  shipped: {
    subject:  'Your custom has shipped! 🚚',
    headline: 'It\'s On Its Way to You',
    message:  'Your finished piece has been packaged and shipped. Your tracking number is available in your portal. Keep an eye on the delivery — your one-of-one is almost home.',
    cta:      'Track My Shipment',
    emoji:    '🚚',
  },

  closed: {
    subject:  'Your order is complete — thank you! ✨',
    headline: 'Order Closed',
    message:  'Your order has been officially closed. Thank you so much for trusting Buffy with your vision. We hope you love your piece. Tag us when you wear it!',
    cta:      'View My Order',
    emoji:    '✨',
  },

  cancelled: {
    subject:  'Your order has been cancelled',
    headline: 'Order Cancelled',
    message:  'Your order has been cancelled. If you have questions or believe this was a mistake, please reach out to Buffy directly at CopeAestheticCustoms@gmail.com or (919) 295-2569.',
    cta:      'Contact Buffy',
    emoji:    '❌',
  },
};


// ============================================================
// STATUS EMAIL HTML BUILDER
// ============================================================
// buildStatusEmailHtml() — generates the full HTML email body for a
// status change notification sent to the customer.
//
// Parameters:
//   customerName — the customer's first name (e.g. "James")
//   orderItem    — the item type (e.g. "Sneakers")
//   orderId      — the order number (e.g. 1047)
//   template     — one entry from STATUS_EMAIL_TEMPLATES above
//   portalUrl    — full URL to the customer's order detail page
//
// BACKEND TODO:
//   Import this logic into Flask as a Jinja2 template or inline string.
//   Call it inside send_status_email() and pass the result to SendGrid.
function buildStatusEmailHtml(customerName, orderItem, orderId, template, portalUrl) {
  return `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"/>
<style>
  body{margin:0;padding:0;background:#0D0D0D;font-family:'Helvetica Neue',Arial,sans-serif;}
  .wrap{max-width:560px;margin:0 auto;background:#161616;border:1px solid #2C2C2C;}
  .header{background:#0D0D0D;padding:28px 32px;border-bottom:2px solid #F217A5;text-align:center;}
  .header-brand{color:#F217A5;font-size:14px;font-weight:700;letter-spacing:3px;text-transform:uppercase;}
  .body{padding:36px 40px;color:#F0EDE8;font-size:15px;line-height:1.7;}
  .emoji{font-size:40px;text-align:center;margin-bottom:16px;}
  .headline{font-size:24px;font-weight:700;letter-spacing:1px;margin-bottom:8px;text-align:center;}
  .order-chip{display:inline-block;background:#1F1F1F;border:1px solid #2C2C2C;border-radius:4px;
    padding:5px 14px;font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#858488;
    margin:0 auto 24px;display:block;text-align:center;}
  .message{color:#B0ADB3;font-size:14px;line-height:1.8;margin-bottom:28px;text-align:center;}
  .cta{display:block;background:#F217A5;color:#fff;text-decoration:none;padding:14px 28px;
    border-radius:4px;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;
    text-align:center;margin:0 auto 32px;max-width:220px;}
  .divider{height:1px;background:#2C2C2C;margin:0 0 24px;}
  .contact{font-size:12px;color:#555;text-align:center;line-height:1.8;}
  .contact a{color:#D8BC84;text-decoration:none;}
  .footer{padding:18px 40px;border-top:1px solid #2C2C2C;font-size:11px;color:#333;text-align:center;}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="header-brand">Cope Aesthetic Customs</div>
  </div>
  <div class="body">
    <div class="emoji">${template.emoji}</div>
    <div class="headline">${template.headline}</div>
    <div class="order-chip">${orderItem} · Order #${orderId}</div>
    <div class="message">Hey ${customerName}, ${template.message}</div>
    <a href="${portalUrl}" class="cta">${template.cta} →</a>
    <div class="divider"></div>
    <div class="contact">
      Questions? Reach Buffy anytime:<br/>
      <a href="mailto:CopeAestheticCustoms@gmail.com">CopeAestheticCustoms@gmail.com</a>
      &nbsp;·&nbsp;
      <a href="tel:9192952569">(919) 295-2569</a>
    </div>
  </div>
  <div class="footer">© 2026 Cope Aesthetic Customs · by Buffy</div>
</div>
</body>
</html>`;
}


// ============================================================
// INVOICE EMAIL HTML BUILDER
// ============================================================
// buildInvoiceEmailHtml() — generates the customer-facing email sent
// when Buffy uploads and sends an invoice.
//
// BACKEND TODO:
//   Call inside POST /api/invoices/:id/send
//   Attach the PDF as an email attachment via SendGrid's Attachments API.
//
//   message.add_attachment(Attachment(
//       FileContent(base64_pdf),
//       FileName(f'cope-invoice-{invoice.type}-order-{order.id}.pdf'),
//       FileType('application/pdf'),
//       Disposition('attachment')
//   ))
function buildInvoiceEmailHtml(customerName, orderItem, orderId, invoiceLabel, amount, portalUrl) {
  return `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"/>
<style>
  body{margin:0;padding:0;background:#0D0D0D;font-family:'Helvetica Neue',Arial,sans-serif;}
  .wrap{max-width:560px;margin:0 auto;background:#161616;border:1px solid #2C2C2C;}
  .header{background:#0D0D0D;padding:28px 32px;border-bottom:2px solid #D8BC84;text-align:center;}
  .header-brand{color:#D8BC84;font-size:14px;font-weight:700;letter-spacing:3px;text-transform:uppercase;}
  .body{padding:36px 40px;color:#F0EDE8;font-size:15px;line-height:1.7;}
  .emoji{font-size:40px;text-align:center;margin-bottom:16px;}
  .headline{font-size:24px;font-weight:700;letter-spacing:1px;margin-bottom:8px;text-align:center;}
  .invoice-box{background:#1F1F1F;border:1px solid #2C2C2C;border-radius:8px;padding:20px 24px;margin:0 0 24px;}
  .inv-row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #2C2C2C;font-size:14px;}
  .inv-row:last-child{border:none;padding-top:12px;font-size:16px;font-weight:700;}
  .inv-label{color:#858488;}
  .inv-val{color:#F0EDE8;}
  .inv-total{color:#D8BC84;}
  .message{color:#B0ADB3;font-size:14px;line-height:1.8;margin-bottom:28px;text-align:center;}
  .cta{display:block;background:#D8BC84;color:#0D0D0D;text-decoration:none;padding:14px 28px;
    border-radius:4px;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;
    text-align:center;margin:0 auto 32px;max-width:240px;}
  .attach-note{font-size:12px;color:#555;text-align:center;margin-bottom:24px;}
  .divider{height:1px;background:#2C2C2C;margin:0 0 24px;}
  .contact{font-size:12px;color:#555;text-align:center;line-height:1.8;}
  .contact a{color:#D8BC84;text-decoration:none;}
  .footer{padding:18px 40px;border-top:1px solid #2C2C2C;font-size:11px;color:#333;text-align:center;}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="header-brand">Cope Aesthetic Customs</div>
  </div>
  <div class="body">
    <div class="emoji">🧾</div>
    <div class="headline">You Have a New Invoice</div>
    <div class="invoice-box">
      <div class="inv-row"><span class="inv-label">Order</span><span class="inv-val">${orderItem} · #${orderId}</span></div>
      <div class="inv-row"><span class="inv-label">Invoice Type</span><span class="inv-val">${invoiceLabel}</span></div>
      <div class="inv-row"><span class="inv-label">Amount Due</span><span class="inv-total">$${parseFloat(amount).toFixed(2)}</span></div>
    </div>
    <div class="message">Hey ${customerName}, Buffy has sent you an invoice. The PDF is attached to this email. You can also view it any time in your portal.</div>
    <div class="attach-note">📎 PDF invoice attached to this email</div>
    <a href="${portalUrl}" class="cta">View in My Portal →</a>
    <div class="divider"></div>
    <div class="contact">
      Pay via Zelle, Venmo, or CashApp · Questions?<br/>
      <a href="mailto:CopeAestheticCustoms@gmail.com">CopeAestheticCustoms@gmail.com</a>
      &nbsp;·&nbsp;
      <a href="tel:9192952569">(919) 295-2569</a>
    </div>
  </div>
  <div class="footer">© 2026 Cope Aesthetic Customs · by Buffy</div>
</div>
</body>
</html>`;
}
