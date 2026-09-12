#!/usr/bin/env node
/**
 * autofix-cli — entry point
 * Usage:
 *   autofix login              Open browser to authenticate
 *   autofix scan               Trigger scan of current repo
 *   autofix scan --dir <path>  Scan a local directory (no git required)
 *   autofix status             Show alerts and fixes
 *   autofix watch              Watch mode (continuous monitoring)
 */
const { execSync, exec } = require("child_process");
const fs = require("fs");
const path = require("path");
const http = require("http");
const https = require("https");
const crypto = require("crypto");

const RC_PATH = path.join(
  process.env.HOME || process.env.USERPROFILE,
  ".autofixrc"
);
const API_BASE = process.env.AUTOFIX_API_URL || "http://localhost:8000";

// ─── API Patterns (detects usage in source code) ────────────────────────────
const API_PATTERNS = {
  stripe: [
    /require\(["']stripe["']\)/gi,
    /from\s+["']stripe["']/gi,
    /import\s+Stripe\s+from\s+["']stripe["']/gi,
    /new\s+Stripe\(/gi,
    /stripe\.(charges|paymentIntents|subscriptions|customers|webhooks)/gi,
  ],
  shopify: [
    /require\(["']@shopify\/shopify-api["']\)/gi,
    /from\s+["']@shopify\/shopify-api["']/gi,
    /Shopify\.Session/gi,
    /shopify\.rest\./gi,
  ],
  twilio: [
    /require\(["']twilio["']\)/gi,
    /from\s+["']twilio["']/gi,
    /new\s+Twilio\(/gi,
    /twilio\.(messages|calls|verify)/gi,
  ],
  sendgrid: [
    /require\(["']@sendgrid\/mail["']\)/gi,
    /from\s+["']@sendgrid\/mail["']/gi,
    /sendgrid\.send\(/gi,
    /SG\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g,
  ],
  github: [
    /@octokit\/rest/gi,
    /octokit\.repos\./gi,
    /api\.github\.com/gi,
    /github\.com\/repos\//gi,
  ],
};

const SCAN_EXTENSIONS = [
  ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
  ".py", ".rb", ".go", ".java", ".php",
  ".env", ".json", ".yaml", ".yml", ".toml",
];

const IGNORE_DIRS = [
  "node_modules", ".git", "dist", "build", "target",
  "__pycache__", ".venv", "venv", ".next", ".nuxt",
  "vendor", "coverage", ".cache",
];

// ─── Helpers ────────────────────────────────────────────────────────────────
function loadConfig() {
  try {
    return JSON.parse(fs.readFileSync(RC_PATH, "utf8"));
  } catch {
    return null;
  }
}

function saveConfig(config) {
  fs.writeFileSync(RC_PATH, JSON.stringify(config, null, 2));
}

function apiRequest(method, endpoint, body, token) {
  const url = new URL(endpoint, API_BASE);
  const isHttps = url.protocol === "https:";
  const lib = isHttps ? https : http;

  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return new Promise((resolve, reject) => {
    const req = lib.request(
      url,
      { method, headers },
      (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => {
          try {
            const json = JSON.parse(data);
            if (res.statusCode >= 400) {
              reject(new Error(json.detail || `HTTP ${res.statusCode}`));
            } else {
              resolve(json);
            }
          } catch {
            reject(new Error(`HTTP ${res.statusCode}: ${data}`));
          }
        });
      }
    );
    req.on("error", reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

// ─── Local File Scanner ─────────────────────────────────────────────────────
function scanLocalDir(dirPath) {
  const resolved = path.resolve(dirPath);
  if (!fs.existsSync(resolved)) {
    console.error(`❌ Directory not found: ${resolved}`);
    process.exit(1);
  }

  console.log(`\n🔍 Scanning: ${resolved}\n`);

  const detections = [];
  let fileCount = 0;

  function walkDir(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);

      if (entry.isDirectory()) {
        if (!IGNORE_DIRS.includes(entry.name)) {
          walkDir(fullPath);
        }
        continue;
      }

      const ext = path.extname(entry.name).toLowerCase();
      if (!SCAN_EXTENSIONS.includes(ext)) continue;

      fileCount++;
      try {
        const content = fs.readFileSync(fullPath, "utf8");
        const relativePath = path.relative(resolved, fullPath);

        for (const [api, patterns] of Object.entries(API_PATTERNS)) {
          for (const pattern of patterns) {
            pattern.lastIndex = 0;
            const matches = content.match(pattern);
            if (matches && matches.length > 0) {
              // Find line numbers
              const lines = content.split("\n");
              const lineNumbers = [];
              for (let i = 0; i < lines.length; i++) {
                pattern.lastIndex = 0;
                if (pattern.test(lines[i])) {
                  lineNumbers.push(i + 1);
                }
              }
              detections.push({
                api,
                file: relativePath,
                matches: matches.length,
                lines: lineNumbers.slice(0, 5),
                snippet: lines[lineNumbers[0] - 1]?.trim().slice(0, 120),
              });
            }
          }
        }
      } catch {
        // Skip unreadable files
      }
    }
  }

  walkDir(resolved);

  // Deduplicate
  const seen = new Set();
  const unique = detections.filter((d) => {
    const key = `${d.api}:${d.file}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  // Sort by severity
  const severityOrder = { github: 0, stripe: 1, twilio: 2, shopify: 3, sendgrid: 4 };
  unique.sort((a, b) => (severityOrder[a.api] ?? 9) - (severityOrder[b.api] ?? 9));

  // Output
  console.log(`📁 Files scanned: ${fileCount}`);
  console.log(`🔗 API detections: ${unique.length}\n`);

  if (unique.length === 0) {
    console.log("✅ No third-party API usage detected.\n");
    return;
  }

  // Group by API
  const grouped = {};
  for (const d of unique) {
    if (!grouped[d.api]) grouped[d.api] = [];
    grouped[d.api].push(d);
  }

  for (const [api, items] of Object.entries(grouped)) {
    const icon = { stripe: "💳", shopify: "🛒", twilio: "📱", sendgrid: "📧", github: "🐙" }[api] || "🔗";
    console.log(`${icon} ${api.toUpperCase()} (${items.length} file${items.length !== 1 ? "s" : ""})`);
    for (const item of items) {
      console.log(`   📄 ${item.file}`);
      console.log(`      Lines: ${item.lines.join(", ")} | Matches: ${item.matches}`);
      if (item.snippet) console.log(`      ${item.snippet}`);
    }
    console.log();
  }

  // Summary
  console.log("─".repeat(50));
  console.log("Summary:");
  for (const [api, items] of Object.entries(grouped)) {
    console.log(`  ${api}: ${items.length} file(s)`);
  }
  console.log();

  return { fileCount, detections: unique, grouped };
}

// ─── Commands ───────────────────────────────────────────────────────────────
async function login() {
  console.log("\n🔑 AutoFix Login\n");
  console.log("To get an API key:");
  console.log("  1. Go to http://localhost:3000/dashboard/settings/api-keys");
  console.log('  2. Click "Generate Key"\n');
  const readline = require("readline");
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const key = await new Promise((r) =>
    rl.question("Paste your API key (afx_live_...): ", r)
  );
  rl.close();

  if (!key.startsWith("afx_live_")) {
    console.error("❌ Invalid key format. Key must start with afx_live_");
    process.exit(1);
  }

  saveConfig({ api_key: key });
  console.log("✅ Saved to " + RC_PATH);
  console.log("   Run `autofix status` to get started.\n");
}

async function scan() {
  const config = loadConfig();
  const args = process.argv.slice(3);

  // Check for --dir flag
  const dirIndex = args.indexOf("--dir");
  if (dirIndex !== -1 && args[dirIndex + 1]) {
    const dirPath = args[dirIndex + 1];
    const result = scanLocalDir(dirPath);

    // Try to upload to API if logged in
    if (config?.api_key && result && result.detections.length > 0) {
      console.log("📤 Uploading results to AutoFix API...");
      try {
        await apiRequest("POST", "/api/public/v1/detections/bulk", {
          detections: result.detections.map((d) => ({
            api_name: d.api,
            file_path: d.file,
            line_numbers: d.lines,
            match_count: d.matches,
          })),
        }, config.api_key);
        console.log("✅ Results uploaded to dashboard.\n");
      } catch (e) {
        console.log(`⚠️  Could not upload: ${e.message}`);
        console.log("   Results saved locally.\n");
      }
    }
    return;
  }

  // Original git-based scan
  if (!config?.api_key) {
    console.error("❌ Not logged in. Run `autofix login` first.");
    process.exit(1);
  }

  console.log("\n🔍 Scanning current directory...\n");

  let repoName;
  try {
    const remote = execSync("git remote get-url origin", { encoding: "utf8" }).trim();
    repoName = remote.split("/").slice(-2).join("/").replace(".git", "");
  } catch {
    console.error("❌ Not a git repository or no remote configured.");
    console.log("   Use `autofix scan --dir /path` to scan a local directory.\n");
    process.exit(1);
  }

  console.log(`   Repository: ${repoName}`);

  try {
    const repos = await apiRequest("GET", "/repos", null, config.api_key);
    const repo = repos.find((r) => r.full_name === repoName);
    if (repo) {
      console.log(`   Repo ID: ${repo.id}`);
      console.log("   Triggering scan...");
      const result = await apiRequest("POST", `/repos/${repo.id}/scan`, null, config.api_key);
      console.log(`   ✅ Scan complete: ${result.detections_count || 0} detections, ${result.alerts_count || 0} alerts\n`);
      return;
    }
  } catch (e) {
    // Fall through
  }

  console.log(`   ⚠️  Repo "${repoName}" not connected to AutoFix.`);
  console.log("   Connect it first at http://localhost:3000/dashboard\n");
}

async function watch() {
  const config = loadConfig();
  if (!config?.api_key) {
    console.error("❌ Not logged in. Run `autofix login` first.");
    process.exit(1);
  }

  console.log("\n👁️  AutoFix Watch Mode");
  console.log("   Monitoring for changes... (Press Ctrl+C to stop)\n");

  let lastScan = null;

  function runScan() {
    const result = scanLocalDir(process.cwd());
    if (result && JSON.stringify(result) !== JSON.stringify(lastScan)) {
      if (lastScan) {
        console.log("🔔 Changes detected!\n");
      }
      lastScan = result;
    }
  }

  runScan();
  setInterval(runScan, 30000); // Scan every 30 seconds
}

async function status() {
  const config = loadConfig();
  if (!config?.api_key) {
    console.error("❌ Not logged in. Run `autofix login` first.");
    process.exit(1);
  }

  console.log("\n📊 AutoFix Status\n");

  try {
    const [alertsRes, fixesRes] = await Promise.all([
      apiRequest("GET", "/api/public/v1/alerts?per_page=50", null, config.api_key),
      apiRequest("GET", "/api/public/v1/fixes?per_page=50", null, config.api_key),
    ]);

    const alerts = alertsRes.alerts || [];
    if (alerts.length === 0) {
      console.log("✅ No alerts — all APIs are stable.\n");
    } else {
      console.log(`⚠️  ${alerts.length} alert${alerts.length !== 1 ? "s" : ""}:\n`);
      console.log(
        "  " +
          "Severity".padEnd(10) +
          "API".padEnd(25) +
          "Change".padEnd(20) +
          "Repo"
      );
      console.log("  " + "─".repeat(75));
      for (const a of alerts.slice(0, 20)) {
        const sev = (a.severity || "medium").padEnd(10);
        const api = (a.api_name || "—").padEnd(25);
        const change = (a.change_type || "—").padEnd(20);
        const repo = a.repo_id ? a.repo_id.slice(0, 8) + "…" : "—";
        console.log(`  ${sev}${api}${change}${repo}`);
      }
      if (alerts.length > 20) console.log(`  ... and ${alerts.length - 20} more`);
      console.log();
    }

    const fixes = fixesRes.fixes || [];
    const pending = fixes.filter((f) => f.status === "needs_review");
    if (pending.length > 0) {
      console.log(`🔧 ${pending.length} pending fix${pending.length !== 1 ? "es" : ""}:\n`);
      console.log(
        "  " +
          "Status".padEnd(15) +
          "Description".padEnd(40) +
          "Repo"
      );
      console.log("  " + "─".repeat(60));
      for (const f of pending.slice(0, 10)) {
        const st = (f.status || "—").padEnd(15);
        const desc = (f.description || "—").slice(0, 38).padEnd(40);
        const repo = f.repo_id ? f.repo_id.slice(0, 8) + "…" : "—";
        console.log(`  ${st}${desc}${repo}`);
      }
      console.log();
    }
  } catch (e) {
    console.error(`❌ API error: ${e.message}`);
    console.error("   Make sure your API key is valid and the server is running.\n");
    process.exit(1);
  }
}

// ─── CLI Router ─────────────────────────────────────────────────────────────
const cmd = process.argv[2];

switch (cmd) {
  case "login":
    login();
    break;
  case "scan":
    scan();
    break;
  case "watch":
    watch();
    break;
  case "status":
    status();
    break;
  default:
    console.log(`
🔧 autofix-cli — AutoFix API CLI

Usage:
  autofix login              Authenticate with your API key
  autofix scan               Scan current git repo for API usage
  autofix scan --dir <path>  Scan a local directory (no git required)
  autofix status             Show alerts and pending fixes
  autofix watch              Watch mode (continuous monitoring)

Examples:
  autofix scan --dir ./src           Scan src folder
  autofix scan --dir C:\\Projects\\app  Scan Windows directory
  autofix scan --dir /home/user/app  Scan Linux directory

Configuration:
  API URL: ${API_BASE}
  Config:  ${RC_PATH}
`);
}
