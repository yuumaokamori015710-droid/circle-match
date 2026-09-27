const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const vm = require('node:vm');

const rendered = spawnSync('python', ['-c', 'from outputs.circlematch_db_app import render_signin_html; import sys; sys.stdout.buffer.write(render_signin_html("/events/test/apply"))'], {
  cwd: require('node:path').resolve(__dirname, '..'),
  env: { ...process.env, CIRCLEMATCH_SUPABASE_URL: 'https://example.supabase.co', CIRCLEMATCH_SUPABASE_ANON_KEY: 'test-publishable-key', CIRCLEMATCH_SESSION_SECRET: 'test-secret', CIRCLEMATCH_EMAIL_AUTH_ENABLED: 'true' },
  encoding: 'utf8',
});
assert.equal(rendered.status, 0, rendered.stderr);
assert.match(rendered.stdout, /id="googleButton" class="gsi-material-button" type="button" disabled/);
assert.match(rendered.stdout, /class="gsi-material-button-contents">Google でログイン<\/span>/);
assert.match(rendered.stdout, /viewBox="0 0 48 48"/);
assert.match(rendered.stdout, /class="gsi-material-button-icon" aria-hidden="true"/);
for (const color of ['#EA4335', '#4285F4', '#FBBC05', '#34A853']) {
  assert.ok(rendered.stdout.includes(`fill="${color}"`));
}
assert.doesNotMatch(rendered.stdout, /google-dot|conic-gradient/);
const script = [...rendered.stdout.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).find(s => s.includes('const supabaseUrl'));
assert.ok(script);

async function scenario({ emailEnabled = true, emailError = null, googleError = null, session = null, authenticated = false, syncFails = false, hash = '' } = {}) {
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, { disabled: true, hidden: false, textContent: '', value: '', classList: { add() {} }, reportValidity: () => true });
    return elements.get(id);
  };
  const calls = [], redirects = [];
  const context = {
    document: { getElementById: get },
    window: { supabase: { createClient: (_url, _key, options) => {
      assert.equal(options.auth.persistSession, false, 'server logout must not resurrect a stored Supabase session');
      assert.equal(options.auth.autoRefreshToken, false);
      return { auth: {
      getSession: async () => ({ data: { session } }),
      signInWithOAuth: async options => { calls.push(['google', options]); return { error: googleError }; },
      signInWithOtp: async options => { calls.push(['email', options]); return { error: emailError }; },
    } }; } } },
    fetch: async url => url === '/api/me'
      ? { ok: true, json: async () => ({ authenticated }) }
      : { ok: !syncFails, json: async () => syncFails ? { error: 'session rejected' } : { user: { email: 'member@example.test' } } },
    location: { origin: 'https://circle-match.jp', search: '', hash, replace: value => redirects.push(value) },
    URLSearchParams,
    setTimeout() {},
  };
  vm.runInNewContext(script.replace('const emailReady = true;', `const emailReady = ${emailEnabled};`), context);
  await new Promise(resolve => setImmediate(resolve));
  return { get, calls, redirects };
}

(async () => {
  const disabled = await scenario({ emailEnabled: false });
  assert.equal(disabled.get('emailButton').disabled, true);
  assert.equal(disabled.get('loginEmail').disabled, true);
  await disabled.get('googleButton').onclick();
  assert.equal(disabled.calls[0][1].provider, 'google');
  assert.equal(new URL(disabled.calls[0][1].options.redirectTo).searchParams.get('return_to'), '/events/test/apply');
  assert.equal(disabled.get('googleButton').disabled, true);
  const googleFailure = await scenario({ googleError: new Error('OAuth unavailable') });
  await googleFailure.get('googleButton').onclick();
  assert.match(googleFailure.get('status').textContent, /Googleログインを開始できませんでした/);
  assert.equal(googleFailure.get('googleButton').disabled, false);
  const login = await scenario();
  assert.equal(login.get('googleButton').disabled, false);
  login.get('loginEmail').value = ' member@example.test ';
  await login.get('emailForm').onsubmit({ preventDefault() {} });
  assert.equal(login.calls[0][0], 'email');
  assert.equal(login.calls[0][1].email, 'member@example.test');
  assert.equal(login.calls[0][1].options.shouldCreateUser, true);
  assert.equal(new URL(login.calls[0][1].options.emailRedirectTo).searchParams.get('return_to'), '/events/test/apply');
  assert.match(login.get('status').textContent, /送信を受け付けました/);
  await login.get('emailForm').onsubmit({ preventDefault() {} });
  assert.equal(login.calls.length, 1, 'duplicate send must wait for cooldown');
  const expired = await scenario({ hash: '#error=access_denied&error_code=otp_expired' });
  assert.match(expired.get('status').textContent, /有効期限/);
  assert.equal(expired.get('emailButton').disabled, false);
  const failure = await scenario({ emailError: new Error('SMTP unavailable') });
  await failure.get('emailForm').onsubmit({ preventDefault() {} });
  assert.match(failure.get('status').textContent, /送信できませんでした/);
  assert.equal(failure.get('emailButton').disabled, false);
  const callback = await scenario({ session: { access_token: 'test-token' } });
  assert.deepEqual(callback.redirects, ['/events/test/apply']);
  const rejected = await scenario({ session: { access_token: 'bad-token' }, syncFails: true });
  assert.deepEqual(rejected.redirects, []);
  assert.equal(rejected.get('googleButton').disabled, false);
  await rejected.get('googleButton').onclick();
  assert.equal(rejected.calls[0][0], 'google');
  const existing = await scenario({ authenticated: true });
  assert.deepEqual(existing.redirects, ['/events/test/apply']);
  console.log('signin flow: ok');
})().catch(error => { console.error(error); process.exitCode = 1; });
