#!/usr/bin/env node

import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import vm from 'node:vm'

const REPO = path.resolve(import.meta.dirname, '..')
const OUTPUT_ROOT = path.join(REPO, 'reproductions', 'upstream-curated')
const CACHE_DIR = path.join(REPO, '.agent', 'upstream-sources')
const BUNDLE_PATH = path.join(CACHE_DIR, 'index-DdHuI7-l.js')
const BUNDLE_URL = 'https://hy-nomas.hy.tencent.com/assets/index-DdHuI7-l.js'
const BUNDLE_SHA256 = 'e135e2bb3948740d32c6f9de8a6efc095491dae508a14d0b9c9ec8343f42bd2a'

const CASES = [
  'snow-palace-walk',
  'snow-palace-ascent',
  'coastal-waterfall',
  'voxel-adventure',
  'kitchen-stories',
  'street-coffee',
]
const EXACT_CASES = new Set([
  'snow-palace-ascent',
  'voxel-adventure',
  'kitchen-stories',
])
const VIDEO_SHA256 = {
  'snow-palace-walk': '49d663c12c13d2971b011fdd009fa444a49ed946566cc5c121949c513d095d0b',
  'snow-palace-ascent': '2ef9551d44afe0051681ce83292d2a8d0733f1a054974713b5f65a8e0ebe3c0d',
  'coastal-waterfall': '9f00398930046472c3143e69e76627365171e733b7d80dede0ef90c74e63d902',
  'voxel-adventure': '7caa5460bb4b22100dd10f442c2f1ec8a3f7b2e892ed44edf718d8cf00e23488',
  'kitchen-stories': '274bfea3e0ce83b2a3a1507eb8dadaedef91e0e2ecaa4bdc04ec903d4bde89ee',
  'street-coffee': 'e11a92e78dc530e908ec4b8ff40b9730b284e3d4222ca9b57147a28bbea800ac',
}

function sha256(data) {
  return crypto.createHash('sha256').update(data).digest('hex')
}

function json(value) {
  return `${JSON.stringify(value, null, 2)}\n`
}

function timestamp(seconds) {
  const millis = Math.round(Number(seconds) * 1000)
  const hours = Math.floor(millis / 3_600_000)
  const minutes = Math.floor((millis % 3_600_000) / 60_000)
  const secs = Math.floor((millis % 60_000) / 1000)
  const ms = millis % 1000
  return [
    String(hours).padStart(2, '0'),
    String(minutes).padStart(2, '0'),
    `${String(secs).padStart(2, '0')}.${String(ms).padStart(3, '0')}`,
  ].join(':')
}

async function loadBundle({ refresh }) {
  if (!refresh && fs.existsSync(BUNDLE_PATH)) {
    const cached = fs.readFileSync(BUNDLE_PATH)
    if (sha256(cached) === BUNDLE_SHA256) return cached
    throw new Error(`cached upstream bundle has unexpected SHA-256: ${BUNDLE_PATH}`)
  }
  const response = await fetch(BUNDLE_URL)
  if (!response.ok) throw new Error(`upstream bundle download failed: HTTP ${response.status}`)
  const bundle = Buffer.from(await response.arrayBuffer())
  const digest = sha256(bundle)
  if (digest !== BUNDLE_SHA256) {
    throw new Error(`upstream bundle SHA-256 changed: expected ${BUNDLE_SHA256}, got ${digest}`)
  }
  fs.mkdirSync(CACHE_DIR, { recursive: true })
  fs.writeFileSync(BUNDLE_PATH, bundle)
  return bundle
}

function extractGallery(bundleBuffer) {
  const bundle = bundleBuffer.toString('utf8')
  const anchor = 'curated-20261022-snow-palace-walk'
  const anchorAt = bundle.indexOf(anchor)
  if (anchorAt < 0) throw new Error(`gallery anchor not found: ${anchor}`)
  const expressionStart = bundle.lastIndexOf('JSON.parse(`', anchorAt)
  const expressionEnd = bundle.indexOf('`)', anchorAt)
  if (expressionStart < 0 || expressionEnd < 0) {
    throw new Error('could not isolate the embedded upstream Gallery JSON')
  }
  const expression = bundle.slice(expressionStart, expressionEnd + 2)
  const gallery = vm.runInNewContext(expression, { JSON }, { timeout: 1000 })
  if (!Array.isArray(gallery)) throw new Error('embedded upstream Gallery is not an array')
  return gallery
}

function missingData(entry) {
  const hiddenPromptSegments = entry.prompt_timeline
    .filter((turn) => turn.prompt === 'Original user prompt unavailable')
    .map((turn) => turn.number)
  const cameraSegments = entry.prompt_timeline
    .filter((turn) => turn.prompt === 'Camera control')
    .map((turn) => ({
      number: turn.number,
      start_seconds: turn.start_seconds,
      end_seconds: turn.end_seconds,
    }))
  const missing = []
  if (hiddenPromptSegments.length) {
    missing.push(`prompt_segments:${hiddenPromptSegments.join(',')}`)
  }
  if (cameraSegments.length) missing.push('camera_trajectory')
  return { hiddenPromptSegments, cameraSegments, missing }
}

function scenarioFor(slug, entry) {
  return [{
    test_id: `upstream-${slug}`,
    title: entry.title,
    source_id: entry.id,
    source_kind: 'official-public-gallery-timeline-adapter',
    perspective: entry.perspective,
    total_duration: entry.prompt_timeline.at(-1).end_seconds,
    segments: entry.prompt_timeline.map((turn, index) => ({
      segment_index: index,
      start_time: timestamp(turn.start_seconds),
      end_time: timestamp(turn.end_seconds),
      ...(index === 0
        ? { visual_description_long: turn.prompt }
        : { description_change: turn.prompt }),
    })),
  }]
}

function expectedFiles(gallery) {
  const files = new Map()
  const manifestCases = []
  for (const slug of CASES) {
    const id = `curated-20261022-${slug}`
    const entry = gallery.find((item) => item.id === id)
    if (!entry) throw new Error(`upstream Gallery entry not found: ${id}`)
    const { hiddenPromptSegments, cameraSegments, missing } = missingData(entry)
    const exactReplay = EXACT_CASES.has(slug)
    if (exactReplay !== (missing.length === 0)) {
      throw new Error(`replay completeness policy is stale for ${slug}`)
    }
    const caseRoot = path.join(OUTPUT_ROOT, slug)
    const videoFilename = path.basename(entry.video)
    const videoUrl = `https://hy-nomas.hy.tencent.com/gallery/${videoFilename}`
    const provenance = {
      source: 'official Hy-Nomas public production frontend',
      extracted_at_policy: 'deterministic; timestamp intentionally omitted',
      gallery_bundle: { url: BUNDLE_URL, sha256: BUNDLE_SHA256 },
      video: {
        url: videoUrl,
        sha256: VIDEO_SHA256[slug],
        local_path: `gallery/media/${videoFilename}`,
      },
      note: 'The Gallery entry is copied verbatim. scenario.json, when present, is a local format adapter over the published timeline, not an upstream-authored scenario file.',
    }
    const availability = {
      exact_replay: exactReplay,
      published_segments: entry.prompt_timeline.length,
      hidden_prompt_segments: hiddenPromptSegments,
      camera_control_segments: cameraSegments.map((segment) => segment.number),
      missing,
      policy: exactReplay
        ? 'The full published text-only timeline can be passed unchanged through the local CLI and Web structured-JSON paths.'
        : 'Exact replay is disabled because public upstream omitted source data. No replacement values are fabricated.',
    }
    const camera = {
      status: cameraSegments.length ? 'not-published' : 'not-present-in-published-timeline',
      segments: cameraSegments,
      trajectory: null,
      note: cameraSegments.length
        ? 'Public upstream identifies these intervals only as Camera control; no frames, key events, transforms, or trajectory JSON are present in the pinned bundle.'
        : 'The published timeline uses text prompts only. Camera directions inside prompt text remain verbatim.',
    }
    files.set(path.join(caseRoot, 'upstream-gallery-entry.json'), json(entry))
    files.set(path.join(caseRoot, 'provenance.json'), json(provenance))
    files.set(path.join(caseRoot, 'availability.json'), json(availability))
    files.set(path.join(caseRoot, 'camera-control.json'), json(camera))
    if (exactReplay) {
      const scenario = scenarioFor(slug, entry)
      files.set(path.join(caseRoot, 'scenario.json'), json(scenario))
      files.set(path.join(caseRoot, 'web-replay.json'), json({
        mode: 'structured-seg-ar-json',
        setup: {
          perspective: entry.perspective,
          subject_description: entry.subject,
          environment_description: entry.attributes,
        },
        scenario,
        instructions: 'Create a world with setup, then paste scenario as one JSON payload into the direction field. The UI detects structured JSON and bypasses prompt enhancement.',
      }))
    } else {
      files.set(path.join(caseRoot, 'web-replay.json'), json({
        mode: 'unavailable-exact-replay',
        setup: {
          perspective: entry.perspective,
          subject_description: entry.subject,
          environment_description: entry.attributes,
        },
        published_timeline: entry.prompt_timeline,
        missing,
        scenario: null,
        instructions: 'Do not run as an exact reproduction. Public upstream omitted required source data.',
      }))
    }
    manifestCases.push({
      slug,
      id,
      title: entry.title,
      exact_replay: exactReplay,
      missing,
      duration: entry.duration,
      video_sha256: VIDEO_SHA256[slug],
    })
  }
  files.set(path.join(OUTPUT_ROOT, 'manifest.json'), json({
    version: 1,
    gallery_bundle: { url: BUNDLE_URL, sha256: BUNDLE_SHA256 },
    cases: manifestCases,
  }))
  return files
}

function writeFiles(files) {
  for (const [filename, contents] of files) {
    fs.mkdirSync(path.dirname(filename), { recursive: true })
    fs.writeFileSync(filename, contents)
    console.log(`wrote ${path.relative(REPO, filename)}`)
  }
}

function checkFiles(files) {
  let failed = false
  for (const [filename, expected] of files) {
    if (!fs.existsSync(filename)) {
      console.error(`missing ${path.relative(REPO, filename)}`)
      failed = true
      continue
    }
    const actual = fs.readFileSync(filename, 'utf8')
    if (actual !== expected) {
      console.error(`stale ${path.relative(REPO, filename)}`)
      failed = true
    }
  }
  for (const slug of CASES.filter((item) => !EXACT_CASES.has(item))) {
    const forbidden = path.join(OUTPUT_ROOT, slug, 'scenario.json')
    if (fs.existsSync(forbidden)) {
      console.error(`partial upstream case must not have exact scenario.json: ${path.relative(REPO, forbidden)}`)
      failed = true
    }
  }
  if (failed) process.exitCode = 1
  else console.log(`verified ${files.size} source-pack files`)
}

const args = new Set(process.argv.slice(2))
const bundle = await loadBundle({ refresh: args.has('--refresh') })
const files = expectedFiles(extractGallery(bundle))
if (args.has('--check')) checkFiles(files)
else writeFiles(files)
