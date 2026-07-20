/**
 * Shared state for pending permission requests (cross-HTTP-request).
 *
 * The canUseTool callback in chat.post.ts returns a Promise -> stores resolve here;
 * user clicks allow/deny in the approval dialog -> permission.post.ts resolvePending -> Promise resolves -> query continues.
 *
 * Uses globalThis to avoid losing state on Nitro HMR reload.
 */

interface PendingPermission {
  resolve: (decision: any) => void
  toolName: string
  input: Record<string, unknown>
  createdAt: number
}

type SessionMap = Map<string, PendingPermission>

const g = globalThis as any
if (!g.__claudePending) {
  g.__claudePending = new Map<string, SessionMap>()
}

export const pendingPermissions: Map<string, SessionMap> = g.__claudePending

export function addPending(
  sessionId: string,
  toolUseId: string,
  toolName: string,
  input: Record<string, unknown>,
  resolve: (decision: any) => void,
) {
  if (!pendingPermissions.has(sessionId)) {
    pendingPermissions.set(sessionId, new Map())
  }
  pendingPermissions.get(sessionId)!.set(toolUseId, {
    resolve,
    toolName,
    input,
    createdAt: Date.now(),
  })
}

export function getPending(
  sessionId: string,
  toolUseId: string,
): PendingPermission | undefined {
  return pendingPermissions.get(sessionId)?.get(toolUseId)
}

export function resolvePending(
  sessionId: string,
  toolUseId: string,
  decision: any,
): boolean {
  const session = pendingPermissions.get(sessionId)
  if (!session) return false
  const pending = session.get(toolUseId)
  if (!pending) return false
  session.delete(toolUseId)
  pending.resolve(decision)
  return true
}

/** Deny all pending requests for a session (used for disconnect/abort cleanup). */
export function denyAllPending(sessionId: string, reason = 'Operation aborted') {
  const session = pendingPermissions.get(sessionId)
  if (!session) return
  for (const [, pending] of session) {
    pending.resolve({ behavior: 'deny', message: reason })
  }
  session.clear()
}
