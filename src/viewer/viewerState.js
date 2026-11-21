export const MIN_ZOOM = 1
export const MAX_ZOOM = 4
export const ZOOM_STEP = 0.25

export function isSupportedImagePath(imagePath = '') {
  return /\.(jpe?g)$/i.test(imagePath.split(/[?#]/, 1)[0])
}

export function imageLoadState(imagePath, event) {
  if (!isSupportedImagePath(imagePath)) return 'unsupported'
  if (event === 'error') return 'missing'
  if (event === 'load') return 'ready'
  return 'loading'
}

export function zoomView(view, amount) {
  const scale = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Number((view.scale + amount).toFixed(2))))
  return scale === MIN_ZOOM ? { scale, x: 0, y: 0 } : { ...view, scale }
}

export function panView(view, deltaX, deltaY) {
  if (view.scale <= MIN_ZOOM) return view
  return { ...view, x: view.x + deltaX, y: view.y + deltaY }
}

export function resetView() {
  return { scale: MIN_ZOOM, x: 0, y: 0 }
}

export function hasAIVisualizations(visualizations) {
  return Boolean(
    visualizations?.gradcam?.src ||
    visualizations?.segmentation?.src ||
    (Array.isArray(visualizations?.detections?.boxes) && visualizations.detections.boxes.length > 0),
  )
}
