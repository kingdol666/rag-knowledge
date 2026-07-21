/**
 * Claude chat history persistence (SQLite via better-sqlite3).
 *
 * Tables:
 *   sessions  — session_id (SDK UUID) + title (first prompt) + cwd/mode/model + timestamps + message count
 *   messages  — each SDK message (stored in order, content = raw JSON)
 *
 * Storage timing: automatically saved when chat.post.ts receives SDK messages (no extra frontend calls).
 * Reading: history.get.ts for listing; history/[sessionId].get.ts for single-session messages (frontend replay rendering).
 */
import Database from 'better-sqlite3'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { mkdirSync } from 'fs'

const __dirname = dirname(fileURLToPath(import.meta.url))
// web/server/utils/ -> web/server/ -> web/ -> rag-knowledge/
const MONOREPO_ROOT = resolve(__dirname, '../../..')
const STORAGE_DIR = resolve(MONOREPO_ROOT, 'storage')
const DB_PATH = resolve(STORAGE_DIR, 'claude-chat.db')

let _db: Database.Database | null = null

function getDb(): Database.Database {
  if (_db) return _db
  mkdirSync(STORAGE_DIR, { recursive: true })
  _db = new Database(DB_PATH)
  _db.pragma('journal_mode = WAL')
  _db.exec(`
    CREATE TABLE IF NOT EXISTS sessions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id TEXT UNIQUE NOT NULL,
      title TEXT,
      cwd TEXT,
      permission_mode TEXT,
      model TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now')),
      message_count INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id TEXT NOT NULL,
      sdk_type TEXT,
      content TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
  `)
  return _db
}

export interface SessionRow {
  session_id: string
  title: string | null
  cwd: string | null
  permission_mode: string | null
  model: string | null
  created_at: string
  updated_at: string
  message_count: number
}

export interface MessageRow {
  sdk_type: string
  content: string
  created_at: string
}

/**
 * Create or update a session. New sessions write the title (first prompt summary); existing sessions only refresh updated_at.
 */
export function upsertSession(
  sessionId: string,
  fields: {
    title?: string
    cwd?: string
    permissionMode?: string
    model?: string
  },
) {
  getDb()
    .prepare(
      `INSERT INTO sessions (session_id, title, cwd, permission_mode, model)
       VALUES (@session_id, @title, @cwd, @permission_mode, @model)
       ON CONFLICT(session_id) DO UPDATE SET
         title = COALESCE(excluded.title, sessions.title),
         cwd = COALESCE(excluded.cwd, sessions.cwd),
         permission_mode = COALESCE(excluded.permission_mode, sessions.permission_mode),
         model = COALESCE(excluded.model, sessions.model),
         updated_at = datetime('now')`,
    )
    .run({
      session_id: sessionId,
      title: fields.title ?? null,
      cwd: fields.cwd ?? null,
      permission_mode: fields.permissionMode ?? null,
      model: fields.model ?? null,
    })
}

export function saveMessage(sessionId: string, sdkType: string, content: string) {
  const db = getDb()
  const tx = db.transaction(() => {
    db.prepare(
      'INSERT INTO messages (session_id, sdk_type, content) VALUES (?, ?, ?)',
    ).run(sessionId, sdkType, content)
    db.prepare(
      `UPDATE sessions SET message_count = message_count + 1, updated_at = datetime('now')
       WHERE session_id = ?`,
    ).run(sessionId)
  })
  tx()
}

export function listSessions(limit = 50): SessionRow[] {
  return getDb()
    .prepare(
      `SELECT session_id, title, cwd, permission_mode, model, created_at, updated_at, message_count
       FROM sessions ORDER BY updated_at DESC LIMIT ?`,
    )
    .all(limit) as SessionRow[]
}

/** 获取单个会话的元信息（标题等），用于历史回放时在顶部展示用户最初的问题。 */
export function getSessionMeta(sessionId: string): { title: string | null; model: string | null } | null {
  return (
    getDb()
      .prepare('SELECT title, model FROM sessions WHERE session_id = ?')
      .get(sessionId) as { title: string | null; model: string | null } | undefined
  ) ?? null
}

export function getSessionMessages(sessionId: string): MessageRow[] {
  return getDb()
    .prepare(
      'SELECT sdk_type, content, created_at FROM messages WHERE session_id = ? ORDER BY id ASC',
    )
    .all(sessionId) as MessageRow[]
}

export function deleteSession(sessionId: string) {
  const db = getDb()
  const tx = db.transaction(() => {
    db.prepare('DELETE FROM messages WHERE session_id = ?').run(sessionId)
    db.prepare('DELETE FROM sessions WHERE session_id = ?').run(sessionId)
  })
  tx()
}
