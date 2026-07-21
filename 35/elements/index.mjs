import { createServer } from 'node:http';
import assert from 'node:assert';
import { spawn } from 'node:child_process';
import { mkdir, mkdtemp, writeFile, rm, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const sleep = delay => new Promise(res => setTimeout(res, delay));

const html = await readFile('static/index.html', 'utf-8');
const js = await readFile('static/index.js', 'utf-8');
const flag = await readFile('flag.txt', 'utf-8');

let visiting = false;

async function visit(state) {
	if (visiting) return;
	visiting = true;

	state = {...state, flag }

	const userDataDir = await mkdtemp(join(tmpdir(), 'elements-'));

	await mkdir(join(userDataDir, 'Default'));
	await writeFile(join(userDataDir, 'Default', 'Preferences'), JSON.stringify({
		net: {
			network_prediction_options: 2
		}
	}));

	const proc = spawn(
		'/usr/bin/chromium-browser-unstable', [
			`--user-data-dir=${userDataDir}`,
			'--profile-directory=Default',
			'--no-sandbox',
			'--js-flags=--noexpose_wasm,--jitless',
			'--disable-gpu',
			'--no-first-run',
			'--enable-experimental-web-platform-features',
			`http://127.0.0.1:8080/#${Buffer.from(JSON.stringify(state)).toString('base64')}`
		],
		{ detached: true }
	)

	await sleep(10000);
	try {
		process.kill(-proc.pid)
	} catch(e) {}
	await sleep(500);

	await rm(userDataDir, { recursive: true, force: true, maxRetries: 10 });

	visiting = false;
}

createServer((req, res) => {
	const url = new URL(req.url, 'http://127.0.0.1');

	const csp =  [
		"default-src 'none'",
		"style-src 'unsafe-inline'",
		"script-src 'unsafe-eval' 'self'",
		"frame-ancestors 'none'",
		"worker-src 'none'",
		"navigate-to 'none'"
	]

	// no seriously, do NOT attack the online-mode server!
	// the solution literally CANNOT use it!
	if (req.headers.host !== '127.0.0.1:8080') {
		csp.push("connect-src https://elements.attest.lol/");
	}

	res.setHeader('Content-Security-Policy', csp.join('; '));
	res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
	res.setHeader('X-Frame-Options', 'deny');
	res.setHeader('X-Content-Type-Options', 'nosniff');

	if (url.pathname === '/') {
		res.setHeader('Content-Type', 'text/html');
		return res.end(html);
	} else if (url.pathname === '/index.js') {
		res.setHeader('Content-Type', 'text/javascript');
		return res.end(js);
	} else if (url.pathname === '/remoteCraft') {
		try {
			const { recipe, xss } = JSON.parse(url.searchParams.get('recipe'));
			assert(typeof xss === 'string');
			assert(xss.length < 300);
			assert(recipe instanceof Array);
			assert(recipe.length < 50);
			for (const step of recipe) {
				assert(step instanceof Array);
				assert(step.length === 2);
				for (const element of step) {
					assert(typeof xss === 'string');
					assert(element.length < 50);
				}
			}
			visit({ recipe, xss });
		} catch(e) {
			console.error(e);
			return res.writeHead(400).end('invalid recipe!');
		}
		return res.end('visiting!');
	}

	return res.writeHead(404).end('not found');
}).listen(8080);
