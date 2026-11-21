import test from 'node:test'
import assert from 'node:assert/strict'
import { hasAIVisualizations, imageLoadState, isSupportedImagePath, panView, resetView, zoomView } from './viewerState.js'

test('viewer reports image formats and missing-file states explicitly', () => {
  assert.equal(isSupportedImagePath('/images/case.jpg'), true)
  assert.equal(isSupportedImagePath('/images/case.PNG'), false)
  assert.equal(imageLoadState('/images/case.png'), 'unsupported')
  assert.equal(imageLoadState('/images/missing.jpg', 'error'), 'missing')
  assert.equal(imageLoadState('/images/ok.jpg', 'load'), 'ready')
  assert.equal(imageLoadState('/images/ok.jpg'), 'loading')
})

test('zoom clamps to supported range and reset restores the original view', () => {
  assert.deepEqual(zoomView(resetView(), 0.25), { scale: 1.25, x: 0, y: 0 })
  assert.equal(zoomView({ scale: 4, x: 2, y: -3 }, 0.25).scale, 4)
  assert.deepEqual(zoomView({ scale: 1.25, x: 3, y: 4 }, -0.25), resetView())
})

test('panning only changes a zoomed image', () => {
  assert.deepEqual(panView(resetView(), 12, -7), resetView())
  assert.deepEqual(panView({ scale: 2, x: 0, y: 0 }, 12, -7), { scale: 2, x: 12, y: -7 })
})

test('viewer only recognizes supplied AI visualisations', () => {
  assert.equal(hasAIVisualizations(undefined), false)
  assert.equal(hasAIVisualizations({}), false)
  assert.equal(hasAIVisualizations({ gradcam: { src: '/model/case-1-gradcam.png' } }), true)
  assert.equal(hasAIVisualizations({ detections: { boxes: [{ x: 1, y: 2, width: 3, height: 4 }] } }), true)
})
