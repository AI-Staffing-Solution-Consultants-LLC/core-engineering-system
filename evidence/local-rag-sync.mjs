/**
 * Local RAG Sync Loop — Step 4: Provision and Seed OpenViking RAG Memory
 *
 * This local shim mirrors the intent of src/scraper.js (Cloudflare Browser Rendering)
 * by walking the workspace tree, discovering all documentation, indexing it,
 * and populating the rag/docs/ directory with structured manifests.
 *
 * Why a shim? scraper.js uses `browserBinding.launch()` (Cloudflare Workers-only API).
 * This script provides equivalent local functionality using Node.js fs APIs.
 *
 * Output:
 *   - manifest.json per module directory
 *   - rag/docs/*.rag.md — indexed content chunks
 *   - evidence/local-rag-sync-report.json — execution evidence
 */

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

// ── Configuration ──────────────────────────────────────────────────────────
const WORKSPACE_ROOT = '/home/olly/core-engineering-system';
const RAG_OUTPUT_DIR = path.join(WORKSPACE_ROOT, 'rag', 'docs');
const EVIDENCE_DIR = path.join(WORKSPACE_ROOT, 'evidence');

const SKIP_DIRS = new Set([
  '.git', '.venv', '__pycache__', '.pytest_cache',
  '.ruff_cache', '.omo', '.opencode', 'node_modules',
  '.test', 'evidence',
]);

const DOC_EXTENSIONS = new Set([
  '.md', '.txt', '.toml', '.yaml', '.yml', '.rego',
  '.json', '.py', '.js', '.sh',
]);

const CONFIG_FILES = new Set([
  'Dockerfile', 'docker-compose.yml', 'cloudbuild.yaml',
  'wrangler.toml', '.env.example', '.gitignore',
  'CEM_Update.txt', 'AGENTS.md', 'README.md',
]);

const MAX_CHUNK_BYTES = 4096; // 4KB per chunk for RAG ingestion

// ── Utilities ──────────────────────────────────────────────────────────────

function sha256(content) {
  return crypto.createHash('sha256').update(content).digest('hex');
}

function nowISO() {
  return new Date().toISOString();
}

/**
 * Walk the workspace tree, yielding file paths (skip hidden/build dirs).
 */
function* walkDir(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.name.startsWith('.') && SKIP_DIRS.has(entry.name)) continue;
    if (entry.name.startsWith('.') && !['.env.example', '.gitignore'].includes(entry.name)) continue;

    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      yield* walkDir(fullPath);
    } else if (entry.isFile()) {
      yield fullPath;
    }
  }
}

/**
 * Classify a file's domain: config, documentation, policy, source, terraform, etc.
 */
function classifyFile(filePath) {
  const rel = path.relative(WORKSPACE_ROOT, filePath);
  const filename = path.basename(filePath);
  const dir = path.dirname(rel);

  if (CONFIG_FILES.has(filename)) return { type: 'config', domain: 'infrastructure' };
  if (filename.endsWith('.rego')) return { type: 'policy', domain: 'constitutional-ai' };
  if (dir.startsWith('terraform')) return { type: 'iac', domain: 'terraform' };
  if (dir.startsWith('track-a')) return { type: 'source', domain: 'control-loop' };
  if (dir.startsWith('track-b')) return { type: 'source', domain: 'actuator' };
  if (dir.startsWith('policy')) return { type: 'policy', domain: 'constitutional-ai' };
  if (dir.startsWith('src')) return { type: 'source', domain: 'cloudflare-edge' };
  if (dir.startsWith('rag')) return { type: 'rag', domain: 'knowledge-base' };
  if (dir.startsWith('tests')) return { type: 'test', domain: 'validation' };
  if (dir.startsWith('mcp')) return { type: 'config', domain: 'mcp-integration' };
  if (dir.startsWith('agency-agents')) return { type: 'config', domain: 'agency-roster' };

  return { type: 'documentation', domain: 'general' };
}

/**
 * Chunk content into max `MAX_CHUNK_BYTES`-byte pieces with overlap.
 */
function chunkContent(content, filename) {
  const chunks = [];
  let offset = 0;
  const overlap = 128; // bytes of overlap between chunks

  while (offset < content.length) {
    const end = Math.min(offset + MAX_CHUNK_BYTES, content.length);
    const chunk = content.slice(offset, end);
    chunks.push({
      chunk_id: sha256(chunk).slice(0, 16),
      source_file: filename,
      byte_offset: offset,
      byte_length: chunk.length,
      content: chunk,
    });
    offset = end - overlap;
    if (offset >= content.length) break;
  }

  return chunks;
}

// ── Main Sync Loop ─────────────────────────────────────────────────────────

async function main() {
  console.log(`[RAG-SYNC] Starting local vector-sync loop at ${nowISO()}`);
  console.log(`[RAG-SYNC] Workspace root: ${WORKSPACE_ROOT}`);
  console.log(`[RAG-SYNC] RAG output dir: ${RAG_OUTPUT_DIR}`);
  console.log('');

  // Ensure output directories exist
  fs.mkdirSync(RAG_OUTPUT_DIR, { recursive: true });
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

  // ── Step 1: Discover all qualifying documentation files ──────────────
  const discoveredFiles = [];
  const moduleDirs = new Map();  // directory → files

  console.log('[1/5] Walking workspace tree...');
  for (const filePath of walkDir(WORKSPACE_ROOT)) {
    const ext = path.extname(filePath).toLowerCase();
    const filename = path.basename(filePath);

    if (!DOC_EXTENSIONS.has(ext) && !CONFIG_FILES.has(filename)) continue;

    const relPath = path.relative(WORKSPACE_ROOT, filePath);
    const classification = classifyFile(filePath);

    discoveredFiles.push({
      absolute_path: filePath,
      relative_path: relPath,
      filename,
      extension: ext,
      classification,
      size_bytes: fs.statSync(filePath).size,
    });

    // Group by module directory
    const moduleDir = path.dirname(relPath);
    if (!moduleDirs.has(moduleDir)) {
      moduleDirs.set(moduleDir, []);
    }
    moduleDirs.get(moduleDir).push(relPath);
  }

  console.log(`  Discovered ${discoveredFiles.length} qualifying files across ${moduleDirs.size} directories.`);

  // ── Step 2: Generate manifest.json per module directory ───────────────
  console.log('[2/5] Generating manifest.json per module directory...');
  const manifestsGenerated = [];

  for (const [moduleDir, files] of moduleDirs) {
    const manifestPath = path.join(WORKSPACE_ROOT, moduleDir, 'manifest.json');
    const cleanName = moduleDir.replace(/[^a-zA-Z0-9._-]/g, '_');

    const fileEntries = files.map((f) => {
      const fullPath = path.join(WORKSPACE_ROOT, f);
      return {
        file: f,
        sha256: sha256(fs.readFileSync(fullPath, 'utf-8')).slice(0, 16),
        size_bytes: fs.statSync(fullPath).size,
      };
    });

    const manifest = {
      module: cleanName || 'root',
      path: moduleDir || '.',
      generated_at: nowISO(),
      source: 'local-rag-sync-loop',
      step: 4,
      file_count: fileEntries.length,
      files: fileEntries,
    };

    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    manifestsGenerated.push({
      module: cleanName,
      relative_path: path.relative(WORKSPACE_ROOT, manifestPath),
      file_count: fileEntries.length,
    });

    console.log(`  ✓ ${path.relative(WORKSPACE_ROOT, manifestPath)} (${fileEntries.length} files)`);
  }

  // ── Step 3: Extract content, chunk, and index into rag/docs/ ─────────
  console.log('[3/5] Extracting, chunking, and indexing into rag/docs/...');
  let totalChunks = 0;
  let totalBytesIndexed = 0;

  const indexEntries = [];

  for (const file of discoveredFiles) {
    let content;
    try {
      content = fs.readFileSync(file.absolute_path, 'utf-8');
    } catch {
      continue; // skip binary/unreadable
    }

    const chunks = chunkContent(content, file.relative_path);
    totalChunks += chunks.length;
    totalBytesIndexed += content.length;

    // Write RAG chunk files
    for (const chunk of chunks) {
      const chunkFilename = `${chunk.chunk_id}.rag.md`;
      const chunkPath = path.join(RAG_OUTPUT_DIR, chunkFilename);

      const chunkDoc = [
        `# RAG Index Entry: ${chunk.chunk_id}`,
        `---`,
        `- **source**: \`${file.relative_path}\``,
        `- **domain**: ${file.classification.domain}`,
        `- **type**: ${file.classification.type}`,
        `- **byte_offset**: ${chunk.byte_offset}`,
        `- **byte_length**: ${chunk.byte_length}`,
        `- **indexed_at**: ${nowISO()}`,
        `- **step**: 4 (OpenViking RAG Memory Seed)`,
        ``,
        chunk.content,
      ].join('\n');

      fs.writeFileSync(chunkPath, chunkDoc);

      indexEntries.push({
        chunk_id: chunk.chunk_id,
        source_file: file.relative_path,
        domain: file.classification.domain,
        type: file.classification.type,
        byte_offset: chunk.byte_offset,
        byte_length: chunk.byte_length,
      });
    }
  }

  console.log(`  Indexed ${totalChunks} chunks (${(totalBytesIndexed / 1024).toFixed(1)} KB total)`);

  // ── Step 4: Write master index ───────────────────────────────────────
  console.log('[4/5] Writing master RAG index...');

  const masterIndex = {
    version: '1.0',
    step: 4,
    phase: 'OpenViking RAG Memory Seed',
    generated_at: nowISO(),
    workspace_root: WORKSPACE_ROOT,
    summary: {
      total_files: discoveredFiles.length,
      total_modules: moduleDirs.size,
      total_chunks: totalChunks,
      total_bytes_indexed: totalBytesIndexed,
      manifests_generated: manifestsGenerated.length,
    },
    modules: manifestsGenerated,
    index: indexEntries,
  };

  const masterIndexPath = path.join(RAG_OUTPUT_DIR, 'index.json');
  fs.writeFileSync(masterIndexPath, JSON.stringify(masterIndex, null, 2));
  console.log(`  ✓ rag/docs/index.json written`);

  // ── Step 5: Generate execution evidence report ───────────────────────
  console.log('[5/5] Generating execution evidence...');

  const evidenceReport = {
    execution_id: sha256(`${nowISO()}-local-rag-sync`).slice(0, 16),
    timestamp: nowISO(),
    phase: 'Step 4 — Provision and Seed OpenViking RAG Memory',
    tool: 'local-rag-sync.mjs',
    tool_path: path.relative(WORKSPACE_ROOT, path.join(EVIDENCE_DIR, 'local-rag-sync.mjs')),
    architecture_note:
      'src/scraper.js is a Cloudflare Workers Browser Rendering module using env.EDGE_BROWSER binding. ' +
      'It cannot execute locally. This local shim provides equivalent workspace walk + doc indexing.',
    results: {
      files_discovered: discoveredFiles.length,
      module_directories: moduleDirs.size,
      manifests_generated: manifestsGenerated.length,
      rag_chunks_indexed: totalChunks,
      rag_bytes_indexed: totalBytesIndexed,
    },
    manifests_created: manifestsGenerated.map((m) => ({
      path: m.relative_path,
      files: m.file_count,
    })),
    rag_output_dir: 'rag/docs/',
    rag_chunk_count: indexEntries.length,
    rag_master_index: 'rag/docs/index.json',
    rag_chunk_pattern: 'rag/docs/*.rag.md',
    module_breakdown: [...moduleDirs.entries()].map(([dir, files]) => ({
      directory: dir,
      file_count: files.length,
      files: files.slice(0, 5), // sample first 5
    })),
    hash_of_evidence: sha256(JSON.stringify(indexEntries)),
  };

  const evidencePath = path.join(EVIDENCE_DIR, 'local-rag-sync-report.json');
  fs.writeFileSync(evidencePath, JSON.stringify(evidenceReport, null, 2));

  // ── Print summary ───────────────────────────────────────────────────
  console.log('');
  console.log('═══════════════════════════════════════════════════════════');
  console.log('  RAG SYNC LOOP — EXECUTION COMPLETE');
  console.log('═══════════════════════════════════════════════════════════');
  console.log(`  Files discovered:    ${discoveredFiles.length}`);
  console.log(`  Module dirs:         ${moduleDirs.size}`);
  console.log(`  Manifests generated: ${manifestsGenerated.length}`);
  console.log(`  RAG chunks indexed:  ${totalChunks}`);
  console.log(`  RAG index:           rag/docs/index.json`);
  console.log(`  Evidence report:     ${path.relative(WORKSPACE_ROOT, evidencePath)}`);
  console.log(`  Evidence hash:       ${evidenceReport.hash_of_evidence}`);
  console.log('═══════════════════════════════════════════════════════════');

  return evidenceReport;
}

// ── Run ─────────────────────────────────────────────────────────────────────
main()
  .then((report) => {
    // Write a clean final line for parsers
    console.log(`\n[RAG-SYNC] DONE — execution_id=${report.execution_id}`);
    process.exit(0);
  })
  .catch((err) => {
    console.error(`[RAG-SYNC] FATAL: ${err.message}`);
    process.exit(1);
  });
