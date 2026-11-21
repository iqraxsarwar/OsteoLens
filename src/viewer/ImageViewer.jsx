import { useTranslation } from 'react-i18next'
import { useState } from 'react'
import { imageLoadState, panView, resetView, ZOOM_STEP, zoomView } from './viewerState'

const DISPLAY_MODES = [
  { id: 'original', label: 'Original X-ray' },
  { id: 'heatmap', label: 'Grad-CAM heatmap' },
  { id: 'overlay', label: 'Overlay' },
]

export default function ImageViewer({ record, analysis, analysisState, analysisError, onRunAnalysis }) {
  const { t } = useTranslation()
  const supported = imageLoadState(record.image_path) !== 'unsupported'
  const [status, setStatus] = useState(() => supported ? 'loading' : 'unsupported')
  const [view, setView] = useState(resetView)
  const [activeView, setActiveView] = useState('original')
  const [drag, setDrag] = useState(null)
  const hasGradcam = analysis?.status === 'complete'
    && Boolean(analysis.gradcam_heatmap_data_url && analysis.gradcam_overlay_data_url)
  const imageSource = activeView === 'heatmap'
    ? analysis?.gradcam_heatmap_data_url
    : activeView === 'overlay'
      ? analysis?.gradcam_overlay_data_url
      : record.image_path

  function selectView(mode) {
    setActiveView(mode)
    setView(resetView())
    setStatus(mode === 'original' ? imageLoadState(record.image_path) : 'loading')
  }

  function beginPan(event) {
    if (!event.target.closest('.image-canvas') || view.scale <= 1) return
    event.currentTarget.setPointerCapture(event.pointerId)
    setDrag({ x: event.clientX, y: event.clientY, originX: view.x, originY: view.y })
  }

  function continuePan(event) {
    if (!drag) return
    setView((current) => panView(
      { ...current, x: drag.originX, y: drag.originY },
      event.clientX - drag.x,
      event.clientY - drag.y,
    ))
  }

  return <section className="image-viewer" aria-label={t("Image viewer for {{v0}}", { v0: record.case_id })}>
    <div className="viewer-heading">
      <div className="viewer-tabs" role="tablist" aria-label={t("Image display mode")}>
        {DISPLAY_MODES.map(({ id, label }) => <button
          key={id}
          type="button"
          role="tab"
          aria-selected={activeView === id}
          className={activeView === id ? 'selected' : ''}
          disabled={id !== 'original' && !hasGradcam}
          onClick={() => selectView(id)}
        >{t(label)}</button>)}
      </div>
      <span className="mono viewer-case">{record.case_id}</span>
    </div>

    <div className="model-analysis" aria-live="polite">
      {analysisState === 'idle' && <div className="analysis-start">
        <span>{t("Run the trained ResNet-18 on this source image to generate its prediction and Grad-CAM.")}</span>
        <button type="button" onClick={onRunAnalysis}>{t("Analyze case")}</button>
      </div>}
      {analysisState === 'loading' && <div className="analysis-message" role="status">{t("Loading the checkpoint and analyzing")}{' '}{record.image_id}…</div>}
      {analysisState === 'error' && <div className="analysis-error" role="alert"><b>{t("Analysis unavailable.")}</b> {analysisError}</div>}
      {hasGradcam && <>
        <div className="prediction-row">
          <span><small>{t("MODEL PREDICTION")}</small><b>{t(analysis.prediction)}</b></span>
          <span><small>{t("UNCALIBRATED SCORE")}</small><b>{(analysis.confidence * 100).toFixed(1)}%</b></span>
          <span><small>{t("MODEL VERSION")}</small><b className="mono">{analysis.model_version}</b></span>
        </div>
        <div className="class-scores">{Object.entries(analysis.probabilities || {}).map(([label, score]) => <span key={t(label)}>{t(label)} <b>{(score * 100).toFixed(1)}%</b></span>)}</div>
        <div className="gradcam-guide">
          <b>{t('Why the model predicted {{label}}', {label:t(analysis.prediction)})}</b>
          <p>{t('Bright yellow regions contributed more to the model’s {{label}} score. Dark regions contributed less. For a Normal prediction, bright regions support the Normal class.', {label:t(analysis.prediction)})}</p>
          <div className="gradcam-scale" aria-label={t("Inferno colour scale from lower to higher relative contribution")}/>
          <div className="gradcam-scale-labels"><span>{t("Lower contribution")}</span><span>{t("Higher contribution")}</span></div>
          <p>{t("Choose Overlay to compare the colours with the X-ray. The scale is relative to this image. Colours cannot establish tumour presence, size, boundaries, or severity. The class score is uncalibrated.")}</p>
        </div>
        <p className="localization-note"><b>{t("Lesion localization:")}</b>{' '}{t("Unavailable. No separately trained and evaluated localization model is connected.")}</p>
      </>}
    </div>

    <div className={`image-stage ${view.scale > 1 ? 'zoomed' : ''}`} onPointerDown={beginPan} onPointerMove={continuePan} onPointerUp={() => setDrag(null)} onPointerCancel={() => setDrag(null)}>
      {status === 'loading' && <div className="image-message" role="status">{t("Loading")}{' '}{activeView === 'original' ? t("original BTXRD image") : t("model-generated Grad-CAM")}…</div>}
      {status === 'unsupported' && <div className="image-message image-error" role="alert">{t("Unsupported image format for")}{' '}{record.case_id}{t(". This viewer supports JPEG images.")}</div>}
      {status === 'missing' && <div className="image-message image-error" role="alert">{t("Unable to load")}{' '}{activeView === 'original' ? t("source image") : t("Grad-CAM image")}{' '}{t("for")}{' '}{record.case_id}.</div>}
      {status !== 'unsupported' && status !== 'missing' && imageSource && <div className="image-canvas" style={{ transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})` }}>
        <img key={`${record.case_id}:${activeView}:${imageSource}`} src={imageSource} alt={activeView === 'original' ? t("{{v0}} original BTXRD radiograph", { v0: record.case_id }) : t("{{v0}} model-generated {{v1}}", { v0: record.case_id, v1: activeView === 'heatmap' ? 'Grad-CAM heatmap' : 'Grad-CAM overlay' })} onLoad={() => setStatus('ready')} onError={() => setStatus('missing')} draggable="false" />
      </div>}
      {status === 'ready' && <div className="xray-label">{record.case_id} · {activeView === 'original' ? t("ORIGINAL SOURCE IMAGE") : t("MODEL-GENERATED {{v0}}", { v0: t(activeView.toUpperCase()) })}</div>}
      {status === 'ready' && <div className="image-controls"><button type="button" onClick={() => setView((current) => zoomView(current, -ZOOM_STEP))} disabled={view.scale <= 1} aria-label={t("Zoom out")}>−</button><span>{Math.round(view.scale * 100)}%</span><button type="button" onClick={() => setView((current) => zoomView(current, ZOOM_STEP))} aria-label={t("Zoom in")}>+</button><i/><button type="button" onClick={() => setView(resetView())} aria-label={t("Reset image view")}>{t("Reset")}</button></div>}
    </div>
    <div className="image-foot"><span><i/> {record.dataset_source} · {record.source_archive_path}</span><span>{record.sha256.slice(0, 12)}…</span></div>
    <div className="viewer-image-meta"><span>{t("IMAGE ID")}{' '}<b>{record.image_id}</b></span><span>{t("FORMAT")}{' '}<b>{record.image_path.split('.').pop().toUpperCase()}</b></span><span>{t("CLASS")}{' '}<b>{t(record.classification)}</b></span></div>
  </section>
}
