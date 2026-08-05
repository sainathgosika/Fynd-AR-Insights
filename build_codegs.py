"""
Reads the slim HTML and produces a SINGLE code.gs file with the HTML
embedded as a base64 string (chunked for editor friendliness).

Apps Script side also contains:
  - JSON data feed (existing)
  - Follow-up email module: preview, send single, send bulk, activity log

Usage:  python3 build_codegs.py
Output: $AR_OUT_DIR/code.gs   (defaults to /sessions/.../mnt/outputs locally
        and to ./build in CI — see .github/workflows/deploy-appsscript.yml)

The output directory is chosen via the AR_OUT_DIR env var so this script
stays in lockstep with build_v4.py (which uses the same env var). Without
this shared convention the CI clasp deploy silently fails because
build_v4.py writes the slim HTML to ./build and build_codegs.py then
looks for it under /sessions/... — a path that only exists in the local
cowork sandbox.
"""
import base64, os, textwrap

# Resolve output/input directory the same way build_v4.py does. Fallback
# is the historical cowork sandbox path so local dev keeps working.
_OUT_DIR = os.environ.get('AR_OUT_DIR') or (
    '/sessions/serene-keen-mendel/mnt/outputs'
)
os.makedirs(_OUT_DIR, exist_ok=True)

SLIM_HTML = os.path.join(_OUT_DIR, 'Fynd_Receivables_Insights__slim.html')
OUT       = os.path.join(_OUT_DIR, 'code.gs')

with open(SLIM_HTML, 'rb') as f:
    html_bytes = f.read()

b64 = base64.b64encode(html_bytes).decode('ascii')
# Chunk to ~100-char lines so the Apps Script editor doesn't lag
chunks = textwrap.wrap(b64, 100)
chunk_block = ',\n  '.join("'" + c + "'" for c in chunks)

GS = r'''/**
 * Fynd · Receivables Insights — Live Web App  (v4.0 / follow-up emails)
 * ---------------------------------------------------------------------
 * Single-file Apps Script. The dashboard HTML is embedded as base64 at
 * the bottom of this file. Same /exec URL serves:
 *   • dashboard HTML        (default)
 *   • JSON data feed        (?action=data)
 *   • follow-up preview     (?action=previewBU&bus=Apparel,Footwear)
 *   • single preview        (?action=previewOne&cid=12345)
 *   • single send           (?action=sendOne&cid=12345)
 *   • bulk send             (?action=sendBulk&cids=12345,67890[&force=1])
 *   • activity log read     (?action=activityLog&from=2026-05-01&to=2026-05-31)
 *   • monthly report build  (?action=monthlyReport&month=2026-05)
 *
 * Required sheet tabs (besides existing AR_Data / PDD_Data / Bank_Receipts):
 *   Customer_Contacts  →  CID | Customer Name | To Email | CC Emails | Account Owner | Notes
 *   Email_Log          →  auto-created on first send if missing
 *
 * Sender setup (one-time):  Gmail → Settings → Accounts → Send mail as
 * → add ar@gofynd.com → verify via the link sent to that inbox.
 * ---------------------------------------------------------------------
 */

// === CORE CONFIG ===============================================
var SHEET_ID = '1DzwXzGyGQ_uAdo9gK92vIuLGjpwbSKCVmL42AWq8Gs4';

var TAB_AR_CANDIDATES   = ['AR_Data', 'AR Data', 'ARData', 'AR'];
var TAB_PDD_CANDIDATES  = ['PDD_Data', 'PDD Data', 'PDDData', 'PDD'];
var TAB_BANK_CANDIDATES = ['Bank_Receipts', 'Bank receipts', 'Bank Receipts', 'BankReceipts', 'Bank Receipt'];

var ERROR_TOKENS = ['#N/A','#REF!','#VALUE!','#NAME?','#DIV/0!','#NULL!','#ERROR!'];

// === FOLLOW-UP EMAIL CONFIG ====================================
var CONTACTS_TAB        = 'Customer_Contacts';
var LOG_TAB             = 'Email_Log';
// User_Audit_Log — append-only audit trail of every user-initiated action.
// Populated via auditLogRoute_. Auto-created on first write with header row:
//   Timestamp | User | Action | Details | UserAgent
var AUDIT_TAB           = 'User_Audit_Log';
var FOLLOWUP_SENDER     = 'ar@gofynd.com';
var FOLLOWUP_BCC        = 'sainathgosika@gofynd.com';
var FOLLOWUP_REPLY_TO   = 'ar@gofynd.com';
var FOLLOWUP_FROM_NAME  = 'Fynd Accounts Receivable';
var COOLDOWN_HOURS      = 24;
var BULK_DELAY_MS       = 1000;  // pacing between sends

// === CUSTOMER POC CONFIG =======================================
// Customer_POCs supersedes the flat Customer_Contacts tab. It is normalized
// (one row per contact person) so a customer can have 1..N POCs with their
// own name / role / email / phone / priority. readContacts_ prefers this tab
// when present and falls back to the legacy tab for backward compatibility.
var POCS_TAB            = 'Customer_POCs';
var POC_HEADERS         = [
  'CID', 'Customer Name', 'Contact Name', 'Role', 'Email', 'Phone',
  'Priority', 'Active', 'Notes', 'Updated By', 'Updated At'
];
var POC_PRIORITIES      = ['Primary', 'CC', 'Escalation'];

// === INTERNAL STAKEHOLDERS CONFIG ==============================
// Internal_Stakeholders mirrors Customer_POCs but tracks Fynd (Gofynd)
// internal owners per CID — Account Managers, KAMs, backup owners. The
// consolidated view of this tab is BCC'd on every outgoing customer
// follow-up so leadership is always in the loop. Escalation-priority
// stakeholders are only BCC'd when the outgoing email is at escalation
// stage.
var IS_TAB          = 'Internal_Stakeholders';
var IS_HEADERS      = ['CID', 'Customer Name', 'Stakeholder Name', 'Role', 'Email', 'Phone',
                       'Priority', 'Active', 'Notes', 'Updated By', 'Updated At'];
var IS_PRIORITIES   = ['Primary', 'CC', 'Escalation'];

// === WORKFLOW CONFIG ===========================================
// The Workflows tab drives scheduled follow-ups. A daily time trigger
// evaluates every Active workflow, picks the eligible CIDs from the live
// AR_Data snapshot, then either sends immediately (approve = auto) or
// stages a row in Workflow_Queue for an admin to approve (approve = review).
var WORKFLOWS_TAB       = 'Workflows';
var WORKFLOW_HEADERS    = [
  'ID', 'Name', 'Region', 'Trigger Type', 'Trigger Value', 'Template ID',
  'Send Window Days', 'Send Window Start', 'Send Window End',
  'Frequency Cap Days', 'Recipient Rule', 'Approve Mode', 'Active',
  'Created By', 'Created At', 'Updated By', 'Updated At', 'Last Run At',
  // Extended scheduling columns (added 2026-07). `Frequency` is the cadence
  // (daily/weekly/monthly/custom); `Start Date`/`End Date` fence when the
  // workflow is allowed to fire (either can be blank for "no bound");
  // `Day Of Month` (1..31) is used when Frequency=monthly; `Status` supersedes
  // Active — values are Active|Paused|Stopped. The scheduler skips Paused
  // + Stopped rows so admins can pause a workflow without deleting it.
  // `Custom Priorities`, `Internal Priorities`, `Customer Scope`, and `CID List`
  // are new too — needed by the split customer/IS recipient buckets.
  'Frequency', 'Start Date', 'End Date', 'Day Of Month', 'Status',
  'Custom Priorities', 'Internal Priorities', 'Customer Scope', 'CID List'
];
var WORKFLOW_QUEUE_TAB  = 'Workflow_Queue';
var WORKFLOW_QUEUE_HEADERS = [
  'Enqueued At', 'Workflow ID', 'Workflow Name', 'CID', 'Customer',
  'Region', 'Open Invoices', 'Outstanding', 'Oldest Days', 'To Email',
  'CC Email', 'Status', 'Approved By', 'Sent At', 'Error'
];
var WORKFLOW_TZ         = 'Asia/Kolkata';

// === ACCESS MATRIX CONFIG ======================================
// Only this email can view/manage the Access Matrix tab. Everyone else
// gets the tabs listed for their row in Access_Matrix (or — if not listed —
// the dashboard's PUBLIC_TABS default).
var ADMIN_EMAIL  = 'sainathgosika@gofynd.com';
var ACM_TAB      = 'Access_Matrix';
var ACM_HEADERS  = ['Name','Email','Department','Role','Tabs','Provisioned On','Notes','Active','Username','Password Hash','Password Salt','Last Login At','Failed Attempts','Locked Until'];
// Auth sessions — one row per issued token. TTL is FIXED (not sliding); rows
// past ExpiresAt are treated as invalid and are lazily purged when we hit
// the login route or _authCleanupExpiredSessions_() is called.
var SESSIONS_TAB    = 'Auth_Sessions';
var SESSIONS_HEADERS= ['Token','Email','Username','IssuedAt','ExpiresAt','LastSeen','UserAgent'];
var SESSION_TTL_MS  = 12 * 60 * 60 * 1000; // 12 hours fixed (not sliding)
// Tabs anyone signed in (but not listed) can see by default.
// Keys must match the dashboard's `data-target` values.
var ACM_DEFAULT_TABS = ['dashboard'];
// Master list of all dashboard tabs. Keep in sync with the sidebar markup.
var ACM_ALL_TABS = ['dashboard','customers','invoices','pdd','bank','followups','pocs','workflows','worklist','statement','reports','activity','acm'];

// === WORKLIST / COLLECTOR CONFIG ===============================
// Three sheets back the Worklist tab:
//   1) Collector_Master    — who the collectors are
//   2) Collector_CIDs      — which CIDs each collector owns
//   3) Collection_Notes    — append-only call/email notes per customer
var COLLECTOR_TAB         = 'Collector_Master';
var COLLECTOR_HEADERS     = ['Email','Name','Active','Added On'];
var COLLECTOR_CIDS_TAB    = 'Collector_CIDs';
var COLLECTOR_CIDS_HEADERS= ['Collector_Email','CID','Added On'];
var NOTES_TAB             = 'Collection_Notes';
// Invoice_No is column index 4 (0-based). Older rows (pre-invoice-level) have a
// blank Invoice_No — those are treated as "Account-level (archived)" and hidden
// from the UI. The sheet retains them so nothing is lost.
var NOTES_HEADERS         = ['Note ID','Timestamp','Collector Email','CID','Invoice_No','Invoice_Type','Customer Name','Note Text','Follow-up Date','Outcome','P2P Amount','P2P Date'];
var OUTCOME_OPTIONS       = ['Promised to pay','Disputed','No response','Wrong contact','Paid','Escalated','Other'];
// ===============================================================

// Hardcoded email template — change here, redeploy.
var BANK_BLOCK_HTML =
  '<div style="font-family:Arial,sans-serif;font-size:13px;color:#1f2937;line-height:1.7">' +
    '<div style="font-weight:700;text-decoration:underline;margin-bottom:6px">Bank details :</div>' +
    'Beneficiary Name - Shopsense Retail Technologies Limited<br>' +
    'Account No - 643805051548<br>' +
    'IFSC Code - ICIC0006438<br>' +
    'Swift Code - ICICINBBCTS<br>' +
    'Bank Name - ICICI Bank' +
  '</div>';

// ===============================================================
// Email Templates: shared pool, editable by any collector via
// Follow-ups -> Manage Templates. Stored in the Email_Templates sheet.
// ===============================================================
var TAB_EMAIL_TEMPLATES = 'Email_Templates';
var EMAIL_TEMPLATE_HEADERS = ['id','name','subject','greeting','bodyAbove','bodyBelow','signature','includeBank','isDefault','createdBy','createdAt','updatedBy','updatedAt'];
// Subject + 4 body fields support these tokens. Always rendered as HTML so
// collectors can paste <b>, <a href>, line breaks etc. straight in.
var EMAIL_TEMPLATE_TOKENS = ['customer_name','collector_name','total_outstanding','invoice_count','max_overdue_days','today'];
// The legacy hard-coded email becomes the seeded "Default" template the
// first time the sheet is created. New deploys keep working unchanged.
var EMAIL_TEMPLATE_DEFAULT_SEED = {
  name: 'Default - Outstanding Statement',
  subject: 'Outstanding Invoice(s) - {{customer_name}}',
  greeting: 'Hi Team,',
  bodyAbove: 'I hope you are doing well.<br><br>Please find below the current statement of your account with us. As of today, the following invoice(s) remain outstanding:',
  bodyBelow: 'We kindly request you to review the above details and arrange payment accordingly:<ul style="margin:6px 0 10px 22px;padding:0"><li style="margin:4px 0">For <b>overdue invoices</b>, we request immediate payment to avoid further delays.</li><li style="margin:4px 0">For <b>due invoices</b>, please ensure payment is made on or before the due date.</li></ul>If payment has already been initiated, kindly share the UTR details along with invoice-wise breakup for our reference.',
  signature: 'If you have any queries regarding the invoice(s) or require any assistance, please feel free to contact us at <a href="mailto:accounts@gofynd.com" style="color:#2563eb">accounts@gofynd.com</a><br><br>Thank you for your continued business.<br><br>Best regards,<br><b>Accounts Receivable</b><br><span style="color:#64748b">Fynd.</span>',
  includeBank: true,
  isDefault: true
};
var EMAIL_TEMPLATE_GENTLE_SEED = {
  name: 'Gentle Reminder',
  subject: 'Gentle reminder - Outstanding payment - {{customer_name}}',
  greeting: 'Hi Team,',
  bodyAbove: 'Trust this email finds you well.<br><br>This is a gentle reminder regarding the following invoice(s) which are pending payment as of {{today}}:',
  bodyBelow: 'We would appreciate your support in clearing these dues at the earliest. If payment has already been initiated, please share the UTR details for our records.',
  signature: 'For any queries, feel free to reach out to us at <a href="mailto:accounts@gofynd.com" style="color:#2563eb">accounts@gofynd.com</a>.<br><br>Best regards,<br><b>{{collector_name}}</b><br>Accounts Receivable, Fynd',
  includeBank: true,
  isDefault: false
};
var EMAIL_TEMPLATE_ESCALATION_SEED = {
  name: 'Escalation - Overdue',
  subject: 'ESCALATION - Overdue invoices ({{invoice_count}}) - {{customer_name}}',
  greeting: 'Dear Sir/Madam,',
  bodyAbove: 'Despite our earlier follow-ups, the following invoice(s) totalling <b>{{total_outstanding}}</b> remain unpaid and are now overdue by up to <b>{{max_overdue_days}} days</b>:',
  bodyBelow: 'We request you to treat this as a final reminder and arrange payment immediately to avoid further escalation. Continued delay may result in suspension of services and escalation to our senior leadership.<br><br>If you require any clarification or wish to dispute these invoices, please respond to this email within 48 hours.',
  signature: 'Regards,<br><b>{{collector_name}}</b><br>Accounts Receivable, Fynd<br><a href="mailto:accounts@gofynd.com" style="color:#2563eb">accounts@gofynd.com</a>',
  includeBank: true,
  isDefault: false
};

// Convert plain-text newlines (from textareas) to <br>. HTML tags the user
// pasted in (like <b>, <a>, existing <br>) are preserved as-is. Safe to run
// on already-HTML content because we only add <br> for raw \n characters.
function nl2br_(text) {
  if (text == null) return '';
  return String(text).replace(/\r\n/g, '\n').replace(/\n/g, '<br>');
}

// Substitute {{token}} placeholders in a string. ctx is { customer_name: '...', ... }.
// Unknown tokens are left intact (defensive — better than blanking them out).
function emailSubstituteTokens_(text, ctx) {
  if (!text) return '';
  var s = String(text);
  return s.replace(/\{\{\s*([a-z_]+)\s*\}\}/gi, function(m, key) {
    var k = String(key).toLowerCase();
    if (ctx && ctx.hasOwnProperty(k) && ctx[k] !== null && typeof ctx[k] !== 'undefined') {
      return String(ctx[k]);
    }
    return m;
  });
}

// Lazily create the Email_Templates sheet on first read. Seeds it with the
// built-in Default + Gentle Reminder + Escalation templates so collectors
// have something to clone.
function ensureEmailTemplatesSheet_(ss) {
  var sh = ss.getSheetByName(TAB_EMAIL_TEMPLATES);
  var created = false;
  if (!sh) {
    sh = ss.insertSheet(TAB_EMAIL_TEMPLATES);
    sh.getRange(1,1,1,EMAIL_TEMPLATE_HEADERS.length).setValues([EMAIL_TEMPLATE_HEADERS]);
    sh.getRange(1,1,1,EMAIL_TEMPLATE_HEADERS.length).setFontWeight('bold').setBackground('#f1f5f9');
    sh.setFrozenRows(1);
    created = true;
  }
  // Auto-seed if the sheet has no data rows (covers both "just created" and
  // "sheet existed from an earlier deploy with only headers / accidentally emptied").
  // Safe to re-run because we check getLastRow() < 2.
  if (sh.getLastRow() < 2) {
    var nowIso = new Date().toISOString();
    var seeds = [EMAIL_TEMPLATE_DEFAULT_SEED, EMAIL_TEMPLATE_GENTLE_SEED, EMAIL_TEMPLATE_ESCALATION_SEED];
    var rows = seeds.map(function(t, i) {
      return [
        'tpl_' + Date.now() + '_' + i,
        t.name, t.subject, t.greeting, t.bodyAbove, t.bodyBelow, t.signature,
        !!t.includeBank, !!t.isDefault,
        'system', nowIso, 'system', nowIso
      ];
    });
    sh.getRange(2,1,rows.length,EMAIL_TEMPLATE_HEADERS.length).setValues(rows);
  }
  return sh;
}

// Read all templates as objects. Returns array sorted with default first.
function readEmailTemplates_(ss) {
  var sh = ensureEmailTemplatesSheet_(ss);
  var lastRow = sh.getLastRow();
  if (lastRow < 2) return [];
  var values = sh.getRange(2,1,lastRow-1,EMAIL_TEMPLATE_HEADERS.length).getValues();
  var out = values.map(function(r) {
    var obj = {};
    EMAIL_TEMPLATE_HEADERS.forEach(function(h,i) { obj[h] = r[i]; });
    obj.includeBank = (obj.includeBank === true || String(obj.includeBank).toLowerCase() === 'true');
    obj.isDefault   = (obj.isDefault   === true || String(obj.isDefault).toLowerCase() === 'true');
    return obj;
  }).filter(function(t){ return t.id; });
  // Default first, then alpha by name
  out.sort(function(a,b) {
    if (a.isDefault && !b.isDefault) return -1;
    if (!a.isDefault && b.isDefault) return 1;
    return String(a.name||'').localeCompare(String(b.name||''));
  });
  return out;
}

function getEmailTemplateById_(ss, id) {
  if (!id) return null;
  var all = readEmailTemplates_(ss);
  for (var i = 0; i < all.length; i++) {
    if (String(all[i].id) === String(id)) return all[i];
  }
  return null;
}

function getDefaultEmailTemplate_(ss) {
  var all = readEmailTemplates_(ss);
  for (var i = 0; i < all.length; i++) if (all[i].isDefault) return all[i];
  return all[0] || null;
}

// Look up the active user's display name from Collector_Master so token
// substitution can produce "Regards, <Name>" instead of a raw email. Returns
// the friendly name on hit, otherwise the email local-part, otherwise ''.
function resolveCollectorName_(ss) {
  try {
    var em = String((Session.getActiveUser().getEmail() || '')).toLowerCase().trim();
    if (!em) return '';
    var sh = ss.getSheetByName(COLLECTOR_TAB);
    if (sh) {
      var v = sh.getDataRange().getValues();
      if (v.length >= 2) {
        var head = v[0]; var iEm = -1, iNm = -1;
        for (var k = 0; k < head.length; k++) {
          var h = String(head[k]).trim().toLowerCase();
          if (h === 'email') iEm = k;
          if (h === 'name')  iNm = k;
        }
        if (iEm !== -1) {
          for (var i = 1; i < v.length; i++) {
            if (String(v[i][iEm]).toLowerCase().trim() === em) {
              var nm = iNm !== -1 ? String(v[i][iNm] || '').trim() : '';
              if (nm) return nm;
              break;
            }
          }
        }
      }
    }
    return em.split('@')[0] || em;
  } catch (_) { return ''; }
}

// Build the email body using a template + the invoice table. Returns
// { subject, htmlBody, ... } in the same shape as buildFollowUpHtml_.
function buildEmailFromTemplate_(tpl, customerName, invoices, extraCtx) {
  // Aggregate metrics for token substitution
  var sumInv = 0, sumOs = 0, oldest = 0;
  invoices.forEach(function(r) {
    sumInv += Number(r['Invoice_Amount'] || 0);
    sumOs  += Number(r['Outstanding_Amount'] || 0);
    var d = Number(r['Days'] || 0); if (d > oldest) oldest = d;
  });
  var today = Utilities.formatDate(new Date(), Session.getScriptTimeZone() || 'Asia/Kolkata', 'dd-MMM-yyyy');
  var ctx = {
    customer_name:      customerName || '',
    collector_name:     (extraCtx && extraCtx.collector_name) || 'Accounts Receivable',
    total_outstanding:  fmtINR_(sumOs),
    invoice_count:      String(invoices.length),
    max_overdue_days:   String(oldest),
    today:              today
  };

  // Reuse the existing invoice table builder for visual consistency
  var rowsHtml = invoices.map(function(r) {
    return '<tr>' +
      '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px">' + String(r['Invoice_No'] || '') + '</td>' +
      '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px">' + String(r['Channel'] || '') + '</td>' +
      '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px">' + String(r['Transaction_Type'] || '') + '</td>' +
      '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px">' + fmtDate_(r['Invoice_Date']) + '</td>' +
      '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px">' + fmtDate_(r['Due_Date']) + '</td>' +
      '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:right">' + fmtINR_(Number(r['Invoice_Amount'] || 0)) + '</td>' +
      '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:right">' + fmtINR_(Number(r['Outstanding_Amount'] || 0)) + '</td>' +
      '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;color:' + (Number(r['Days']||0) > 0 ? '#b91c1c' : '#1f2937') + '">' +
        (Number(r['Days']||0) > 0 ? 'Overdue by ' + Number(r['Days']) + ' days' : 'Due in ' + Math.abs(Number(r['Days']||0)) + ' days') +
      '</td>' +
    '</tr>';
  }).join('');
  rowsHtml += '<tr style="background:#f8fafc;font-weight:600">' +
      '<td colspan="5" style="padding:10px;border:1px solid #e5e7eb;font-size:12px;text-align:right">Total :</td>' +
      '<td style="padding:10px;border:1px solid #e5e7eb;font-size:12px;text-align:right">' + fmtINR_(sumInv) + '</td>' +
      '<td style="padding:10px;border:1px solid #e5e7eb;font-size:12px;text-align:right">' + fmtINR_(sumOs) + '</td>' +
      '<td style="padding:10px;border:1px solid #e5e7eb"></td>' +
    '</tr>';
  var table =
    '<table cellspacing="0" cellpadding="0" style="border-collapse:collapse;width:100%;margin:14px 0;font-family:Arial,sans-serif">' +
      '<thead><tr style="background:#f1f5f9">' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:left">Invoice Number</th>' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:left">Channel</th>' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:left">Transaction Type</th>' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:left">Invoice Date</th>' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:left">Due Date</th>' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:right">Invoice Amount</th>' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:right">Outstanding Amount</th>' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:left">Days</th>' +
      '</tr></thead>' +
      '<tbody>' + rowsHtml + '</tbody>' +
    '</table>';

  // Substitute tokens in every editable field. Subject stays plain text;
  // body fields are HTML-allowed, but Enter-key newlines from the textarea
  // (\n) need to become <br> so the rendered email respects line breaks.
  var subject   = emailSubstituteTokens_(tpl.subject   || ('Outstanding Invoice(s) - ' + customerName), ctx);
  var greeting  = emailSubstituteTokens_(nl2br_(tpl.greeting  || ''), ctx);
  var above     = emailSubstituteTokens_(nl2br_(tpl.bodyAbove || ''), ctx);
  var below     = emailSubstituteTokens_(nl2br_(tpl.bodyBelow || ''), ctx);
  var signature = emailSubstituteTokens_(nl2br_(tpl.signature || ''), ctx);

  // Assemble body. Each section becomes a <p> only if non-empty so a sparse
  // template doesn't produce ugly empty paragraphs.
  var pieces = ['<div style="font-family:Arial,sans-serif;font-size:14px;color:#1f2937;max-width:920px;line-height:1.55">'];
  if (greeting) pieces.push('<p>' + greeting + '</p>');
  if (above)    pieces.push('<p>' + above + '</p>');
  pieces.push(table);
  pieces.push('<p style="font-size:11px;color:#64748b;font-style:italic">Note: Table may truncate on small devices. View in browser for full table.</p>');
  if (below)    pieces.push('<p>' + below + '</p>');
  if (tpl.includeBank !== false) pieces.push(BANK_BLOCK_HTML);
  if (signature) pieces.push('<p style="margin-top:14px">' + signature + '</p>');
  pieces.push('</div>');

  return {
    subject: subject,
    htmlBody: pieces.join(''),
    invoiceCount: invoices.length,
    invoiceTotal: sumInv,
    outstandingTotal: sumOs,
    oldestDays: oldest
  };
}

// CRUD route handlers ---------------------------------------------------

function emailTemplatesListRoute_(e) {
  try {
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var list = readEmailTemplates_(ss);
    return respond_({ ok: true, rows: list, tokens: EMAIL_TEMPLATE_TOKENS }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

function emailTemplatesSaveRoute_(e) {
  try {
    var p = e.parameter || {};
    var id   = String(p.id || '').trim();
    var name = String(p.name || '').trim();
    if (!name) throw new Error('Template name required');
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sh = ensureEmailTemplatesSheet_(ss);
    var nowIso = new Date().toISOString();
    var actor  = (Session.getActiveUser().getEmail() || 'unknown');
    var record = {
      id:          id || ('tpl_' + Date.now() + '_' + Math.floor(Math.random()*1000)),
      name:        name,
      subject:     String(p.subject || ''),
      greeting:    String(p.greeting || ''),
      bodyAbove:   String(p.bodyAbove || ''),
      bodyBelow:   String(p.bodyBelow || ''),
      signature:   String(p.signature || ''),
      includeBank: String(p.includeBank || 'true') !== 'false',
      isDefault:   String(p.isDefault || 'false') === 'true',
      updatedBy:   actor,
      updatedAt:   nowIso
    };
    var lastRow = sh.getLastRow();
    var rowIdx = -1;
    if (id && lastRow >= 2) {
      var ids = sh.getRange(2,1,lastRow-1,1).getValues();
      for (var i = 0; i < ids.length; i++) {
        if (String(ids[i][0]) === id) { rowIdx = i + 2; break; }
      }
    }
    // If marking this template as default, clear isDefault on all others
    if (record.isDefault && lastRow >= 2) {
      var defaultCol = EMAIL_TEMPLATE_HEADERS.indexOf('isDefault') + 1;
      var rng = sh.getRange(2,defaultCol,lastRow-1,1);
      var vals = rng.getValues();
      for (var j = 0; j < vals.length; j++) vals[j][0] = false;
      rng.setValues(vals);
    }
    if (rowIdx > 0) {
      // Update — preserve createdBy / createdAt
      var existing = sh.getRange(rowIdx,1,1,EMAIL_TEMPLATE_HEADERS.length).getValues()[0];
      var createdBy = existing[EMAIL_TEMPLATE_HEADERS.indexOf('createdBy')] || actor;
      var createdAt = existing[EMAIL_TEMPLATE_HEADERS.indexOf('createdAt')] || nowIso;
      sh.getRange(rowIdx,1,1,EMAIL_TEMPLATE_HEADERS.length).setValues([[
        record.id, record.name, record.subject, record.greeting, record.bodyAbove, record.bodyBelow, record.signature,
        record.includeBank, record.isDefault, createdBy, createdAt, record.updatedBy, record.updatedAt
      ]]);
    } else {
      // Insert
      sh.appendRow([
        record.id, record.name, record.subject, record.greeting, record.bodyAbove, record.bodyBelow, record.signature,
        record.includeBank, record.isDefault, actor, nowIso, record.updatedBy, record.updatedAt
      ]);
    }
    return respond_({ ok: true, id: record.id }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

function emailTemplatesDeleteRoute_(e) {
  try {
    var p = e.parameter || {};
    var id = String(p.id || '').trim();
    if (!id) throw new Error('Missing template id');
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sh = ensureEmailTemplatesSheet_(ss);
    var lastRow = sh.getLastRow();
    if (lastRow < 2) throw new Error('No templates');
    var ids = sh.getRange(2,1,lastRow-1,1).getValues();
    for (var i = 0; i < ids.length; i++) {
      if (String(ids[i][0]) === id) {
        sh.deleteRow(i + 2);
        return respond_({ ok: true, id: id }, e);
      }
    }
    throw new Error('Template not found');
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}
// ===============================================================


/**
 * Router. Same URL serves dashboard HTML or JSON data based on params.
 */
function doGet(e) {
  var p = (e && e.parameter) || {};
  if (p.action === 'previewOne')    return previewOne_(e);
  if (p.action === 'previewBU')     return previewBU_(e);
  if (p.action === 'sendOne')       return sendOneRoute_(e);
  if (p.action === 'sendBulk')      return sendBulkRoute_(e);
  if (p.action === 'activityLog')   return activityLogRoute_(e);
  // User audit log — write from any authed viewer; read is admin-only.
  if (p.action === 'auditLog')      return auditLogRoute_(e);
  if (p.action === 'auditLogList')  return auditLogListRoute_(e);
  if (p.action === 'monthlyReport') return monthlyReportRoute_(e);
  if (p.action === 'contactsList')  return contactsListRoute_(e);
  if (p.action === 'aliases')       return aliasesRoute_(e);
  // Access Matrix routes (admin-only, except whoAmI)
  if (p.action === 'whoAmI')        return whoAmIRoute_(e);
  if (p.action === 'acmList')       return acmListRoute_(e);
  if (p.action === 'acmUpsert')     return acmUpsertRoute_(e);
  if (p.action === 'acmDelete')     return acmDeleteRoute_(e);
  // Auth routes (username / password / session token)
  if (p.action === 'authLogin')          return authLoginRoute_(e);
  if (p.action === 'authWhoAmI')         return authWhoAmIRoute_(e);
  if (p.action === 'authLogout')         return authLogoutRoute_(e);
  if (p.action === 'authChangePassword') return authChangePasswordRoute_(e);
  if (p.action === 'acmSetPassword')     return acmSetPasswordRoute_(e);
  // Worklist routes (collector or admin)
  if (p.action === 'collectorList')      return collectorListRoute_(e);
  if (p.action === 'collectorUpsert')    return collectorUpsertRoute_(e);
  if (p.action === 'collectorDelete')    return collectorDeleteRoute_(e);
  if (p.action === 'collectorCidsList')  return collectorCidsListRoute_(e);
  if (p.action === 'collectorCidsSet')   return collectorCidsSetRoute_(e);
  if (p.action === 'collectorCidReassign') return collectorCidReassignRoute_(e);
  if (p.action === 'notesList')          return notesListRoute_(e);
  if (p.action === 'notesAdd')           return notesAddRoute_(e);
  if (p.action === 'notesAddBulk')       return notesAddBulkRoute_(e);
  if (p.action === 'notesDelete')        return notesDeleteRoute_(e);
  if (p.action === 'customerInvoices')   return customerInvoicesRoute_(e);
  if (p.action === 'worklistData')       return worklistDataRoute_(e);
  if (p.action === 'dailyReport')        return dailyReportRoute_(e);
  if (p.action === 'cidUniverse')        return cidUniverseRoute_(e);
  if (p.action === 'bulkAssignCids')     return bulkAssignCidsRoute_(e);
  if (p.action === 'collectorCidsConflicts')         return collectorCidsConflictsRoute_(e);
  if (p.action === 'collectorCidsResolveConflicts')  return collectorCidsResolveConflictsRoute_(e);
  // Email Templates routes (any collector — shared template pool)
  if (p.action === 'templatesList')   return emailTemplatesListRoute_(e);
  if (p.action === 'templatesSave')   return emailTemplatesSaveRoute_(e);
  if (p.action === 'templatesDelete') return emailTemplatesDeleteRoute_(e);
  // Customer Statement (ledger) email-out route
  if (p.action === 'statementEmail')  return statementEmailRoute_(e);
  // Customer POCs routes (contact management)
  if (p.action === 'pocList')         return pocListRoute_(e);
  if (p.action === 'pocSave')         return pocSaveRoute_(e);
  if (p.action === 'pocDelete')       return pocDeleteRoute_(e);
  if (p.action === 'pocBulkImport')   return pocBulkImportRoute_(e);
  if (p.action === 'pocTemplate')     return pocTemplateRoute_(e);
  if (p.action === 'pocMigrateFromContacts') return pocMigrateFromContactsRoute_(e);
  if (p.action === 'pocMigrateStatus')       return pocMigrateStatusRoute_(e);
  // Repeatable sync from Customer_Contacts — no one-time lock, and additionally
  // sweeps Customer_POCs + Internal_Stakeholders to remove duplicate rows
  // (same CID + lowercased email), keeping the most recently updated row.
  if (p.action === 'pocSyncFromContacts')    return pocSyncFromContactsRoute_(e);
  // Internal Stakeholders routes (Fynd owners per CID, BCC'd on follow-ups)
  if (p.action === 'isList')          return isListRoute_(e);
  if (p.action === 'isSave')          return isSaveRoute_(e);
  if (p.action === 'isDelete')        return isDeleteRoute_(e);
  if (p.action === 'isBulkImport')    return isBulkImportRoute_(e);
  if (p.action === 'isTemplate')      return isTemplateRoute_(e);
  // Workflows routes (scheduled follow-ups)
  if (p.action === 'wfList')          return workflowListRoute_(e);
  if (p.action === 'wfSave')          return workflowSaveRoute_(e);
  if (p.action === 'wfDelete')        return workflowDeleteRoute_(e);
  if (p.action === 'wfPreview')       return workflowPreviewRoute_(e);
  if (p.action === 'wfTest')          return workflowTestRoute_(e);
  if (p.action === 'wfRunNow')        return workflowRunNowRoute_(e);
  if (p.action === 'wfQueueList')     return workflowQueueListRoute_(e);
  if (p.action === 'wfQueueApprove')  return workflowQueueApproveRoute_(e);
  if (p.action === 'wfQueueDelete')   return workflowQueueDeleteRoute_(e);
  if (p.action === 'dataRefresh')  return dataRefreshRoute_(e);
  if (p.action === 'data' || p.callback) return serveData_(e);
  return serveDashboard_(e);
}

/**
 * POST router — same dispatch table as doGet(). Apps Script surfaces
 * form fields on e.parameter identically for GET and POST, so we can just
 * re-enter doGet() to reuse the routing table without duplicating it.
 * Used by the JSONP transport's fallback path (_fuPost) for oversized
 * payloads AND for the authLogin route (passwords should not be in a
 * URL query string / server logs / browser history).
 */
function doPost(e) {
  return doGet(e);
}

// ===============================================================
// Customer Statement of Account — email out
// ===============================================================
// Sends a pre-rendered HTML Statement of Account to the client.
// Used by the Customer Statement tool in the dashboard. The HTML body
// is built client-side and POSTed via JSONP — we just relay via Gmail.
//
// Params:
//   to, cc (optional), subject, htmlBody (the full <div>…</div> ledger),
//   custName, cid, fromDate, toDate (for log + safety check)
// Returns: { ok:true, sender:'…' } or { ok:false, error:'…' }.
function statementEmailRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var to    = String(p.to    || '').trim();
    var cc    = String(p.cc    || '').trim();
    var subj  = String(p.subject || '').trim();
    var html  = String(p.htmlBody || '');
    if (!to)   return respond_({ ok:false, error:'Recipient email is empty' }, e);
    if (!subj) return respond_({ ok:false, error:'Subject is empty' }, e);
    if (!html) return respond_({ ok:false, error:'Statement body is empty' }, e);
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(to)) {
      return respond_({ ok:false, error:'Invalid recipient email: ' + to }, e);
    }
    var senderUsed = FOLLOWUP_SENDER;
    var aliases = [];
    try { aliases = GmailApp.getAliases() || []; } catch (_) {}
    var aliasOK = (aliases.indexOf(FOLLOWUP_SENDER) !== -1);
    var opts = {
      htmlBody: html,
      replyTo:  FOLLOWUP_REPLY_TO,
      name:     FOLLOWUP_FROM_NAME
    };
    if (aliasOK) {
      opts.from = FOLLOWUP_SENDER;
    } else {
      senderUsed = Session.getActiveUser().getEmail() || '(default account)';
    }
    if (cc) opts.cc = cc;
    GmailApp.sendEmail(to, subj, '', opts);
    return respond_({
      ok: true,
      sender: senderUsed,
      to: to, cc: cc,
      custName: String(p.custName || ''),
      cid: String(p.cid || ''),
      period: String(p.fromDate || '') + ' → ' + String(p.toDate || '')
    }, e);
  } catch (err) {
    return respond_({ ok:false, error: String(err && err.message || err) }, e);
  }
}

// ===============================================================
// 1) DASHBOARD HOSTING — decodes the embedded HTML below
// ===============================================================
function serveDashboard_(e) {
  var html;
  try {
    html = Utilities.newBlob(
      Utilities.base64Decode(getDashboardHtmlB64_()),
      'text/html'
    ).getDataAsString('UTF-8');
  } catch (err) {
    return HtmlService.createHtmlOutput(
      '<div style="font-family:system-ui;padding:32px;max-width:680px;margin:auto;color:#1f2937">'+
      '<h3 style="color:#b85450;margin:0 0 12px">Could not decode embedded dashboard HTML</h3>'+
      '<p style="font-size:12px;color:#475569">Internal error: '+ String(err && err.message || err) +'</p>'+
      '</div>'
    ).setTitle('Fynd · Receivables Insights — error');
  }

  var dataUrl = ScriptApp.getService().getUrl();
  var inject  =
    '<script>'+
      'window.__DATA_URL__ = '+ JSON.stringify(dataUrl) +';'+
      'window.__SERVED_BY_APPS_SCRIPT__ = true;'+
    '</script>';

  if (html.indexOf('<head>') !== -1) {
    html = html.replace('<head>', '<head>'+inject);
  } else {
    html = inject + html;
  }

  return HtmlService.createHtmlOutput(html)
    .setTitle('Fynd · Receivables Insights')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
    .setSandboxMode(HtmlService.SandboxMode.IFRAME);
}

// ===============================================================
// 2) DATA FEED  (JSON or JSONP)
// ---------------------------------------------------------------
// Reads AR + PDD + Bank tabs from the spreadsheet and returns them
// as one JSON payload. Because these reads are the single biggest
// slice of dashboard boot time (typically 4-8 s on a warm cache
// server), we memoise the entire JSON string in CacheService for
// AR_DATA_CACHE_TTL_SEC. Apps Script caps a single cache value at
// 100 KB, so the JSON is base64-sliced across `payload_c0`,
// `payload_c1`, … with a header `payload_meta` recording the chunk
// count and total byte size.
//
// Cache hit  → we serve the cached JSON verbatim (no sheet reads,
//              no JSON.stringify, no filtering). Warm cost is
//              measured in ms, not seconds.
// Cache miss → do the reads, stringify once, put chunks into cache,
//              respond.
//
// The user-facing "Refresh data" button hits dataRefreshRoute_(),
// which calls CacheService.removeAll(...) to force a fresh miss on
// the next request.
// ===============================================================
var AR_DATA_CACHE_KEY_META = 'ar_data_payload_v1__meta';
var AR_DATA_CACHE_KEY_PREF = 'ar_data_payload_v1__c';
var AR_DATA_CACHE_TTL_SEC  = 300;       // 5 minutes
var AR_DATA_CACHE_CHUNK    = 90 * 1024; // stay comfortably under the 100 KB / key cap

function _arCacheKeys_(n){
  var out = [AR_DATA_CACHE_KEY_META];
  for (var i = 0; i < n; i++) out.push(AR_DATA_CACHE_KEY_PREF + i);
  return out;
}

function _arCacheRead_(cache){
  try {
    var metaRaw = cache.get(AR_DATA_CACHE_KEY_META);
    if (!metaRaw) return null;
    var meta = JSON.parse(metaRaw);
    if (!meta || !meta.chunks) return null;
    var keys = [];
    for (var i = 0; i < meta.chunks; i++) keys.push(AR_DATA_CACHE_KEY_PREF + i);
    var got = cache.getAll(keys);
    var parts = [];
    for (var j = 0; j < meta.chunks; j++) {
      var v = got[AR_DATA_CACHE_KEY_PREF + j];
      if (v == null) return null;   // partial expiry — treat as miss
      parts.push(v);
    }
    return parts.join('');
  } catch (_) {
    return null;
  }
}

function _arCacheWrite_(cache, json){
  try {
    var chunks = [];
    for (var i = 0; i < json.length; i += AR_DATA_CACHE_CHUNK) {
      chunks.push(json.substring(i, i + AR_DATA_CACHE_CHUNK));
    }
    var toPut = {};
    toPut[AR_DATA_CACHE_KEY_META] = JSON.stringify({
      chunks: chunks.length,
      bytes:  json.length,
      generated: new Date().toISOString()
    });
    for (var k = 0; k < chunks.length; k++) {
      toPut[AR_DATA_CACHE_KEY_PREF + k] = chunks[k];
    }
    cache.putAll(toPut, AR_DATA_CACHE_TTL_SEC);
  } catch (_) { /* cache is best-effort; never fail the request */ }
}

function _arCachePurge_(){
  try {
    var cache = CacheService.getScriptCache();
    // Best-effort: we don't know the current chunk count, so guess up to 200
    // chunks (~18 MB payload cap — well beyond current sheet size).
    cache.removeAll(_arCacheKeys_(200));
  } catch (_) {}
}

function serveData_(e) {
  try {
    var p = (e && e.parameter) || {};
    var cache = CacheService.getScriptCache();

    // LIVE-ONLY MODE: the dashboard must always reflect the current state of
    // the Google Sheet. Historically we cached the JSON payload in
    // CacheService for 5 minutes; that led to stale numbers after collectors
    // updated the sheet. The cache-read step is now permanently disabled —
    // every request re-reads the tabs. The client can *opt in* to a cached
    // response via ?cache=1 (nobody does today; kept for future use).
    var useCache = String(p.cache || '') === '1';
    if (useCache) {
      var cached = _arCacheRead_(cache);
      if (cached) {
        var cb = e && e.parameter && e.parameter.callback;
        if (cb && /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(cb)) {
          return ContentService
            .createTextOutput(cb + '(' + cached + ');')
            .setMimeType(ContentService.MimeType.JAVASCRIPT);
        }
        return ContentService
          .createTextOutput(cached)
          .setMimeType(ContentService.MimeType.JSON);
      }
    }

    var ss = SpreadsheetApp.openById(SHEET_ID);
    var allTabs = ss.getSheets().map(function(s){ return s.getName(); });

    var arName   = resolveTab_(allTabs, TAB_AR_CANDIDATES);
    var pddName  = resolveTab_(allTabs, TAB_PDD_CANDIDATES);
    var bankName = resolveTab_(allTabs, TAB_BANK_CANDIDATES);

    var ar  = arName   ? readTab_(ss, arName)   : { rows: [], headers: [] };
    var pdd = pddName  ? readTab_(ss, pddName)  : { rows: [], headers: [] };
    var bank= bankName ? readTab_(ss, bankName) : { rows: [], headers: [] };

    var arClean = ar.rows.filter(function(r){ return !rowHasError_(r); });
    var arSkipped = ar.rows.length - arClean.length;

    // Also surface the Customer_Contacts set so the dashboard can
    // grey out non-eligible rows in the follow-up tab.
    var contactsSet = readContactCids_(ss);

    var payload = {
      generated:    new Date().toISOString(),
      sheetId:      SHEET_ID,
      sheetUrl:     ss.getUrl(),
      tabsFound:    allTabs,
      tabsResolved: { ar: arName, pdd: pddName, bank: bankName },
      counts: {
        ar:        arClean.length,
        arSkipped: arSkipped,
        pdd:       pdd.rows.length,
        bank:      bank.rows.length,
        contacts:  contactsSet.length
      },
      headers: { ar: ar.headers, pdd: pdd.headers, bank: bank.headers },
      samples: { ar: arClean[0]||null, pdd: pdd.rows[0]||null, bank: bank.rows[0]||null },
      ar:   arClean,
      pdd:  pdd.rows,
      bank: bank.rows,
      followupContactCids: contactsSet
    };

    // Stringify once and hand the same string to respond_ (which would
    // re-parse-and-restringify if we let it — instead, do JSONP wrap
    // inline to avoid the double serialisation cost).
    // NB: cache write is only meaningful when useCache=true reads can happen;
    // keep writing so the opt-in cache path still works for future callers.
    var json = JSON.stringify(payload);
    if (useCache) _arCacheWrite_(cache, json);

    var cb2 = e && e.parameter && e.parameter.callback;
    if (cb2 && /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(cb2)) {
      return ContentService
        .createTextOutput(cb2 + '(' + json + ');')
        .setMimeType(ContentService.MimeType.JAVASCRIPT);
    }
    return ContentService
      .createTextOutput(json)
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return respond_({ error: String(err && err.message || err), stack: err && err.stack }, e);
  }
}

// Route: purge the AR_Data cache so the very next serveData_ call
// re-reads from the spreadsheet. Wired to a header "Refresh data"
// button in the dashboard.
function dataRefreshRoute_(e){
  _arCachePurge_();
  return respond_({ ok: true, cache: 'cleared', at: new Date().toISOString() }, e);
}

function respond_(payload, e) {
  var json = JSON.stringify(payload);
  var cb = e && e.parameter && e.parameter.callback;
  if (cb && /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(cb)) {
    return ContentService
      .createTextOutput(cb + '(' + json + ');')
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }
  return ContentService
    .createTextOutput(json)
    .setMimeType(ContentService.MimeType.JSON);
}

function resolveTab_(all, candidates) {
  var norm = function(s){ return String(s||'').toLowerCase().replace(/[^a-z0-9]/g,''); };
  var normalized = all.map(norm);
  for (var i = 0; i < candidates.length; i++) {
    var c = norm(candidates[i]);
    var idx = normalized.indexOf(c);
    if (idx !== -1) return all[idx];
  }
  for (var j = 0; j < candidates.length; j++) {
    var c2 = norm(candidates[j]);
    for (var k = 0; k < normalized.length; k++) {
      if (normalized[k].indexOf(c2) !== -1) return all[k];
    }
  }
  return null;
}

function readTab_(ss, name) {
  var sh = ss.getSheetByName(name);
  if (!sh) return { rows: [], headers: [] };
  var rng = sh.getDataRange();
  var values = rng.getValues();
  if (values.length < 2) {
    var emptyHeaders = (values.length === 1)
      ? values[0].map(function(h){ return String(h||'').trim(); }).filter(function(h){ return h; })
      : [];
    return { rows: [], headers: emptyHeaders };
  }

  var headers = values[0].map(function(h){ return String(h||'').trim(); });
  var headersClean = headers.filter(function(h){ return h; });

  var rows = [];
  for (var i = 1; i < values.length; i++) {
    var row = values[i];
    if (row.every(function(v){ return v === '' || v === null; })) continue;
    var obj = {};
    var hasContent = false;
    for (var j = 0; j < headers.length; j++) {
      var h = headers[j]; if (!h) continue;
      var v = row[j];
      if (v instanceof Date) {
        obj[h] = formatISODate_(v);
      } else if (typeof v === 'number') {
        obj[h] = v;
      } else {
        obj[h] = (v === null || v === undefined) ? '' : String(v);
      }
      if (obj[h] !== '' && obj[h] !== 0) hasContent = true;
    }
    if (hasContent) rows.push(obj);
  }
  return { rows: rows, headers: headersClean };
}

function rowHasError_(obj) {
  for (var k in obj) {
    var v = obj[k]; if (v == null) continue;
    var s = String(v).trim().toUpperCase();
    if (ERROR_TOKENS.indexOf(s) !== -1) return true;
  }
  return false;
}

function formatISODate_(d) {
  var yr = d.getFullYear();
  var mm = ('0' + (d.getMonth()+1)).slice(-2);
  var dd = ('0' + d.getDate()).slice(-2);
  return yr + '-' + mm + '-' + dd;
}

// ===============================================================
// 3) FOLLOW-UP EMAILS — contacts, eligibility, send, log
// ===============================================================

/** Read Customer_Contacts → map of cid -> { to, cc, owner, name } */
function readContacts_(ss) {
  // Prefer the normalized Customer_POCs tab when present — it consolidates
  // 1..N POCs into the { cid, name, to, cc } shape the follow-up sender
  // expects. Falls back to the legacy Customer_Contacts tab so existing
  // sheets keep working during migration.
  var poc = readPOCsConsolidated_(ss);
  if (poc && Object.keys(poc).length) return poc;
  var sh = ss.getSheetByName(CONTACTS_TAB);
  if (!sh) return {};
  var v = sh.getDataRange().getValues();
  if (v.length < 2) return {};
  var head = v[0].map(function(h){ return String(h||'').trim().toLowerCase(); });
  var ix = function(name){ return head.indexOf(name); };
  var iCid   = ix('cid'); if (iCid === -1) iCid = ix('company id');
  var iName  = ix('customer name'); if (iName === -1) iName = ix('customer');
  var iTo    = ix('to email'); if (iTo === -1) iTo = ix('email');
  var iCc    = ix('cc emails'); if (iCc === -1) iCc = ix('cc');
  var iOwn   = ix('account owner name'); if (iOwn === -1) iOwn = ix('account owner');
  var out = {};
  for (var i = 1; i < v.length; i++) {
    var row = v[i];
    var cid = String(row[iCid] || '').trim();
    if (!cid) continue;
    out[cid] = {
      cid:   cid,
      name:  iName > -1 ? String(row[iName] || '').trim() : '',
      to:    iTo   > -1 ? String(row[iTo]   || '').trim() : '',
      cc:    iCc   > -1 ? String(row[iCc]   || '').trim() : '',
      owner: iOwn  > -1 ? String(row[iOwn]  || '').trim() : ''
    };
  }
  return out;
}

// -----------------------------------------------------------------
// Customer_POCs — normalized contact store
// -----------------------------------------------------------------

/**
 * Read the raw Customer_POCs tab and return an array of contact records.
 * Rows with a blank CID are skipped. Missing tab / missing columns → empty.
 * We only look at header names (case-insensitive) so the sheet can grow
 * without breaking readers.
 */
function readPOCs_(ss) {
  var sh = ss.getSheetByName(POCS_TAB);
  if (!sh) return [];
  var v = sh.getDataRange().getValues();
  if (v.length < 2) return [];
  var head = v[0].map(function(h){ return String(h||'').trim().toLowerCase(); });
  var ix = function(name){ return head.indexOf(name); };
  var iCid  = ix('cid'); if (iCid === -1) iCid = ix('company id');
  var iName = ix('customer name');
  var iCn   = ix('contact name');
  var iRole = ix('role'); if (iRole === -1) iRole = ix('designation');
  var iEm   = ix('email');
  var iPh   = ix('phone'); if (iPh === -1) iPh = ix('contact number');
  var iPri  = ix('priority');
  var iAct  = ix('active');
  var iNote = ix('notes');
  var iUpBy = ix('updated by');
  var iUpAt = ix('updated at');
  var out = [];
  for (var i = 1; i < v.length; i++) {
    var row = v[i];
    var cid = String(row[iCid] || '').trim();
    if (!cid) continue;
    out.push({
      rowIndex:    i + 1,  // 1-based sheet row for update/delete
      cid:         cid,
      customerName: iName > -1 ? String(row[iName] || '').trim() : '',
      contactName: iCn   > -1 ? String(row[iCn]   || '').trim() : '',
      role:        iRole > -1 ? String(row[iRole] || '').trim() : '',
      email:       iEm   > -1 ? String(row[iEm]   || '').trim() : '',
      phone:       iPh   > -1 ? String(row[iPh]   || '').trim() : '',
      priority:    iPri  > -1 ? String(row[iPri]  || '').trim() : '',
      active:      iAct  > -1 ? _pocIsActive_(row[iAct]) : true,
      notes:       iNote > -1 ? String(row[iNote] || '').trim() : '',
      updatedBy:   iUpBy > -1 ? String(row[iUpBy] || '').trim() : '',
      updatedAt:   iUpAt > -1 ? String(row[iUpAt] || '').trim() : ''
    });
  }
  return out;
}

function _pocIsActive_(v) {
  if (v === true) return true;
  if (v === false) return false;
  var s = String(v == null ? '' : v).trim().toLowerCase();
  if (!s) return true;
  return !(s === 'n' || s === 'no' || s === 'false' || s === '0' || s === 'inactive');
}

/**
 * Consolidate Customer_POCs into the flat { cid → {cid,name,to,cc,owner} }
 * shape used by the follow-up sender. Rules:
 *   • Only Active rows contribute.
 *   • Priority=Primary → first Primary email becomes `to`.
 *     Extra Primaries pile onto `cc` (we still deliver, we don't drop).
 *   • Priority=CC → appended to `cc`.
 *   • Priority=Escalation → recorded separately so escalation-stage
 *     workflows can target them without spamming during soft reminders.
 *   • Blank priority is treated as Primary (charitable — many imported rows
 *     will not have a priority set on day one).
 *   • Customer Name is taken from the first row that has one.
 */
function readPOCsConsolidated_(ss) {
  var rows = readPOCs_(ss);
  if (!rows.length) return null;  // signal: no POCs tab → caller falls back
  var byCid = {};
  rows.forEach(function(r){
    if (!r.active) return;
    if (!r.email) return;
    var cid = r.cid;
    if (!byCid[cid]) byCid[cid] = {
      cid: cid, name: r.customerName || '', to: '', cc: '',
      escalation: '', phones: [], contacts: [], owner: ''
    };
    var bucket = byCid[cid];
    if (!bucket.name && r.customerName) bucket.name = r.customerName;
    var pri = (r.priority || 'primary').toLowerCase();
    if (pri === 'primary') {
      // Multiple Primaries all land in the To line (comma-separated).
      // Previously the first Primary became To and the rest were demoted to
      // Cc; Sainath asked for the group-email behaviour instead so every
      // person tagged Primary is a direct addressee.
      bucket.to = bucket.to ? (bucket.to + ',' + r.email) : r.email;
    } else if (pri === 'escalation') {
      bucket.escalation = bucket.escalation
        ? (bucket.escalation + ',' + r.email) : r.email;
    } else {
      // Default (blank / CC / anything else) → CC
      bucket.cc = bucket.cc ? (bucket.cc + ',' + r.email) : r.email;
    }
    if (r.phone) bucket.phones.push(r.phone);
    bucket.contacts.push({
      name: r.contactName, role: r.role, email: r.email,
      phone: r.phone, priority: r.priority
    });
  });
  // Drop rows without a To email (nothing to send).
  Object.keys(byCid).forEach(function(k){
    if (!byCid[k].to) {
      // Promote the first CC (if any) into To — better than dropping the row,
      // matches how a human would send if there is no explicit Primary tag.
      if (byCid[k].cc) {
        var parts = byCid[k].cc.split(',');
        byCid[k].to = parts.shift();
        byCid[k].cc = parts.join(',');
      } else {
        delete byCid[k];
      }
    }
  });
  return byCid;
}

/** Ensure the Customer_POCs tab exists with headers frozen. */
function ensurePOCsTab_(ss) {
  var sh = ss.getSheetByName(POCS_TAB);
  if (sh) return sh;
  sh = ss.insertSheet(POCS_TAB);
  sh.getRange(1, 1, 1, POC_HEADERS.length).setValues([POC_HEADERS])
    .setFontWeight('bold').setBackground('#2c4a52').setFontColor('#ffffff');
  sh.setFrozenRows(1);
  sh.autoResizeColumns(1, POC_HEADERS.length);
  return sh;
}

/**
 * Upsert one POC row. Match key is (cid, email) — case-insensitive on email
 * so the caller can safely re-import a spreadsheet where one contact was
 * re-typed with different casing. Returns { ok, mode: 'insert'|'update' }.
 */
function upsertPOC_(ss, rec, actor) {
  var sh = ensurePOCsTab_(ss);
  var cid = String(rec.cid || '').trim();
  var email = String(rec.email || '').trim().toLowerCase();
  if (!cid) throw new Error('CID is required');
  if (!email) throw new Error('Email is required');
  var lastRow = sh.getLastRow();
  var matchRow = 0;
  if (lastRow > 1) {
    var range = sh.getRange(2, 1, lastRow - 1, POC_HEADERS.length).getValues();
    for (var i = 0; i < range.length; i++) {
      var r = range[i];
      if (String(r[0]).trim() === cid &&
          String(r[4]).trim().toLowerCase() === email) {
        matchRow = i + 2;
        break;
      }
    }
  }
  var now = _pocNowIso_();
  var priority = _pocNormalizePriority_(rec.priority);
  var active = rec.active === false ? false : (rec.active === 'N' ? false : true);
  var row = [
    cid,
    String(rec.customerName || '').trim(),
    String(rec.contactName || '').trim(),
    String(rec.role || '').trim(),
    String(rec.email || '').trim(),
    String(rec.phone || '').trim(),
    priority,
    active ? 'Y' : 'N',
    String(rec.notes || '').trim(),
    actor || '',
    now
  ];
  if (matchRow) {
    sh.getRange(matchRow, 1, 1, POC_HEADERS.length).setValues([row]);
    return { ok: true, mode: 'update', row: matchRow };
  } else {
    sh.appendRow(row);
    return { ok: true, mode: 'insert', row: sh.getLastRow() };
  }
}

function _pocNormalizePriority_(v) {
  var s = String(v || '').trim().toLowerCase();
  if (s === 'primary' || s === 'p' || s === 'to') return 'Primary';
  if (s === 'cc') return 'CC';
  if (s === 'escalation' || s === 'esc' || s === 'e') return 'Escalation';
  return 'Primary';
}

function _pocNowIso_() {
  return Utilities.formatDate(new Date(), WORKFLOW_TZ, 'yyyy-MM-dd HH:mm:ss');
}

/** Delete one row from Customer_POCs. matchKey = (cid, email). */
function deletePOC_(ss, cid, email) {
  var sh = ss.getSheetByName(POCS_TAB);
  if (!sh) return { ok: false, error: 'POCs tab not found' };
  cid = String(cid || '').trim();
  email = String(email || '').trim().toLowerCase();
  if (!cid || !email) return { ok: false, error: 'CID + email required' };
  var lastRow = sh.getLastRow();
  if (lastRow < 2) return { ok: false, error: 'No rows to delete' };
  var range = sh.getRange(2, 1, lastRow - 1, POC_HEADERS.length).getValues();
  for (var i = 0; i < range.length; i++) {
    var r = range[i];
    if (String(r[0]).trim() === cid &&
        String(r[4]).trim().toLowerCase() === email) {
      sh.deleteRow(i + 2);
      return { ok: true, deleted: 1 };
    }
  }
  return { ok: false, error: 'Row not found' };
}

// ===============================================================
// Internal Stakeholders — Fynd (Gofynd) owners per CID
// ===============================================================
// Mirror of the Customer_POCs helpers. Same schema, same match-key
// semantics — the difference is purely intent: these rows describe
// *our* owners of the account (AM, KAM, backup). Consolidated view is
// BCC'd on every outgoing customer follow-up.

/**
 * Read the raw Internal_Stakeholders tab and return an array of records.
 * Rows with a blank CID are skipped. Missing tab / missing columns → empty.
 * We only look at header names (case-insensitive) so the sheet can grow
 * without breaking readers.
 */
function readIS_(ss) {
  var sh = ss.getSheetByName(IS_TAB);
  if (!sh) return [];
  var v = sh.getDataRange().getValues();
  if (v.length < 2) return [];
  var head = v[0].map(function(h){ return String(h||'').trim().toLowerCase(); });
  var ix = function(name){ return head.indexOf(name); };
  var iCid  = ix('cid'); if (iCid === -1) iCid = ix('company id');
  var iName = ix('customer name');
  var iCn   = ix('stakeholder name');
  var iRole = ix('role'); if (iRole === -1) iRole = ix('designation');
  var iEm   = ix('email');
  var iPh   = ix('phone'); if (iPh === -1) iPh = ix('contact number');
  var iPri  = ix('priority');
  var iAct  = ix('active');
  var iNote = ix('notes');
  var iUpBy = ix('updated by');
  var iUpAt = ix('updated at');
  var out = [];
  for (var i = 1; i < v.length; i++) {
    var row = v[i];
    var cid = String(row[iCid] || '').trim();
    if (!cid) continue;
    out.push({
      rowIndex:    i + 1,  // 1-based sheet row for update/delete
      cid:         cid,
      customerName:    iName > -1 ? String(row[iName] || '').trim() : '',
      stakeholderName: iCn   > -1 ? String(row[iCn]   || '').trim() : '',
      role:        iRole > -1 ? String(row[iRole] || '').trim() : '',
      email:       iEm   > -1 ? String(row[iEm]   || '').trim() : '',
      phone:       iPh   > -1 ? String(row[iPh]   || '').trim() : '',
      priority:    iPri  > -1 ? String(row[iPri]  || '').trim() : '',
      active:      iAct  > -1 ? _pocIsActive_(row[iAct]) : true,
      notes:       iNote > -1 ? String(row[iNote] || '').trim() : '',
      updatedBy:   iUpBy > -1 ? String(row[iUpBy] || '').trim() : '',
      updatedAt:   iUpAt > -1 ? String(row[iUpAt] || '').trim() : ''
    });
  }
  return out;
}

/**
 * Consolidate Internal_Stakeholders into the shape used by the follow-up
 * sender when populating BCC. Rules:
 *   • Only Active rows contribute.
 *   • Priority=Primary OR Priority=CC → email joins `bucket.bcc`
 *     (comma-separated). These are the "always BCC'd" owners.
 *   • Priority=Escalation → joins `bucket.escalationBcc` — only included
 *     when the outgoing email is at escalation stage.
 *   • Blank priority is treated as Primary (charitable — many imported
 *     rows will not have a priority set on day one).
 *   • No "promote from CC" step — if a CID has zero internal
 *     stakeholders, that's fine, the CID just has no BCC line.
 *   • Customer Name is taken from the first row that has one.
 * Returns { cid: {cid, name, bcc, escalationBcc, owners: [...]} }.
 */
function readISConsolidated_(ss) {
  var rows = readIS_(ss);
  if (!rows.length) return null;  // signal: no IS tab → caller omits BCC
  var byCid = {};
  rows.forEach(function(r){
    if (!r.active) return;
    if (!r.email) return;
    var cid = r.cid;
    if (!byCid[cid]) byCid[cid] = {
      cid: cid, name: r.customerName || '', bcc: '',
      escalationBcc: '', owners: []
    };
    var bucket = byCid[cid];
    if (!bucket.name && r.customerName) bucket.name = r.customerName;
    var pri = (r.priority || 'primary').toLowerCase();
    if (pri === 'escalation') {
      bucket.escalationBcc = bucket.escalationBcc
        ? (bucket.escalationBcc + ',' + r.email) : r.email;
    } else {
      // Primary OR CC (OR blank) → BCC on every follow-up
      bucket.bcc = bucket.bcc ? (bucket.bcc + ',' + r.email) : r.email;
    }
    bucket.owners.push({
      name: r.stakeholderName, role: r.role, email: r.email,
      phone: r.phone, priority: r.priority
    });
  });
  return byCid;
}

/** Ensure the Internal_Stakeholders tab exists with headers frozen. */
function ensureISTab_(ss) {
  var sh = ss.getSheetByName(IS_TAB);
  if (sh) return sh;
  sh = ss.insertSheet(IS_TAB);
  sh.getRange(1, 1, 1, IS_HEADERS.length).setValues([IS_HEADERS])
    .setFontWeight('bold').setBackground('#2c4a52').setFontColor('#ffffff');
  sh.setFrozenRows(1);
  sh.autoResizeColumns(1, IS_HEADERS.length);
  return sh;
}

/**
 * Upsert one Internal Stakeholder row. Match key is (cid, email) —
 * case-insensitive on email so the caller can safely re-import a
 * spreadsheet where one stakeholder was re-typed with different casing.
 * Returns { ok, mode: 'insert'|'update' }.
 */
function upsertIS_(ss, rec, actor) {
  var sh = ensureISTab_(ss);
  var cid = String(rec.cid || '').trim();
  var email = String(rec.email || '').trim().toLowerCase();
  if (!cid) throw new Error('CID is required');
  if (!email) throw new Error('Email is required');
  var lastRow = sh.getLastRow();
  var matchRow = 0;
  if (lastRow > 1) {
    var range = sh.getRange(2, 1, lastRow - 1, IS_HEADERS.length).getValues();
    for (var i = 0; i < range.length; i++) {
      var r = range[i];
      if (String(r[0]).trim() === cid &&
          String(r[4]).trim().toLowerCase() === email) {
        matchRow = i + 2;
        break;
      }
    }
  }
  var now = _pocNowIso_();
  var priority = _pocNormalizePriority_(rec.priority);
  var active = rec.active === false ? false : (rec.active === 'N' ? false : true);
  var row = [
    cid,
    String(rec.customerName || '').trim(),
    String(rec.stakeholderName || '').trim(),
    String(rec.role || '').trim(),
    String(rec.email || '').trim(),
    String(rec.phone || '').trim(),
    priority,
    active ? 'Y' : 'N',
    String(rec.notes || '').trim(),
    actor || '',
    now
  ];
  if (matchRow) {
    sh.getRange(matchRow, 1, 1, IS_HEADERS.length).setValues([row]);
    return { ok: true, mode: 'update', row: matchRow };
  } else {
    sh.appendRow(row);
    return { ok: true, mode: 'insert', row: sh.getLastRow() };
  }
}

/** Delete one row from Internal_Stakeholders. matchKey = (cid, email). */
function deleteIS_(ss, cid, email) {
  var sh = ss.getSheetByName(IS_TAB);
  if (!sh) return { ok: false, error: 'Internal Stakeholders tab not found' };
  cid = String(cid || '').trim();
  email = String(email || '').trim().toLowerCase();
  if (!cid || !email) return { ok: false, error: 'CID + email required' };
  var lastRow = sh.getLastRow();
  if (lastRow < 2) return { ok: false, error: 'No rows to delete' };
  var range = sh.getRange(2, 1, lastRow - 1, IS_HEADERS.length).getValues();
  for (var i = 0; i < range.length; i++) {
    var r = range[i];
    if (String(r[0]).trim() === cid &&
        String(r[4]).trim().toLowerCase() === email) {
      sh.deleteRow(i + 2);
      return { ok: true, deleted: 1 };
    }
  }
  return { ok: false, error: 'Row not found' };
}

/** Set of CIDs that have contact rows (for greying out non-eligible). */
function readContactCids_(ss) {
  var m = readContacts_(ss);
  return Object.keys(m);
}

/**
 * Return open INV invoices for one CID, sorted by Days DESC.
 * Filter: STATUS = Open AND Invoice_Type = INV AND Company ID = cid.
 *
 * `opts.bus` — optional array of Business names. When provided, only
 * invoices whose Business matches the list are returned. This keeps the
 * Follow-up preview / send / Excel export honest when the user has picked
 * a Region on the Follow-ups tab: only that region's outstanding should
 * flow into the email body, the on-screen table, and the Excel download.
 * When omitted, behaviour is unchanged (all regions).
 */
function getOpenInvForCid_(ar, cid, opts) {
  cid = String(cid).trim();
  var busFilter = (opts && Array.isArray(opts.bus) && opts.bus.length) ? opts.bus : null;
  var rows = ar.filter(function(r){
    var status = String(r['STATUS'] || r['Status'] || '').trim().toLowerCase();
    var itype  = String(r['Invoice_Type'] || '').trim().toUpperCase();
    var ci     = String(r['Company ID'] || '').trim();
    if (ci !== cid || itype !== 'INV' || status !== 'open') return false;
    if (busFilter && busFilter.indexOf(String(r['Business'] || '')) === -1) return false;
    return true;
  });
  rows.sort(function(a, b){
    var da = Number(a['Days'] || 0);
    var db = Number(b['Days'] || 0);
    return db - da;
  });
  return rows;
}

/** Format INR with Indian grouping. */
function fmtINR_(n) {
  n = Number(n) || 0;
  var sign = n < 0 ? '-' : '';
  n = Math.abs(n);
  var i = Math.floor(n);
  var frac = (Math.round((n - i) * 100)).toString();
  if (frac.length < 2) frac = '0' + frac;
  var istr = String(i);
  if (istr.length > 3) {
    var last3 = istr.slice(-3);
    var rest  = istr.slice(0, -3);
    rest = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',');
    istr = rest + ',' + last3;
  }
  return sign + '\u20B9 ' + istr + '.' + frac;
}

/** Format DD-Mon-YYYY from ISO yyyy-mm-dd. */
function fmtDate_(iso) {
  if (!iso) return '';
  var m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return String(iso);
  var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return m[3] + '-' + months[parseInt(m[2],10)-1] + '-' + m[1];
}

/** Build the full email HTML body (inline-styled for Gmail). */
function buildFollowUpHtml_(customerName, invoices) {
  var rowsHtml = '';
  var sumInv = 0, sumOs = 0;
  var oldest = 0;
  invoices.forEach(function(r){
    var days = Number(r['Days'] || 0);
    var invAmt = Number(r['Invoice_Amount'] || 0);
    var osAmt  = Number(r['Outstanding_Amount'] || 0);
    sumInv += invAmt;
    sumOs  += osAmt;
    if (days > oldest) oldest = days;

    var daysLabel = days >= 1 ? ('Overdue by ' + days + ' days') : 'Not due';
    var daysColor = days >= 60 ? '#b91c1c' : (days >= 1 ? '#92400e' : '#15803d');

    rowsHtml +=
      '<tr>' +
        '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px">' + (r['Invoice_No'] || '') + '</td>' +
        '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px">' + (r['Channel'] || '') + '</td>' +
        '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px">' + (r['Transaction_Type'] || '') + '</td>' +
        '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px">' + fmtDate_(r['Invoice_Date']) + '</td>' +
        '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px">' + fmtDate_(r['Due_Date']) + '</td>' +
        '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:right">' + fmtINR_(invAmt) + '</td>' +
        '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:right">' + fmtINR_(osAmt) + '</td>' +
        '<td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;color:' + daysColor + '">' + daysLabel + '</td>' +
      '</tr>';
  });

  // Totals row — both Invoice and Outstanding totals
  rowsHtml +=
    '<tr style="background:#f8fafc;font-weight:700">' +
      '<td colspan="5" style="padding:10px;border:1px solid #e5e7eb;font-size:12px;text-align:right">Total :</td>' +
      '<td style="padding:10px;border:1px solid #e5e7eb;font-size:12px;text-align:right">' + fmtINR_(sumInv) + '</td>' +
      '<td style="padding:10px;border:1px solid #e5e7eb;font-size:12px;text-align:right">' + fmtINR_(sumOs) + '</td>' +
      '<td style="padding:10px;border:1px solid #e5e7eb"></td>' +
    '</tr>';

  var table =
    '<table cellspacing="0" cellpadding="0" style="border-collapse:collapse;width:100%;margin:14px 0;font-family:Arial,sans-serif">' +
      '<thead><tr style="background:#f1f5f9">' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:left">Invoice Number</th>' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:left">Channel</th>' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:left">Transaction Type</th>' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:left">Invoice Date</th>' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:left">Due Date</th>' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:right">Invoice Amount</th>' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:right">Outstanding Amount</th>' +
        '<th style="padding:9px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:left">Days</th>' +
      '</tr></thead>' +
      '<tbody>' + rowsHtml + '</tbody>' +
    '</table>';

  var body =
    '<div style="font-family:Arial,sans-serif;font-size:14px;color:#1f2937;max-width:920px;line-height:1.55">' +
      '<p>Hi Team,</p>' +
      '<p>I hope you are doing well.</p>' +
      '<p>Please find below the current statement of your account with us. As of today, the following invoice(s) remain outstanding:</p>' +
      table +
      '<p style="font-size:11px;color:#64748b;font-style:italic">Note: Table may truncate on small devices. View in browser for full table.</p>' +
      '<p>We kindly request you to review the above details and arrange payment accordingly:</p>' +
      '<ul style="margin:6px 0 10px 22px;padding:0">' +
        '<li style="margin:4px 0">For <b>overdue invoices</b>, we request immediate payment to avoid further delays.</li>' +
        '<li style="margin:4px 0">For <b>due invoices</b>, please ensure payment is made on or before the due date.</li>' +
      '</ul>' +
      '<p>If payment has already been initiated, kindly share the UTR details along with invoice-wise breakup for our reference.</p>' +
      BANK_BLOCK_HTML +
      '<p style="margin-top:14px">If you have any queries regarding the invoice(s) or require any assistance, please feel free to contact us at ' +
        '<a href="mailto:accounts@gofynd.com" style="color:#2563eb">accounts@gofynd.com</a>' +
      '</p>' +
      '<p>Thank you for your continued business.</p>' +
      '<p style="margin-bottom:0">Best regards,<br><b>Accounts Receivable</b><br><span style="color:#64748b">Fynd.</span></p>' +
    '</div>';

  return {
    subject: 'Outstanding Invoice(s) - ' + customerName,
    htmlBody: body,
    invoiceCount: invoices.length,
    invoiceTotal: sumInv,
    outstandingTotal: sumOs,
    oldestDays: oldest
  };
}

// ----- Preview routes ------------------------------------------------

function previewOne_(e) {
  try {
    var p = e.parameter || {};
    var cid = String(p.cid || '').trim();
    var templateId = String(p.templateId || '').trim();
    // Same region scope the Follow-ups tab used to build the preview list —
    // when set, the modal preview only shows invoices from that region so
    // the user sees the exact email that will land in the customer's inbox.
    var bus = (p.bus || '').split(',').map(function(s){ return s.trim(); }).filter(Boolean);
    if (!cid) throw new Error('Missing cid');
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var contacts = readContacts_(ss);
    var contact = contacts[cid];
    if (!contact) {
      return respond_({
        ok: false,
        reason: 'no-contact',
        message: 'No contact configured for CID ' + cid + '. Add a row in Customer_Contacts.'
      }, e);
    }
    var ar = readTab_(ss, resolveTab_(ss.getSheets().map(function(s){return s.getName();}), TAB_AR_CANDIDATES)).rows
              .filter(function(r){ return !rowHasError_(r); });
    var inv = getOpenInvForCid_(ar, cid, { bus: bus });
    if (inv.length === 0) {
      return respond_({
        ok: false,
        reason: 'no-invoices',
        message: 'No open INV invoices for this customer — nothing to follow up on.'
      }, e);
    }
    var custName = contact.name || (inv[0]['Seller_Name'] || inv[0]['Seller Name'] || '');
    var html;
    if (templateId) {
      var tpl = getEmailTemplateById_(ss, templateId);
      if (tpl) {
        var collectorName = resolveCollectorName_(ss) || '';
        html = buildEmailFromTemplate_(tpl, custName, inv, { collector_name: collectorName });
      } else {
        html = buildFollowUpHtml_(custName, inv);
      }
    } else {
      html = buildFollowUpHtml_(custName, inv);
    }
    var cooldown = cooldownStatus_(ss, cid);
    return respond_({
      ok: true,
      contact: contact,
      preview: html,
      invoices: inv.map(function(r){ return invoiceToPreview_(r); }),
      cooldown: cooldown,
      sender: FOLLOWUP_SENDER,
      bcc: FOLLOWUP_BCC
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

function previewBU_(e) {
  try {
    var p = e.parameter || {};
    var bus  = (p.bus  || '').split(',').map(function(s){ return s.trim(); }).filter(Boolean);
    var cids = (p.cids || '').split(',').map(function(s){ return s.trim(); }).filter(Boolean);
    var force = String(p.force || '') === '1';
    if (bus.length === 0 && cids.length === 0) {
      throw new Error('Provide either bus= or cids= parameter');
    }
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var contacts = readContacts_(ss);
    var ar = readTab_(ss, resolveTab_(ss.getSheets().map(function(s){return s.getName();}), TAB_AR_CANDIDATES)).rows
              .filter(function(r){ return !rowHasError_(r); });

    // Reduce AR to open INV rows once
    var openInv = ar.filter(function(r){
      var status = String(r['STATUS'] || r['Status'] || '').trim().toLowerCase();
      var itype  = String(r['Invoice_Type'] || '').trim().toUpperCase();
      return itype === 'INV' && status === 'open';
    });

    // Group by CID
    var byCid = {};
    openInv.forEach(function(r){
      var ci = String(r['Company ID'] || '').trim();
      if (!ci) return;
      if (bus.length && bus.indexOf(String(r['Business'] || '')) === -1) return;
      if (cids.length && cids.indexOf(ci) === -1) return;
      if (!byCid[ci]) byCid[ci] = { cid: ci,
        customer: String(r['Seller_Name'] || r['Seller Name'] || ''),
        bu: String(r['Business'] || ''),
        count: 0, invoiceTotal: 0, outstandingTotal: 0, oldestDays: 0
      };
      var bucket = byCid[ci];
      bucket.count += 1;
      bucket.invoiceTotal     += Number(r['Invoice_Amount'] || 0);
      bucket.outstandingTotal += Number(r['Outstanding_Amount'] || 0);
      var d = Number(r['Days'] || 0);
      if (d > bucket.oldestDays) bucket.oldestDays = d;
    });

    var list = Object.keys(byCid).map(function(k){
      var b = byCid[k];
      var c = contacts[k];
      var cooldown = cooldownStatus_(ss, k);
      b.toEmail = c ? c.to : '';
      b.ccEmails = c ? c.cc : '';
      b.hasContact = !!c;
      b.contactName = c ? c.name : '';
      b.cooldownActive = cooldown.active;
      b.cooldownUntil  = cooldown.until || '';
      b.lastSent       = cooldown.lastSent || '';
      // When force=1 the user has explicitly overridden the 24h cooldown
      // (Force resend checkbox on Follow-ups tab) — treat all rows as
      // eligible so they can be re-selected for an immediate re-send.
      b.eligible = !!c && b.count > 0 && (force || !cooldown.active);
      b.reason = !c ? 'No contact in Customer_Contacts'
              : (b.count === 0 ? 'No open INV invoices'
              : (cooldown.active
                  ? (force ? 'Cooldown overridden — last sent ' + cooldown.lastSent
                           : 'Cooldown — last sent ' + cooldown.lastSent)
                  : 'Ready'));
      return b;
    });

    // Sort by outstanding desc
    list.sort(function(a, b){ return b.outstandingTotal - a.outstandingTotal; });

    // Build the full per-invoice list too (for Excel export).
    // CRITICAL: apply the SAME per-row region + cids gate that byCid used.
    // Without this the invoice list leaks other-region rows for any customer
    // whose CID happened to appear in the selected region — so the "Download
    // Excel" would show all outstanding, not just the region the user picked.
    var invoiceRows = [];
    openInv.forEach(function(r){
      var ci = String(r['Company ID'] || '').trim();
      if (!byCid[ci]) return;
      if (bus.length && bus.indexOf(String(r['Business'] || '')) === -1) return;
      if (cids.length && cids.indexOf(ci) === -1) return;
      invoiceRows.push({
        cid: ci,
        customer: byCid[ci].customer,
        channel: String(r['Channel'] || ''),
        transactionType: String(r['Transaction_Type'] || ''),
        invoiceNo: String(r['Invoice_No'] || ''),
        invoiceType: String(r['Invoice_Type'] || ''),
        invoiceDate: r['Invoice_Date'] || '',
        dueDate: r['Due_Date'] || '',
        invoiceAmount: Number(r['Invoice_Amount'] || 0),
        outstandingAmount: Number(r['Outstanding_Amount'] || 0),
        business: String(r['Business'] || ''),
        days: Number(r['Days'] || 0)
      });
    });

    return respond_({ ok: true, customers: list, invoices: invoiceRows, sender: FOLLOWUP_SENDER, bcc: FOLLOWUP_BCC }, e);

  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

function invoiceToPreview_(r) {
  return {
    invoiceNo: String(r['Invoice_No'] || ''),
    channel: String(r['Channel'] || ''),
    transactionType: String(r['Transaction_Type'] || ''),
    invoiceDate: r['Invoice_Date'] || '',
    dueDate: r['Due_Date'] || '',
    invoiceAmount: Number(r['Invoice_Amount'] || 0),
    outstandingAmount: Number(r['Outstanding_Amount'] || 0),
    days: Number(r['Days'] || 0)
  };
}

// ----- Send routes ---------------------------------------------------

function sendOneRoute_(e) {
  try {
    var p = e.parameter || {};
    var cid = String(p.cid || '').trim();
    var force = String(p.force || '') === '1';
    var templateId = String(p.templateId || '').trim();
    // Same region scope used during preview. When set, the sent email only
    // lists invoices from the selected Business(es) — matching what the user
    // saw in the on-screen Follow-up preview.
    var bus = (p.bus || '').split(',').map(function(s){ return s.trim(); }).filter(Boolean);
    if (!cid) throw new Error('Missing cid');
    var result = sendFollowUp_(cid, false, force, templateId, bus);
    return respond_(result, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

function sendBulkRoute_(e) {
  try {
    var p = e.parameter || {};
    var cids = (p.cids || '').split(',').map(function(s){ return s.trim(); }).filter(Boolean);
    var force = String(p.force || '') === '1';
    var templateId = String(p.templateId || '').trim();
    var bus = (p.bus || '').split(',').map(function(s){ return s.trim(); }).filter(Boolean);
    if (cids.length === 0) throw new Error('No CIDs provided');
    var results = [];
    for (var i = 0; i < cids.length; i++) {
      try {
        var r = sendFollowUp_(cids[i], false, force, templateId, bus);
        results.push(r);
      } catch (err) {
        results.push({ ok: false, cid: cids[i], error: String(err && err.message || err) });
      }
      if (i < cids.length - 1) Utilities.sleep(BULK_DELAY_MS);
    }
    var ok = results.filter(function(r){ return r.ok; }).length;
    return respond_({ ok: true, total: results.length, successCount: ok, failureCount: results.length - ok, results: results }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

/**
 * The core send function. Re-reads AR_Data live, builds the email
 * from the current open-INV snapshot, sends via GmailApp from
 * ar@gofynd.com (alias), and appends to Email_Log.
 */
function sendFollowUp_(cid, dryRun, force, templateId, bus) {
  cid = String(cid).trim();
  var busFilter = (Array.isArray(bus) && bus.length) ? bus : null;
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var contacts = readContacts_(ss);
  var contact = contacts[cid];
  if (!contact) {
    return { ok: false, cid: cid, error: 'No contact for ' + cid };
  }
  if (!contact.to) {
    return { ok: false, cid: cid, error: 'No To Email for ' + cid };
  }

  // Cooldown check
  if (!force) {
    var cooldown = cooldownStatus_(ss, cid);
    if (cooldown.active) {
      return { ok: false, cid: cid, error: 'Cooldown active — last sent ' + cooldown.lastSent, cooldown: cooldown };
    }
  }

  // Re-read AR live → automatic append/remove.
  // When bus filter is set, only that region's invoices are pulled — the
  // email body then matches what the user previewed and expected to send.
  var ar = readTab_(ss, resolveTab_(ss.getSheets().map(function(s){return s.getName();}), TAB_AR_CANDIDATES)).rows
            .filter(function(r){ return !rowHasError_(r); });
  var inv = getOpenInvForCid_(ar, cid, { bus: busFilter });
  if (inv.length === 0) {
    return { ok: false, cid: cid, error: 'No open INV invoices' };
  }

  var custName = contact.name || (inv[0]['Seller_Name'] || inv[0]['Seller Name'] || '');
  var bu = String(inv[0]['Business'] || '');
  var built;
  if (templateId) {
    var tpl = getEmailTemplateById_(ss, templateId);
    if (tpl) {
      var collectorName = resolveCollectorName_(ss) || '';
      built = buildEmailFromTemplate_(tpl, custName, inv, { collector_name: collectorName });
    } else {
      built = buildFollowUpHtml_(custName, inv);
    }
  } else {
    built = buildFollowUpHtml_(custName, inv);
  }

  var status = 'Sent', errMsg = '', messageId = '';
  // Track which sender actually ended up being used (may differ from FOLLOWUP_SENDER
  // if the alias isn't verified on the Apps Script account).
  var senderUsed = FOLLOWUP_SENDER;

  if (!dryRun) {
    // Validate that FOLLOWUP_SENDER is a verified "Send mail as" alias.
    // GmailApp.sendEmail({from: ...}) throws "Invalid argument: from" when the
    // alias isn't set up — but in some accounts the message still gets delivered
    // from the user's default sender. To make the log honest, validate first
    // and fall back cleanly when the alias is missing.
    var aliases = [];
    try { aliases = GmailApp.getAliases() || []; } catch (_) { aliases = []; }
    var aliasOK = (aliases.indexOf(FOLLOWUP_SENDER) !== -1);

    try {
      var opts = {
        htmlBody: built.htmlBody,
        replyTo: FOLLOWUP_REPLY_TO,
        name: FOLLOWUP_FROM_NAME,
        bcc: FOLLOWUP_BCC
      };
      if (aliasOK) {
        opts.from = FOLLOWUP_SENDER;
      } else {
        // No verified alias — send from default sender; record that fact.
        senderUsed = Session.getActiveUser().getEmail() || '(default account)';
        errMsg = 'Alias ' + FOLLOWUP_SENDER + ' is not in GmailApp.getAliases() — ' +
                 'email was sent from default sender (' + senderUsed + '). ' +
                 'Set up "Send mail as" for ' + FOLLOWUP_SENDER + ' in Gmail settings, then redeploy.';
      }
      if (contact.cc) opts.cc = contact.cc;

      // ===== THREADING =====
      // If we've already emailed this recipient with this exact subject before,
      // reply on the existing thread so Gmail keeps the whole conversation
      // together (subject acts as the key). Otherwise send a brand-new email.
      var searchSender = aliasOK ? FOLLOWUP_SENDER : senderUsed;
      var existingThread = findExistingThread_(searchSender, contact.to, built.subject);
      if (existingThread) {
        // GmailThread.reply() keeps Gmail-side threading; ‘from’ alias is honoured
        // only when present in opts (GmailApp will fall back to default sender otherwise).
        existingThread.replyAll('', opts);
        try {
          var tmsgs = existingThread.getMessages();
          if (tmsgs && tmsgs.length) messageId = tmsgs[tmsgs.length-1].getId();
        } catch (_) {}
      } else {
        GmailApp.sendEmail(contact.to, built.subject, '', opts);
        // Best-effort message-id capture for the freshly-sent email.
        try {
          var q = 'to:' + contact.to + ' from:' + searchSender + ' newer_than:1d';
          var threads = GmailApp.search(q, 0, 1);
          if (threads && threads.length) {
            var msgs = threads[0].getMessages();
            if (msgs && msgs.length) messageId = msgs[msgs.length-1].getId();
          }
        } catch (_) {}
      }
    } catch (err) {
      status = 'Failed';
      errMsg = String(err && err.message || err);
    }
  } else {
    status = 'DryRun';
  }

  // Always log (sent OR failed OR dryrun)
  appendEmailLog_(ss, {
    timestamp: new Date(),
    cid: cid,
    customer: custName,
    bu: bu,
    to: contact.to,
    cc: contact.cc || '',
    bcc: FOLLOWUP_BCC,
    sender: senderUsed,
    invoiceCount: built.invoiceCount,
    invoiceTotal: built.invoiceTotal,
    outstandingTotal: built.outstandingTotal,
    invoiceNumbers: inv.map(function(r){ return r['Invoice_No']; }).join(', '),
    status: status,
    messageId: messageId,
    error: errMsg
  });

  return {
    ok: status === 'Sent' || status === 'DryRun',
    cid: cid,
    customer: custName,
    to: contact.to,
    invoiceCount: built.invoiceCount,
    invoiceTotal: built.invoiceTotal,
    outstandingTotal: built.outstandingTotal,
    status: status,
    error: errMsg
  };
}

/**
 * Look up the most recent Gmail thread between this sender and recipient
 * that has the same subject — used so follow-up emails reply on the
 * same conversation thread instead of starting a fresh one each time.
 *
 * Returns the GmailThread on success, or null when no matching thread exists
 * (or when the search fails for any reason — we never throw out of here).
 */
function findExistingThread_(senderEmail, recipientEmail, subject) {
  try {
    // Strip any leading "Re:" / "Fwd:" so the search matches the original subject.
    var s = String(subject || '').replace(/^(\s*(re|fw|fwd)\s*:\s*)+/i, '').trim();
    if (!s || !senderEmail || !recipientEmail) return null;
    // Gmail's search treats backslash-escaped quotes inside a "subject:..." phrase as literal.
    var qSubj = s.replace(/"/g, '\\"');
    // Restrict to recent threads to keep the search fast; 180d covers most real follow-up cadences.
    var q = 'from:' + senderEmail + ' to:' + recipientEmail +
            ' subject:"' + qSubj + '" newer_than:180d';
    var threads = GmailApp.search(q, 0, 5);
    if (threads && threads.length) {
      // Most-recent thread wins (GmailApp.search returns newest first).
      return threads[0];
    }
  } catch (_) { /* swallow — fall through to null */ }
  return null;
}

// ----- Email_Log -----------------------------------------------------

var LOG_HEADERS = [
  'Timestamp','CID','Customer','BU','To','CC','BCC','Sender',
  'Invoice Count','Invoice Total','Outstanding Total','Invoice Numbers',
  'Status','Gmail Message ID','Error'
];

function ensureLogTab_(ss) {
  var sh = ss.getSheetByName(LOG_TAB);
  if (!sh) {
    sh = ss.insertSheet(LOG_TAB);
    sh.getRange(1, 1, 1, LOG_HEADERS.length).setValues([LOG_HEADERS]);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, LOG_HEADERS.length)
      .setFontWeight('bold')
      .setBackground('#2c4a52')
      .setFontColor('#ffffff');
    sh.setColumnWidths(1, LOG_HEADERS.length, 130);
  }
  return sh;
}

function appendEmailLog_(ss, entry) {
  var sh = ensureLogTab_(ss);
  sh.appendRow([
    entry.timestamp,
    entry.cid,
    entry.customer,
    entry.bu,
    entry.to,
    entry.cc,
    entry.bcc,
    entry.sender,
    entry.invoiceCount,
    entry.invoiceTotal,
    entry.outstandingTotal,
    entry.invoiceNumbers,
    entry.status,
    entry.messageId,
    entry.error
  ]);
}

function cooldownStatus_(ss, cid) {
  var sh = ss.getSheetByName(LOG_TAB);
  if (!sh) return { active: false };
  var v = sh.getDataRange().getValues();
  if (v.length < 2) return { active: false };
  var head = v[0];
  var iCid = head.indexOf('CID'), iTs = head.indexOf('Timestamp'), iSt = head.indexOf('Status');
  if (iCid === -1 || iTs === -1) return { active: false };
  var nowMs = (new Date()).getTime();
  var cutoff = nowMs - COOLDOWN_HOURS * 3600 * 1000;
  var latest = null;
  for (var i = v.length - 1; i >= 1; i--) {
    if (String(v[i][iCid]).trim() !== String(cid).trim()) continue;
    var st = String(v[i][iSt] || '').toLowerCase();
    if (st !== 'sent') continue;
    var ts = v[i][iTs];
    var d = (ts instanceof Date) ? ts : new Date(ts);
    if (!latest || d.getTime() > latest.getTime()) latest = d;
  }
  if (!latest) return { active: false };
  var active = latest.getTime() > cutoff;
  return {
    active: active,
    lastSent: Utilities.formatDate(latest, 'Asia/Kolkata', 'dd-MMM-yyyy HH:mm'),
    until: Utilities.formatDate(new Date(latest.getTime() + COOLDOWN_HOURS*3600*1000), 'Asia/Kolkata', 'dd-MMM-yyyy HH:mm')
  };
}

// ----- Activity log read + monthly report ---------------------------

function activityLogRoute_(e) {
  try {
    var p = e.parameter || {};
    var fromS = p.from || ''; // yyyy-mm-dd
    var toS   = p.to   || '';
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sh = ss.getSheetByName(LOG_TAB);
    if (!sh) return respond_({ ok: true, rows: [], summary: emptySummary_() }, e);

    var v = sh.getDataRange().getValues();
    if (v.length < 2) return respond_({ ok: true, rows: [], summary: emptySummary_() }, e);
    var head = v[0];
    var rows = [];
    var from = fromS ? new Date(fromS+'T00:00:00') : null;
    var to   = toS   ? new Date(toS  +'T23:59:59') : null;
    for (var i = 1; i < v.length; i++) {
      var r = {};
      for (var j = 0; j < head.length; j++) {
        var val = v[i][j];
        if (val instanceof Date) val = Utilities.formatDate(val, 'Asia/Kolkata', "yyyy-MM-dd'T'HH:mm:ssXXX");
        r[head[j]] = val;
      }
      var ts = v[i][head.indexOf('Timestamp')];
      var d = (ts instanceof Date) ? ts : new Date(ts);
      if (from && d < from) continue;
      if (to && d > to) continue;
      rows.push(r);
    }

    // Summary — Outstanding Chased is DEDUPED by (CID|Invoice Number) so the
    // same invoice chased N times counts its outstanding amount only ONCE.
    // We apportion each log row's Outstanding Total evenly across the invoices
    // it covers (Outstanding Total / Invoice Count) and accumulate the first
    // occurrence per (CID|invoice).
    var summary = { total: rows.length, sent: 0, failed: 0, customers: {}, totalOs: 0, monthly: {} };
    var seenInvAll = {}; // overall dedup
    var seenInvMonth = {}; // per-month dedup
    rows.forEach(function(r){
      if (String(r['Status']).toLowerCase() === 'sent') summary.sent++;
      else if (String(r['Status']).toLowerCase() === 'failed') summary.failed++;
      summary.customers[r['CID']] = true;
      var ts = r['Timestamp'];
      var ym = String(ts).slice(0, 7); // yyyy-MM
      if (!summary.monthly[ym]) summary.monthly[ym] = { sends: 0, customers: {}, outstanding: 0 };
      summary.monthly[ym].sends++;
      summary.monthly[ym].customers[r['CID']] = true;
      // ----- Deduped outstanding -----
      var invNos = String(r['Invoice Numbers'] || '').split(/[,;\n]+/).map(function(s){return s.trim();}).filter(function(s){return !!s;});
      var cnt = invNos.length || Number(r['Invoice Count'] || 0) || 1;
      var totOs = Number(r['Outstanding Total'] || 0);
      var perInv = totOs / cnt;
      var cid = r['CID'];
      if (!seenInvMonth[ym]) seenInvMonth[ym] = {};
      if (invNos.length) {
        invNos.forEach(function(inv){
          var key = String(cid) + '||' + inv;
          if (!seenInvAll[key])      { seenInvAll[key]      = true; summary.totalOs += perInv; }
          if (!seenInvMonth[ym][key]){ seenInvMonth[ym][key]= true; summary.monthly[ym].outstanding += perInv; }
        });
      } else {
        // Fallback when Invoice Numbers missing: dedup by (CID, log row id ~ timestamp)
        var fkey = String(cid) + '||TS||' + String(ts);
        if (!seenInvAll[fkey])      { seenInvAll[fkey]      = true; summary.totalOs += totOs; }
        if (!seenInvMonth[ym][fkey]){ seenInvMonth[ym][fkey]= true; summary.monthly[ym].outstanding += totOs; }
      }
    });
    summary.uniqueCustomers = Object.keys(summary.customers).length;
    delete summary.customers;
    Object.keys(summary.monthly).forEach(function(ym){
      summary.monthly[ym].uniqueCustomers = Object.keys(summary.monthly[ym].customers).length;
      delete summary.monthly[ym].customers;
    });

    return respond_({ ok: true, rows: rows, summary: summary }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

function emptySummary_() {
  return { total: 0, sent: 0, failed: 0, uniqueCustomers: 0, totalOs: 0, monthly: {} };
}

// ===============================================================
// User audit log — every user-initiated action (add / edit / delete /
// sync / bulk import / config change) posts here so an admin can trace
// who did what and when. Read via auditLogListRoute_; write via
// auditLogRoute_. The sheet is created on first write.
// ===============================================================
function _auditSheet_(ss) {
  var sh = ss.getSheetByName(AUDIT_TAB);
  if (!sh) {
    sh = ss.insertSheet(AUDIT_TAB);
    sh.getRange(1, 1, 1, 5).setValues([['Timestamp', 'User', 'Action', 'Details', 'UserAgent']]);
    sh.setFrozenRows(1);
    try {
      sh.getRange(1, 1, 1, 5).setFontWeight('bold').setBackground('#f5f2ed');
      sh.setColumnWidth(1, 170); // Timestamp
      sh.setColumnWidth(2, 220); // User
      sh.setColumnWidth(3, 200); // Action
      sh.setColumnWidth(4, 500); // Details
      sh.setColumnWidth(5, 260); // UserAgent
    } catch (_) {}
  }
  return sh;
}
function auditLogRoute_(e) {
  try {
    var p = e.parameter || {};
    var action = String(p.event || p.a || '').slice(0, 120);
    if (!action) return respond_({ ok: false, error: 'event required' }, e);
    // Details can be an arbitrary JSON blob — cap size so a runaway caller
    // can't fill the sheet with megabytes per row.
    var details = String(p.details || p.d || '').slice(0, 4000);
    var ua = String(p.ua || '').slice(0, 260);
    var em = '';
    try { em = getViewerEmail_(e) || ''; } catch (_) {}
    var ts = Utilities.formatDate(new Date(), 'Asia/Kolkata', "yyyy-MM-dd'T'HH:mm:ssXXX");
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sh = _auditSheet_(ss);
    sh.appendRow([ts, em || '(unknown)', action, details, ua]);
    return respond_({ ok: true, ts: ts, user: em || '', action: action }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}
function auditLogListRoute_(e) {
  try {
    var p = e.parameter || {};
    // Admin-only read — regular users shouldn't be able to enumerate other
    // users' actions.
    var em = '';
    try { em = getViewerEmail_(e) || ''; } catch (_) {}
    if (!isAdmin_(em)) return respond_({ ok: false, error: 'admin only' }, e);
    var limit = Math.max(1, Math.min(5000, parseInt(p.limit || '500', 10)));
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sh = ss.getSheetByName(AUDIT_TAB);
    if (!sh) return respond_({ ok: true, rows: [] }, e);
    var v = sh.getDataRange().getValues();
    if (v.length < 2) return respond_({ ok: true, rows: [] }, e);
    var head = v[0];
    var out = [];
    // Newest first — walk from the bottom of the sheet up to `limit`.
    for (var i = v.length - 1; i >= 1 && out.length < limit; i--) {
      var r = {};
      for (var j = 0; j < head.length; j++) {
        var val = v[i][j];
        if (val instanceof Date) val = Utilities.formatDate(val, 'Asia/Kolkata', "yyyy-MM-dd'T'HH:mm:ssXXX");
        r[head[j]] = val;
      }
      out.push(r);
    }
    return respond_({ ok: true, rows: out }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

function monthlyReportRoute_(e) {
  try {
    var p = e.parameter || {};
    var ym = p.month || ''; // yyyy-mm
    if (!/^\d{4}-\d{2}$/.test(ym)) throw new Error('Pass ?month=YYYY-MM');
    var data = generateMonthlyReportData_(ym);
    return respond_({ ok: true, month: ym, report: data }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

function generateMonthlyReportData_(ym) {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sh = ss.getSheetByName(LOG_TAB);
  if (!sh) return { rows: [], summary: emptySummary_() };
  var v = sh.getDataRange().getValues();
  if (v.length < 2) return { rows: [], summary: emptySummary_() };
  var head = v[0];
  var iTs = head.indexOf('Timestamp');
  var rows = [];
  for (var i = 1; i < v.length; i++) {
    var ts = v[i][iTs];
    var d = (ts instanceof Date) ? ts : new Date(ts);
    var rowYm = Utilities.formatDate(d, 'Asia/Kolkata', 'yyyy-MM');
    if (rowYm !== ym) continue;
    var r = {};
    for (var j = 0; j < head.length; j++) {
      var val = v[i][j];
      if (val instanceof Date) val = Utilities.formatDate(val, 'Asia/Kolkata', "yyyy-MM-dd HH:mm:ss");
      r[head[j]] = val;
    }
    rows.push(r);
  }
  var byCustomer = {};
  // Per-customer invoice dedup: same invoice chased N times in this month
  // contributes its outstanding only ONCE per customer.
  var seenInvByCust = {};
  rows.forEach(function(r){
    var k = r['CID'] + '|' + r['Customer'];
    if (!byCustomer[k]) byCustomer[k] = { cid: r['CID'], customer: r['Customer'], bu: r['BU'], sends: 0, lastSent: '', totalOs: 0, statuses: {} };
    byCustomer[k].sends++;
    if (!byCustomer[k].lastSent || r['Timestamp'] > byCustomer[k].lastSent) byCustomer[k].lastSent = r['Timestamp'];
    var invNos = String(r['Invoice Numbers'] || '').split(/[,;\n]+/).map(function(s){return s.trim();}).filter(function(s){return !!s;});
    var cnt = invNos.length || Number(r['Invoice Count'] || 0) || 1;
    var perInv = Number(r['Outstanding Total'] || 0) / cnt;
    if (!seenInvByCust[k]) seenInvByCust[k] = {};
    if (invNos.length) {
      invNos.forEach(function(inv){
        if (!seenInvByCust[k][inv]) { seenInvByCust[k][inv] = true; byCustomer[k].totalOs += perInv; }
      });
    } else {
      // Fallback when Invoice Numbers missing
      var fk = 'TS||' + String(r['Timestamp']);
      if (!seenInvByCust[k][fk]) { seenInvByCust[k][fk] = true; byCustomer[k].totalOs += Number(r['Outstanding Total'] || 0); }
    }
    byCustomer[k].statuses[r['Status']] = (byCustomer[k].statuses[r['Status']] || 0) + 1;
  });
  return {
    month: ym,
    totalSends: rows.length,
    uniqueCustomers: Object.keys(byCustomer).length,
    sent: rows.filter(function(r){ return String(r['Status']).toLowerCase() === 'sent'; }).length,
    failed: rows.filter(function(r){ return String(r['Status']).toLowerCase() === 'failed'; }).length,
    perCustomer: Object.keys(byCustomer).map(function(k){ return byCustomer[k]; }),
    rows: rows
  };
}

// ===============================================================
// ACCESS MATRIX — admin-only management of who sees which tabs
// ===============================================================
function getActiveUserEmail_() {
  // Returns the VIEWER's email — ONLY when the script is deployed as
  //   "Execute as: User accessing the web app"
  //   "Who has access: Anyone within <your Workspace domain>"
  // and the viewer is signed in to that Workspace.
  //
  // CRITICAL: we deliberately do NOT fall back to Session.getEffectiveUser()
  // here. EffectiveUser is the DEPLOYER (= you, the admin) — falling back to
  // it makes every anonymous/incognito viewer look like the admin and grants
  // them admin powers. Return empty string instead, and let isAdmin_() reject.
  try {
    var e = Session.getActiveUser().getEmail();
    return String(e || '').toLowerCase().trim();
  } catch (_) { return ''; }
}
function isAdmin_(email) {
  var em = String(email || '').toLowerCase().trim();
  if (!em) return false;                              // never grant admin to anonymous
  return em === String(ADMIN_EMAIL).toLowerCase();    // exact match required
}
function ensureAcmTab_(ss) {
  var sh = ss.getSheetByName(ACM_TAB);
  if (!sh) {
    sh = ss.insertSheet(ACM_TAB);
    sh.getRange(1, 1, 1, ACM_HEADERS.length).setValues([ACM_HEADERS]);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, ACM_HEADERS.length)
      .setFontWeight('bold').setBackground('#2c4a52').setFontColor('#ffffff');
    sh.setColumnWidths(1, ACM_HEADERS.length, 150);
    // Seed admin row so the sheet is never empty. Password columns are left
    // blank — the admin uses Google-identity break-glass by default and can
    // set a password later via the User Management UI.
    sh.appendRow([
      'Sainath Gosika', ADMIN_EMAIL, 'Finance / AR', 'Sheet Admin',
      ACM_ALL_TABS.join(','), Utilities.formatDate(new Date(),'Asia/Kolkata','yyyy-MM-dd'),
      'Owner', 'Yes',
      'sainath',  // Username — case-insensitive login handle
      '', '', '', 0, ''
    ]);
  } else {
    // Auto-migrate legacy sheets by APPENDING any missing header columns at
    // the end. Existing rows keep their values; new columns land blank.
    var existingHeader = (sh.getLastColumn() > 0)
      ? sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0].map(function(h){ return String(h||'').trim(); })
      : [];
    var missing = ACM_HEADERS.filter(function(h){ return existingHeader.indexOf(h) === -1; });
    if (missing.length) {
      var startCol = existingHeader.length + 1;
      sh.getRange(1, startCol, 1, missing.length).setValues([missing]);
      sh.getRange(1, startCol, 1, missing.length).setFontWeight('bold').setBackground('#2c4a52').setFontColor('#ffffff');
    }
  }
  return sh;
}
// Ensure the Auth_Sessions tab exists. Same pattern as ensureAcmTab_: create
// with headers if missing, otherwise auto-append any new headers.
function ensureSessionsTab_(ss) {
  var sh = ss.getSheetByName(SESSIONS_TAB);
  if (!sh) {
    sh = ss.insertSheet(SESSIONS_TAB);
    sh.getRange(1, 1, 1, SESSIONS_HEADERS.length).setValues([SESSIONS_HEADERS]);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, SESSIONS_HEADERS.length)
      .setFontWeight('bold').setBackground('#2c4a52').setFontColor('#ffffff');
    sh.setColumnWidths(1, SESSIONS_HEADERS.length, 150);
    // Hide the tab from casual viewers — tokens are secrets.
    try { sh.hideSheet(); } catch (_) {}
  } else {
    var existingHeader = (sh.getLastColumn() > 0)
      ? sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0].map(function(h){ return String(h||'').trim(); })
      : [];
    var missing = SESSIONS_HEADERS.filter(function(h){ return existingHeader.indexOf(h) === -1; });
    if (missing.length) {
      var startCol = existingHeader.length + 1;
      sh.getRange(1, startCol, 1, missing.length).setValues([missing]);
      sh.getRange(1, startCol, 1, missing.length).setFontWeight('bold').setBackground('#2c4a52').setFontColor('#ffffff');
    }
  }
  return sh;
}
function readAcm_() {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sh = ensureAcmTab_(ss);
  var v = sh.getDataRange().getValues();
  if (v.length < 2) return { rows: [], byEmail: {}, byUsername: {}, sheet: sh, headers: v[0] || [], idx: {} };
  var head = v[0];
  var idx = {};
  head.forEach(function(h, i){ idx[String(h).trim()] = i; });
  // Optional columns default to '' / 0 when missing on legacy sheets.
  function _col(row, key, fallback) {
    return (idx[key] != null) ? row[idx[key]] : (fallback == null ? '' : fallback);
  }
  var rows = [];
  var byEmail = {};
  var byUsername = {};
  for (var i = 1; i < v.length; i++) {
    var em = String(v[i][idx['Email']] || '').toLowerCase().trim();
    if (!em) continue;
    var tabsRaw = String(v[i][idx['Tabs']] || '').trim();
    var tabs = tabsRaw ? tabsRaw.split(/[,;\s]+/).map(function(s){return s.trim();}).filter(Boolean) : [];
    var username = String(_col(v[i], 'Username', '') || '').trim();
    var lockedUntilRaw = _col(v[i], 'Locked Until', '');
    var failedAttemptsRaw = _col(v[i], 'Failed Attempts', 0);
    var lastLoginRaw = _col(v[i], 'Last Login At', '');
    var row = {
      name:        v[i][idx['Name']] || '',
      email:       em,
      department:  v[i][idx['Department']] || '',
      role:        v[i][idx['Role']] || '',
      tabs:        tabs,
      provisionedOn: v[i][idx['Provisioned On']] || '',
      notes:       v[i][idx['Notes']] || '',
      active:      String(v[i][idx['Active']] || 'Yes').toLowerCase() === 'yes',
      username:    username,
      passwordHash: String(_col(v[i], 'Password Hash', '') || ''),
      passwordSalt: String(_col(v[i], 'Password Salt', '') || ''),
      lastLoginAt: (lastLoginRaw instanceof Date)
        ? lastLoginRaw.toISOString()
        : String(lastLoginRaw || ''),
      failedAttempts: Number(failedAttemptsRaw || 0) || 0,
      lockedUntil: (lockedUntilRaw instanceof Date)
        ? lockedUntilRaw.getTime()
        : (lockedUntilRaw === '' || lockedUntilRaw == null
            ? 0
            : (isNaN(Number(lockedUntilRaw)) ? Date.parse(String(lockedUntilRaw)) || 0 : Number(lockedUntilRaw))),
      _rowIndex:   i + 1
    };
    rows.push(row);
    byEmail[em] = row;
    if (username) byUsername[username.toLowerCase()] = row;
  }
  return { rows: rows, byEmail: byEmail, byUsername: byUsername, sheet: sh, headers: head, idx: idx };
}

// ===============================================================
// AUTH — session tokens + password hashing (application-level layer)
// ===============================================================
// The auth flow lives on top of the existing Google-identity primitive
// (getActiveUserEmail_). Callers should use getViewerEmail_(e) which prefers
// a valid session token from e.parameter._tok before falling back to the
// Google-identity primitive. The break-glass path for the admin
// (ADMIN_EMAIL via Google identity, no token) is preserved so the admin
// can never lock themselves out of their own instance.

// _authGenToken_ — 32 bytes of randomness expressed as hex. Two UUIDs
// concatenated with hyphens removed give us 64 hex chars ≈ 256 bits of
// entropy, which is comfortably beyond a session token's needs.
function _authGenToken_() {
  var a = Utilities.getUuid().replace(/-/g, '');
  var b = Utilities.getUuid().replace(/-/g, '');
  return (a + b).toLowerCase().slice(0, 64);
}
// _authGenSalt_ — 16 bytes hex (32 chars). Enough per-user entropy that a
// stolen sheet doesn't let an attacker precompute rainbow tables.
function _authGenSalt_() {
  return Utilities.getUuid().replace(/-/g, '').toLowerCase().slice(0, 32);
}
// _authHashPassword_ — SHA-256(salt + password) as lowercase hex.
// NOT bcrypt/scrypt — Apps Script doesn't ship either — but with a random
// per-user salt SHA-256 is still safe against basic dictionary attacks
// on a hypothetically leaked sheet. Do NOT log the input or output.
function _authHashPassword_(password, salt) {
  var raw = String(salt || '') + String(password || '');
  var bytes = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, raw);
  var hex = '';
  for (var i = 0; i < bytes.length; i++) {
    var v = bytes[i]; if (v < 0) v += 256;
    var s = v.toString(16); if (s.length < 2) s = '0' + s;
    hex += s;
  }
  return hex;
}
// _authValidatePasswordRules_ — returns null if OK, else an error string.
// Rules: length >= 6 AND at least one letter AND one number AND one symbol.
function _authValidatePasswordRules_(pw) {
  var s = String(pw == null ? '' : pw);
  if (s.length < 6) return 'Password must be at least 6 characters.';
  if (!/[A-Za-z]/.test(s)) return 'Password must contain at least one letter.';
  if (!/[0-9]/.test(s))    return 'Password must contain at least one number.';
  if (!/[^A-Za-z0-9]/.test(s)) return 'Password must contain at least one symbol.';
  return null;
}
// _authIssueSession_ — writes a new row to Auth_Sessions and returns the
// issued token + expiresAt (epoch ms). Fixed TTL — no sliding.
function _authIssueSession_(email, username, userAgent) {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sh = ensureSessionsTab_(ss);
  var token = _authGenToken_();
  var now = Date.now();
  var expiresAt = now + SESSION_TTL_MS;
  sh.appendRow([token, String(email || '').toLowerCase(), String(username || ''), now, expiresAt, now, String(userAgent || '').slice(0, 400)]);
  return { token: token, expiresAt: expiresAt };
}
// _authValidateToken_ — returns { email, username, expiresAt, _rowIndex } or null.
// Expired rows return null (and are treated as invalid).
function _authValidateToken_(token) {
  token = String(token || '').trim();
  if (!token) return null;
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sh = ensureSessionsTab_(ss);
  var last = sh.getLastRow();
  if (last < 2) return null;
  var v = sh.getRange(2, 1, last - 1, SESSIONS_HEADERS.length).getValues();
  var now = Date.now();
  for (var i = 0; i < v.length; i++) {
    if (String(v[i][0]) === token) {
      var exp = Number(v[i][4] || 0);
      if (!exp || exp <= now) return null;
      return {
        email: String(v[i][1] || '').toLowerCase(),
        username: String(v[i][2] || ''),
        issuedAt: Number(v[i][3] || 0),
        expiresAt: exp,
        _rowIndex: i + 2
      };
    }
  }
  return null;
}
// _authInvalidateToken_ — deletes the row for `token`, if present.
function _authInvalidateToken_(token) {
  token = String(token || '').trim();
  if (!token) return false;
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sh = ensureSessionsTab_(ss);
  var last = sh.getLastRow();
  if (last < 2) return false;
  var v = sh.getRange(2, 1, last - 1, 1).getValues();
  for (var i = 0; i < v.length; i++) {
    if (String(v[i][0]) === token) {
      sh.deleteRow(i + 2);
      return true;
    }
  }
  return false;
}
// _authCleanupExpiredSessions_ — purges expired rows (best effort).
function _authCleanupExpiredSessions_() {
  try {
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sh = ensureSessionsTab_(ss);
    var last = sh.getLastRow();
    if (last < 2) return;
    var v = sh.getRange(2, 1, last - 1, SESSIONS_HEADERS.length).getValues();
    var now = Date.now();
    // Delete from bottom-up so indices stay stable.
    for (var i = v.length - 1; i >= 0; i--) {
      var exp = Number(v[i][4] || 0);
      if (!exp || exp <= now) {
        try { sh.deleteRow(i + 2); } catch (_) {}
      }
    }
  } catch (_) {}
}
// getViewerEmail_ — identity source used inside route handlers. If a valid
// _tok is on the request, its email wins. Otherwise fall back to the
// Google-identity primitive. This lets a token-authed viewer (including a
// non-Google-identified caller) act as themselves without breaking existing
// Google-identity-only deployments.
function getViewerEmail_(e) {
  try {
    var p = (e && e.parameter) || {};
    var tok = String(p._tok || '').trim();
    if (tok) {
      var sess = _authValidateToken_(tok);
      if (sess && sess.email) return String(sess.email).toLowerCase().trim();
    }
  } catch (_) {}
  return getActiveUserEmail_();
}
// _authTabsFor_ — resolve the tabs list for a given email, mirrors
// whoAmIRoute_'s logic so authWhoAmIRoute_ can return the same shape.
function _authTabsFor_(em) {
  var admin = isAdmin_(em);
  var collectorFlag = false;
  try { collectorFlag = !!isCollector_(em); } catch (_) {}
  var allowed;
  if (admin) {
    allowed = ACM_ALL_TABS.slice();
  } else {
    var acm = readAcm_();
    var rec = acm.byEmail[em];
    if (rec && rec.active && rec.tabs && rec.tabs.length) {
      // `acm` (User Management) is strictly admin-only. Even if a legacy
      // row still lists it, strip it here so non-admins can never see it.
      allowed = rec.tabs.filter(function(t){ return t !== 'acm'; });
    } else {
      allowed = ACM_DEFAULT_TABS.slice();
    }
    if (collectorFlag && allowed.indexOf('worklist') === -1) {
      allowed.push('worklist');
    }
  }
  return { isAdmin: admin, isCollector: collectorFlag, tabs: allowed };
}

// ---- whoAmI: tells the dashboard who's viewing + which tabs they can see ----
function whoAmIRoute_(e) {
  try {
    // Token path — if the caller ships _tok, hand off to the auth-aware
    // route so token identity supersedes Google identity.
    var pTok = (e && e.parameter && e.parameter._tok) ? String(e.parameter._tok).trim() : '';
    if (pTok) return authWhoAmIRoute_(e);
    var em = getViewerEmail_(e);
    var admin = isAdmin_(em);
    // Diagnostic: if active user is empty, the deployment is either
    //   (a) "Execute as: Me" — script can never see the real viewer, or
    //   (b) viewer is signed out / on a non-Workspace account.
    // Either way, we cannot identify the viewer and must NOT grant admin.
    var effective = '';
    try { effective = String(Session.getEffectiveUser().getEmail() || '').toLowerCase(); } catch (_) {}
    var deploymentWarning = '';
    if (!em) {
      deploymentWarning = 'Viewer identity unknown. Either the viewer is not signed in to a Workspace account, '
        + 'OR the Apps Script Web App is deployed as "Execute as: Me" (it must be "Execute as: User accessing the web app").';
    }

    var allowed;
    var collectorFlag = false;
    try { collectorFlag = !!isCollector_(em); } catch (_) {}
    if (admin) {
      allowed = ACM_ALL_TABS.slice(); // admin sees everything
    } else {
      var acm = readAcm_();
      var rec = acm.byEmail[em];
      if (rec && rec.active && rec.tabs && rec.tabs.length) {
        // `acm` (User Management) is strictly admin-only. Strip it if a
        // legacy row still carries it — non-admins never see this tab.
        allowed = rec.tabs.filter(function(t){ return t !== 'acm'; });
      } else {
        allowed = ACM_DEFAULT_TABS.slice();
      }
      // Auto-grant the worklist tab to anyone listed (and active) in Collector_Master.
      if (collectorFlag && allowed.indexOf('worklist') === -1) {
        allowed.push('worklist');
      }
    }
    return respond_({
      ok: true,
      email: em,
      effectiveEmail: effective, // for diagnostic only — never used for auth
      isAdmin: admin,
      isCollector: collectorFlag,
      tabs: allowed,
      adminEmail: ADMIN_EMAIL,
      allTabs: ACM_ALL_TABS,
      deploymentWarning: deploymentWarning
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

// ---- acmList: admin-only, return all stakeholder rows ----
function acmListRoute_(e) {
  try {
    var em = getViewerEmail_(e);
    if (!isAdmin_(em)) {
      return respond_({
        ok: false,
        error: 'Forbidden — admin only. Viewer email seen by the server: "' + (em || '(empty)') + '".',
        viewer: em
      }, e);
    }
    var acm;
    try { acm = readAcm_(); }
    catch (rerr) {
      return respond_({
        ok: false,
        error: 'Could not read Access_Matrix sheet: ' + String(rerr && rerr.message || rerr) +
               '. Make sure SHEET_ID is correct and the deployed script has spreadsheet access.'
      }, e);
    }
    // Strip the non-serialisable sheet handle + secrets (hashes/salts) before
    // returning. Never leak password material — even to the admin UI.
    var safeRows = (acm.rows || []).map(function(r){
      return {
        name: String(r.name || ''),
        email: String(r.email || ''),
        department: String(r.department || ''),
        role: String(r.role || ''),
        tabs: r.tabs || [],
        provisionedOn: (r.provisionedOn instanceof Date)
          ? Utilities.formatDate(r.provisionedOn, 'Asia/Kolkata', 'yyyy-MM-dd')
          : String(r.provisionedOn || ''),
        notes: String(r.notes || ''),
        active: !!r.active,
        username: String(r.username || ''),
        hasPassword: !!(r.passwordHash && r.passwordSalt),
        lastLoginAt: String(r.lastLoginAt || ''),
        failedAttempts: Number(r.failedAttempts || 0),
        lockedUntil: Number(r.lockedUntil || 0)
      };
    });
    return respond_({
      ok: true,
      rows: safeRows,
      allTabs: ACM_ALL_TABS,
      adminEmail: ADMIN_EMAIL
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: 'acmList exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- acmUpsert: admin-only, add or update stakeholder by email ----
function acmUpsertRoute_(e) {
  try {
    var em = getViewerEmail_(e);
    if (!isAdmin_(em)) return respond_({ ok: false, error: 'Forbidden — admin only.', viewer: em }, e);
    var p = e.parameter || {};
    var stakeholderEmail = String(p.email || '').toLowerCase().trim();
    if (!stakeholderEmail) throw new Error('email is required');
    var name        = String(p.name || '').trim();
    var department  = String(p.department || '').trim();
    var role        = String(p.role || '').trim();
    var tabsCsv     = String(p.tabs || '').trim();
    var notes       = String(p.notes || '').trim();
    // Form no longer sends Active — default to Yes for new rows, preserve on
    // updates. `active` param is still honored if explicitly provided.
    var provisionedOn = String(p.provisionedOn || Utilities.formatDate(new Date(),'Asia/Kolkata','yyyy-MM-dd'));

    // Username — required, unique across Access_Matrix (case-insensitive),
    // 3..32 chars of [A-Za-z0-9._-]. Enforced here so the UI can display the
    // exact server-side reason on a mismatch.
    var username = String(p.username || '').trim();
    if (!username) throw new Error('username is required');
    if (!/^[A-Za-z0-9._-]+$/.test(username)) throw new Error('Username may contain letters, digits, . _ - only.');
    if (username.length < 3 || username.length > 32) throw new Error('Username must be 3–32 characters.');

    var password = String(p.password || '');

    // Sanitize tabs against the allow-list. `acm` is admin-only and can never
    // be granted to non-admins, even if the admin ticks the box in the UI —
    // the checkbox for `acm` is not rendered, but strip defensively anyway.
    var requested = tabsCsv ? tabsCsv.split(/[,;\s]+/).map(function(s){return s.trim();}).filter(Boolean) : [];
    var clean = [];
    requested.forEach(function(t){
      if (ACM_ALL_TABS.indexOf(t) !== -1 && t !== 'acm') clean.push(t);
    });
    // De-dup
    var seen = {}; clean = clean.filter(function(t){ if(seen[t]) return false; seen[t]=true; return true; });

    var acm = readAcm_();
    var sh = acm.sheet;
    var existing = acm.byEmail[stakeholderEmail];

    // Username uniqueness — reject if another row already uses this username.
    var usernameOwner = acm.byUsername[username.toLowerCase()];
    if (usernameOwner && usernameOwner.email !== stakeholderEmail) {
      throw new Error('Username already in use by ' + usernameOwner.email + '.');
    }

    // Password handling: required for new rows, optional for updates.
    var passwordHash = existing ? String(existing.passwordHash || '') : '';
    var passwordSalt = existing ? String(existing.passwordSalt || '') : '';
    if (password) {
      var pwErr = _authValidatePasswordRules_(password);
      if (pwErr) throw new Error(pwErr);
      passwordSalt = _authGenSalt_();
      passwordHash = _authHashPassword_(password, passwordSalt);
    } else if (!existing) {
      throw new Error('password is required for new users');
    }

    var active;
    if (p.active != null && String(p.active).trim() !== '') {
      active = String(p.active).toLowerCase() === 'yes' ? 'Yes' : 'No';
    } else if (existing) {
      active = existing.active ? 'Yes' : 'No';
    } else {
      active = 'Yes'; // default for new rows — form no longer ships Active
    }

    // Preserve login-tracking columns on update; zero them on insert.
    var lastLoginAt   = existing ? String(existing.lastLoginAt || '') : '';
    var failedAttempts = existing ? Number(existing.failedAttempts || 0) : 0;
    var lockedUntil   = existing ? Number(existing.lockedUntil || 0) : 0;

    var rowData = [
      name, stakeholderEmail, department, role, clean.join(','),
      provisionedOn, notes, active,
      username, passwordHash, passwordSalt,
      lastLoginAt, failedAttempts, lockedUntil
    ];
    if (existing) {
      sh.getRange(existing._rowIndex, 1, 1, ACM_HEADERS.length).setValues([rowData]);
    } else {
      sh.appendRow(rowData);
    }
    return respond_({
      ok: true,
      email: stakeholderEmail,
      username: username,
      tabs: clean,
      mode: existing ? 'updated' : 'added'
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

// ---- acmDelete: admin-only, remove a stakeholder row by email ----
function acmDeleteRoute_(e) {
  try {
    var em = getViewerEmail_(e);
    if (!isAdmin_(em)) return respond_({ ok: false, error: 'Forbidden — admin only.', viewer: em }, e);
    var p = e.parameter || {};
    var target = String(p.email || '').toLowerCase().trim();
    if (!target) throw new Error('email is required');
    if (target === ADMIN_EMAIL.toLowerCase()) throw new Error('The admin row cannot be deleted.');
    var acm = readAcm_();
    var rec = acm.byEmail[target];
    if (!rec) return respond_({ ok: true, mode: 'not-found' }, e);
    acm.sheet.deleteRow(rec._rowIndex);
    return respond_({ ok: true, mode: 'deleted', email: target }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

// ===============================================================
// AUTH ROUTES (login / logout / whoAmI / password management)
// ===============================================================

// authLogin — username + password → session token. Applies the lockout
// policy after 5 failed attempts (15 min lock). Errors are intentionally
// generic ("Invalid username or password.") so the surface doesn't leak
// which field was wrong.
function authLoginRoute_(e) {
  try {
    _authCleanupExpiredSessions_(); // best-effort tidy of the sessions sheet
    var p = (e && e.parameter) || {};
    var username = String(p.username || '').trim();
    var password = String(p.password || '');
    if (!username || !password) {
      return respond_({ ok: false, error: 'Username and password are required.' }, e);
    }
    var acm = readAcm_();
    var rec = acm.byUsername[username.toLowerCase()];
    if (!rec) {
      // Constant-ish delay to blunt username enumeration timing attacks.
      try { Utilities.sleep(150); } catch (_) {}
      return respond_({ ok: false, error: 'Invalid username or password.' }, e);
    }
    if (!rec.active) {
      return respond_({ ok: false, error: 'Account inactive. Contact ' + ADMIN_EMAIL + '.' }, e);
    }
    var now = Date.now();
    if (rec.lockedUntil && rec.lockedUntil > now) {
      var mins = Math.ceil((rec.lockedUntil - now) / 60000);
      return respond_({ ok: false, error: 'Account temporarily locked. Try again in ' + mins + ' min.' }, e);
    }
    if (!rec.passwordHash || !rec.passwordSalt) {
      return respond_({ ok: false, error: 'No password set for this user. Contact ' + ADMIN_EMAIL + '.' }, e);
    }
    var candidate = _authHashPassword_(password, rec.passwordSalt);
    if (candidate !== rec.passwordHash) {
      // Increment failure counter, apply lockout if warranted.
      var fa = Number(rec.failedAttempts || 0) + 1;
      var lock = 0;
      if (fa >= 5) { lock = now + (15 * 60 * 1000); fa = 0; }
      var sh = acm.sheet;
      var faCol = (acm.idx['Failed Attempts'] || 0) + 1;
      var luCol = (acm.idx['Locked Until']    || 0) + 1;
      try {
        if (faCol > 0) sh.getRange(rec._rowIndex, faCol).setValue(fa);
        if (luCol > 0) sh.getRange(rec._rowIndex, luCol).setValue(lock);
      } catch (_) {}
      return respond_({ ok: false, error: 'Invalid username or password.' }, e);
    }
    // Success — clear counters, stamp last-login, issue token.
    var sh2 = acm.sheet;
    var faCol2 = (acm.idx['Failed Attempts'] || 0) + 1;
    var luCol2 = (acm.idx['Locked Until']    || 0) + 1;
    var llCol  = (acm.idx['Last Login At']   || 0) + 1;
    try {
      if (faCol2 > 0) sh2.getRange(rec._rowIndex, faCol2).setValue(0);
      if (luCol2 > 0) sh2.getRange(rec._rowIndex, luCol2).setValue(0);
      if (llCol  > 0) sh2.getRange(rec._rowIndex, llCol).setValue(new Date());
    } catch (_) {}
    var ua = String((p.ua || '') || '').slice(0, 400);
    var session = _authIssueSession_(rec.email, rec.username, ua);
    var tabsInfo = _authTabsFor_(rec.email);
    return respond_({
      ok: true,
      token: session.token,
      email: rec.email,
      username: rec.username,
      name: String(rec.name || ''),
      expiresAt: session.expiresAt,
      isAdmin: tabsInfo.isAdmin,
      isCollector: tabsInfo.isCollector,
      tabs: tabsInfo.tabs,
      adminEmail: ADMIN_EMAIL,
      allTabs: ACM_ALL_TABS
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

// authWhoAmI — token → identity + tabs. Preserves the Google-identity
// break-glass path for the admin so a misplaced token never locks them
// out of their own instance.
function authWhoAmIRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var tok = String(p._tok || '').trim();
    if (tok) {
      var sess = _authValidateToken_(tok);
      if (!sess) return respond_({ ok: false, needsLogin: true, error: 'Session expired. Please sign in again.' }, e);
      var acm = readAcm_();
      var rec = acm.byEmail[sess.email];
      var info = _authTabsFor_(sess.email);
      return respond_({
        ok: true,
        email: sess.email,
        username: sess.username || (rec && rec.username) || '',
        name: rec ? String(rec.name || '') : '',
        isAdmin: info.isAdmin,
        isCollector: info.isCollector,
        tabs: info.tabs,
        allTabs: ACM_ALL_TABS,
        adminEmail: ADMIN_EMAIL,
        expiresAt: sess.expiresAt,
        via: 'token'
      }, e);
    }
    // Break-glass: no token, but the Google identity IS the admin. Let them
    // in without a password so the owner can never lock themselves out.
    var goog = getActiveUserEmail_();
    if (goog && isAdmin_(getActiveUserEmail_())) {
      var info2 = _authTabsFor_(goog);
      return respond_({
        ok: true,
        email: goog,
        username: '',
        name: 'Admin (Google identity)',
        isAdmin: true,
        isCollector: info2.isCollector,
        tabs: info2.tabs,
        allTabs: ACM_ALL_TABS,
        adminEmail: ADMIN_EMAIL,
        via: 'google-break-glass'
      }, e);
    }
    return respond_({ ok: false, needsLogin: true }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

// authLogout — invalidate a token.
function authLogoutRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var tok = String(p._tok || '').trim();
    if (tok) _authInvalidateToken_(tok);
    return respond_({ ok: true }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

// authChangePassword — the token-authenticated user rotates their own
// password. Requires the old password to prove they own the session.
function authChangePasswordRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var tok = String(p._tok || '').trim();
    var sess = tok ? _authValidateToken_(tok) : null;
    if (!sess) return respond_({ ok: false, needsLogin: true, error: 'Session expired.' }, e);
    var oldPassword = String(p.oldPassword || '');
    var newPassword = String(p.newPassword || '');
    if (!oldPassword || !newPassword) throw new Error('Old and new passwords are required.');
    var acm = readAcm_();
    var rec = acm.byEmail[sess.email];
    if (!rec) throw new Error('Account not found.');
    var cand = _authHashPassword_(oldPassword, rec.passwordSalt);
    if (cand !== rec.passwordHash) return respond_({ ok: false, error: 'Old password is incorrect.' }, e);
    var pwErr = _authValidatePasswordRules_(newPassword);
    if (pwErr) return respond_({ ok: false, error: pwErr }, e);
    var newSalt = _authGenSalt_();
    var newHash = _authHashPassword_(newPassword, newSalt);
    var sh = acm.sheet;
    var salCol = (acm.idx['Password Salt'] || 0) + 1;
    var hshCol = (acm.idx['Password Hash'] || 0) + 1;
    if (salCol > 0) sh.getRange(rec._rowIndex, salCol).setValue(newSalt);
    if (hshCol > 0) sh.getRange(rec._rowIndex, hshCol).setValue(newHash);
    return respond_({ ok: true }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

// acmSetPassword — admin-only, sets a user's password (and optionally
// their username at the same time). Used by the User Management UI when
// the admin wants to reset a stakeholder's password without going through
// the full add/edit form.
function acmSetPasswordRoute_(e) {
  try {
    var em = getViewerEmail_(e);
    if (!isAdmin_(em)) return respond_({ ok: false, error: 'Forbidden — admin only.', viewer: em }, e);
    var p = (e && e.parameter) || {};
    var target = String(p.email || '').toLowerCase().trim();
    if (!target) throw new Error('email is required');
    var password = String(p.password || '');
    var pwErr = _authValidatePasswordRules_(password);
    if (pwErr) throw new Error(pwErr);
    var acm = readAcm_();
    var rec = acm.byEmail[target];
    if (!rec) throw new Error('Account not found.');
    var sh = acm.sheet;
    var usernameNew = String(p.username || '').trim();
    if (usernameNew) {
      if (!/^[A-Za-z0-9._-]+$/.test(usernameNew)) throw new Error('Invalid username characters.');
      if (usernameNew.length < 3 || usernameNew.length > 32) throw new Error('Username must be 3–32 chars.');
      var owner = acm.byUsername[usernameNew.toLowerCase()];
      if (owner && owner.email !== target) throw new Error('Username already in use.');
      var uCol = (acm.idx['Username'] || 0) + 1;
      if (uCol > 0) sh.getRange(rec._rowIndex, uCol).setValue(usernameNew);
    }
    var salt = _authGenSalt_();
    var hash = _authHashPassword_(password, salt);
    var salCol = (acm.idx['Password Salt'] || 0) + 1;
    var hshCol = (acm.idx['Password Hash'] || 0) + 1;
    var faCol = (acm.idx['Failed Attempts'] || 0) + 1;
    var luCol = (acm.idx['Locked Until']    || 0) + 1;
    if (salCol > 0) sh.getRange(rec._rowIndex, salCol).setValue(salt);
    if (hshCol > 0) sh.getRange(rec._rowIndex, hshCol).setValue(hash);
    // Reset lockout state whenever an admin resets a password.
    if (faCol > 0) sh.getRange(rec._rowIndex, faCol).setValue(0);
    if (luCol > 0) sh.getRange(rec._rowIndex, luCol).setValue(0);
    return respond_({ ok: true, email: target }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

// ===============================================================
// WORKLIST — collector queues, notes, daily reporting
// ===============================================================
function ensureCollectorTabs_(ss) {
  // Collector_Master
  var m = ss.getSheetByName(COLLECTOR_TAB);
  if (!m) {
    m = ss.insertSheet(COLLECTOR_TAB);
    m.getRange(1,1,1,COLLECTOR_HEADERS.length).setValues([COLLECTOR_HEADERS]);
    m.setFrozenRows(1);
    m.getRange(1,1,1,COLLECTOR_HEADERS.length).setFontWeight('bold').setBackground('#2c4a52').setFontColor('#ffffff');
    m.setColumnWidths(1, COLLECTOR_HEADERS.length, 170);
    // Seed admin as the first collector so the worklist isn't empty
    m.appendRow([ADMIN_EMAIL, 'Sainath Gosika', 'Yes', Utilities.formatDate(new Date(),'Asia/Kolkata','yyyy-MM-dd')]);
  }
  // Collector_CIDs
  var c = ss.getSheetByName(COLLECTOR_CIDS_TAB);
  if (!c) {
    c = ss.insertSheet(COLLECTOR_CIDS_TAB);
    c.getRange(1,1,1,COLLECTOR_CIDS_HEADERS.length).setValues([COLLECTOR_CIDS_HEADERS]);
    c.setFrozenRows(1);
    c.getRange(1,1,1,COLLECTOR_CIDS_HEADERS.length).setFontWeight('bold').setBackground('#2c4a52').setFontColor('#ffffff');
  }
  // Collection_Notes — auto-migrate old schemas by APPENDING any missing
  // header columns at the end. This preserves historical rows (their values
  // for the new columns will simply be blank) so legacy customer-level notes
  // keep their data while the UI treats them as archived (hidden).
  var n = ss.getSheetByName(NOTES_TAB);
  if (!n) {
    n = ss.insertSheet(NOTES_TAB);
    n.getRange(1,1,1,NOTES_HEADERS.length).setValues([NOTES_HEADERS]);
    n.setFrozenRows(1);
    n.getRange(1,1,1,NOTES_HEADERS.length).setFontWeight('bold').setBackground('#2c4a52').setFontColor('#ffffff');
    n.setColumnWidths(1, NOTES_HEADERS.length, 150);
  } else {
    var existingHeader = (n.getLastColumn() > 0)
      ? n.getRange(1, 1, 1, n.getLastColumn()).getValues()[0].map(function(h){ return String(h||'').trim(); })
      : [];
    var missing = NOTES_HEADERS.filter(function(h){ return existingHeader.indexOf(h) === -1; });
    if (missing.length) {
      var startCol = existingHeader.length + 1;
      n.getRange(1, startCol, 1, missing.length).setValues([missing]);
      n.getRange(1, startCol, 1, missing.length).setFontWeight('bold').setBackground('#2c4a52').setFontColor('#ffffff');
    }
  }
  return { master: m, cids: c, notes: n };
}

function readCollectors_() {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var tabs = ensureCollectorTabs_(ss);
  var v = tabs.master.getDataRange().getValues();
  var rows = [];
  var byEmail = {};
  if (v.length >= 2) {
    var head = v[0]; var idx = {};
    head.forEach(function(h,i){ idx[String(h).trim()] = i; });
    for (var i=1;i<v.length;i++){
      var em = String(v[i][idx['Email']] || '').toLowerCase().trim();
      if (!em) continue;
      var row = {
        email: em,
        name: String(v[i][idx['Name']] || ''),
        active: String(v[i][idx['Active']] || 'Yes').toLowerCase() === 'yes',
        addedOn: (v[i][idx['Added On']] instanceof Date)
          ? Utilities.formatDate(v[i][idx['Added On']],'Asia/Kolkata','yyyy-MM-dd')
          : String(v[i][idx['Added On']] || ''),
        _rowIndex: i+1
      };
      rows.push(row); byEmail[em] = row;
    }
  }
  return { rows: rows, byEmail: byEmail, sheet: tabs.master };
}

function readCollectorCids_() {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var tabs = ensureCollectorTabs_(ss);
  var v = tabs.cids.getDataRange().getValues();
  var byEmail = {};   // email -> [cid,...]
  var byCid = {};     // cid -> email (last writer wins)
  var rows = [];
  if (v.length >= 2) {
    var head = v[0]; var idx = {};
    head.forEach(function(h,i){ idx[String(h).trim()] = i; });
    for (var i=1;i<v.length;i++){
      var em = String(v[i][idx['Collector_Email']] || '').toLowerCase().trim();
      var cid = String(v[i][idx['CID']] || '').trim();
      if (!em || !cid) continue;
      if (!byEmail[em]) byEmail[em] = [];
      byEmail[em].push(cid);
      byCid[cid] = em;
      rows.push({ email: em, cid: cid, _rowIndex: i+1 });
    }
  }
  return { rows: rows, byEmail: byEmail, byCid: byCid, sheet: tabs.cids };
}

function readNotes_() {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var tabs = ensureCollectorTabs_(ss);
  var v = tabs.notes.getDataRange().getValues();
  var rows = [];
  if (v.length >= 2) {
    var head = v[0]; var idx = {};
    head.forEach(function(h,i){ idx[String(h).trim()] = i; });
    for (var i=1;i<v.length;i++){
      var id = String(v[i][idx['Note ID']] || '').trim();
      var cid = String(v[i][idx['CID']] || '').trim();
      if (!id || !cid) continue;
      var ts = v[i][idx['Timestamp']];
      var fu = v[i][idx['Follow-up Date']];
      var p2pd = v[i][idx['P2P Date']];
      var p2pa = Number(v[i][idx['P2P Amount']] || 0);
      // Invoice_No / Invoice_Type may be missing on legacy sheets — default ''
      var invNoIdx = idx['Invoice_No'];
      var invTypeIdx = idx['Invoice_Type'];
      var invoiceNo = (invNoIdx != null) ? String(v[i][invNoIdx] || '').trim() : '';
      var invoiceType = (invTypeIdx != null) ? String(v[i][invTypeIdx] || '').trim() : '';
      rows.push({
        id: id,
        ts: (ts instanceof Date) ? ts.toISOString() : String(ts||''),
        collector: String(v[i][idx['Collector Email']] || '').toLowerCase().trim(),
        cid: cid,
        invoiceNo: invoiceNo,
        invoiceType: invoiceType,
        customer: String(v[i][idx['Customer Name']] || ''),
        text: String(v[i][idx['Note Text']] || ''),
        followUp: (fu instanceof Date) ? Utilities.formatDate(fu,'Asia/Kolkata','yyyy-MM-dd') : String(fu||''),
        outcome: String(v[i][idx['Outcome']] || ''),
        p2pAmount: p2pa || 0,
        p2pDate: (p2pd instanceof Date) ? Utilities.formatDate(p2pd,'Asia/Kolkata','yyyy-MM-dd') : String(p2pd||''),
        _rowIndex: i+1
      });
    }
  }
  return { rows: rows, sheet: tabs.notes };
}

function isCollector_(email) {
  var em = String(email||'').toLowerCase().trim();
  if (!em) return false;
  var c = readCollectors_();
  var rec = c.byEmail[em];
  return !!(rec && rec.active);
}

function getOwnedCids_(email) {
  var em = String(email||'').toLowerCase().trim();
  if (!em) return [];
  var m = readCollectorCids_();
  // Apply canonical (last-write-wins) ownership via byCid. The byEmail map
  // can carry stale duplicate rows from earlier CSV reassigns — so using it
  // directly would make the backend disagree with the UI (which already
  // dedups via byCid). Concretely: Mayuri may appear in 325 historical rows
  // but only own 8 CIDs canonically.
  var owned = [];
  var seen = {};
  Object.keys(m.byCid).forEach(function(cid){
    if (m.byCid[cid] === em && !seen[cid]) {
      seen[cid] = true;
      owned.push(cid);
    }
  });
  return owned;
}

// ---- collectorList: admin only ----
function collectorListRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!isAdmin_(em)) return respond_({ ok: false, error: 'Forbidden — admin only. Viewer: ' + (em||'(empty)') }, e);
    var c = readCollectors_();
    var m = readCollectorCids_();
    // Add count of assigned CIDs to each collector
    var rows = c.rows.map(function(r){
      var n = (m.byEmail[r.email] || []).length;
      return { email: r.email, name: r.name, active: r.active, addedOn: r.addedOn, cidCount: n };
    });
    return respond_({ ok: true, rows: rows }, e);
  } catch (err) {
    return respond_({ ok: false, error: 'collectorList exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- collectorUpsert: admin only ----
function collectorUpsertRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!isAdmin_(em)) return respond_({ ok: false, error: 'Forbidden — admin only.' }, e);
    var p = e.parameter || {};
    var target = String(p.email || '').toLowerCase().trim();
    if (!target) throw new Error('email is required');
    var name = String(p.name || '').trim();
    var active = String(p.active || 'Yes').toLowerCase() === 'yes' ? 'Yes' : 'No';
    var c = readCollectors_();
    var existing = c.byEmail[target];
    var rowData = [target, name, active, existing ? existing.addedOn : Utilities.formatDate(new Date(),'Asia/Kolkata','yyyy-MM-dd')];
    if (existing) {
      c.sheet.getRange(existing._rowIndex, 1, 1, COLLECTOR_HEADERS.length).setValues([rowData]);
    } else {
      c.sheet.appendRow(rowData);
    }
    return respond_({ ok: true, email: target, mode: existing ? 'updated' : 'added' }, e);
  } catch (err) {
    return respond_({ ok: false, error: 'collectorUpsert exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- collectorDelete: admin only ----
function collectorDeleteRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!isAdmin_(em)) return respond_({ ok: false, error: 'Forbidden — admin only.' }, e);
    var p = e.parameter || {};
    var target = String(p.email || '').toLowerCase().trim();
    if (!target) throw new Error('email is required');
    if (target === ADMIN_EMAIL.toLowerCase()) throw new Error('The admin collector row cannot be deleted.');
    var c = readCollectors_();
    var rec = c.byEmail[target];
    if (!rec) return respond_({ ok: true, mode: 'not-found' }, e);
    c.sheet.deleteRow(rec._rowIndex);
    // Also remove their CID assignments
    var m = readCollectorCids_();
    var toDel = [];
    m.rows.forEach(function(r){ if (r.email === target) toDel.push(r._rowIndex); });
    // Delete from bottom up so indexes stay valid
    toDel.sort(function(a,b){ return b-a; }).forEach(function(rIx){ m.sheet.deleteRow(rIx); });
    return respond_({ ok: true, mode: 'deleted', email: target, cidsRemoved: toDel.length }, e);
  } catch (err) {
    return respond_({ ok: false, error: 'collectorDelete exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- collectorCidsList: admin sees all, collector sees own ----
function collectorCidsListRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!em) return respond_({ ok: false, error: 'Viewer not identified.' }, e);
    var p = e.parameter || {};
    var requested = String(p.email || '').toLowerCase().trim();
    var admin = isAdmin_(em);
    if (requested && !admin && requested !== em) {
      return respond_({ ok: false, error: 'You can only view your own assignments.' }, e);
    }
    var m = readCollectorCids_();
    if (requested) {
      return respond_({ ok: true, email: requested, cids: m.byEmail[requested] || [] }, e);
    }
    // No specific email — admin gets all, collector gets own
    if (admin) {
      return respond_({ ok: true, byEmail: m.byEmail }, e);
    }
    return respond_({ ok: true, email: em, cids: m.byEmail[em] || [] }, e);
  } catch (err) {
    return respond_({ ok: false, error: 'collectorCidsList exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- collectorCidsSet: admin only — replace the CID set for a collector ----
// We REWRITE the sheet (clearContents → setValues) rather than calling deleteRow
// per affected row. Google Sheets throws "Sorry, it is not possible to delete
// all non-frozen rows" when a deleteRow call would leave zero unfrozen rows,
// which is exactly what happens when the target collector has all the data
// rows and the admin is replacing them with a different set (e.g. unassigning
// everything, or moving CIDs from collector A → B). Rewriting the sheet
// atomically sidesteps the constraint and is fewer API calls.
function collectorCidsSetRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!isAdmin_(em)) return respond_({ ok: false, error: 'Forbidden — admin only.' }, e);
    var p = e.parameter || {};
    var target = String(p.email || '').toLowerCase().trim();
    if (!target) throw new Error('email is required');
    var cidsCsv = String(p.cids || '').trim();
    var newCids = cidsCsv ? cidsCsv.split(/[,;\s]+/).map(function(s){return s.trim();}).filter(Boolean) : [];
    // De-dup the incoming list
    var seen = {}; newCids = newCids.filter(function(c){ if(seen[c]) return false; seen[c]=true; return true; });
    var incoming = {}; newCids.forEach(function(c){ incoming[c] = true; });

    var m = readCollectorCids_();
    var sh = m.sheet;

    // ONE-CID-ONE-COLLECTOR enforcement:
    // (1) Drop every row owned by the target collector — we rewrite their set.
    // (2) ALSO drop every row where some OTHER collector currently owns one of
    //     the incoming CIDs — latest assignment wins so the CID moves to target.
    var nRows = sh.getLastRow();
    var keep = [];
    var removed = 0;
    var reassigned = {};   // otherEmail -> [cid, cid, ...]  (for response)
    if (nRows > 1) {
      var data = sh.getRange(2, 1, nRows - 1, COLLECTOR_CIDS_HEADERS.length).getValues();
      data.forEach(function(row){
        var rowEmail = String(row[0]||'').toLowerCase().trim();
        var rowCid   = String(row[1]||'').trim();
        if (rowEmail === target) { removed += 1; return; }
        if (rowCid && incoming[rowCid]) {
          if (!reassigned[rowEmail]) reassigned[rowEmail] = [];
          reassigned[rowEmail].push(rowCid);
          return; // strip from previous owner
        }
        keep.push(row);
      });
    }

    // New rows for the target collector
    var today = Utilities.formatDate(new Date(),'Asia/Kolkata','yyyy-MM-dd');
    var fresh = newCids.map(function(c){ return [target, c, today]; });
    var finalRows = keep.concat(fresh);

    // Atomic rewrite: clear data, restore header, write everything back
    sh.clearContents();
    sh.getRange(1, 1, 1, COLLECTOR_CIDS_HEADERS.length).setValues([COLLECTOR_CIDS_HEADERS]);
    sh.getRange(1, 1, 1, COLLECTOR_CIDS_HEADERS.length).setFontWeight('bold').setBackground('#2c4a52').setFontColor('#ffffff');
    if (finalRows.length) {
      sh.getRange(2, 1, finalRows.length, COLLECTOR_CIDS_HEADERS.length).setValues(finalRows);
    }
    var reassignCount = 0;
    Object.keys(reassigned).forEach(function(k){ reassignCount += reassigned[k].length; });
    return respond_({
      ok: true, email: target, count: newCids.length, removed: removed,
      reassigned: reassigned, reassignedCount: reassignCount
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: 'collectorCidsSet exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- collectorCidReassign: admin only — move a single CID to a new owner ----
// Inline-reassign UI in Manage Collectors. Atomically:
//   • Removes the CID from every existing collector row (last write wins).
//   • If `owner` is empty, leaves the CID unassigned.
//   • If `owner` is provided, appends ONE row {owner, cid, today}.
// Uses an atomic rewrite for the same reason collectorCidsSetRoute_ does:
// per-row deleteRow blows up if it would empty the sheet.
function collectorCidReassignRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!isAdmin_(em)) return respond_({ ok: false, error: 'Forbidden — admin only.' }, e);
    var p = e.parameter || {};
    var cid = String(p.cid || '').trim();
    if (!cid) throw new Error('cid is required');
    var newOwner = String(p.owner || '').toLowerCase().trim();

    var m = readCollectorCids_();
    var sh = m.sheet;
    var nRows = sh.getLastRow();
    var keep = [];
    var prevOwners = [];
    if (nRows > 1) {
      var data = sh.getRange(2, 1, nRows - 1, COLLECTOR_CIDS_HEADERS.length).getValues();
      data.forEach(function(row){
        var rowEmail = String(row[0]||'').toLowerCase().trim();
        var rowCid   = String(row[1]||'').trim();
        if (rowCid === cid) {
          if (rowEmail) prevOwners.push(rowEmail);
          return; // strip ALL existing rows for this CID
        }
        keep.push(row);
      });
    }
    if (newOwner) {
      var today = Utilities.formatDate(new Date(), 'Asia/Kolkata', 'yyyy-MM-dd');
      keep.push([newOwner, cid, today]);
    }
    sh.clearContents();
    sh.getRange(1, 1, 1, COLLECTOR_CIDS_HEADERS.length).setValues([COLLECTOR_CIDS_HEADERS]);
    sh.getRange(1, 1, 1, COLLECTOR_CIDS_HEADERS.length).setFontWeight('bold').setBackground('#2c4a52').setFontColor('#ffffff');
    if (keep.length) {
      sh.getRange(2, 1, keep.length, COLLECTOR_CIDS_HEADERS.length).setValues(keep);
    }
    return respond_({
      ok: true, cid: cid, owner: newOwner,
      previousOwners: prevOwners, previousOwnerCount: prevOwners.length
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: 'collectorCidReassign exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- notesList: admin sees all, collector sees notes for their CIDs ----
// (or for an explicitly scoped collector — mirrors worklistData so the
//  KPI panel — Follow-ups Today / Overdue / P2P This Week — stays
//  consistent with the customer list when the dropdown changes.)
function notesListRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!em) return respond_({ ok: false, error: 'Viewer not identified.' }, e);
    var admin = isAdmin_(em);
    var p = e.parameter || {};
    var cid = String(p.cid || '').trim();
    var collectorScope = String(p.scope || '').toLowerCase().trim();
    var n = readNotes_();
    var rows = n.rows;
    // Scope resolution (mirrors worklistDataRoute_):
    //   · explicit scope → that collector's CIDs
    //   · admin + no scope → all notes
    //   · non-admin + no scope → caller's own owned CIDs
    var owned = null;
    if (collectorScope) {
      owned = {};
      getOwnedCids_(collectorScope).forEach(function(c){ owned[c] = true; });
    } else if (!admin) {
      owned = {};
      getOwnedCids_(em).forEach(function(c){ owned[c] = true; });
    }
    if (owned) {
      rows = rows.filter(function(r){ return owned[r.cid]; });
    }
    if (cid) rows = rows.filter(function(r){ return r.cid === cid; });
    // Sort newest first
    rows.sort(function(a,b){ return (b.ts||'').localeCompare(a.ts||''); });
    return respond_({ ok: true, rows: rows, isAdmin: admin }, e);
  } catch (err) {
    return respond_({ ok: false, error: 'notesList exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- notesAdd: collector (must own the CID) or admin ----
function notesAddRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!em) return respond_({ ok: false, error: 'Viewer not identified.' }, e);
    var admin = isAdmin_(em);
    var p = e.parameter || {};
    var cid = String(p.cid || '').trim();
    if (!cid) throw new Error('cid is required');
    if (!admin) {
      var owned = getOwnedCids_(em);
      if (owned.indexOf(cid) === -1) {
        return respond_({ ok: false, error: 'You do not own this CID.' }, e);
      }
    }
    var customer = String(p.customer || '').trim();
    var invoiceNo = String(p.invoiceNo || '').trim();
    var invoiceType = String(p.invoiceType || '').trim();
    if (!invoiceNo) throw new Error('invoiceNo is required — notes are now stored at invoice level');
    var text = String(p.text || '').trim();
    if (!text) throw new Error('Note text is required');
    var followUp = String(p.followUp || '').trim();
    var outcome = String(p.outcome || '').trim();
    var p2pAmount = Number(p.p2pAmount || 0) || 0;
    var p2pDate = String(p.p2pDate || '').trim();
    var noteId = 'N' + new Date().getTime() + '-' + Math.random().toString(36).slice(2,6);
    var nowIso = new Date().toISOString();
    var n = readNotes_();
    // Column order MUST match NOTES_HEADERS exactly. The sheet may have been
    // migrated and have extra trailing columns from older deployments — append
    // by header position rather than positionally to avoid drift.
    var sheet = n.sheet;
    var headerRow = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0].map(function(h){ return String(h||'').trim(); });
    var rowOut = new Array(headerRow.length).fill('');
    var setByHeader = function(name, val){
      var i = headerRow.indexOf(name);
      if (i >= 0) rowOut[i] = val;
    };
    setByHeader('Note ID', noteId);
    setByHeader('Timestamp', nowIso);
    setByHeader('Collector Email', em);
    setByHeader('CID', cid);
    setByHeader('Invoice_No', invoiceNo);
    setByHeader('Invoice_Type', invoiceType);
    setByHeader('Customer Name', customer);
    setByHeader('Note Text', text);
    setByHeader('Follow-up Date', followUp);
    setByHeader('Outcome', outcome);
    setByHeader('P2P Amount', p2pAmount);
    setByHeader('P2P Date', p2pDate);
    sheet.appendRow(rowOut);
    return respond_({ ok: true, id: noteId, ts: nowIso, invoiceNo: invoiceNo }, e);
  } catch (err) {
    return respond_({ ok: false, error: 'notesAdd exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- notesAddBulk: write the SAME note text/follow-up/outcome against many
// invoices for one CID in a single request. Collector must own the CID
// (admin can write against any CID). Used by the multi-select bulk save in
// the Notes modal so a collector can mark "Dispute" against, say, all
// 19 INV rows for a customer in one click.
// Input parameters (all strings, JSONP-friendly):
//   cid            — Company ID
//   customer       — customer name (for the sheet row)
//   text           — note text (required)
//   followUp       — YYYY-MM-DD (optional)
//   outcome        — Outcome string (optional)
//   p2pAmount      — number (optional)
//   p2pDate        — YYYY-MM-DD (optional)
//   invoices       — JSON string: [{invoiceNo, invoiceType}, ...]
// Returns { ok, ts, results:[{invoiceNo, id}], count }
function notesAddBulkRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!em) return respond_({ ok: false, error: 'Viewer not identified.' }, e);
    var admin = isAdmin_(em);
    var p = e.parameter || {};
    var cid = String(p.cid || '').trim();
    if (!cid) throw new Error('cid is required');
    if (!admin) {
      var owned = getOwnedCids_(em);
      if (owned.indexOf(cid) === -1) {
        return respond_({ ok: false, error: 'You do not own this CID.' }, e);
      }
    }
    var customer = String(p.customer || '').trim();
    var text = String(p.text || '').trim();
    if (!text) throw new Error('Note text is required');
    var followUp = String(p.followUp || '').trim();
    var outcome = String(p.outcome || '').trim();
    var p2pAmount = Number(p.p2pAmount || 0) || 0;
    var p2pDate = String(p.p2pDate || '').trim();
    var invoicesRaw = String(p.invoices || '').trim();
    if (!invoicesRaw) throw new Error('invoices is required (JSON array)');
    var invoices;
    try { invoices = JSON.parse(invoicesRaw); }
    catch (jx) { throw new Error('invoices must be a JSON array of {invoiceNo,invoiceType}'); }
    if (!Array.isArray(invoices) || !invoices.length) {
      throw new Error('invoices must be a non-empty array');
    }
    // Dedupe by invoiceNo (keep first invoiceType seen)
    var seen = {};
    var clean = [];
    invoices.forEach(function(it){
      var no = String((it && it.invoiceNo) || '').trim();
      var typ = String((it && it.invoiceType) || '').trim();
      if (!no) return;
      if (seen[no]) return;
      seen[no] = true;
      clean.push({ invoiceNo: no, invoiceType: typ });
    });
    if (!clean.length) throw new Error('No valid invoiceNo values in invoices');

    var n = readNotes_();
    var sheet = n.sheet;
    var headerRow = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0].map(function(h){ return String(h||'').trim(); });
    var nowIso = new Date().toISOString();
    var baseId = 'N' + new Date().getTime();

    var results = [];
    var rowsOut = [];
    for (var i = 0; i < clean.length; i++) {
      var inv = clean[i];
      var noteId = baseId + '-' + i.toString(36) + '-' + Math.random().toString(36).slice(2,5);
      var rowOut = new Array(headerRow.length).fill('');
      var setByHeader = function(name, val){
        var idx = headerRow.indexOf(name);
        if (idx >= 0) rowOut[idx] = val;
      };
      setByHeader('Note ID', noteId);
      setByHeader('Timestamp', nowIso);
      setByHeader('Collector Email', em);
      setByHeader('CID', cid);
      setByHeader('Invoice_No', inv.invoiceNo);
      setByHeader('Invoice_Type', inv.invoiceType);
      setByHeader('Customer Name', customer);
      setByHeader('Note Text', text);
      setByHeader('Follow-up Date', followUp);
      setByHeader('Outcome', outcome);
      setByHeader('P2P Amount', p2pAmount);
      setByHeader('P2P Date', p2pDate);
      rowsOut.push(rowOut);
      results.push({ invoiceNo: inv.invoiceNo, id: noteId, invoiceType: inv.invoiceType });
    }
    // Bulk append — single setValues call beats N appendRow calls
    var startRow = sheet.getLastRow() + 1;
    sheet.getRange(startRow, 1, rowsOut.length, headerRow.length).setValues(rowsOut);
    return respond_({ ok: true, ts: nowIso, count: results.length, results: results }, e);
  } catch (err) {
    return respond_({ ok: false, error: 'notesAddBulk exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- notesDelete: admin only ----
function notesDeleteRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!isAdmin_(em)) return respond_({ ok: false, error: 'Forbidden — admin only.' }, e);
    var p = e.parameter || {};
    var id = String(p.id || '').trim();
    if (!id) throw new Error('id is required');
    var n = readNotes_();
    var hit = null;
    n.rows.forEach(function(r){ if (r.id === id) hit = r; });
    if (!hit) return respond_({ ok: true, mode: 'not-found' }, e);
    n.sheet.deleteRow(hit._rowIndex);
    return respond_({ ok: true, mode: 'deleted', id: id }, e);
  } catch (err) {
    return respond_({ ok: false, error: 'notesDelete exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- worklistData: per-customer summary for the calling collector (or admin sees all) ----
// Aggregates AR_Data + Collection_Notes so the dashboard can render the queue without
// downloading the full AR feed twice.
function worklistDataRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!em) return respond_({ ok: false, error: 'Viewer not identified.' }, e);
    var admin = isAdmin_(em);
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var allTabs = ss.getSheets().map(function(s){ return s.getName(); });
    var arName = resolveTab_(allTabs, TAB_AR_CANDIDATES);
    var ar = arName ? readTab_(ss, arName) : { rows: [] };
    var arRows = ar.rows.filter(function(r){ return !rowHasError_(r); });

    var ownedSet = {};
    var p = e.parameter || {};
    var collectorScope = String(p.scope || '').toLowerCase().trim(); // '' = no explicit scope
    // Scope resolution (revised — the collector-scope dropdown is now
    // universally visible in the UI, so it must work for every viewer):
    //   · ANY viewer + scope explicitly set in the request → that scope's CIDs.
    //     This lets a non-admin collaborator who picks "Naveen Soni (40)"
    //     see Naveen's 40 customers, instead of silently falling through to
    //     their own assigned list (which was the bug).
    //   · admin + no scope → see all CIDs.
    //   · non-admin + no scope → fall back to their own owned CIDs.
    if (collectorScope) {
      getOwnedCids_(collectorScope).forEach(function(c){ ownedSet[c] = true; });
    } else if (!admin) {
      getOwnedCids_(em).forEach(function(c){ ownedSet[c] = true; });
    } // admin + no scope: leave ownedSet empty → admin-sees-all branch below

    // Aggregate by CID — outstanding sum + customer/BU + open invoice list
    // For invoice-level notes we need per-invoice ageing so the customer row
    // can pick the "earliest follow-up" invoice and we can derive
    // status (Dispute / P2P / Open) per invoice.
    var byCid = {};
    // Unified scope gate (mirrors the resolution above):
    //   · ownedSet populated → restrict to those CIDs (any viewer + scope set,
    //     OR non-admin viewer with no scope)
    //   · ownedSet empty → admin-sees-all branch (admin + no scope only)
    var hasOwnedFilter = false;
    for (var _k in ownedSet) { hasOwnedFilter = true; break; }
    arRows.forEach(function(r){
      var cid = String(r['Company ID'] || '').trim();
      if (!cid) return;
      if (hasOwnedFilter && !ownedSet[cid]) return;
      var status = String(r['STATUS']||'').toLowerCase();
      if (status === 'closed') return;  // open only
      var os = Number(r['Outstanding_Amount']||0);
      var days = Number(r['Days']||0);
      var invNo = String(r['Invoice_No']||'').trim();
      var invType = String(r['Invoice_Type']||'').trim();
      if (!byCid[cid]) byCid[cid] = {
        cid: cid, customer: String(r['Seller_Name']||''), bu: String(r['Business']||''),
        openOs: 0, openInvCount: 0, maxDays: 0,
        invoiceKeys: {}  // invNo -> { days, openOs, invType }
      };
      byCid[cid].openOs += os;
      byCid[cid].openInvCount += 1;
      if (days > byCid[cid].maxDays) byCid[cid].maxDays = days;
      if (invNo) {
        // Aggregate by invoice number in case the source has multiple lines
        var k = byCid[cid].invoiceKeys[invNo];
        if (!k) k = byCid[cid].invoiceKeys[invNo] = { invType: invType, days: days, openOs: 0 };
        k.openOs += os;
        if (days > k.days) k.days = days;
      }
    });

    // Bring in notes; filter out legacy customer-level notes (no invoice_no)
    var allNotes = readNotes_().rows;
    var notes = allNotes.filter(function(n){ return n.invoiceNo; });
    // Index by cid then by invoiceNo. Each invoice → newest-first notes.
    var notesByCidInv = {};
    notes.forEach(function(n){
      if (!notesByCidInv[n.cid]) notesByCidInv[n.cid] = {};
      var bucket = notesByCidInv[n.cid];
      if (!bucket[n.invoiceNo]) bucket[n.invoiceNo] = [];
      bucket[n.invoiceNo].push(n);
    });

    var todayStr = Utilities.formatDate(new Date(), 'Asia/Kolkata', 'yyyy-MM-dd');
    var rows = [];
    Object.keys(byCid).forEach(function(cid){
      var c = byCid[cid];
      if (c.openOs <= 0 && c.openInvCount === 0) return;
      // For each open invoice on this customer, find the most recent note's
      // follow-up date (if any). The customer's "earliest follow-up" is the
      // minimum of those — that drives status filter bucketing on the client.
      var invNos = Object.keys(c.invoiceKeys);
      var earliestFu = '';        // YYYY-MM-DD or '' if none
      var leadInvoice = '';
      var leadOutcome = '';
      var invoicesWithFu = 0;
      var totalNotes = 0;
      invNos.forEach(function(invNo){
        var ns = (notesByCidInv[cid] || {})[invNo] || [];
        totalNotes += ns.length;
        if (!ns.length) return;
        ns.sort(function(a,b){ return (b.ts||'').localeCompare(a.ts||''); });
        var latestWithFu = null;
        for (var i=0;i<ns.length;i++){ if (ns[i].followUp) { latestWithFu = ns[i]; break; } }
        if (!latestWithFu) return;
        invoicesWithFu += 1;
        if (!earliestFu || latestWithFu.followUp < earliestFu) {
          earliestFu = latestWithFu.followUp;
          leadInvoice = invNo;
          leadOutcome = latestWithFu.outcome || '';
        }
      });
      // If no invoice has a follow-up yet, fall back to most recent note's outcome
      var anyNotes = notesByCidInv[cid] || {};
      if (!leadOutcome) {
        var flat = [];
        Object.keys(anyNotes).forEach(function(k){ anyNotes[k].forEach(function(n){ flat.push(n); }); });
        flat.sort(function(a,b){ return (b.ts||'').localeCompare(a.ts||''); });
        if (flat[0]) leadOutcome = flat[0].outcome || '';
      }
      rows.push({
        cid: cid,
        customer: c.customer,
        bu: c.bu,
        openOs: c.openOs,
        openInvCount: c.openInvCount,
        maxDays: c.maxDays,
        notesCount: totalNotes,
        invoicesWithFu: invoicesWithFu,
        nextFollowUp: earliestFu,       // earliest across invoices
        leadInvoice: leadInvoice,        // which invoice drives the FU
        lastOutcome: leadOutcome
      });
    });
    rows.sort(function(a,b){ return (b.maxDays||0) - (a.maxDays||0); });
    return respond_({ ok: true, rows: rows, isAdmin: admin, today: todayStr, scope: (admin ? collectorScope : em) }, e);
  } catch (err) {
    return respond_({ ok: false, error: 'worklistData exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- customerInvoices: on-demand per-customer detail for the Notes modal ----
// Returns every OPEN invoice for a CID with its type, ageing, outstanding,
// and all invoice-level notes (legacy customer-level notes are excluded —
// they remain on the sheet but are hidden from the UI per user choice).
function customerInvoicesRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!em) return respond_({ ok: false, error: 'Viewer not identified.' }, e);
    var admin = isAdmin_(em);
    var p = e.parameter || {};
    var cid = String(p.cid || '').trim();
    if (!cid) throw new Error('cid is required');
    if (!admin) {
      var owned = getOwnedCids_(em);
      if (owned.indexOf(cid) === -1) {
        return respond_({ ok: false, error: 'You do not own this CID.' }, e);
      }
    }
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var allTabs = ss.getSheets().map(function(s){ return s.getName(); });
    var arName = resolveTab_(allTabs, TAB_AR_CANDIDATES);
    var ar = arName ? readTab_(ss, arName) : { rows: [] };
    var arRows = ar.rows.filter(function(r){ return !rowHasError_(r); });

    // Aggregate by invoiceNo for this CID
    var invMap = {};       // invNo -> { invoiceNo, invoiceType, dueDate, invoiceDate, openAmount, days, customer }
    arRows.forEach(function(r){
      if (String(r['Company ID']||'').trim() !== cid) return;
      var status = String(r['STATUS']||'').toLowerCase();
      if (status === 'closed') return;
      var invNo = String(r['Invoice_No']||'').trim();
      if (!invNo) return;
      var os = Number(r['Outstanding_Amount']||0);
      var days = Number(r['Days']||0);
      var entry = invMap[invNo];
      if (!entry) entry = invMap[invNo] = {
        invoiceNo: invNo,
        invoiceType: String(r['Invoice_Type']||''),
        invoiceDate: String(r['Invoice_Date']||''),
        dueDate: String(r['Due_Date']||''),
        days: days,
        openAmount: 0,
        customer: String(r['Seller_Name']||''),
        bu: String(r['Business']||'')
      };
      entry.openAmount += os;
      if (days > entry.days) entry.days = days;
    });

    // Attach notes (invoice-level only)
    var allNotes = readNotes_().rows;
    var notesByInv = {};
    allNotes.forEach(function(n){
      if (n.cid !== cid) return;
      if (!n.invoiceNo) return;  // hide legacy customer-level notes
      if (!notesByInv[n.invoiceNo]) notesByInv[n.invoiceNo] = [];
      notesByInv[n.invoiceNo].push(n);
    });
    Object.keys(notesByInv).forEach(function(k){
      notesByInv[k].sort(function(a,b){ return (b.ts||'').localeCompare(a.ts||''); });
    });

    // Group invoices by type for the master/detail UX, sort by days desc
    var invList = Object.keys(invMap).map(function(k){
      var inv = invMap[k];
      var notes = notesByInv[inv.invoiceNo] || [];
      var nextFu = '';
      var lastOutcome = '';
      for (var i=0;i<notes.length;i++){ if (notes[i].followUp) { nextFu = notes[i].followUp; lastOutcome = notes[i].outcome; break; } }
      if (!lastOutcome && notes[0]) lastOutcome = notes[0].outcome || '';
      inv.notes = notes;
      inv.nextFollowUp = nextFu;
      inv.lastOutcome = lastOutcome;
      return inv;
    });
    invList.sort(function(a,b){ return (b.days||0) - (a.days||0); });

    // Group by Invoice_Type for the UI (INV / CN / Receipt / Advance Receipt / Other)
    var byType = {};
    invList.forEach(function(inv){
      var t = inv.invoiceType || 'Other';
      if (!byType[t]) byType[t] = [];
      byType[t].push(inv);
    });
    var groups = Object.keys(byType).sort().map(function(t){
      var items = byType[t];
      var subOpen = items.reduce(function(s,i){ return s + (i.openAmount||0); }, 0);
      return { type: t, count: items.length, openAmount: subOpen, invoices: items };
    });
    var customer = invList[0] ? invList[0].customer : '';
    var totalOpen = invList.reduce(function(s,i){ return s + (i.openAmount||0); }, 0);
    return respond_({
      ok: true,
      cid: cid,
      customer: customer,
      totalOpen: totalOpen,
      invoiceCount: invList.length,
      groups: groups,
      today: Utilities.formatDate(new Date(),'Asia/Kolkata','yyyy-MM-dd'),
      isAdmin: admin
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: 'customerInvoices exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- dailyReport: collector-wise summary for today ----
function dailyReportRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!em) return respond_({ ok: false, error: 'Viewer not identified.' }, e);
    var admin = isAdmin_(em);
    var p = (e && e.parameter) || {};
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var collectors = readCollectors_().rows;
    var cidsMap = readCollectorCids_().byEmail;
    var notes = readNotes_().rows;

    var tz = 'Asia/Kolkata';
    var todayStr    = Utilities.formatDate(new Date(),                       tz, 'yyyy-MM-dd');
    var tomorrowStr = Utilities.formatDate(new Date(Date.now()+86400000),    tz, 'yyyy-MM-dd');
    var weekEnd     = Utilities.formatDate(new Date(Date.now()+7*86400000),  tz, 'yyyy-MM-dd');
    var sevenAgo    = Utilities.formatDate(new Date(Date.now()-7*86400000),  tz, 'yyyy-MM-dd');

    // Range resolution: 'today' | '7d' | 'month' | 'all' | 'custom'
    // 'today'  → just today
    // '7d'     → last 7 days inclusive (today-6 .. today)
    // 'month'  → MTD (first of month .. today)
    // 'all'    → no bound
    // 'custom' → from / to supplied by client (YYYY-MM-DD)
    var range     = String(p.range||'today').toLowerCase();
    var rangeFrom = todayStr, rangeTo = todayStr, rangeLabel = 'Today';
    if (range === '7d') {
      rangeFrom  = Utilities.formatDate(new Date(Date.now()-6*86400000), tz, 'yyyy-MM-dd');
      rangeTo    = todayStr;
      rangeLabel = 'Last 7 days';
    } else if (range === 'month') {
      rangeFrom  = todayStr.slice(0,8) + '01';
      rangeTo    = todayStr;
      rangeLabel = 'Month to date';
    } else if (range === 'all') {
      rangeFrom  = '';
      rangeTo    = '';
      rangeLabel = 'All time';
    } else if (range === 'custom') {
      var f = String(p.from||'').trim().slice(0,10);
      var t = String(p.to||'').trim().slice(0,10);
      if (f) rangeFrom = f;
      if (t) rangeTo = t;
      rangeLabel = 'Custom: ' + (rangeFrom||'…') + ' to ' + (rangeTo||'…');
    }
    function inRange_(ymd){
      if (!ymd) return false;
      var d = String(ymd).slice(0,10);
      if (rangeFrom && d < rangeFrom) return false;
      if (rangeTo   && d > rangeTo)   return false;
      return true;
    }

    // Build AR outstanding by CID once
    var allTabs = ss.getSheets().map(function(s){ return s.getName(); });
    var arName = resolveTab_(allTabs, TAB_AR_CANDIDATES);
    var ar = arName ? readTab_(ss, arName) : { rows: [] };
    var arRows = ar.rows.filter(function(r){ return !rowHasError_(r); });
    var openByCid = {};        // cid -> openOs
    var openInvByCid = {};     // cid -> #open invoices
    var custByCid   = {};      // cid -> customer name (first seen)
    var osByInv     = {};      // cid + '|' + invNo -> outstanding
    arRows.forEach(function(r){
      var cid = String(r['Company ID'] || '').trim();
      if (!cid) return;
      var status = String(r['STATUS']||'').toLowerCase();
      if (status === 'closed') return;
      var os = Number(r['Outstanding_Amount']||0);
      openByCid[cid]    = (openByCid[cid]||0) + os;
      openInvByCid[cid] = (openInvByCid[cid]||0) + 1;
      var nm = String(r['Seller_Name']||r['Seller Name']||'');
      if (nm && !custByCid[cid]) custByCid[cid] = nm;
      var invNo = String(r['Invoice_No'] || '').trim();
      if (invNo) osByInv[cid + '|' + invNo] = os;
    });
    // Most recent note per CID
    var lastNoteTsByCid = {};
    notes.forEach(function(n){
      var prev = lastNoteTsByCid[n.cid] || '';
      if (n.ts > prev) lastNoteTsByCid[n.cid] = n.ts;
    });

    var per = collectors.filter(function(c){ return c.active; }).map(function(c){
      var myCids = cidsMap[c.email] || [];
      var myNotes = notes.filter(function(n){ return n.collector === c.email; });
      // Range-aware metrics
      var notesInRange = myNotes.filter(function(n){ return inRange_((n.ts||'').slice(0,10)); });
      var p2pInRange   = myNotes.filter(function(n){
        return n.outcome === 'Promised to pay' && inRange_(n.p2pDate);
      });
      var p2pAmtRange  = p2pInRange.reduce(function(s,n){ return s + (n.p2pAmount||0); }, 0);
      // Snapshot metrics (always anchored to "now")
      var dueToday    = myNotes.filter(function(n){ return n.followUp === todayStr; });
      var dueTomorrow = myNotes.filter(function(n){ return n.followUp === tomorrowStr; });
      var dueWeek     = myNotes.filter(function(n){ return n.followUp && n.followUp >= todayStr && n.followUp <= weekEnd; });
      // Untouched 7+ days: assigned CIDs with no note newer than 7 days ago
      var untouched = myCids.filter(function(cid){
        var lt = (lastNoteTsByCid[cid] || '').slice(0,10);
        if (!lt) return openByCid[cid] > 0;
        return lt < sevenAgo && openByCid[cid] > 0;
      });
      var myOpenOs = myCids.reduce(function(s,cid){ return s + (openByCid[cid]||0); }, 0);
      return {
        email: c.email,
        name: c.name,
        cidsAssigned: myCids.length,
        openOs: myOpenOs,
        notesInRange: notesInRange.length,
        notesToday: myNotes.filter(function(n){ return (n.ts||'').slice(0,10) === todayStr; }).length, // back-compat
        dueToday: dueToday.length,
        dueTomorrow: dueTomorrow.length,
        dueThisWeek: dueWeek.length,
        p2pCount: p2pInRange.length,
        p2pAmount: p2pAmtRange,
        untouched7d: untouched.length,
        dueTodayList: dueToday.map(function(n){ return { cid: n.cid, customer: n.customer, ts: n.ts, text: n.text }; })
      };
    });
    // ----- Per-customer rollup (notes activity within range, one row per touched CID) -----
    // Used in the Excel Summary sheet so the report is customer-wise, not just collector-wise.
    var perCustomer = [];
    var notesDetail = [];
    var collectorNameByEm = {};
    collectors.forEach(function(c){ collectorNameByEm[String(c.email||'').toLowerCase()] = c.name || c.email; });
    var groupedNotes = {};  // (collector|cid) -> {collector, cid, customer, notes:[...]}
    notes.forEach(function(n){
      var d = (n.ts||'').slice(0,10);
      if (!inRange_(d)) return;
      var colEm = String(n.collector||'').toLowerCase();
      var key   = colEm + '|' + n.cid;
      if (!groupedNotes[key]) {
        groupedNotes[key] = {
          collector: colEm,
          collectorName: collectorNameByEm[colEm] || colEm,
          cid: n.cid,
          customer: custByCid[n.cid] || n.customer || '',
          notes: []
        };
      }
      groupedNotes[key].notes.push(n);
      // Build notes-detail row enriched with invoice OS
      var invKey = n.cid + '|' + n.invoiceNo;
      var invOs  = (n.invoiceNo && osByInv[invKey] != null) ? osByInv[invKey] : 0;
      notesDetail.push({
        date:        d,                                 // YYYY-MM-DD, no timestamp
        ts:          n.ts || '',                        // full ISO ts so Activity Log can render the SAME timestamp the Worklist shows
        collector:   colEm,
        collectorName: collectorNameByEm[colEm] || colEm,
        cid:         n.cid,
        customer:    custByCid[n.cid] || n.customer || '',
        invoiceNo:   n.invoiceNo || '',
        invoiceOs:   invOs,
        note:        n.text,
        text:        n.text,                            // alias for parity with the Worklist Notes modal (which uses n.text)
        outcome:     n.outcome,
        followUp:    n.followUp,
        p2pAmount:   n.p2pAmount || 0,
        p2pDate:     n.p2pDate || ''
      });
    });
    Object.keys(groupedNotes).forEach(function(k){
      var g = groupedNotes[k];
      var dates = g.notes.map(function(n){ return (n.ts||'').slice(0,10); }).filter(Boolean).sort();
      var outcomes = {};
      g.notes.forEach(function(n){ if (n.outcome) outcomes[n.outcome] = (outcomes[n.outcome]||0) + 1; });
      perCustomer.push({
        collector:     g.collector,
        collectorName: g.collectorName,
        cid:           g.cid,
        customer:      g.customer,
        openOs:        openByCid[g.cid] || 0,
        openInvoices:  openInvByCid[g.cid] || 0,
        notesCount:    g.notes.length,
        firstNoteDate: dates[0] || '',
        lastNoteDate:  dates[dates.length-1] || '',
        outcomes:      outcomes
      });
    });
    // Sort: collector A→Z, then OS desc
    perCustomer.sort(function(a,b){
      var c = String(a.collectorName||'').localeCompare(String(b.collectorName||''));
      if (c) return c;
      return (b.openOs||0) - (a.openOs||0);
    });
    notesDetail.sort(function(a,b){
      var c = String(a.collectorName||'').localeCompare(String(b.collectorName||''));
      if (c) return c;
      var d = String(b.date||'').localeCompare(String(a.date||''));
      if (d) return d;
      return String(a.cid||'').localeCompare(String(b.cid||''));
    });

    // ----- Access scoping -----
    // Admin sees everything; a collector sees ONLY their own rows everywhere.
    if (!admin) {
      per         = per.filter(function(r){ return r.email === em; });
      perCustomer = perCustomer.filter(function(r){ return r.collector === em; });
      notesDetail = notesDetail.filter(function(r){ return r.collector === em; });
    }

    return respond_({
      ok: true,
      today: todayStr,
      range: range,
      rangeFrom: rangeFrom,
      rangeTo: rangeTo,
      rangeLabel: rangeLabel,
      perCollector: per,
      perCustomer:  perCustomer,
      notesDetail:  notesDetail,
      viewerEmail:  em,
      isAdmin:      admin
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: 'dailyReport exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- cidUniverse: admin-only, returns every CID in AR with customer + BU + open OS.
// Used by the Manage Collectors → Assign CIDs picker so the customer list works
// even when the viewer hasn't loaded the Overview tab yet.
function cidUniverseRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!isAdmin_(em)) {
      return respond_({ ok:false, error:'Admin only', email:em }, e);
    }
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var allTabs = ss.getSheets().map(function(s){ return s.getName(); });
    var arName = resolveTab_(allTabs, TAB_AR_CANDIDATES);
    if (!arName) return respond_({ ok:false, error:'AR_Data tab not found in spreadsheet' }, e);
    var ar = readTab_(ss, arName);
    var byCid = {};
    ar.rows.forEach(function(r){
      if (rowHasError_(r)) return;
      var cid = String(r['Company ID']||'').trim();
      if (!cid) return;
      if (!byCid[cid]) {
        byCid[cid] = {
          cid:      cid,
          customer: String(r['Seller_Name']||r['Seller Name']||''),
          bu:       String(r['Business']||''),
          openOs:   0,
          totalOs:  0,
          rows:     0
        };
      }
      var st = String(r['STATUS']||'').toLowerCase();
      var os = Number(r['Outstanding_Amount']||0) || 0;
      byCid[cid].totalOs += os;
      byCid[cid].rows    += 1;
      if (st !== 'closed') byCid[cid].openOs += os;
    });
    var rows = Object.keys(byCid).map(function(k){ return byCid[k]; });
    rows.sort(function(a,b){ return (b.openOs||0) - (a.openOs||0); });
    return respond_({ ok:true, rows: rows, count: rows.length }, e);
  } catch (err) {
    return respond_({ ok:false, error: 'cidUniverse exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- bulkAssignCids: admin-only. Accepts parsed CSV as `payload` (JSON string
// of [{email, cid}, ...]) plus `mode` ('merge'|'replace'). Groups by email,
// validates each email is in Collector_Master, and writes via the same
// Collector_CIDs sheet logic used by collectorCidsSet.
function bulkAssignCidsRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!isAdmin_(em)) {
      return respond_({ ok:false, error:'Admin only', email:em }, e);
    }
    var p = (e && e.parameter) || {};
    var mode = (p.mode === 'replace') ? 'replace' : 'merge';
    var payload;
    try { payload = JSON.parse(String(p.payload||'[]')); }
    catch (perr) { return respond_({ ok:false, error:'Invalid payload JSON: '+String(perr.message||perr) }, e); }
    if (!Array.isArray(payload) || !payload.length) {
      return respond_({ ok:false, error:'Empty bulk payload' }, e);
    }
    // Group: email (lower) -> Set(cid)
    var grouped = {};
    payload.forEach(function(r){
      var em2 = String(r && r.email||'').toLowerCase().trim();
      var cd  = String(r && r.cid||'').trim();
      if (!em2 || !cd) return;
      if (!grouped[em2]) grouped[em2] = {};
      grouped[em2][cd] = true;
    });
    var emails = Object.keys(grouped);
    if (!emails.length) return respond_({ ok:false, error:'No valid email,cid rows after parsing' }, e);

    ensureCollectorTabs_();
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var coll = readCollectors_();
    var validEmails = {};
    coll.rows.forEach(function(c){ if (c.active) validEmails[String(c.email||'').toLowerCase()] = true; });

    var report = [];
    var existing = readCollectorCids_();
    var sh = ss.getSheetByName(COLLECTOR_CIDS_TAB);

    // For each target email — compute the final set, then rewrite that
    // collector's rows in Collector_CIDs.
    var now = new Date();

    // Read current sheet once into memory, then we'll mutate by deleting +
    // appending rows in a single write per collector.
    // Also build a flat set of every CID appearing in the bulk payload so we
    // can strip those CIDs from any OTHER collector who currently owns them
    // (ONE-CID-ONE-COLLECTOR — latest assignment wins).
    var incomingAllCids = {};
    Object.keys(grouped).forEach(function(em3){
      Object.keys(grouped[em3]).forEach(function(cd){ incomingAllCids[cd] = em3; });
    });
    var reassignedBulk = {}; // otherEmail -> [cid, ...]
    var keepRows = [];   // [Collector_Email, CID, Added On]
    var nRows    = sh.getLastRow();
    if (nRows > 1) {
      var data = sh.getRange(2, 1, nRows-1, COLLECTOR_CIDS_HEADERS.length).getValues();
      data.forEach(function(row){
        var rowEmail = String(row[0]||'').toLowerCase().trim();
        var rowCid   = String(row[1]||'').trim();
        if (grouped[rowEmail]) {
          if (mode === 'replace') {
            return; // drop entirely; we'll rebuild below
          } else {
            // merge: keep, but also record in 'existing' map so we don't dupe
            keepRows.push(row);
          }
        } else if (rowCid && incomingAllCids[rowCid] && incomingAllCids[rowCid] !== rowEmail) {
          // CID is currently owned by someone else but the bulk payload reassigns
          // it to a new owner. Drop the old row.
          if (!reassignedBulk[rowEmail]) reassignedBulk[rowEmail] = [];
          reassignedBulk[rowEmail].push(rowCid);
        } else {
          keepRows.push(row);
        }
      });
    }
    // Now compute additions for each grouped email
    var additions = [];
    emails.forEach(function(em3){
      if (!validEmails[em3]) {
        report.push({ email: em3, ok: false, message: 'Not in Collector_Master (skipped)' });
        delete grouped[em3];
        return;
      }
      var have = {};
      if (mode === 'merge') {
        ((existing.byEmail[em3]||[])).forEach(function(c){ have[c]=true; });
      }
      var added = 0;
      Object.keys(grouped[em3]).forEach(function(cd){
        if (have[cd]) return;
        have[cd] = true;
        additions.push([em3, cd, now]);
        added += 1;
      });
      report.push({ email: em3, ok: true, mode: mode, finalCount: Object.keys(have).length, added: added });
    });

    // Rewrite sheet: header + keepRows + additions
    sh.clearContents();
    sh.getRange(1, 1, 1, COLLECTOR_CIDS_HEADERS.length).setValues([COLLECTOR_CIDS_HEADERS]);
    var allRows = keepRows.concat(additions);
    if (allRows.length) {
      sh.getRange(2, 1, allRows.length, COLLECTOR_CIDS_HEADERS.length).setValues(allRows);
    }
    var bulkReassignCount = 0;
    Object.keys(reassignedBulk).forEach(function(k){ bulkReassignCount += reassignedBulk[k].length; });
    return respond_({
      ok:true, mode: mode, totalParsed: payload.length,
      collectorsAffected: Object.keys(grouped).length, report: report,
      reassigned: reassignedBulk, reassignedCount: bulkReassignCount
    }, e);
  } catch (err) {
    return respond_({ ok:false, error: 'bulkAssignCids exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- collectorCidsConflictsRoute_: admin-only.
// Returns every CID that is currently owned by more than one collector — a
// state which should never exist after the latest-assignment-wins write
// logic in collectorCidsSetRoute_ / bulkAssignCidsRoute_, but might still be
// present in legacy data written before the fix.
// Response: { ok, conflicts: [{ cid, owners: [{email, addedOn}, ...] }, ...],
//             total, totalOwnerships }
function collectorCidsConflictsRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!isAdmin_(em)) {
      return respond_({ ok:false, error:'Admin only', email:em }, e);
    }
    ensureCollectorTabs_();
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sh = ss.getSheetByName(COLLECTOR_CIDS_TAB);
    if (!sh) return respond_({ ok:true, conflicts:[], total:0, totalOwnerships:0 }, e);
    var nRows = sh.getLastRow();
    if (nRows < 2) return respond_({ ok:true, conflicts:[], total:0, totalOwnerships:0 }, e);
    var data = sh.getRange(2, 1, nRows-1, COLLECTOR_CIDS_HEADERS.length).getValues();

    // Group rows by CID. Multiple rows for the same {email,cid} (stale dupes)
    // are also collapsed — we only treat a CID as "conflicting" if there are
    // 2+ DISTINCT collector emails for it.
    var byCid = {};
    var totalOwnerships = 0;
    data.forEach(function(row){
      var rowEmail = String(row[0]||'').toLowerCase().trim();
      var rowCid   = String(row[1]||'').trim();
      var addedOn  = row[2];
      if (!rowEmail || !rowCid) return;
      totalOwnerships += 1;
      if (!byCid[rowCid]) byCid[rowCid] = {};
      // keep the latest addedOn per (cid,email) pair
      var t = (addedOn instanceof Date) ? addedOn.getTime() : (addedOn ? new Date(addedOn).getTime() : 0);
      if (!byCid[rowCid][rowEmail] || byCid[rowCid][rowEmail].t < t) {
        byCid[rowCid][rowEmail] = { email: rowEmail, addedOn: addedOn, t: t };
      }
    });
    var conflicts = [];
    Object.keys(byCid).forEach(function(cid){
      var emails = Object.keys(byCid[cid]);
      if (emails.length > 1) {
        var owners = emails.map(function(em2){ return byCid[cid][em2]; });
        // sort newest first
        owners.sort(function(a,b){ return (b.t||0) - (a.t||0); });
        conflicts.push({
          cid: cid,
          owners: owners.map(function(o){
            return {
              email: o.email,
              addedOn: o.addedOn ? Utilities.formatDate(new Date(o.addedOn), Session.getScriptTimeZone()||'Asia/Kolkata', 'yyyy-MM-dd HH:mm') : ''
            };
          })
        });
      }
    });
    // sort by cid for stable display
    conflicts.sort(function(a,b){ return String(a.cid).localeCompare(String(b.cid)); });
    return respond_({
      ok:true,
      conflicts: conflicts,
      total: conflicts.length,
      totalOwnerships: totalOwnerships
    }, e);
  } catch (err) {
    return respond_({ ok:false, error: 'collectorCidsConflicts exception: ' + String(err && err.message || err) }, e);
  }
}

// ---- collectorCidsResolveConflictsRoute_: admin-only.
// For every CID with >1 distinct owner: keep the row with the LATEST Added On
// timestamp and remove the rest. Rewrites the sheet atomically.
// Response: { ok, resolved, kept:[{cid, keptEmail, addedOn}],
//             dropped:[{cid, email, addedOn}] }
function collectorCidsResolveConflictsRoute_(e) {
  try {
    var em = getActiveUserEmail_();
    if (!isAdmin_(em)) {
      return respond_({ ok:false, error:'Admin only', email:em }, e);
    }
    ensureCollectorTabs_();
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sh = ss.getSheetByName(COLLECTOR_CIDS_TAB);
    if (!sh) return respond_({ ok:true, resolved:0, kept:[], dropped:[] }, e);
    var nRows = sh.getLastRow();
    if (nRows < 2) return respond_({ ok:true, resolved:0, kept:[], dropped:[] }, e);
    var data = sh.getRange(2, 1, nRows-1, COLLECTOR_CIDS_HEADERS.length).getValues();

    // For each CID track {email -> {addedOn, t, row}}. Then for CIDs with >1
    // distinct email, keep only the latest. For CIDs with 1 email but multiple
    // duplicate rows, also collapse to one row.
    var byCid = {};
    data.forEach(function(row){
      var rowEmail = String(row[0]||'').toLowerCase().trim();
      var rowCid   = String(row[1]||'').trim();
      var addedOn  = row[2];
      if (!rowEmail || !rowCid) return;
      if (!byCid[rowCid]) byCid[rowCid] = {};
      var t = (addedOn instanceof Date) ? addedOn.getTime() : (addedOn ? new Date(addedOn).getTime() : 0);
      if (!byCid[rowCid][rowEmail] || byCid[rowCid][rowEmail].t < t) {
        byCid[rowCid][rowEmail] = { email: rowEmail, addedOn: addedOn, t: t };
      }
    });

    var keepRows = [];
    var kept    = [];
    var dropped = [];
    var resolved = 0;
    Object.keys(byCid).forEach(function(cid){
      var emails = Object.keys(byCid[cid]);
      // find newest
      var newestEmail = null, newestT = -1;
      emails.forEach(function(em2){
        if (byCid[cid][em2].t > newestT) {
          newestT = byCid[cid][em2].t;
          newestEmail = em2;
        }
      });
      var newest = byCid[cid][newestEmail];
      keepRows.push([newestEmail, cid, newest.addedOn || new Date()]);
      if (emails.length > 1) {
        resolved += 1;
        kept.push({
          cid: cid,
          keptEmail: newestEmail,
          addedOn: newest.addedOn ? Utilities.formatDate(new Date(newest.addedOn), Session.getScriptTimeZone()||'Asia/Kolkata', 'yyyy-MM-dd HH:mm') : ''
        });
        emails.forEach(function(em2){
          if (em2 !== newestEmail) {
            var d = byCid[cid][em2];
            dropped.push({
              cid: cid,
              email: em2,
              addedOn: d.addedOn ? Utilities.formatDate(new Date(d.addedOn), Session.getScriptTimeZone()||'Asia/Kolkata', 'yyyy-MM-dd HH:mm') : ''
            });
          }
        });
      }
    });

    // Atomic rewrite
    sh.clearContents();
    sh.getRange(1, 1, 1, COLLECTOR_CIDS_HEADERS.length).setValues([COLLECTOR_CIDS_HEADERS]);
    if (keepRows.length) {
      sh.getRange(2, 1, keepRows.length, COLLECTOR_CIDS_HEADERS.length).setValues(keepRows);
    }
    return respond_({
      ok:true,
      resolved: resolved,
      kept: kept,
      dropped: dropped,
      finalRows: keepRows.length
    }, e);
  } catch (err) {
    return respond_({ ok:false, error: 'collectorCidsResolveConflicts exception: ' + String(err && err.message || err) }, e);
  }
}

// Surface contact list separately (for "missing contact" warnings in dashboard)
function contactsListRoute_(e) {
  try {
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var c = readContacts_(ss);
    return respond_({ ok: true, contacts: c }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

// ===============================================================
// Customer POCs — CRUD + bulk import routes
// ===============================================================

/**
 * Return all POC rows plus a summary. Optional filter=activeOnly to hide
 * inactive rows. The frontend renders the full list and filters in-browser
 * (search / region / priority) since payload size stays small.
 */
function pocListRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var activeOnly = String(p.activeOnly || '') === '1';
    var ss = SpreadsheetApp.openById(SHEET_ID);
    ensurePOCsTab_(ss);
    var rows = readPOCs_(ss);
    if (activeOnly) rows = rows.filter(function(r){ return r.active; });
    // Also return the list of unique CIDs from AR_Data so the "Add POC"
    // dropdown shows only real customers (no typos).
    var arSh = ss.getSheetByName(resolveTab_(ss.getSheets().map(function(s){return s.getName();}), TAB_AR_CANDIDATES));
    var cidUniverse = [];
    if (arSh) {
      var arRows = readTab_(ss, arSh.getName()).rows;
      var seen = {};
      arRows.forEach(function(r){
        var cid = String(r['Company ID'] || '').trim();
        var name = String(r['Seller_Name'] || r['Seller Name'] || '').trim();
        var region = String(r['Business'] || '').trim();
        if (cid && !seen[cid]) {
          seen[cid] = true;
          cidUniverse.push({ cid: cid, name: name, region: region });
        }
      });
      cidUniverse.sort(function(a,b){ return a.cid.localeCompare(b.cid); });
    }
    return respond_({
      ok: true, rows: rows, total: rows.length,
      priorities: POC_PRIORITIES, cidUniverse: cidUniverse
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

function pocSaveRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var actor = _pocActor_(e);
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var rec = {
      cid: p.cid,
      customerName: p.customerName,
      contactName: p.contactName,
      role: p.role,
      email: p.email,
      phone: p.phone,
      priority: p.priority,
      active: String(p.active || 'Y') !== 'N',
      notes: p.notes
    };
    // Basic validation
    if (!rec.cid) throw new Error('CID is required');
    if (!rec.email) throw new Error('Email is required');
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(rec.email)) {
      throw new Error('Invalid email: ' + rec.email);
    }
    var res = upsertPOC_(ss, rec, actor);
    return respond_(res, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

function pocDeleteRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var res = deletePOC_(ss, p.cid, p.email);
    return respond_(res, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

/**
 * Bulk import from a client-supplied JSON payload. The client parses the
 * user's Excel file with ExcelJS (avoids server-side file-upload plumbing),
 * turns rows into a JSON array, and POSTs it here. We validate each row,
 * upsert on (cid, email), and return a per-row status list so the UI can
 * show a nice preview.
 *
 * dryRun=1 → validate only, don't touch the sheet. The client should
 * always call once with dryRun=1 to render the preview, then again without
 * to commit.
 */
function pocBulkImportRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var dryRun = String(p.dryRun || '') === '1';
    var actor = _pocActor_(e);
    var payload = String(p.rows || '[]');
    var rows;
    try { rows = JSON.parse(payload); } catch (_) {
      throw new Error('rows param is not valid JSON');
    }
    if (!Array.isArray(rows)) throw new Error('rows must be an array');
    var ss = SpreadsheetApp.openById(SHEET_ID);
    if (!dryRun) ensurePOCsTab_(ss);
    var report = [];
    var inserts = 0, updates = 0, errors = 0;
    // Pre-fetch existing keys for accurate insert/update preview during dryRun
    var existing = {};
    (readPOCs_(ss) || []).forEach(function(r){
      existing[r.cid + '|' + r.email.toLowerCase()] = r.rowIndex;
    });
    for (var i = 0; i < rows.length; i++) {
      var rec = rows[i] || {};
      var line = i + 2;  // Excel row number (header on row 1)
      var cid = String(rec.cid || '').trim();
      var email = String(rec.email || '').trim();
      var status = 'ok';
      var mode = '';
      var err = '';
      if (!cid) { status = 'error'; err = 'Missing CID'; }
      else if (!email) { status = 'error'; err = 'Missing Email'; }
      else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        status = 'error'; err = 'Invalid Email';
      }
      if (status === 'ok') {
        mode = existing[cid + '|' + email.toLowerCase()] ? 'update' : 'insert';
        if (!dryRun) {
          try {
            var res = upsertPOC_(ss, {
              cid: cid,
              customerName: rec.customerName,
              contactName: rec.contactName,
              role: rec.role,
              email: email,
              phone: rec.phone,
              priority: rec.priority,
              active: rec.active !== 'N' && rec.active !== false,
              notes: rec.notes
            }, actor);
            mode = res.mode;
          } catch (uerr) {
            status = 'error';
            err = String(uerr && uerr.message || uerr);
          }
        }
      }
      report.push({ line: line, cid: cid, email: email,
                    status: status, mode: mode, error: err });
      if (status === 'error') errors++;
      else if (mode === 'insert') inserts++;
      else if (mode === 'update') updates++;
    }
    return respond_({
      ok: true, dryRun: dryRun, total: rows.length,
      inserts: inserts, updates: updates, errors: errors, report: report
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

/** Return the canonical template columns for the bulk-upload Excel. */
function pocTemplateRoute_(e) {
  return respond_({ ok: true, headers: POC_HEADERS, priorities: POC_PRIORITIES }, e);
}

function _pocActor_(e) {
  try { return Session.getActiveUser().getEmail() || ''; } catch (_) { return ''; }
}

// ===============================================================
// Internal Stakeholders — CRUD + bulk import routes
// ===============================================================

/**
 * Return all Internal Stakeholder rows plus a summary. Optional
 * filter=activeOnly to hide inactive rows. The frontend renders the full
 * list and filters in-browser (search / region / priority) since payload
 * size stays small.
 */
function isListRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var activeOnly = String(p.activeOnly || '') === '1';
    var ss = SpreadsheetApp.openById(SHEET_ID);
    ensureISTab_(ss);
    var rows = readIS_(ss);
    if (activeOnly) rows = rows.filter(function(r){ return r.active; });
    // Also return the list of unique CIDs from AR_Data so the "Add
    // Stakeholder" dropdown shows only real customers (no typos).
    var arSh = ss.getSheetByName(resolveTab_(ss.getSheets().map(function(s){return s.getName();}), TAB_AR_CANDIDATES));
    var cidUniverse = [];
    if (arSh) {
      var arRows = readTab_(ss, arSh.getName()).rows;
      var seen = {};
      arRows.forEach(function(r){
        var cid = String(r['Company ID'] || '').trim();
        var name = String(r['Seller_Name'] || r['Seller Name'] || '').trim();
        var region = String(r['Business'] || '').trim();
        if (cid && !seen[cid]) {
          seen[cid] = true;
          cidUniverse.push({ cid: cid, name: name, region: region });
        }
      });
      cidUniverse.sort(function(a,b){ return a.cid.localeCompare(b.cid); });
    }
    return respond_({
      ok: true, rows: rows, total: rows.length,
      priorities: IS_PRIORITIES, cidUniverse: cidUniverse
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

function isSaveRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var actor = _pocActor_(e);
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var rec = {
      cid: p.cid,
      customerName: p.customerName,
      stakeholderName: p.stakeholderName,
      role: p.role,
      email: p.email,
      phone: p.phone,
      priority: p.priority,
      active: String(p.active || 'Y') !== 'N',
      notes: p.notes
    };
    // Basic validation
    if (!rec.cid) throw new Error('CID is required');
    if (!rec.email) throw new Error('Email is required');
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(rec.email)) {
      throw new Error('Invalid email: ' + rec.email);
    }
    var res = upsertIS_(ss, rec, actor);
    return respond_(res, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

function isDeleteRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var res = deleteIS_(ss, p.cid, p.email);
    return respond_(res, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

/**
 * Bulk import Internal Stakeholders from a client-supplied JSON payload.
 * The client parses the user's Excel file with ExcelJS (avoids
 * server-side file-upload plumbing), turns rows into a JSON array, and
 * POSTs it here. We validate each row, upsert on (cid, email), and
 * return a per-row status list so the UI can show a nice preview.
 *
 * dryRun=1 → validate only, don't touch the sheet. The client should
 * always call once with dryRun=1 to render the preview, then again
 * without to commit.
 */
function isBulkImportRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var dryRun = String(p.dryRun || '') === '1';
    var actor = _pocActor_(e);
    var payload = String(p.rows || '[]');
    var rows;
    try { rows = JSON.parse(payload); } catch (_) {
      throw new Error('rows param is not valid JSON');
    }
    if (!Array.isArray(rows)) throw new Error('rows must be an array');
    var ss = SpreadsheetApp.openById(SHEET_ID);
    if (!dryRun) ensureISTab_(ss);
    var report = [];
    var inserts = 0, updates = 0, errors = 0;
    // Pre-fetch existing keys for accurate insert/update preview during dryRun
    var existing = {};
    (readIS_(ss) || []).forEach(function(r){
      existing[r.cid + '|' + r.email.toLowerCase()] = r.rowIndex;
    });
    for (var i = 0; i < rows.length; i++) {
      var rec = rows[i] || {};
      var line = i + 2;  // Excel row number (header on row 1)
      var cid = String(rec.cid || '').trim();
      var email = String(rec.email || '').trim();
      var status = 'ok';
      var mode = '';
      var err = '';
      if (!cid) { status = 'error'; err = 'Missing CID'; }
      else if (!email) { status = 'error'; err = 'Missing Email'; }
      else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        status = 'error'; err = 'Invalid Email';
      }
      if (status === 'ok') {
        mode = existing[cid + '|' + email.toLowerCase()] ? 'update' : 'insert';
        if (!dryRun) {
          try {
            var res = upsertIS_(ss, {
              cid: cid,
              customerName: rec.customerName,
              stakeholderName: rec.stakeholderName,
              role: rec.role,
              email: email,
              phone: rec.phone,
              priority: rec.priority,
              active: rec.active !== 'N' && rec.active !== false,
              notes: rec.notes
            }, actor);
            mode = res.mode;
          } catch (uerr) {
            status = 'error';
            err = String(uerr && uerr.message || uerr);
          }
        }
      }
      report.push({ line: line, cid: cid, email: email,
                    status: status, mode: mode, error: err });
      if (status === 'error') errors++;
      else if (mode === 'insert') inserts++;
      else if (mode === 'update') updates++;
    }
    return respond_({
      ok: true, dryRun: dryRun, total: rows.length,
      inserts: inserts, updates: updates, errors: errors, report: report
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

/** Return the canonical template columns for the IS bulk-upload Excel. */
function isTemplateRoute_(e) {
  return respond_({ ok: true, headers: IS_HEADERS, priorities: IS_PRIORITIES }, e);
}

/**
 * ONE-TIME MIGRATION — read the legacy Customer_Contacts tab (columns
 * Company ID | Seller_Name | To Email | CC Emails) and materialize each
 * comma-separated email as a normalized row in Customer_POCs.
 *
 * • To Email addresses become Priority=Primary rows in Customer_POCs
 * • CC Email addresses become Priority=CC rows in Customer_POCs — EXCEPT
 *   for @gofynd.com addresses, which are routed to Internal_Stakeholders
 *   instead (Priority=CC there too), so Fynd owners are not misclassified
 *   as external customer contacts.
 * • Duplicate emails per CID are deduped (case-insensitive)
 * • Idempotent: safe to re-run — upsertPOC_ / upsertIS_ match on (cid, email)
 *
 * RUN IT: In the Apps Script editor, pick this function from the dropdown
 * and click ▶ Run. Grant permissions when prompted. Watch the Execution
 * log for the count summary.
 *
 * Can also be invoked from the UI via ?action=pocMigrateFromContacts.
 */
function migrateContactsToPOCs() {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var res = _pocMigrateFromLegacy_(ss, /*actor*/ 'migration');
  Logger.log('Migration done. Total=%s | POCs ins=%s upd=%s | IS ins=%s upd=%s | Skipped=%s Errors=%s',
    res.total, res.pocInserts, res.pocUpdates, res.isInserts, res.isUpdates, res.skipped, res.errors);
  return res;
}

/**
 * Public route so the migration can be triggered from the dashboard UI too
 * (a hidden URL: ?action=pocMigrateFromContacts). Same behaviour as the
 * menu-driven migrateContactsToPOCs() function.
 */
function pocMigrateFromContactsRoute_(e) {
  try {
    var actor = _pocActor_(e) || 'migration';
    var p = (e && e.parameter) || {};
    // ONE-TIME GUARD: once the legacy Customer_Contacts sheet has been
    // successfully imported, we lock this route so nobody re-triggers it
    // by mistake. Pass ?force=1 (only intended for the Apps Script menu
    // driver, migrateContactsToPOCs()) to override the guard.
    var force = String(p.force || '').trim() === '1' || String(p.force || '').toLowerCase() === 'true';
    var props = PropertiesService.getScriptProperties();
    var doneAt = props.getProperty('POC_LEGACY_MIGRATION_DONE_AT') || '';
    var doneBy = props.getProperty('POC_LEGACY_MIGRATION_DONE_BY') || '';
    if (doneAt && !force) {
      return respond_({
        ok: false,
        error: 'Migration already completed on ' + doneAt + (doneBy ? ' by ' + doneBy : '') + '. This is a one-time activity.',
        alreadyMigrated: true,
        completedAt: doneAt,
        completedBy: doneBy
      }, e);
    }
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var res = _pocMigrateFromLegacy_(ss, actor);
    // Persist the lock on success (any run — even a re-run via force —
    // refreshes the timestamp so we always report the latest run).
    var stamp = _pocNowIso_();
    props.setProperty('POC_LEGACY_MIGRATION_DONE_AT', stamp);
    props.setProperty('POC_LEGACY_MIGRATION_DONE_BY', actor);
    return respond_({
      ok: true,
      migrated: res,
      completedAt: stamp,
      completedBy: actor
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

/**
 * Read-only status of the one-time legacy migration lock. Lets the UI
 * decide whether the "Migrate legacy" button should be enabled or shown
 * in a disabled/complete state.
 */
function pocMigrateStatusRoute_(e) {
  try {
    var props = PropertiesService.getScriptProperties();
    var doneAt = props.getProperty('POC_LEGACY_MIGRATION_DONE_AT') || '';
    var doneBy = props.getProperty('POC_LEGACY_MIGRATION_DONE_BY') || '';
    return respond_({
      ok: true,
      done: Boolean(doneAt),
      completedAt: doneAt,
      completedBy: doneBy
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

/**
 * Worker for the migration — pure function on the sheet, returns counts.
 * Splits comma-separated To/CC email fields, dedupes per (cid, lowercased-email),
 * and upserts each into Customer_POCs.
 */
function _pocMigrateFromLegacy_(ss, actor) {
  // -------------------------------------------------------------------------
  // BATCH MIGRATION — read each destination sheet ONCE, resolve inserts vs
  // updates in memory, then write updates in-place via setValues and new
  // rows as a single appended block. This replaces the previous per-row
  // upsertPOC_/upsertIS_ loop which scanned the whole destination sheet on
  // every legacy row (O(n·m)) and blew past the 60s JSONP timeout at scale.
  // -------------------------------------------------------------------------
  var legacyName = 'Customer_Contacts';
  var sh = ss.getSheetByName(legacyName);
  if (!sh) throw new Error('Legacy tab not found: ' + legacyName);
  var pocSh = ensurePOCsTab_(ss);
  var isSh  = ensureISTab_(ss);
  var emptyCounts = {
    total: 0,
    // Aggregate insert/update tallies (both destinations combined) preserved
    // for backwards compatibility with any older consumer.
    inserts: 0, updates: 0,
    // Destination-specific breakdown so the UI can show what landed where.
    pocInserts: 0, pocUpdates: 0,
    isInserts: 0,  isUpdates: 0,
    // "alreadySynced" = row already present in destination on (cid, email);
    // insert-only sync leaves it untouched to preserve manual edits (roles,
    // phones, priorities, notes). Aggregate + per-target for UI display.
    alreadySynced: 0, pocAlreadySynced: 0, isAlreadySynced: 0,
    skipped: 0, errors: 0, details: []
  };
  var vals = sh.getDataRange().getValues();
  emptyCounts.dataRows = Math.max(0, vals.length - 1);
  emptyCounts.header   = vals.length ? vals[0].map(function(h){ return String(h == null ? '' : h); }) : [];
  if (vals.length < 2) return emptyCounts;
  var head = vals[0].map(function(h){ return String(h||'').trim().toLowerCase(); });
  // Column resolution — tolerate small header variants. Aliases listed
  // in preference order; first hit wins.
  var findCol = function(aliases){
    for (var a = 0; a < aliases.length; a++){
      var ix = head.indexOf(aliases[a]);
      if (ix !== -1) return ix;
    }
    return -1;
  };
  var iCid  = findCol(['company id', 'cid', 'company_id', 'seller cid', 'seller_id', 'customer id', 'customer_id']);
  var iName = findCol(['seller_name', 'seller name', 'customer name', 'customer', 'name']);
  var iTo   = findCol(['to email', 'to', 'to_email', 'toemail', 'primary email', 'primary_email', 'email', 'email address', 'email_address', 'customer email']);
  var iCc   = findCol(['cc emails', 'cc email', 'cc', 'cc_email', 'cc_emails', 'ccemails']);
  // Publish the resolution result back onto counts so the caller (route) can
  // surface it in the response when zero-rows-scanned looks suspicious.
  emptyCounts.headerLc = head;
  emptyCounts.columns  = { iCid: iCid, iName: iName, iTo: iTo, iCc: iCc };
  if (iCid === -1 || iTo === -1) {
    throw new Error('Required columns not found in ' + legacyName + '. Need at least "Company ID" and "To Email"; got header: ' + head.join(' | '));
  }
  // counts and emptyCounts point at the same object; the diag fields on
  // emptyCounts above are already visible on counts.
  var counts = emptyCounts;
  var splitEmails = function(s){
    // Splitters: comma, semicolon, newline. Filter blanks + strip
    // trailing punctuation the sheet often carries after paste.
    return String(s||'').split(/[,;\n]/).map(function(x){ return x.trim(); }).filter(Boolean);
  };
  var emailRx = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
  // Fynd internal domain — CC entries from this domain are Fynd owners, not
  // external customer contacts, so they land in Internal_Stakeholders.
  var isFyndInternal = function(email){
    return /@gofynd\.com$/i.test(String(email || ''));
  };

  // -------------------------------------------------------------------------
  // 1) Read POC + IS destination sheets ONCE. Build (cid|email-lc) → rowIdx
  //    lookup maps so we can decide insert-vs-update in O(1) per legacy row.
  // -------------------------------------------------------------------------
  var pocLastRow = pocSh.getLastRow();
  var pocRows = pocLastRow > 1
    ? pocSh.getRange(2, 1, pocLastRow - 1, POC_HEADERS.length).getValues()
    : [];
  var pocKeyToIdx = {};   // key → { rowIdx (0-based within pocRows), sheetRow }
  for (var pi = 0; pi < pocRows.length; pi++) {
    var pr = pocRows[pi];
    var pk = String(pr[0] || '').trim() + '|' + String(pr[4] || '').trim().toLowerCase();
    if (pk === '|') continue;
    if (pocKeyToIdx[pk] == null) pocKeyToIdx[pk] = { idx: pi, sheetRow: pi + 2 };
  }
  var isLastRow = isSh.getLastRow();
  var isRows = isLastRow > 1
    ? isSh.getRange(2, 1, isLastRow - 1, IS_HEADERS.length).getValues()
    : [];
  var isKeyToIdx = {};
  for (var ii = 0; ii < isRows.length; ii++) {
    var ir = isRows[ii];
    var ik = String(ir[0] || '').trim() + '|' + String(ir[4] || '').trim().toLowerCase();
    if (ik === '|') continue;
    if (isKeyToIdx[ik] == null) isKeyToIdx[ik] = { idx: ii, sheetRow: ii + 2 };
  }

  var now = _pocNowIso_();
  var pocInsertRows = [];    // arrays to append in a single batch
  var isInsertRows  = [];
  // Track pending updates as { sheetRow, values }. Applied via setValues.
  var pocUpdatePlan = [];
  var isUpdatePlan  = [];
  // Track keys we've queued as inserts within this run so a duplicate email
  // in a later legacy row lands as an update instead of another new row.
  var pocQueuedKeys = {};
  var isQueuedKeys  = {};

  var pocDefaults = { role: '', phone: '', notes: 'Imported from Customer_Contacts' };
  var isDefaults  = { role: '', phone: '', notes: 'Imported from Customer_Contacts' };

  var buildPOCRow = function(cid, cust, email, priority){
    return [
      cid,                                    // CID
      cust || '',                             // Customer Name
      '',                                     // Contact Name (unknown from legacy)
      pocDefaults.role,                       // Role
      email,                                  // Email (preserve original case)
      pocDefaults.phone,                      // Phone
      _pocNormalizePriority_(priority),       // Priority
      'Y',                                    // Active
      pocDefaults.notes,                      // Notes
      actor || '',                            // Updated By
      now                                     // Updated At
    ];
  };
  var buildISRow = function(cid, cust, email, priority){
    return [
      cid,                                    // CID
      cust || '',                             // Customer Name
      '',                                     // Stakeholder Name (unknown)
      isDefaults.role,                        // Role
      email,                                  // Email
      isDefaults.phone,                       // Phone
      _pocNormalizePriority_(priority),       // Priority
      'Y',                                    // Active
      isDefaults.notes,                       // Notes
      actor || '',                            // Updated By
      now                                     // Updated At
    ];
  };

  // -------------------------------------------------------------------------
  // 2) Walk legacy rows, decide per-email insert vs update via in-memory maps.
  //    NO sheet reads inside this loop.
  // -------------------------------------------------------------------------
  for (var r = 1; r < vals.length; r++) {
    var row = vals[r];
    var cid = String(row[iCid] || '').trim();
    if (!cid) continue;
    var cust = iName >= 0 ? String(row[iName] || '').trim() : '';
    var toList = splitEmails(row[iTo]);
    var ccList = iCc >= 0 ? splitEmails(row[iCc]) : [];
    var seen = {};
    // targetHint: 'poc' | 'is' | 'auto'
    //   'auto' means "route @gofynd.com to IS, everything else to POC" — the
    //   right default for CC lines. Primary (To) recipients stay in POCs
    //   because a To address is the customer counterparty by definition.
    var pushOne = function(email, priority, targetHint){
      if (!email) return;
      var key = email.toLowerCase();
      if (seen[key]) return;      // dedupe within the row
      seen[key] = true;
      counts.total++;
      if (!emailRx.test(email)) {
        counts.errors++;
        counts.details.push({ cid: cid, email: email, status: 'error', message: 'Invalid email format' });
        return;
      }
      var target = targetHint === 'is' ? 'is'
                 : targetHint === 'poc' ? 'poc'
                 : (isFyndInternal(email) ? 'is' : 'poc');
      try {
        var mapKey = cid + '|' + key;
        // ---------------------------------------------------------------
        // INSERT-ONLY semantics — if the (cid, email) pair is already in
        // the destination sheet, leave the existing row untouched. Users
        // routinely add role / phone / notes / priority to POC rows after
        // the first sync; an update-on-match would silently wipe those
        // edits. Only rows new to the destination land on the sheet.
        // ---------------------------------------------------------------
        if (target === 'is') {
          if (isKeyToIdx[mapKey] != null) {
            counts.isAlreadySynced++; counts.alreadySynced++;
            counts.details.push({ cid: cid, email: email, status: 'alreadySynced', target: target });
          } else if (isQueuedKeys[mapKey]) {
            // Already queued as insert this run — skip duplicate
            counts.skipped++;
            counts.details.push({ cid: cid, email: email, status: 'skip', target: target });
          } else {
            isInsertRows.push(buildISRow(cid, cust, email, priority));
            isQueuedKeys[mapKey] = true;
            counts.isInserts++; counts.inserts++;
            counts.details.push({ cid: cid, email: email, status: 'insert', target: target });
          }
        } else {
          if (pocKeyToIdx[mapKey] != null) {
            counts.pocAlreadySynced++; counts.alreadySynced++;
            counts.details.push({ cid: cid, email: email, status: 'alreadySynced', target: target });
          } else if (pocQueuedKeys[mapKey]) {
            counts.skipped++;
            counts.details.push({ cid: cid, email: email, status: 'skip', target: target });
          } else {
            pocInsertRows.push(buildPOCRow(cid, cust, email, priority));
            pocQueuedKeys[mapKey] = true;
            counts.pocInserts++; counts.inserts++;
            counts.details.push({ cid: cid, email: email, status: 'insert', target: target });
          }
        }
      } catch (uerr) {
        counts.errors++;
        counts.details.push({ cid: cid, email: email, status: 'error', target: target, message: String(uerr && uerr.message || uerr) });
      }
    };
    // To → Primary POC (customer counterparty, never routed to IS)
    toList.forEach(function(e){ pushOne(e, 'Primary', 'poc'); });
    // CC → route @gofynd.com to IS, everything else stays as CC POC
    ccList.forEach(function(e){ pushOne(e, 'CC', 'auto'); });
  }

  // -------------------------------------------------------------------------
  // 3) Apply the plan in bulk. Insert-only sync — no update writes. New rows
  //    land as a single appended block per sheet. The pocUpdatePlan /
  //    isUpdatePlan arrays are kept declared above so unrelated helpers can
  //    reference them without ReferenceError, but they always stay empty
  //    under insert-only semantics.
  // -------------------------------------------------------------------------
  if (pocInsertRows.length) {
    var pocInsertStart = pocSh.getLastRow() + 1;
    pocSh.getRange(pocInsertStart, 1, pocInsertRows.length, POC_HEADERS.length).setValues(pocInsertRows);
  }
  if (isInsertRows.length) {
    var isInsertStart = isSh.getLastRow() + 1;
    isSh.getRange(isInsertStart, 1, isInsertRows.length, IS_HEADERS.length).setValues(isInsertRows);
  }
  return counts;
}

/**
 * Repeatable Sync route — always re-runs the upsert from Customer_Contacts
 * (no one-time lock) AND removes duplicate rows from Customer_POCs and
 * Internal_Stakeholders. Duplicates are defined as rows sharing the same
 * (CID, lowercased-email) key; the row with the most recent "Updated At"
 * wins, ties broken by the higher sheet row (later paste wins).
 *
 * Callable at ?action=pocSyncFromContacts. Never blocks — safe to call any
 * number of times from the UI's "Sync from Customer_Contacts" button.
 */
function pocSyncFromContactsRoute_(e) {
  try {
    var actor = _pocActor_(e) || 'sync';
    var ss = SpreadsheetApp.openById(SHEET_ID);
    // Pre-flight: what does the Customer_Contacts sheet look like from the
    // backend's perspective? Captured for diagnostics — always returned so
    // a "0 rows scanned" response is self-explanatory in the UI.
    var diag = _pocContactsDiag_(ss);
    // 1) Upsert from Customer_Contacts (idempotent — matches on cid+email)
    var migrated = _pocMigrateFromLegacy_(ss, actor);
    // 2) Dedup pass over BOTH destination sheets. Runs after the upsert so
    //    freshly inserted duplicates from a re-run legacy tab are collapsed.
    var pocSh = ensurePOCsTab_(ss);
    var isSh  = ensureISTab_(ss);
    var pocDedup = _pocDedupSheet_(pocSh, POC_HEADERS.length);
    var isDedup  = _pocDedupSheet_(isSh,  IS_HEADERS.length);
    // Refresh the timestamp lock too, so pocMigrateStatus still shows a
    // "last synced at" — the UI no longer uses it as a hard lock, but any
    // API consumer reading the timestamp gets a fresh value.
    var stamp = _pocNowIso_();
    var props = PropertiesService.getScriptProperties();
    props.setProperty('POC_LEGACY_MIGRATION_DONE_AT', stamp);
    props.setProperty('POC_LEGACY_MIGRATION_DONE_BY', actor);
    return respond_({
      ok: true,
      migrated: migrated,
      dedup: { poc: pocDedup, is: isDedup },
      diag: diag,
      syncedAt: stamp,
      syncedBy: actor
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

/**
 * Diagnostic snapshot of Customer_Contacts as the backend sees it —
 * bundled into the sync response so the UI can explain a 0-rows-scanned
 * result without guessing (wrong tab, missing header, misnamed columns,
 * blank CID column, etc.). Fails soft: an inspection error is captured
 * as a diag field, never propagates up.
 */
function _pocContactsDiag_(ss) {
  var out = {
    sheetName: 'Customer_Contacts',
    sheetFound: false,
    lastRow: 0,
    lastCol: 0,
    dataRows: 0,
    header: [],
    headerLc: [],
    columns: { iCid: -1, iName: -1, iTo: -1, iCc: -1 },
    sampleRows: []
  };
  try {
    var sh = ss.getSheetByName('Customer_Contacts');
    if (!sh) return out;
    out.sheetFound = true;
    out.lastRow = sh.getLastRow();
    out.lastCol = sh.getLastColumn();
    if (out.lastRow < 1 || out.lastCol < 1) return out;
    var vals = sh.getRange(1, 1, out.lastRow, out.lastCol).getValues();
    out.header   = vals[0].map(function(h){ return String(h == null ? '' : h); });
    out.headerLc = out.header.map(function(h){ return h.trim().toLowerCase(); });
    var findCol = function(aliases){
      for (var a = 0; a < aliases.length; a++){
        var ix = out.headerLc.indexOf(aliases[a]);
        if (ix !== -1) return ix;
      }
      return -1;
    };
    out.columns.iCid  = findCol(['company id', 'cid', 'company_id', 'seller cid', 'seller_id', 'customer id', 'customer_id']);
    out.columns.iName = findCol(['seller_name', 'seller name', 'customer name', 'customer', 'name']);
    out.columns.iTo   = findCol(['to email', 'to', 'to_email', 'toemail', 'primary email', 'primary_email', 'email', 'email address', 'email_address', 'customer email']);
    out.columns.iCc   = findCol(['cc emails', 'cc email', 'cc', 'cc_email', 'cc_emails', 'ccemails']);
    out.dataRows = Math.max(0, vals.length - 1);
    // Grab up to 3 sample data rows (post-header) so we can see whether
    // the "email" column is actually populated for real data.
    var sampleLimit = Math.min(3, vals.length - 1);
    for (var s = 1; s <= sampleLimit; s++) {
      var r = vals[s];
      out.sampleRows.push(r.map(function(cell){ return String(cell == null ? '' : cell); }));
    }
    return out;
  } catch (err) {
    out.error = String(err && err.message || err);
    return out;
  }
}

/**
 * Remove duplicate rows in-place. Duplicates share the same (CID, email-lc)
 * key. When collapsing, we keep the row with the most recent "Updated At"
 * value (column index 10 in both POC_HEADERS and IS_HEADERS — CID=0, Email=4,
 * Updated At=10). If timestamps tie we keep the LAST occurrence (later row =
 * later paste). Returns { scanned, kept, removed } counts.
 */
function _pocDedupSheet_(sh, colCount) {
  var lastRow = sh.getLastRow();
  if (lastRow < 3) return { scanned: Math.max(0, lastRow - 1), kept: Math.max(0, lastRow - 1), removed: 0 };
  var vals = sh.getRange(2, 1, lastRow - 1, colCount).getValues();
  var scanned = vals.length;
  // Build best-per-key map. Track sheetRow (2-based) and updatedAt for
  // tie-breaking. A blank Updated At is treated as epoch (older than any
  // real ISO timestamp), so real data always wins over legacy blanks.
  var CID_COL = 0, EMAIL_COL = 4, UPDATED_COL = 10;
  var toEpoch = function(v){
    if (v instanceof Date && !isNaN(v.getTime())) return v.getTime();
    var s = String(v == null ? '' : v).trim();
    if (!s) return 0;
    var d = new Date(s);
    return isNaN(d.getTime()) ? 0 : d.getTime();
  };
  var best = {};      // key → { rowIdx (0-based within vals), ts }
  for (var i = 0; i < vals.length; i++) {
    var cid = String(vals[i][CID_COL] || '').trim();
    var email = String(vals[i][EMAIL_COL] || '').trim().toLowerCase();
    if (!cid || !email) continue;   // skip blank rows — they'll be preserved as-is
    var key = cid + '|' + email;
    var ts = toEpoch(vals[i][UPDATED_COL]);
    var prev = best[key];
    if (!prev || ts >= prev.ts) {
      // >= (not >) means later duplicates with equal timestamp overwrite —
      // matches "later paste wins" behaviour.
      best[key] = { rowIdx: i, ts: ts };
    }
  }
  // Decide which rows survive. Any row whose (cid,email) is non-blank AND
  // whose rowIdx is NOT the winner for its key is a duplicate; drop it.
  // Blank-key rows (missing cid or email) are always kept.
  var keepMask = new Array(vals.length);
  for (var j = 0; j < vals.length; j++) {
    var cj = String(vals[j][CID_COL] || '').trim();
    var ej = String(vals[j][EMAIL_COL] || '').trim().toLowerCase();
    if (!cj || !ej) { keepMask[j] = true; continue; }
    var k2 = cj + '|' + ej;
    keepMask[j] = (best[k2] && best[k2].rowIdx === j);
  }
  var kept = [];
  var removed = 0;
  for (var m = 0; m < vals.length; m++) {
    if (keepMask[m]) kept.push(vals[m]);
    else removed++;
  }
  if (removed === 0) return { scanned: scanned, kept: kept.length, removed: 0 };
  // Rewrite the whole data range in one shot: overwrite kept rows, then
  // clear any surplus rows below (whitespace + values) so the trailing
  // duplicates don't linger.
  if (kept.length) {
    sh.getRange(2, 1, kept.length, colCount).setValues(kept);
  }
  // Clear the tail (rows kept.length+2 .. lastRow) if we shrank.
  var tailStart = 2 + kept.length;
  var tailRows = lastRow - tailStart + 1;
  if (tailRows > 0) {
    // Prefer deleteRows over clearContent so downstream range references
    // (LastRow, filters) reflect the true size of the table.
    sh.deleteRows(tailStart, tailRows);
  }
  return { scanned: scanned, kept: kept.length, removed: removed };
}

// ===============================================================
// Workflows — scheduled follow-up rules
// ===============================================================

/** Ensure the Workflows tab exists with headers frozen. */
function ensureWorkflowsTab_(ss) {
  var sh = ss.getSheetByName(WORKFLOWS_TAB);
  if (sh) return sh;
  sh = ss.insertSheet(WORKFLOWS_TAB);
  sh.getRange(1, 1, 1, WORKFLOW_HEADERS.length).setValues([WORKFLOW_HEADERS])
    .setFontWeight('bold').setBackground('#2c4a52').setFontColor('#ffffff');
  sh.setFrozenRows(1);
  return sh;
}

function ensureWorkflowQueueTab_(ss) {
  var sh = ss.getSheetByName(WORKFLOW_QUEUE_TAB);
  if (sh) return sh;
  sh = ss.insertSheet(WORKFLOW_QUEUE_TAB);
  sh.getRange(1, 1, 1, WORKFLOW_QUEUE_HEADERS.length).setValues([WORKFLOW_QUEUE_HEADERS])
    .setFontWeight('bold').setBackground('#2c4a52').setFontColor('#ffffff');
  sh.setFrozenRows(1);
  return sh;
}

/** Read all workflow rows into typed objects. */
/**
 * Coerce a Workflows-tab date cell to the canonical `YYYY-MM-DD` shape used
 * throughout the workflow config. Accepts Date objects (Google Sheets often
 * hands us those for date-formatted cells) and any string that already looks
 * like an ISO-ish date. Blank stays blank.
 */
function _wfDateStr_(v) {
  if (v == null || v === '') return '';
  if (v instanceof Date && !isNaN(v.getTime())) {
    return Utilities.formatDate(v, WORKFLOW_TZ, 'yyyy-MM-dd');
  }
  var s = String(v).trim();
  if (!s) return '';
  // Already yyyy-mm-dd? keep it.
  if (/^\d{4}-\d{1,2}-\d{1,2}/.test(s)) return s.slice(0, 10);
  var d = new Date(s);
  if (!isNaN(d.getTime())) return Utilities.formatDate(d, WORKFLOW_TZ, 'yyyy-MM-dd');
  return s;
}

function readWorkflows_(ss) {
  var sh = ss.getSheetByName(WORKFLOWS_TAB);
  if (!sh) return [];
  var v = sh.getDataRange().getValues();
  if (v.length < 2) return [];
  var head = v[0].map(function(h){ return String(h||'').trim().toLowerCase(); });
  var ix = function(name){ return head.indexOf(name); };
  var out = [];
  for (var i = 1; i < v.length; i++) {
    var r = v[i];
    var id = String(r[ix('id')] || '').trim();
    if (!id) continue;
    // Resolve extended columns leniently — headers may be missing on legacy
    // Workflows tabs that predate the 2026-07 schema bump.
    var rawStatus = String((ix('status') > -1 ? r[ix('status')] : '') || '').trim().toLowerCase();
    var rawActive = _pocIsActive_(r[ix('active')]);
    // Status drives runtime gating; Active is retained for backwards-compat.
    // If Status is blank, fall back to Active: Y → Active, N → Paused.
    var status;
    if (rawStatus === 'active' || rawStatus === 'paused' || rawStatus === 'stopped') {
      status = rawStatus;
    } else {
      status = rawActive ? 'active' : 'paused';
    }
    out.push({
      rowIndex:    i + 1,
      id:          id,
      name:        String(r[ix('name')] || '').trim(),
      region:      String(r[ix('region')] || '').trim(),
      triggerType: String(r[ix('trigger type')] || '').trim().toLowerCase(),
      triggerValue: String(r[ix('trigger value')] || '').trim(),
      templateId:  String(r[ix('template id')] || '').trim(),
      windowDays:  String(r[ix('send window days')] || 'Mon,Tue,Wed,Thu,Fri').trim(),
      windowStart: String(r[ix('send window start')] || '10:00').trim(),
      windowEnd:   String(r[ix('send window end')] || '17:00').trim(),
      freqCapDays: Number(r[ix('frequency cap days')] || 7),
      recipient:   String(r[ix('recipient rule')] || 'primary+cc').trim().toLowerCase(),
      approveMode: String(r[ix('approve mode')] || 'auto').trim().toLowerCase(),
      active:      status === 'active',
      // Extended scheduling columns — all tolerated as blank on legacy rows.
      frequency:   String((ix('frequency') > -1 ? r[ix('frequency')] : '') || 'weekly').trim().toLowerCase(),
      startDate:   _wfDateStr_(ix('start date') > -1 ? r[ix('start date')] : ''),
      endDate:     _wfDateStr_(ix('end date') > -1 ? r[ix('end date')] : ''),
      dayOfMonth:  Number((ix('day of month') > -1 ? r[ix('day of month')] : '') || 0),
      status:      status,
      custPriorities: String((ix('custom priorities') > -1 ? r[ix('custom priorities')] : '') || '').trim(),
      intPriorities:  String((ix('internal priorities') > -1 ? r[ix('internal priorities')] : '') || '').trim(),
      customerScope:  String((ix('customer scope') > -1 ? r[ix('customer scope')] : 'all') || 'all').trim().toLowerCase(),
      cidList:        String((ix('cid list') > -1 ? r[ix('cid list')] : '') || '').trim(),
      createdBy:   String(r[ix('created by')] || '').trim(),
      createdAt:   String(r[ix('created at')] || '').trim(),
      updatedBy:   String(r[ix('updated by')] || '').trim(),
      updatedAt:   String(r[ix('updated at')] || '').trim(),
      lastRunAt:   String(r[ix('last run at')] || '').trim()
    });
  }
  return out;
}

function workflowListRoute_(e) {
  try {
    var ss = SpreadsheetApp.openById(SHEET_ID);
    ensureWorkflowsTab_(ss);
    var rows = readWorkflows_(ss);
    var regions = [];
    var arSh = ss.getSheetByName(resolveTab_(ss.getSheets().map(function(s){return s.getName();}), TAB_AR_CANDIDATES));
    if (arSh) {
      var arRows = readTab_(ss, arSh.getName()).rows;
      var seen = {};
      arRows.forEach(function(r){
        var b = String(r['Business'] || '').trim();
        // Filter out spreadsheet-error tokens ("#N/A", "#REF!", etc.) — these
        // aren't real regions, they're broken lookup formulas. They shouldn't
        // pollute the Region dropdown in the workflow editor.
        if (!b || _wfIsErrorToken_(b)) return;
        if (!seen[b]) { seen[b] = true; regions.push(b); }
      });
      regions.sort();
    }
    // Also return templates so the editor dropdown is populated in one call.
    var templates = [];
    try { templates = readEmailTemplates_(ss); } catch (_) {}
    return respond_({ ok:true, rows: rows, regions: regions, templates: templates }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

/**
 * Detect Google Sheets error tokens so we can suppress them from picklists.
 * Kept in sync with ERROR_TOKENS but tolerant of casing / stray whitespace.
 */
function _wfIsErrorToken_(s) {
  var v = String(s || '').trim().toUpperCase();
  if (!v) return false;
  if (v.charAt(0) === '#' && v.charAt(v.length - 1) !== ' ') {
    // #N/A, #REF!, #VALUE!, #NAME?, #DIV/0!, #NULL!, #ERROR!
    return true;
  }
  return false;
}

function workflowSaveRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var actor = _pocActor_(e);
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sh = ensureWorkflowsTab_(ss);
    var id = String(p.id || '').trim();
    if (!id) id = 'WF-' + new Date().getTime() + '-' + Math.floor(Math.random() * 999);
    var name = String(p.name || '').trim();
    if (!name) throw new Error('Name is required');
    var triggerType = String(p.triggerType || 'aging').trim().toLowerCase();
    var validTriggers = { aging: 1, schedule: 1, cadence: 1 };
    if (!validTriggers[triggerType]) throw new Error('Invalid trigger type: ' + triggerType);
    var triggerValue = String(p.triggerValue || '').trim();
    if (!triggerValue) throw new Error('Trigger value is required');
    var now = _pocNowIso_();
    var recipient = String(p.recipient || 'primary+cc').trim().toLowerCase();
    var approveMode = String(p.approveMode || 'auto').trim().toLowerCase();
    if (approveMode !== 'auto' && approveMode !== 'review') approveMode = 'auto';
    // `status` supersedes `active` — but we still accept and normalise
    // `active` for backwards-compat with older client builds.
    var statusRaw = String(p.status || '').trim().toLowerCase();
    var status;
    if (statusRaw === 'active' || statusRaw === 'paused' || statusRaw === 'stopped') {
      status = statusRaw;
    } else {
      status = String(p.active || 'Y') !== 'N' ? 'active' : 'paused';
    }
    var active = status === 'active';
    // Cadence + expiry inputs. Blank means "no bound" — the runtime gate
    // handles that. Day-of-month is clamped to 1..31; blank/invalid → 0.
    var frequency = String(p.frequency || 'weekly').trim().toLowerCase();
    var validFreq = { daily: 1, weekly: 1, monthly: 1, custom: 1 };
    if (!validFreq[frequency]) frequency = 'weekly';
    var startDate = _wfDateStr_(p.startDate || '');
    var endDate   = _wfDateStr_(p.endDate || '');
    var dayOfMonth = Number(p.dayOfMonth || 0);
    if (isNaN(dayOfMonth) || dayOfMonth < 0 || dayOfMonth > 31) dayOfMonth = 0;
    // Cross-field validation — a Custom range without both dates is
    // ambiguous; block it here so we don't ship a broken row.
    if (frequency === 'custom' && (!startDate || !endDate)) {
      throw new Error('Custom frequency requires both Start Date and End Date');
    }
    if (startDate && endDate && startDate > endDate) {
      throw new Error('End Date must be on or after Start Date');
    }
    if (frequency === 'monthly' && (!dayOfMonth || dayOfMonth < 1 || dayOfMonth > 31)) {
      throw new Error('Monthly frequency requires Day of Month (1..31)');
    }
    var newRow = [
      id, name,
      String(p.region || '').trim(),
      triggerType,
      triggerValue,
      String(p.templateId || '').trim(),
      String(p.windowDays || 'Mon,Tue,Wed,Thu,Fri').trim(),
      String(p.windowStart || '10:00').trim(),
      String(p.windowEnd || '17:00').trim(),
      Number(p.freqCapDays || 7),
      recipient,
      approveMode,
      active ? 'Y' : 'N',
      '', '', actor, now, '',
      // Extended columns
      frequency,
      startDate,
      endDate,
      dayOfMonth || '',
      status,
      String(p.custPriorities || '').trim(),
      String(p.intPriorities  || '').trim(),
      String(p.customerScope  || 'all').trim().toLowerCase(),
      String(p.cidList || '').trim()
    ];
    // Find existing row by ID
    var lastRow = sh.getLastRow();
    var matchRow = 0;
    if (lastRow > 1) {
      var col = sh.getRange(2, 1, lastRow - 1, 1).getValues();
      for (var i = 0; i < col.length; i++) {
        if (String(col[i][0]).trim() === id) { matchRow = i + 2; break; }
      }
    }
    if (matchRow) {
      // Preserve original createdBy/createdAt/lastRunAt on update
      var existing = sh.getRange(matchRow, 1, 1, WORKFLOW_HEADERS.length).getValues()[0];
      newRow[13] = existing[13];  // createdBy
      newRow[14] = existing[14];  // createdAt
      newRow[17] = existing[17];  // lastRunAt
      sh.getRange(matchRow, 1, 1, WORKFLOW_HEADERS.length).setValues([newRow]);
      return respond_({ ok:true, mode:'update', id:id, status:status }, e);
    } else {
      newRow[13] = actor;
      newRow[14] = now;
      sh.appendRow(newRow);
      return respond_({ ok:true, mode:'insert', id:id, status:status }, e);
    }
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

function workflowDeleteRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var id = String(p.id || '').trim();
    if (!id) throw new Error('id is required');
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sh = ss.getSheetByName(WORKFLOWS_TAB);
    if (!sh) return respond_({ ok: false, error: 'Workflows tab not found' }, e);
    var lastRow = sh.getLastRow();
    if (lastRow < 2) return respond_({ ok: false, error: 'No workflows to delete' }, e);
    var col = sh.getRange(2, 1, lastRow - 1, 1).getValues();
    for (var i = 0; i < col.length; i++) {
      if (String(col[i][0]).trim() === id) {
        sh.deleteRow(i + 2);
        return respond_({ ok: true, deleted: 1 }, e);
      }
    }
    return respond_({ ok: false, error: 'Workflow not found: ' + id }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

/**
 * Dry-run a workflow: return the list of CIDs the workflow WOULD send to
 * right now, given the current AR snapshot. Used by the "Preview eligible"
 * button in the editor.
 */
function workflowPreviewRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var wf = _wfBuildFromParams_(p);
    var eligible = evaluateWorkflow_(ss, wf, /*dryRun=*/true);
    return respond_({ ok: true, workflow: wf, eligible: eligible }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

/**
 * Test a saved workflow BY ID — this is the "dry run" cousin of wfRunNow.
 * It resolves the workflow from the sheet, evaluates eligibility, and
 * returns the full list plus recipient breakdown so the UI can render
 * "will send to N customers today" and offer an Excel export.
 *
 * Unlike wfPreview (which takes ad-hoc params from the editor), this uses
 * the persisted workflow row — the source of truth the scheduler will use
 * when it fires next.
 */
function workflowTestRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var id = String(p.id || '').trim();
    if (!id) throw new Error('id is required');
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var wf = readWorkflows_(ss).filter(function(w){ return w.id === id; })[0];
    if (!wf) throw new Error('Workflow not found: ' + id);
    var eligible = evaluateWorkflow_(ss, wf, /*dryRun=*/true);
    // Summary stats useful for the "N customers, ₹X outstanding" header
    var totalOutstanding = 0;
    var totalOpenInv = 0;
    var oldest = 0;
    for (var i = 0; i < eligible.length; i++) {
      totalOutstanding += Number(eligible[i].outstanding || 0);
      totalOpenInv     += Number(eligible[i].openInv || 0);
      if (Number(eligible[i].oldestDays || 0) > oldest) oldest = Number(eligible[i].oldestDays);
    }
    return respond_({
      ok: true,
      workflow: {
        id: wf.id, name: wf.name, region: wf.region || '',
        triggerType: wf.triggerType, triggerValue: wf.triggerValue,
        templateId: wf.templateId, frequency: wf.frequency,
        windowDays: wf.windowDays, windowStart: wf.windowStart,
        startDate: wf.startDate, endDate: wf.endDate,
        dayOfMonth: wf.dayOfMonth, status: wf.status,
        approveMode: wf.approveMode, freqCapDays: wf.freqCapDays
      },
      eligible: eligible,
      summary: {
        customers: eligible.length,
        openInv: totalOpenInv,
        outstanding: totalOutstanding,
        oldestDays: oldest
      }
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

/**
 * Run a workflow immediately (bypasses time trigger). Useful for testing
 * and for admins who want to fire a one-shot escalation on demand.
 */
function workflowRunNowRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var id = String(p.id || '').trim();
    if (!id) throw new Error('id is required');
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var wf = readWorkflows_(ss).filter(function(w){ return w.id === id; })[0];
    if (!wf) throw new Error('Workflow not found: ' + id);
    var result = runWorkflow_(ss, wf, /*force=*/String(p.force || '') === '1');
    return respond_(result, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

/** Draft-queue list (rows staged from approve-mode workflows). */
function workflowQueueListRoute_(e) {
  try {
    var ss = SpreadsheetApp.openById(SHEET_ID);
    ensureWorkflowQueueTab_(ss);
    var sh = ss.getSheetByName(WORKFLOW_QUEUE_TAB);
    var v = sh.getDataRange().getValues();
    var rows = [];
    for (var i = 1; i < v.length; i++) {
      var r = v[i];
      rows.push({
        rowIndex:    i + 1,
        enqueuedAt:  String(r[0] || ''),
        workflowId:  String(r[1] || ''),
        workflow:    String(r[2] || ''),
        cid:         String(r[3] || ''),
        customer:    String(r[4] || ''),
        region:      String(r[5] || ''),
        openInv:     Number(r[6] || 0),
        outstanding: Number(r[7] || 0),
        oldestDays:  Number(r[8] || 0),
        to:          String(r[9] || ''),
        cc:          String(r[10] || ''),
        status:      String(r[11] || 'Pending'),
        approvedBy:  String(r[12] || ''),
        sentAt:      String(r[13] || ''),
        error:       String(r[14] || '')
      });
    }
    return respond_({ ok: true, rows: rows }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

function workflowQueueApproveRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var rowIndex = Number(p.rowIndex || 0);
    if (!rowIndex) throw new Error('rowIndex is required');
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sh = ss.getSheetByName(WORKFLOW_QUEUE_TAB);
    if (!sh) throw new Error('Queue tab not found');
    var row = sh.getRange(rowIndex, 1, 1, WORKFLOW_QUEUE_HEADERS.length).getValues()[0];
    var cid = String(row[3] || '').trim();
    var wfId = String(row[1] || '').trim();
    if (!cid) throw new Error('Row has no CID');
    var wf = readWorkflows_(ss).filter(function(w){ return w.id === wfId; })[0];
    var templateId = wf ? wf.templateId : '';
    var actor = _pocActor_(e);
    var res = sendFollowUp_(cid, false, /*force=*/true, templateId, wf && wf.region ? [wf.region] : []);
    if (res.ok) {
      sh.getRange(rowIndex, 12).setValue('Sent');
      sh.getRange(rowIndex, 13).setValue(actor);
      sh.getRange(rowIndex, 14).setValue(_pocNowIso_());
    } else {
      sh.getRange(rowIndex, 12).setValue('Failed');
      sh.getRange(rowIndex, 15).setValue(String(res.error || ''));
    }
    return respond_(res, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

function workflowQueueDeleteRoute_(e) {
  try {
    var p = (e && e.parameter) || {};
    var rowIndex = Number(p.rowIndex || 0);
    if (!rowIndex) throw new Error('rowIndex is required');
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sh = ss.getSheetByName(WORKFLOW_QUEUE_TAB);
    if (!sh) throw new Error('Queue tab not found');
    sh.deleteRow(rowIndex);
    return respond_({ ok: true, deleted: 1 }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

/**
 * Build a workflow object from URL params (for the dry-run preview route
 * where the workflow isn't saved yet). Mirrors the shape returned by
 * readWorkflows_ so evaluateWorkflow_ can consume it uniformly.
 */
function _wfBuildFromParams_(p) {
  var statusRaw = String(p.status || '').trim().toLowerCase();
  var status = (statusRaw === 'active' || statusRaw === 'paused' || statusRaw === 'stopped')
    ? statusRaw
    : (String(p.active || 'Y') !== 'N' ? 'active' : 'paused');
  var frequency = String(p.frequency || 'weekly').trim().toLowerCase();
  var validFreq = { daily: 1, weekly: 1, monthly: 1, custom: 1 };
  if (!validFreq[frequency]) frequency = 'weekly';
  return {
    id:          'preview',
    name:        String(p.name || 'Preview'),
    region:      String(p.region || '').trim(),
    triggerType: String(p.triggerType || 'aging').trim().toLowerCase(),
    triggerValue: String(p.triggerValue || '30').trim(),
    templateId:  String(p.templateId || '').trim(),
    windowDays:  String(p.windowDays || 'Mon,Tue,Wed,Thu,Fri').trim(),
    windowStart: String(p.windowStart || '10:00').trim(),
    windowEnd:   String(p.windowEnd || '17:00').trim(),
    freqCapDays: Number(p.freqCapDays || 7),
    recipient:   String(p.recipient || 'primary+cc').trim().toLowerCase(),
    approveMode: String(p.approveMode || 'auto').trim().toLowerCase(),
    active:      status === 'active',
    // Extended scheduling knobs, mirrored so the preview route respects the
    // same gating the real runtime uses.
    frequency:   frequency,
    startDate:   _wfDateStr_(p.startDate || ''),
    endDate:     _wfDateStr_(p.endDate || ''),
    dayOfMonth:  Number(p.dayOfMonth || 0),
    status:      status,
    // Customer-scope guardrails — MUST be surfaced or evaluateWorkflow_
    // silently falls back to region-wide scope even when the user picked
    // allow-list/deny-list in the editor.
    customerScope: (function(){
      var s = String(p.customerScope || 'all').trim().toLowerCase();
      return (s === 'include' || s === 'exclude') ? s : 'all';
    })(),
    cidList:     String(p.cidList || '').trim()
  };
}

/**
 * Evaluate a workflow against the live AR snapshot. Returns an array of
 * eligible customer records (cid, customer, region, openInv, outstanding,
 * oldestDays, to, cc). Skips CIDs whose most-recent Email_Log entry is
 * within `freqCapDays`.
 */
function evaluateWorkflow_(ss, wf, dryRun) {
  var contacts = readContacts_(ss);
  // ── Customer-scope allow/deny list ──────────────────────────────────
  // Parse `cidList` (comma / newline / whitespace separated) into a Set.
  // Compare CIDs as trimmed strings so "7352" from the sheet matches
  // "07352" or " 7352 " the user might paste. When the scope is set to
  // "include" or "exclude" we require the list to be non-empty — an empty
  // allow-list would otherwise reject every customer, and an empty
  // deny-list would silently degrade to region-wide.
  var scopeMode = String(wf.customerScope || 'all').trim().toLowerCase();
  var cidSet = null;
  if (scopeMode === 'include' || scopeMode === 'exclude') {
    var parts = String(wf.cidList || '').split(/[\s,;]+/)
      .map(function(s){ return String(s || '').trim(); })
      .filter(Boolean)
      // Also strip leading zeros for the lookup key so "07352" == "7352".
      .map(function(s){ return s.replace(/^0+/, '') || s; });
    if (parts.length) {
      cidSet = {};
      parts.forEach(function(s){ cidSet[s] = true; });
    } else {
      // Non-empty scope + empty list = misconfiguration; fall back to
      // region-wide rather than silently sending to zero (include) or
      // everyone (exclude with no exclusions is the whole region).
      scopeMode = 'all';
    }
  }
  function _cidInScope(ci){
    if (scopeMode === 'all' || !cidSet) return true;
    var key = String(ci || '').trim().replace(/^0+/, '') || String(ci || '').trim();
    var hit = !!cidSet[key];
    return (scopeMode === 'include') ? hit : !hit;
  }
  var ar = readTab_(ss, resolveTab_(ss.getSheets().map(function(s){return s.getName();}), TAB_AR_CANDIDATES)).rows
            .filter(function(r){ return !rowHasError_(r); });
  var openInv = ar.filter(function(r){
    var status = String(r['STATUS'] || r['Status'] || '').trim().toLowerCase();
    var itype  = String(r['Invoice_Type'] || '').trim().toUpperCase();
    if (itype !== 'INV' || status !== 'open') return false;
    if (wf.region && String(r['Business'] || '').trim() !== wf.region) return false;
    // Early-filter at the invoice level so we don't waste work grouping
    // customers we're about to drop anyway.
    if (!_cidInScope(r['Company ID'])) return false;
    return true;
  });
  var byCid = {};
  openInv.forEach(function(r){
    var ci = String(r['Company ID'] || '').trim();
    if (!ci) return;
    if (!byCid[ci]) byCid[ci] = {
      cid: ci,
      customer: String(r['Seller_Name'] || r['Seller Name'] || ''),
      region:   String(r['Business'] || ''),
      openInv:  0, outstanding: 0, oldestDays: 0
    };
    var b = byCid[ci];
    b.openInv += 1;
    b.outstanding += Number(r['Outstanding_Amount'] || 0);
    var d = Number(r['Days'] || 0);
    if (d > b.oldestDays) b.oldestDays = d;
  });
  // Trigger filter
  var threshold = Number(wf.triggerValue || 0);
  var eligible = [];
  Object.keys(byCid).forEach(function(ci){
    var b = byCid[ci];
    var contact = contacts[ci];
    if (!contact || !contact.to) return;
    // Aging trigger: oldestDays must be >= threshold
    if (wf.triggerType === 'aging') {
      if (b.oldestDays < threshold) return;
    }
    // Cadence trigger: last send >= N days ago (checked via freq cap below)
    // Fixed schedule: no per-CID gate; time-of-day is enforced in runWorkflow_
    // Frequency cap
    if (wf.freqCapDays > 0) {
      var last = lastSentAt_(ss, ci);
      if (last) {
        var ageDays = (new Date().getTime() - last.getTime()) / (1000 * 60 * 60 * 24);
        if (ageDays < wf.freqCapDays) return;
      }
    }
    b.to = contact.to;
    b.cc = contact.cc || '';
    eligible.push(b);
  });
  eligible.sort(function(a, b){ return b.outstanding - a.outstanding; });
  return eligible;
}

/** Return the Date of the most recent Email_Log entry for a CID (or null). */
function lastSentAt_(ss, cid) {
  var sh = ss.getSheetByName(LOG_TAB);
  if (!sh) return null;
  var v = sh.getDataRange().getValues();
  if (v.length < 2) return null;
  var head = v[0].map(function(h){ return String(h||'').trim().toLowerCase(); });
  var iCid = head.indexOf('cid');
  var iTs  = head.indexOf('timestamp');
  var iSt  = head.indexOf('status');
  if (iCid === -1 || iTs === -1) return null;
  var latest = null;
  for (var i = v.length - 1; i >= 1; i--) {
    var row = v[i];
    if (String(row[iCid] || '').trim() !== cid) continue;
    if (iSt !== -1 && String(row[iSt] || '').trim().toLowerCase() !== 'sent') continue;
    var ts = row[iTs];
    var d = ts instanceof Date ? ts : new Date(ts);
    if (!isNaN(d.getTime())) { latest = d; break; }
  }
  return latest;
}

/**
 * Run one workflow — either sends (approve=auto) or enqueues (approve=review).
 * Called from the time trigger and from workflowRunNowRoute_.
 *
 * `force=true` skips the send-window guard so a user can fire manually
 * outside of business hours from the "Run now" button.
 */
function runWorkflow_(ss, wf, force) {
  // Status supersedes the legacy `active` flag — Paused / Stopped workflows
  // never run automatically. `force` (manual "Run now") ignores Status so
  // admins can still fire a paused rule on demand.
  var status = String(wf.status || (wf.active ? 'active' : 'paused')).toLowerCase();
  if (status !== 'active' && !force) {
    return { ok: true, cid: null, skipped: true, reason: 'status=' + status };
  }
  // Send-window gate (skip on force)
  if (!force) {
    var now = new Date();
    var todayStr = Utilities.formatDate(now, WORKFLOW_TZ, 'yyyy-MM-dd');
    // Start/End date fence — a workflow with an end date auto-stops after
    // that date, so a "1-day only" run doesn't keep firing forever if the
    // admin forgets to pause it.
    if (wf.startDate && todayStr < wf.startDate) {
      return { ok: true, skipped: true, reason: 'before start date ' + wf.startDate };
    }
    if (wf.endDate && todayStr > wf.endDate) {
      return { ok: true, skipped: true, reason: 'past end date ' + wf.endDate };
    }
    // Frequency-specific cadence gate.
    var dayName = Utilities.formatDate(now, WORKFLOW_TZ, 'EEE');  // Mon/Tue/...
    var frequency = String(wf.frequency || 'weekly').toLowerCase();
    if (frequency === 'weekly' || frequency === 'custom') {
      var days = String(wf.windowDays || '').split(',').map(function(s){ return s.trim(); }).filter(Boolean);
      if (days.length && days.indexOf(dayName) === -1) {
        return { ok: true, skipped: true, reason: 'day out of window' };
      }
    } else if (frequency === 'monthly') {
      var dom = Number(wf.dayOfMonth || 0);
      var todayDom = Number(Utilities.formatDate(now, WORKFLOW_TZ, 'd'));
      // Handle "last day" convenience: dom > days-in-month falls back to
      // month-end so Feb-30 doesn't skip February entirely.
      var monthEnd = Number(Utilities.formatDate(new Date(now.getFullYear(), now.getMonth() + 1, 0), WORKFLOW_TZ, 'd'));
      var effectiveDom = dom > monthEnd ? monthEnd : dom;
      if (!effectiveDom || todayDom !== effectiveDom) {
        return { ok: true, skipped: true, reason: 'monthly day mismatch' };
      }
    }
    // Time-of-day gate — start time only (end time was retired). Give the
    // workflow a 59-minute grace window so the hourly trigger can still
    // catch it after a small drift.
    var hh = Utilities.formatDate(now, WORKFLOW_TZ, 'HH:mm');
    var startHH = String(wf.windowStart || '10:00');
    if (hh < startHH) {
      return { ok: true, skipped: true, reason: 'before start time ' + startHH };
    }
    // Once we're past the start time we allow the run; the frequency cap
    // (`freqCapDays`) prevents duplicate sends to the same CID.
  }
  var eligible = evaluateWorkflow_(ss, wf, /*dryRun=*/false);
  var results = [];
  var sent = 0, queued = 0, failed = 0;
  for (var i = 0; i < eligible.length; i++) {
    var b = eligible[i];
    if (wf.approveMode === 'review') {
      // Stage in Workflow_Queue
      var qsh = ensureWorkflowQueueTab_(ss);
      qsh.appendRow([
        _pocNowIso_(), wf.id, wf.name, b.cid, b.customer, b.region,
        b.openInv, b.outstanding, b.oldestDays, b.to, b.cc,
        'Pending', '', '', ''
      ]);
      queued++;
      results.push({ cid: b.cid, status: 'queued' });
    } else {
      // Auto-send
      try {
        var res = sendFollowUp_(b.cid, false, /*force=*/false, wf.templateId,
                                wf.region ? [wf.region] : []);
        if (res.ok) sent++; else failed++;
        results.push({ cid: b.cid, status: res.ok ? 'sent' : 'failed', error: res.error || '' });
      } catch (uerr) {
        failed++;
        results.push({ cid: b.cid, status: 'failed', error: String(uerr && uerr.message || uerr) });
      }
      Utilities.sleep(BULK_DELAY_MS);
    }
  }
  // Stamp Last Run At on the workflow row
  var sh = ss.getSheetByName(WORKFLOWS_TAB);
  if (sh && wf.rowIndex) {
    sh.getRange(wf.rowIndex, WORKFLOW_HEADERS.indexOf('Last Run At') + 1)
      .setValue(_pocNowIso_());
  }
  return {
    ok: true, workflow: wf.id, eligibleCount: eligible.length,
    sent: sent, queued: queued, failed: failed, results: results
  };
}

/**
 * The daily time-trigger entry point. Iterates every Active workflow and
 * calls runWorkflow_. Install by opening the Apps Script editor and
 * running `installWorkflowTrigger` once.
 */
function runDailyWorkflows_() {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var wfs = readWorkflows_(ss).filter(function(w){ return w.active; });
  wfs.forEach(function(w){
    try { runWorkflow_(ss, w, /*force=*/false); }
    catch (err) { Logger.log('Workflow ' + w.id + ' failed: ' + err); }
  });
}

/** Install (or re-install) the daily trigger. Run once from the editor. */
function installWorkflowTrigger() {
  // Clear old triggers targeting runDailyWorkflows_
  ScriptApp.getProjectTriggers().forEach(function(t){
    if (t.getHandlerFunction() === 'runDailyWorkflows_') ScriptApp.deleteTrigger(t);
  });
  // Fire every hour — runWorkflow_ enforces the send-window guard so it
  // only actually sends during the configured days/hours.
  ScriptApp.newTrigger('runDailyWorkflows_')
    .timeBased().everyHours(1).create();
  Logger.log('Trigger installed: runDailyWorkflows_ every hour');
}

// ===============================================================
// 4) DIAGNOSTIC HELPERS — run from the editor → Logs
// ===============================================================
function smokeTest() {
  var out = serveData_({});
  var s = out.getContent();
  var p = JSON.parse(s);
  Logger.log('payload bytes: ' + s.length);
  Logger.log('Tabs found:    ' + (p.tabsFound||[]).join(', '));
  Logger.log('Resolved AR:   ' + p.tabsResolved.ar);
  Logger.log('Resolved PDD:  ' + p.tabsResolved.pdd);
  Logger.log('Resolved Bank: ' + p.tabsResolved.bank);
  Logger.log('Counts:        AR ' + p.counts.ar + ' · PDD ' + p.counts.pdd + ' · Bank ' + p.counts.bank);
  Logger.log('Contacts:      ' + p.counts.contacts);
}

function testDashboardLoad() {
  try {
    var html = Utilities.newBlob(
      Utilities.base64Decode(getDashboardHtmlB64_()),
      'text/html'
    ).getDataAsString('UTF-8');
    Logger.log('OK — embedded HTML decodes to ' + html.length + ' chars.');
    Logger.log('Sanity check: starts with "' + html.substring(0, 60).replace(/\s+/g, ' ') + '..."');
  } catch (err) {
    Logger.log('FAIL — ' + String(err && err.message || err));
  }
}

// Diagnostic: list GmailApp aliases so the dashboard can show whether the
// FOLLOWUP_SENDER alias is actually configured on the deploying account.
function aliasesRoute_(e) {
  try {
    var aliases = [];
    try { aliases = GmailApp.getAliases() || []; } catch (_) {}
    var active = '';
    try { active = Session.getActiveUser().getEmail() || ''; } catch (_) {}
    return respond_({
      ok: true,
      configuredSender: FOLLOWUP_SENDER,
      activeUser: active,
      aliases: aliases,
      aliasConfigured: aliases.indexOf(FOLLOWUP_SENDER) !== -1
    }, e);
  } catch (err) {
    return respond_({ ok: false, error: String(err && err.message || err) }, e);
  }
}

// Test send to a single CID without actually sending. Call from editor.
function testFollowUpDryRun() {
  var TEST_CID = '';  // <-- paste the CID you want to test, then Run
  if (!TEST_CID) { Logger.log('Set TEST_CID at top of this function.'); return; }
  var r = sendFollowUp_(TEST_CID, true, true);
  Logger.log(JSON.stringify(r, null, 2));
}

// ===============================================================
// 5) EMBEDDED DASHBOARD HTML  (base64 — generated by build_codegs.py)
// ===============================================================
function getDashboardHtmlB64_() {
  return [
  __CHUNKS__
  ].join('');
}
'''.replace('__CHUNKS__', chunk_block)

with open(OUT, 'w') as f:
    f.write(GS)

print('Wrote:', OUT)
print('Size: ', os.path.getsize(OUT), 'bytes')
print('HTML embedded:', len(html_bytes), 'bytes ->', len(b64), 'base64 chars in', len(chunks), 'chunks')
