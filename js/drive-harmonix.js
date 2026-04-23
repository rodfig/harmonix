/**
 * drive-harmonix.js
 * =================
 * Google Drive persistence for Harmonix Sandbox sessions.
 *
 * Folder: "Pairings/" in the user's Google Drive
 * Index:  indice_pairings.json  — list of { id, label, created_at, updated_at }
 * Files:  <session-id>.json     — full session object
 *
 * Pattern adapted from avaliador-vinhos/auth.js + drive.js.
 *
 * SETUP: Replace GOOGLE_API_KEY and GOOGLE_CLIENT_ID with credentials
 * from Google Cloud Console. Add your Vercel domain (and localhost) as
 * authorized JavaScript origins in the OAuth 2.0 client settings.
 *
 * Public API (called from sandbox.html):
 *   driveInit()                 — call once after DOMContentLoaded
 *   driveConnect()              — request OAuth token
 *   driveDisconnect()
 *   driveSaveSession(session)   — save/update; session must have .id
 *   driveLoadSessions()         — returns array of index entries
 *   driveLoadSession(id)        — returns full session object or null
 *   driveDeleteSession(id)
 *   driveIsConnected()          — boolean
 */

const DRIVE_API_KEY    = 'PLACEHOLDER_GOOGLE_API_KEY';
const DRIVE_CLIENT_ID  = 'PLACEHOLDER_GOOGLE_CLIENT_ID';
const DRIVE_FOLDER     = 'Pairings';
const DRIVE_INDEX_FILE = 'indice_pairings.json';
const DRIVE_DISCOVERY  = 'https://www.googleapis.com/discovery/v1/apis/drive/v3/rest';
const DRIVE_SCOPE      = 'https://www.googleapis.com/auth/drive';

// ── Internal state ────────────────────────────────────────────────────────────

let _tokenClient    = null;
let _pairingsFolder = null;
let _connected      = false;
let _apiLoaded      = false;
let _tokenExpiry    = null;
let _refreshTimer   = null;
let _refreshResolve = null;
let _refreshReject  = null;
let _refreshTimeout = null;

// Callbacks registered by sandbox.html
let _onStatusChange = null;   // (status: 'connected'|'disconnected'|'connecting'|'error', msg) => void

function _emit(status, msg) {
    if (_onStatusChange) _onStatusChange(status, msg);
}

// ── Token refresh ─────────────────────────────────────────────────────────────

function _startRefreshTimer(expiresIn) {
    if (_refreshTimer) clearInterval(_refreshTimer);
    const lifetimeMs = (expiresIn || 3600) * 1000;
    _tokenExpiry     = Date.now() + lifetimeMs;
    const refreshIn  = Math.max(lifetimeMs - 5 * 60 * 1000, 60 * 1000);
    _refreshTimer    = setInterval(async () => {
        try { await _refreshToken(); }
        catch (e) { console.warn('Harmonix Drive: proactive token refresh failed', e.message); }
    }, refreshIn);
}

function _stopRefreshTimer() {
    if (_refreshTimer) { clearInterval(_refreshTimer); _refreshTimer = null; }
    _tokenExpiry = null;
}

async function _refreshToken() {
    return new Promise((resolve, reject) => {
        _refreshResolve = resolve;
        _refreshReject  = reject;
        _refreshTimeout = setTimeout(() => {
            const r = _refreshReject;
            _refreshResolve = _refreshReject = _refreshTimeout = null;
            if (r) r(new Error('Token refresh timeout'));
        }, 10000);
        _tokenClient.requestAccessToken({ prompt: '' });
    });
}

async function _ensureToken() {
    if (!gapi.client.getToken())
        throw new Error('Sem token de autenticação');
    const buffer = 5 * 60 * 1000;
    if (_tokenExpiry && Date.now() >= (_tokenExpiry - buffer)) {
        await _refreshToken();
    }
}

// ── Initialization ────────────────────────────────────────────────────────────

async function driveInit(onStatusChange) {
    _onStatusChange = onStatusChange || null;

    try {
        await new Promise((res, rej) => gapi.load('client', { callback: res, onerror: rej }));
        await gapi.client.init({ apiKey: DRIVE_API_KEY, discoveryDocs: [DRIVE_DISCOVERY] });

        _tokenClient = google.accounts.oauth2.initTokenClient({
            client_id: DRIVE_CLIENT_ID,
            scope:     DRIVE_SCOPE,
            callback:  _handleTokenResponse,
        });

        _apiLoaded = true;
        _emit('disconnected', '');

        // Auto-restore from localStorage
        _tryRestoreToken();

    } catch (err) {
        console.error('Harmonix Drive: init failed', err);
        _emit('error', 'Erro ao carregar Google API');
    }
}

function _handleTokenResponse(resp) {
    if (resp.error) {
        const r = _refreshReject;
        _refreshResolve = _refreshReject = null;
        if (_refreshTimeout) { clearTimeout(_refreshTimeout); _refreshTimeout = null; }
        if (r) r(new Error('Token error: ' + resp.error));
        else   _emit('error', 'Erro de autenticação Google');
        return;
    }

    // Persist token
    try {
        localStorage.setItem('harmonix_drive_token', JSON.stringify({
            access_token: resp.access_token,
            expires_at:   Date.now() + resp.expires_in * 1000,
        }));
    } catch (_) {}

    if (_refreshTimeout) { clearTimeout(_refreshTimeout); _refreshTimeout = null; }

    if (_refreshResolve) {
        // Background refresh path
        const r = _refreshResolve;
        _refreshResolve = _refreshReject = null;
        _startRefreshTimer(resp.expires_in);
        r(true);
    } else {
        // Initial login path
        _connected = true;
        _startRefreshTimer(resp.expires_in);
        _emit('connected', 'Ligado ao Google Drive');
    }
}

function _tryRestoreToken() {
    try {
        const raw = localStorage.getItem('harmonix_drive_token');
        if (!raw) return;
        const td = JSON.parse(raw);
        if (!td.expires_at || td.expires_at <= Date.now()) {
            localStorage.removeItem('harmonix_drive_token');
            return;
        }
        gapi.client.setToken({ access_token: td.access_token });
        _connected = true;
        _startRefreshTimer(Math.floor((td.expires_at - Date.now()) / 1000));
        _emit('connected', 'Sessão restaurada');
    } catch (_) {}
}

// ── Connect / disconnect ──────────────────────────────────────────────────────

function driveConnect() {
    if (!_apiLoaded) { _emit('error', 'API não carregada'); return; }

    // Already have a valid token
    if (_connected && gapi.client.getToken()) {
        _emit('connected', 'Já ligado');
        return;
    }

    _emit('connecting', 'A aguardar autenticação…');
    _tokenClient.requestAccessToken();
}

function driveDisconnect() {
    gapi.client.setToken(null);
    try { localStorage.removeItem('harmonix_drive_token'); } catch (_) {}
    _stopRefreshTimer();
    if (_refreshTimeout) { clearTimeout(_refreshTimeout); _refreshTimeout = null; }
    if (_refreshReject) {
        const r = _refreshReject;
        _refreshResolve = _refreshReject = null;
        r(new Error('Desconectado pelo utilizador'));
    }
    _connected = false;
    _pairingsFolder = null;
    _emit('disconnected', 'Desligado do Google Drive');
}

function driveIsConnected() { return _connected && !!gapi.client.getToken(); }

// ── Folder ────────────────────────────────────────────────────────────────────

async function _ensureFolder() {
    if (_pairingsFolder) return _pairingsFolder;
    await _ensureToken();

    const resp = await gapi.client.drive.files.list({
        q: `name='${DRIVE_FOLDER}' and mimeType='application/vnd.google-apps.folder' and trashed=false`,
        fields: 'files(id, name)',
    });

    if (resp.result.files.length) {
        _pairingsFolder = resp.result.files[0];
        return _pairingsFolder;
    }

    const create = await gapi.client.drive.files.create({
        resource: { name: DRIVE_FOLDER, mimeType: 'application/vnd.google-apps.folder' },
        fields: 'id, name',
    });
    _pairingsFolder = create.result;
    return _pairingsFolder;
}

// ── Multipart body helper ─────────────────────────────────────────────────────

function _multipart(metadata, body, contentType = 'application/json') {
    const delim = 'harmonix_boundary';
    return [
        `--${delim}\r\nContent-Type: application/json\r\n\r\n`,
        JSON.stringify(metadata),
        `\r\n--${delim}\r\nContent-Type: ${contentType}\r\n\r\n`,
        body,
        `\r\n--${delim}--`,
    ].join('') ;
}

// ── File helpers ──────────────────────────────────────────────────────────────

async function _findFile(name) {
    await _ensureFolder();
    const resp = await gapi.client.drive.files.list({
        q: `name="${name}" and '${_pairingsFolder.id}' in parents and trashed=false`,
        fields: 'files(id, name)',
    });
    return resp.result.files[0] || null;
}

async function _readFile(fileId) {
    const resp = await gapi.client.drive.files.get({ fileId, alt: 'media' });
    return resp.body;
}

async function _writeFile(name, content) {
    const existing = await _findFile(name);
    if (existing) {
        await gapi.client.request({
            path:   `https://www.googleapis.com/upload/drive/v3/files/${existing.id}`,
            method: 'PATCH',
            params: { uploadType: 'media' },
            headers: { 'Content-Type': 'application/json' },
            body:   content,
        });
    } else {
        await gapi.client.request({
            path:   'https://www.googleapis.com/upload/drive/v3/files',
            method: 'POST',
            params: { uploadType: 'multipart' },
            headers: { 'Content-Type': 'multipart/related; boundary="harmonix_boundary"' },
            body:   _multipart({ name, parents: [_pairingsFolder.id] }, content),
        });
    }
}

async function _deleteFile(name) {
    const existing = await _findFile(name);
    if (!existing) return;
    await gapi.client.drive.files.delete({ fileId: existing.id });
}

// ── Index management ──────────────────────────────────────────────────────────

async function _loadIndex() {
    await _ensureFolder();
    const file = await _findFile(DRIVE_INDEX_FILE);
    if (!file) return [];
    const raw = await _readFile(file.id);
    try { return JSON.parse(raw); } catch (_) { return []; }
}

async function _saveIndex(entries) {
    await _writeFile(DRIVE_INDEX_FILE, JSON.stringify(entries, null, 2));
}

// ── Public session API ────────────────────────────────────────────────────────

/**
 * Returns array of { id, label, created_at, updated_at } from index.
 */
async function driveLoadSessions() {
    if (!driveIsConnected()) throw new Error('Não ligado ao Drive');
    await _ensureToken();
    return await _loadIndex();
}

/**
 * Saves or updates a session. session.id must be set (generate with Date.now() or UUID).
 */
async function driveSaveSession(session) {
    if (!driveIsConnected()) throw new Error('Não ligado ao Drive');
    await _ensureToken();

    const fileName = `${session.id}.json`;
    await _writeFile(fileName, JSON.stringify(session, null, 2));

    // Update index
    let index = await _loadIndex();
    const existing = index.findIndex(e => e.id === session.id);
    const entry = {
        id:         session.id,
        label:      session.label || 'Sessão sem nome',
        created_at: session.created_at || new Date().toISOString(),
        updated_at: new Date().toISOString(),
    };

    if (existing >= 0) index[existing] = entry;
    else               index.unshift(entry);

    await _saveIndex(index);
    return entry;
}

/**
 * Returns full session object or null.
 */
async function driveLoadSession(id) {
    if (!driveIsConnected()) throw new Error('Não ligado ao Drive');
    await _ensureToken();

    const file = await _findFile(`${id}.json`);
    if (!file) return null;
    const raw = await _readFile(file.id);
    return JSON.parse(raw);
}

/**
 * Deletes session file and removes from index.
 */
async function driveDeleteSession(id) {
    if (!driveIsConnected()) throw new Error('Não ligado ao Drive');
    await _ensureToken();

    await _deleteFile(`${id}.json`);

    let index = await _loadIndex();
    index = index.filter(e => e.id !== id);
    await _saveIndex(index);
}
