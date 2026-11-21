import manifest from './cases.json' with { type: 'json' }

export const caseRecords = manifest.cases
export const datasetInfo = manifest.dataset

export function filterCases(records, { query = '', classification = 'All classes', anatomy = 'All locations', source = 'All sources' } = {}) {
  const q = query.trim().toLowerCase()
  return records.filter((record) => {
    const matchesSearch = !q || [
      record.case_id,
      record.image_id,
      record.classification,
      record.source_subtype,
      ...record.anatomical_location,
      record.dataset_source,
    ].filter(Boolean).join(' ').toLowerCase().includes(q)
    const matchesClass = classification === 'All classes' || record.classification === classification
    const matchesAnatomy = anatomy === 'All locations' || record.anatomical_location.includes(anatomy)
    const matchesSource = source === 'All sources' || record.dataset_source === source
    return matchesSearch && matchesClass && matchesAnatomy && matchesSource
  })
}

export function validateManifest(records) {
  const errors = []
  const ids = new Set()
  const hashes = new Set()
  for (const record of records) {
    if (!record.case_id || ids.has(record.case_id)) errors.push(`Missing or duplicate case ID: ${record.case_id || '(empty)'}`)
    ids.add(record.case_id)
    if (!record.image_path || !record.image_id || !record.source_url || !record.source_archive_path) errors.push(`Incomplete source/image provenance: ${record.case_id}`)
    if (!record.sha256 || hashes.has(record.sha256)) errors.push(`Missing or duplicate image checksum: ${record.case_id}`)
    hashes.add(record.sha256)
    if (!['Normal', 'Benign', 'Malignant'].includes(record.classification)) errors.push(`Unsupported source classification: ${record.case_id}`)
    if (record.clinical_description !== null) errors.push(`Unexpected free-text clinical description: ${record.case_id}`)
  }
  return errors
}
