/**
 * build.js
 * Substitutes API key placeholders with values from environment variables.
 * Run by Vercel before deploying: npm run build
 */

const replace = require('replace-in-file');

const apiKey   = process.env.GOOGLE_API_KEY;
const clientId = process.env.GOOGLE_CLIENT_ID;

const googleKeys = Object.keys(process.env).filter(k => k.startsWith('GOOGLE'));
console.log('build.js: GOOGLE_* env keys visible:', googleKeys.length ? googleKeys : '(none)');

if (!apiKey || !clientId) {
    console.error('build.js: GOOGLE_API_KEY and GOOGLE_CLIENT_ID must be set as environment variables.');
    process.exit(1);
}

const results = replace.sync({
    files: 'js/drive-harmonix.js',
    from:  [/PLACEHOLDER_GOOGLE_API_KEY/g, /PLACEHOLDER_GOOGLE_CLIENT_ID/g],
    to:    [apiKey, clientId],
});

const changed = results.filter(r => r.hasChanged).map(r => r.file);
if (changed.length === 0) {
    console.error('build.js: No replacements made — placeholders not found in drive-harmonix.js.');
    process.exit(1);
}

console.log('build.js: credentials injected into', changed.join(', '));
