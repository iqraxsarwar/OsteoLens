import test from 'node:test'
import assert from 'node:assert/strict'
import { findReportPassages, readPersonalReport } from './localReport.js'

test('personal TXT stays local and returns verbatim evidence with page references', async () => {
  const original = globalThis.fetch
  globalThis.fetch = () => { throw new Error('No network allowed') }
  try {
    const text = 'SYNTHETIC TEST ONLY. Biopsy was recommended for the femur lesion. No fracture is described.'
    const pages = await readPersonalReport({ name: 'synthetic.txt', size: text.length, text: async () => text })
    const answer = findReportPassages(pages, 'What does the report say about biopsy?')
    assert.equal(answer[0].text, 'Biopsy was recommended for the femur lesion.')
    assert.equal(answer[0].page, 1)
    assert.deepEqual(findReportPassages(pages, 'What about chemotherapy?'), [])
    assert.equal(findReportPassages(pages, 'Biyopsi hakkında ne yazıyor?')[0].text, answer[0].text)
  } finally { globalThis.fetch = original }
})
test('unsupported and oversized personal files are rejected before reading', async () => {
  const text = async () => { throw new Error('Should not read') }
  await assert.rejects(readPersonalReport({ name: 'private.exe', size: 12, text }), /format/)
  await assert.rejects(readPersonalReport({ name: 'private.txt', size: 6 * 1024 * 1024, text }), /size/)
})
