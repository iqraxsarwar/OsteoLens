import test from 'node:test'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'
import { caseRecords, datasetInfo, filterCases, validateManifest } from './caseLibrary.js'

test('the sample manifest has 60 unique, source-traceable image records', () => {
  assert.equal(caseRecords.length, 60)
  assert.deepEqual(validateManifest(caseRecords), [])
  assert.equal(new Set(caseRecords.map((record) => record.case_id)).size, 60)
  assert.equal(new Set(caseRecords.map((record) => record.image_id)).size, 60)
  assert.equal(new Set(caseRecords.map((record) => record.sha256)).size, 60)
  assert.equal(datasetInfo.license, 'CC BY 4.0')
  assert.equal(caseRecords.filter((record) => record.classification === 'Normal').length, 20)
  assert.equal(caseRecords.filter((record) => record.classification === 'Benign').length, 20)
  assert.equal(caseRecords.filter((record) => record.classification === 'Malignant').length, 20)
})

test('every manifest image is a real, distinct JPEG with the recorded checksum', async () => {
  const hashes = new Set()
  for (const record of caseRecords) {
    const imagePath = path.join(process.cwd(), 'public', ...record.image_path.split('/').filter(Boolean))
    const bytes = await readFile(imagePath)
    assert.equal(bytes[0], 0xff, `${record.case_id}: JPEG start marker`)
    assert.equal(bytes[1], 0xd8, `${record.case_id}: JPEG start marker`)
    assert.equal(bytes.at(-2), 0xff, `${record.case_id}: JPEG end marker`)
    assert.equal(bytes.at(-1), 0xd9, `${record.case_id}: JPEG end marker`)
    const checksum = createHash('sha256').update(bytes).digest('hex')
    assert.equal(checksum, record.sha256, `${record.case_id}: manifest checksum`)
    assert.ok(!hashes.has(checksum), `${record.case_id}: duplicate image bytes`)
    hashes.add(checksum)
  }
})

test('search and filters return matching source records', () => {
  assert.equal(filterCases(caseRecords).length, 60)
  assert.equal(filterCases(caseRecords, { classification: 'Normal' }).length, 20)
  assert.equal(filterCases(caseRecords, { query: 'IMG001350' }).length, 1)
  assert.equal(filterCases(caseRecords, { anatomy: 'Tibia' }).every((record) => record.anatomical_location.includes('Tibia')), true)
  assert.equal(filterCases(caseRecords, { source: caseRecords[0].dataset_source }).length, 60)
  const joined = filterCases(caseRecords, { classification: 'Malignant', anatomy: 'Tibia' })
  assert.ok(joined.length > 0)
  assert.ok(joined.every((record) => record.classification === 'Malignant' && record.anatomical_location.includes('Tibia')))
})

test('source narrative is explicitly unavailable instead of invented', () => {
  assert.ok(caseRecords.every((record) => record.clinical_description === null))
  assert.ok(caseRecords.every((record) => record.clinical_description_status === 'Not provided in the BTXRD metadata.'))
})
