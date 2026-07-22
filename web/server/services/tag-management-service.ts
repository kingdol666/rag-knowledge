/**
 * Tag Management Service
 *
 * Maintains a global tag registry at `.tags.json` under the tree storage
 * root. Tags are plain strings (trimmed, case-sensitive, max 50 chars).
 * The registry is the single source of truth for "which tags exist" —
 * individual documents store their own `tags: string[]` inside
 * `.knowledge-base.yml`.
 */
import { promises as fs } from 'fs'
import { join } from 'path'
import { getTreeStorageAbsolutePath } from '~/server/utils/runtime-paths'
import { writeJsonAtomic } from '~/server/utils/atomic-write'

const TAGS_FILENAME = '.tags.json'

interface TagsRegistry {
  tags: string[]
  updated_at: string
}

export class TagManagementService {
  private basePath: string
  private filePath: string
  private cache: TagsRegistry | null = null

  constructor(basePath?: string) {
    this.basePath = basePath || getTreeStorageAbsolutePath()
    this.filePath = join(this.basePath, TAGS_FILENAME)
  }

  private async load(): Promise<TagsRegistry> {
    if (this.cache) return this.cache
    try {
      const raw = await fs.readFile(this.filePath, 'utf-8')
      this.cache = JSON.parse(raw) as TagsRegistry
    } catch {
      this.cache = { tags: [], updated_at: new Date().toISOString() }
    }
    return this.cache
  }

  private async save(): Promise<void> {
    if (!this.cache) return
    this.cache.updated_at = new Date().toISOString()
    await writeJsonAtomic(this.filePath, this.cache)
  }

  /** Return all registered tags, excluding garbage patterns by default.
   *  Pass { includeGarbage: true } to get the raw registry (for admin/debug). */
  async listTags(options?: { includeGarbage?: boolean }): Promise<string[]> {
    const reg = await this.load()
    if (options?.includeGarbage) return [...reg.tags]
    // K3 fix: filter test-residue / section-heading / garbage tags at read time
    return reg.tags.filter(t => !TagManagementService.isGarbageTag(t))
  }

  /** Remove a tag from the registry. */
  async removeTag(tag: string): Promise<void> {
    const reg = await this.load()
    const idx = reg.tags.indexOf(tag.trim())
    if (idx >= 0) {
      reg.tags.splice(idx, 1)
      await this.save()
    }
  }

  /** Rebuild the registry by scanning all .knowledge-base.yml files (garbage-filtered). */
  async rebuildTags(): Promise<string[]> {
    const { KnowledgeBaseYamlService } = await import('~/server/services/knowledge-base-yaml-service')
    const yamlService = new KnowledgeBaseYamlService(this.basePath)
    const allTags = await yamlService.getAllTags()
    const cleanTags = allTags.filter(t => !TagManagementService.isGarbageTag(t))
    this.cache = { tags: cleanTags, updated_at: new Date().toISOString() }
    await this.save()
    return cleanTags
  }

  /** K3 fix: remove tags not referenced by any document (orphan cleanup).
   *  Scans all .knowledge-base.yml once for live tags, then prunes the registry. */
  async removeOrphanTags(): Promise<{ removed: string[]; kept: string[] }> {
    const { KnowledgeBaseYamlService } = await import('~/server/services/knowledge-base-yaml-service')
    const yamlService = new KnowledgeBaseYamlService(this.basePath)
    const liveTags = new Set(await yamlService.getAllTags())
    const reg = await this.load()
    const removed: string[] = []
    const kept: string[] = []
    for (const tag of reg.tags) {
      if (liveTags.has(tag) && !TagManagementService.isGarbageTag(tag)) {
        kept.push(tag)
      } else {
        removed.push(tag)
      }
    }
    this.cache = { tags: kept, updated_at: new Date().toISOString() }
    await this.save()
    return { removed, kept }
  }

  /** Validate a tags array: must be string[], each trim non-empty <= 50. */
  static validateTags(tags: any): string[] | null {
    if (!Array.isArray(tags)) return null
    const clean: string[] = []
    for (const t of tags) {
      if (typeof t !== 'string') return null
      const trimmed = t.trim()
      if (!trimmed || trimmed.length > 50) return null
      clean.push(trimmed)
    }
    return clean
  }

  // ── T1 garbage-pattern blocker (prevents chapter-heading / test-artifact
  //     / structural-word tags from ever entering the tag registry) ──

  /** Patterns that indicate a tag is garbage (section heading, test artifact, etc).
   *  Returns true if the tag should be REJECTED at the registry gate. */
  static isGarbageTag(tag: string): boolean {
    const s = tag.trim()
    if (!s || s.length > 50) return true

    // T1a: section-heading patterns — starts with digit(s) + dot/space + word
    if (/^\d+(\.\d+)*\s/.test(s)) return true

    // T1a: standard paper-structure words (case-insensitive)
    const headingWords = [
      'abstract', 'introduction', 'method', 'methods',
      'results', 'discussion', 'conclusion', 'conclusions',
      'references', 'acknowledgments', 'acknowledgements',
      'keywords', 'appendix', 'limitations',
      '摘要', '关键词', '附录', '引言', '绪论',
    ]
    if (headingWords.includes(s.toLowerCase())) return true

    // T1a: truncated headings (ends abruptly with a space-word fragment)
    if (/^[A-Z]\w+\s+[A-Z]\w*\s*$/.test(s) && s.length < 25) return true

    // T1b: test-artifact patterns
    if (/\b(test|demo|debug|scratch|tmp)\b/i.test(s)) return true
    if (s.startsWith('test-') || s.endsWith('-test') ||
        s.startsWith('mcp-') || s.startsWith('batch-') ||
        s.startsWith('graph-')) return true

    // T1c: meta / status tags (not content tags)
    const metaWords = ['完整版', '基线对比', '拆分测试',
      '文件名内容不匹配', '待补', '未验证', 'e2e', 'verification']
    if (metaWords.includes(s)) return true

    // T1d: contains special characters (not word chars, spaces, hyphens)
    if (/[!@#$%^&*()=+[\]{}|;:'",<>?/\\~`]/.test(s)) return true

    // Truncation smell: ends with a space then truncated word
    if (/\s[a-zA-Z]{1,4}$/.test(s) && s.length < 22) return true

    return false
  }

  /** Add a single tag (dedup, trim, garbage-filter). No-op if garbage or already present. */
  async addTag(tag: string): Promise<void> {
    const clean = tag.trim()
    if (!clean || clean.length > 50 || TagManagementService.isGarbageTag(clean)) return
    const reg = await this.load()
    if (!reg.tags.includes(clean)) {
      reg.tags.push(clean)
      await this.save()
    }
  }

  /** Ensure all tags in the list exist in the registry (garbage-filtered). */
  async ensureTags(tags: string[]): Promise<void> {
    if (!tags || tags.length === 0) return
    const reg = await this.load()
    let changed = false
    for (const t of tags) {
      const clean = t.trim()
      if (!clean || clean.length > 50 || TagManagementService.isGarbageTag(clean)) continue
      if (!reg.tags.includes(clean)) {
        reg.tags.push(clean)
        changed = true
      }
    }
    if (changed) await this.save()
  }
}

let _instance: TagManagementService | null = null
export function getTagManagementService(): TagManagementService {
  if (!_instance) _instance = new TagManagementService()
  return _instance
}
