/** Reject names that are not a single portable filename on Windows and POSIX.
 * Do not sanitize: silently changing a name can overwrite an unrelated file.
 */
export function assertSafeFilename(filename: unknown): asserts filename is string {
  if (typeof filename !== 'string' || !filename || filename === '.' || filename === '..'
      || /[\\/<>:"|?*\x00-\x1f\x7f]/.test(filename) || /[ .]$/.test(filename)) {
    throw new Error('Invalid filename: expected a portable basename')
  }

  // Windows reserves these device names even with an extension. Spaces before
  // the extension are ignored by Windows' device-name resolution.
  const deviceStem = filename.split('.')[0].replace(/[ ]+$/, '')
  if (/^(?:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³]|conin\$|conout\$|clock\$)$/i.test(deviceStem)) {
    throw new Error('Invalid filename: expected a portable basename')
  }
}
