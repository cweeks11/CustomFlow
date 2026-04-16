# Cope Aesthetic Customs — Flask Backend

## Project Structure

```
cope-flask/
├── app.py              ← Flask app — API routes + serves static HTML
├── seed.py             ← Run once to create admin account + sample data
├── requirements.txt    ← Python packages
├── Procfile            ← Tells Railway how to start the app
├── railway.json        ← Railway configuration
└── static/             ← All HTML/CSS/JS files served to the browser
    ├── landing.html
    ├── admin-login.html
    ├── admin-dashboard.html
    └── ... all other pages
```

## Deploying to Railway

### Step 1 — Create a GitHub repo
Upload ALL files in this folder (including the static/ subfolder) to a new GitHub repo.

### Step 2 — Create a new Railway service
1. Go to railway.com → your project
2. Click **+ New Service → GitHub Repo**
3. Select your new repo
4. Railway will auto-detect Python and start building

### Step 3 — Add environment variables
In your Railway service → **Variables** tab, add:
```
DATABASE_URL  = (Railway sets this automatically if you link the PostgreSQL service)
SECRET_KEY    = any-long-random-string-here
```

To link PostgreSQL: in your service → **Variables** → click **Add Reference** → select your PostgreSQL service → select `DATABASE_URL`.

### Step 4 — Run the seed script (one time only)
In Railway → your service → **Settings** → find the terminal/shell option, or add a one-time start command:
```
python seed.py
```
This creates Buffy's admin account and sample data.

### Step 5 — Your app is live
Railway gives you a URL like: `https://cope-flask-production.up.railway.app`

Send Buffy: `https://cope-flask-production.up.railway.app/landing.html`

## Login Credentials (after seeding)
- **Admin (Buffy):** admin@copeaesthetic.com / admin123
- **Customer (test):** customer@email.com / customer123

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/login | Login — returns JWT token |
| POST | /api/register | Register new customer |
| GET | /api/orders | Get orders (all for admin, own for customer) |
| GET | /api/orders/:id | Full order detail |
| POST | /api/orders | Create new order |
| PATCH | /api/orders/:id | Update order (status, tracking, notes, etc.) |
| POST | /api/payments | Log a payment |
| POST | /api/revisions | Add revision request |
| POST | /api/add_ons | Add an add-on service |
| POST | /api/consult_calls | Schedule a consult call |
| GET | /api/orders/:id/invoices | Get invoices for an order |
| POST | /api/invoices/:id/send | Mark invoice as sent |
| GET | /api/queue | Production queue (priority sorted) |
| GET | /api/dashboard | Dashboard stats |
| GET | /api/reports | Revenue analytics |
| GET | /api/users/me | Current user profile |
| PATCH | /api/users/me | Update profile |
| POST | /api/change-password | Change password |
| GET | /api/settings/booking | Booking availability (public) |
| PATCH | /api/settings/booking | Update booking settings (admin) |
| GET | /api/faqs | FAQ list (public) |

## TODO for Full Deployment
- [ ] Wire up SendGrid for emails (welcome email, status change emails, invoice emails)
- [ ] Add file upload to Cloudinary/S3 for mockup images and invoice PDFs
- [ ] Add proper password reset flow
- [ ] Set up SSL/custom domain on Railway
