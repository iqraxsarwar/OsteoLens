// Pure on-device retrieval. No network or persistent-storage API.
const stopWords = new Set('what does this the a an in is are of to and for about say report please explain hangi nedir bu bir ve ile için rapor raporda'.split(' '))
const tokens = text => (text.toLocaleLowerCase('tr').match(/[\p{L}\p{N}]+/gu) || []).filter(word => word.length > 2 && !stopWords.has(word))
export function reportPassages(pages) {
  return pages.flatMap(page => page.text.split(/\n+|(?<=[.!?])\s+/u).map(text => ({ page: page.page, text: text.trim() })).filter(item => item.text.length > 8))
}
export function findReportPassages(pages, question) {
  const query = new Set(tokens(question))
  const groups = [
    ['diagnosis', 'diagnostic', 'diagnosed', 'tanı', 'tanısı', 'impression', 'conclusion'],
    ['biopsy', 'biyopsi', 'histology', 'histopathology', 'pathology', 'patoloji'],
    ['findings', 'finding', 'bulgu', 'bulgular', 'bulguları'],
    ['location', 'located', 'yer', 'bölge', 'anatomical', 'femur', 'tibia', 'humerus', 'pelvis'],
    ['follow', 'recommendation', 'recommend', 'takip', 'öneri', 'önerilen'],
  ]
  for (const group of groups) if (group.some(word => query.has(word))) group.forEach(word => query.add(word))
  const passages = reportPassages(pages)
  if (/\b(summary|summarise|summarize|özet|özetle)\b/iu.test(question)) return passages.slice(0, 5)
  return passages.map(item => ({ ...item, score: tokens(item.text).filter(word => query.has(word)).length }))
    .filter(item => item.score > 0).sort((a, b) => b.score - a.score).slice(0, 5)
}
export async function readPersonalReport(file, { signal } = {}) {
  signal?.throwIfAborted()
  if (file.size > 5 * 1024 * 1024) throw new Error('size')
  if (/\.pdf$/i.test(file.name)) {
    // Lazy imports keep the parser and same-origin worker out of the main bundle.
    const pdfjs = await import('pdfjs-dist/build/pdf.mjs')
    const { default: workerUrl } = await import('pdfjs-dist/build/pdf.worker.mjs?url')
    pdfjs.GlobalWorkerOptions.workerSrc = workerUrl
    const task = pdfjs.getDocument({ data: new Uint8Array(await file.arrayBuffer()), isEvalSupported: false, useSystemFonts: true, disableFontFace: true, useWasm: false })
    const cancel = () => { task.destroy() }
    signal?.addEventListener('abort', cancel, { once: true })
    // Reject encrypted files without collecting a password or waiting forever.
    let rejectPassword
    const passwordFailure = new Promise((_resolve, reject) => { rejectPassword = reject })
    task.onPassword = () => rejectPassword(new Error('encrypted'))
    try {
      const document = await Promise.race([task.promise, passwordFailure])
      signal?.throwIfAborted()
      if (document.numPages > 80) throw new Error('pages')
      const pages = []
      let length = 0
      for (let number = 1; number <= document.numPages; number++) {
        signal?.throwIfAborted()
        const page = await document.getPage(number)
        const content = await page.getTextContent()
        const text = content.items.map(item => item.str + (item.hasEOL ? '\n' : ' ')).join('')
        length += text.length
        if (length > 500000) throw new Error('text-limit')
        pages.push({ page: number, text }); page.cleanup()
      }
      if (!pages.some(page => page.text.trim())) throw new Error('scanned')
      return pages
    } finally { signal?.removeEventListener('abort', cancel); await task.destroy() }
  }
  if (!/\.txt$/i.test(file.name)) throw new Error('format')
  const text = await file.text()
  signal?.throwIfAborted()
  if (!text.trim() || text.includes('\u0000')) throw new Error('text')
  return [{ page: 1, text }]
}
