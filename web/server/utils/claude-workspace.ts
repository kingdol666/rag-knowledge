/**
 * Claude Workspace management — SQLite persistence
 *
 * Table: workspaces
 *   id          INTEGER PRIMARY KEY
 *   name        TEXT — user-friendly workspace name (e.g. "RAG Knowledge Base")
 *   path        TEXT UNIQUE — absolute path
 *   description TEXT — optional description
 *   pin_order   INTEGER — pin order (NULL = not pinned)
 *   last_used   TEXT — last used timestamp
 *   created_at  TEXT
 *   updated_at  TEXT
 */
import Database from 'better-sqlite3'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { mkdirSync, existsSync, statSync } from 'fs'

const __dirname = dirname(fileURLToPath(import.meta.url))
const MONOREPO_ROOT = resolve(__dirname, '../../..')
const STORAGE_DIR = resolve(MONOREPO_ROOT, 'storage')
const DB_PATH = resolve(STORAGE_DIR, 'claude-workspace.db')

let _db: Database.Database | null = null

function getDb(): Database.Database {
  if (_db) return _db
  mkdirSync(STORAGE_DIR, { recursive: true })
  _db = new Database(DB_PATH)
  _db.pragma('journal_mode = WAL')
  _db.exec(`
    CREATE TABLE IF NOT EXISTS workspaces (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      path TEXT UNIQUE NOT NULL,
      description TEXT,
      pin_order INTEGER,
      last_used TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_workspaces_last_used ON workspaces(last_used);
  `)
  return _db
}

export interface WorkspaceRow {
  id: number
  name: string
  path: string
  description: string | null
  pin_order: number | null
  last_used: string | null
  created_at: string
  updated_at: string
}

/** Add or update a workspace (path is unique) */
export function upsertWorkspace(fields: {
  name: string
  path: string
  description?: string
  pin_order?: number | null
}): WorkspaceRow {
  const db = getDb()
  db.prepare(`
    INSERT INTO workspaces (name, path, description, pin_order)
    VALUES (@name, @path, @description, @pin_order)
    ON CONFLICT(path) DO UPDATE SET
      name = excluded.name,
      description = COALESCE(excluded.description, workspaces.description),
      pin_order = COALESCE(excluded.pin_order, workspaces.pin_order),
      updated_at = datetime('now')
  `).run({
    name: fields.name,
    path: fields.path,
    description: fields.description ?? null,
    pin_order: fields.pin_order ?? null,
  })
  return db.prepare('SELECT * FROM workspaces WHERE path = ?').get(fields.path) as WorkspaceRow
}

/** List all workspaces (pinned first, then by last used) */
export function listWorkspaces(): WorkspaceRow[] {
  return getDb()
    .prepare(
      `SELECT * FROM workspaces
       ORDER BY
         pin_order IS NOT NULL DESC,
         pin_order ASC,
         last_used DESC,
         created_at DESC`,
    )
    .all() as WorkspaceRow[]
}

/** Delete a workspace */
export function deleteWorkspace(id: number): boolean {
  const r = getDb().prepare('DELETE FROM workspaces WHERE id = ?').run(id)
  return r.changes > 0
}

/** Record workspace usage time */
export function touchWorkspace(path: string) {
  getDb()
    .prepare("UPDATE workspaces SET last_used = datetime('now'), updated_at = datetime('now') WHERE path = ?")
    .run(path)
}

/** Get workspace by path */
export function getWorkspaceByPath(path: string): WorkspaceRow | undefined {
  return getDb().prepare('SELECT * FROM workspaces WHERE path = ?').get(path) as WorkspaceRow | undefined
}

/** Validate whether a path is valid (directory exists) */
export function validatePath(path: string): { valid: boolean; exists: boolean; isDirectory: boolean; error?: string } {
  try {
    const exists = existsSync(path)
    if (!exists) return { valid: false, exists: false, isDirectory: false, error: '路径不存在' }
    const stat = statSync(path)
    return { valid: true, exists: true, isDirectory: stat.isDirectory() }
  } catch (e: any) {
    return { valid: false, exists: false, isDirectory: false, error: e?.message || '验证失败' }
  }
}
