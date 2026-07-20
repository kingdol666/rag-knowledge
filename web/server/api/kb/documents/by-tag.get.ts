﻿import { defineEventHandler, getQuery, createError } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import { getKnowledgeBaseYamlService } from '~/server/services/knowledge-base-yaml-service'
import { getTreeStorageAbsolutePath } from '~/server/utils/runtime-paths'

/** GET /api/kb/documents/by-tag?tag=xxx&kb_id=uuid — find documents by tag.
 *
 * Fix: previously used yamlService.listAll() which only scans top-level
 * directories, missing nested sub-KBs. Now uses treeService.metadata.folders
 * (from .tree-fs.json) which includes ALL KBs at any depth.
 *
 * Fix: tag matching is now case-insensitive to avoid misses on case mismatch.
 */
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const tag = (query.tag as string || '').trim()
  if (!tag) {
    throw createError({ statusCode: 400, statusMessage: 'tag is required' })
  }

  const treeService = await getTreeFileSystemService()
  await treeService.reloadMetadata()

  const yamlService = getKnowledgeBaseYamlService(getTreeStorageAbsolutePath())
  const tagLower = tag.toLowerCase()

  let kbId = (query.kb_id as string || '').trim()

  // Collect all KB folders from .tree-fs.json — this includes nested sub-KBs
  // that yamlService.listAll() would miss (listAll only reads top-level dirs).
  type KbFolderInfo = { id: string; path: string; name: string }
  let allKbFolders: KbFolderInfo[]

  // Access the metadata property to get all folders marked as knowledge bases
  const metadata = (treeService as any)['metadata']
  if (metadata?.folders) {
    allKbFolders = metadata.folders
      .filter((f: any) => f.isKnowledgeBase)
      .map((f: any) => ({ id: f.id, path: f.path, name: f.name }))
  } else {
    // Fallback to yamlService.listAll() if metadata is not accessible
    allKbFolders = (await yamlService.listAll()).map(kb => ({
      id: kb.id || kb.path,
      path: kb.path,
      name: kb.name,
    }))
  }

  const results: any[] = []

  if (kbId) {
    // Search single KB (and its sub-KBs if it's a parent)
    const targetKb = allKbFolders.find(kb => kb.id === kbId || kb.path === kbId)
    if (!targetKb) {
      throw createError({ statusCode: 404, statusMessage: 'Knowledge base not found' })
    }

    // Find the target KB and any sub-KBs that are nested under it
    const targetKbs = allKbFolders.filter(kb =>
      kb.id === targetKb.id ||
      kb.path === targetKb.path ||
      kb.path.startsWith(targetKb.path + '/') ||
      kb.path.startsWith(targetKb.path + '\\')
    )

    for (const kb of targetKbs) {
      const docs = await yamlService.getDocumentsByTag(kb.path, tag)
      for (const doc of docs) {
        results.push({ ...doc, kb_id: kb.id, kb_path: kb.path, kb_name: kb.name })
      }
    }
  } else {
    // Search all KBs (including nested sub-KBs)
    for (const kb of allKbFolders) {
      const docs = await yamlService.getDocumentsByTag(kb.path, tag)
      for (const doc of docs) {
        results.push({ ...doc, kb_id: kb.id, kb_path: kb.path, kb_name: kb.name })
      }
    }
  }

  // Sort by updated_at desc
  results.sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''))

  return {
    success: true,
    tag,
    kb_id: kbId || null,
    count: results.length,
    documents: results
  }
})
