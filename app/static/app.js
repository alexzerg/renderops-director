const form = document.querySelector('#investigationForm');
const button = document.querySelector('#runButton');
const progress = document.querySelector('#progress');
const result = document.querySelector('#result');
const errorBox = document.querySelector('#error');
const progressBar = document.querySelector('#progressBar');
const progressLabel = document.querySelector('#progressLabel');
const steps = [...document.querySelectorAll('.steps span')];
const shotVideo = document.querySelector('#shotVideo');
const previewStatus = document.querySelector('#previewStatus');
const previewTitle = document.querySelector('#previewTitle');
const previewDescription = document.querySelector('#previewDescription');
const previewTabs = [...document.querySelectorAll('.preview-tab')];
const recoveryWorkflow = document.querySelector('#recoveryWorkflow');
const phaseVerification = document.querySelector('#phaseVerification');
const approveCanaryButton = document.querySelector('#approveCanaryButton');
const approveRecoveryButton = document.querySelector('#approveRecoveryButton');
const canaryStep = document.querySelector('#canaryStep');
const recoveryStep = document.querySelector('#recoveryStep');
const canaryTab = document.querySelector('#canaryTab');
const recoveredTab = document.querySelector('#recoveredTab');
const continueWorkflowButton = document.querySelector('#continueWorkflowButton');
const videoToggle = document.querySelector('#videoToggle');
const videoTrack = document.querySelector('#videoTrack');
const videoProgress = document.querySelector('#videoProgress');
const videoClock = document.querySelector('#videoClock');
const previewTimecode = document.querySelector('#previewTimecode');
const artifactIndicator = document.querySelector('#artifactIndicator');
const comparisonLabels = document.querySelector('#comparisonLabels');
let activePreviewMode = 'failed';
const generatedMediaUrls = {};
const failedWindows = [[1.2, 1.72], [3.35, 4.15], [6.1, 6.58]];

const previewModes = {
  source: {
    src: '/static/media/shot-sh042-source.webm',
    poster: '/static/media/shot-sh042-source.jpg',
    status: 'ORIGINAL PLATE',
    title: 'The intended cinematic shot',
    description: 'The clean source plate contains the composition, camera move, rain, lighting, and cargo tram before final-denoise processing.',
  },
  failed: {
    src: '/static/media/shot-sh042-failed.webm',
    poster: '/static/media/shot-sh042-failed.jpg',
    status: 'FAILED RENDER',
    title: 'What the failure looks like',
    description: 'Final-denoise tiles disappear, temporal noise spikes, and several frames become unusable for editorial review.',
  },
  canary: {
    src: '/static/media/shot-sh042-canary.webm',
    poster: '/static/media/shot-sh042-canary.jpg',
    status: 'CANARY PASS',
    title: 'Same frames: failed render versus canary',
    description: 'A synchronized side-by-side comparison shows frames 1042–1046: damaged v47 output on the left and the validated v46-safe canary on the right.',
  },
  recovered: {
    src: '/static/media/shot-sh042-recovered.webm',
    poster: '/static/media/shot-sh042-recovered.jpg',
    status: 'EDITORIAL READY',
    title: 'The recovered final shot',
    description: 'All 38 failed frames have been rerendered with the validated configuration and the shot is ready for editorial review.',
  },
};

function setPreviewMode(mode) {
  const selected = previewModes[mode];
  if (!selected) return;
  shotVideo.pause();
  shotVideo.src = selected.src;
  shotVideo.poster = selected.poster;
  shotVideo.load();
  shotVideo.play().catch(() => {});
  previewStatus.textContent = selected.status;
  previewStatus.className = `viewer-status-pill ${mode}`;
  previewTitle.textContent = selected.title;
  previewDescription.textContent = selected.description;
  previewTabs.forEach(tab => tab.classList.toggle('active', tab.dataset.mode === mode));
  activePreviewMode = mode;
  videoTrack.classList.toggle('no-failures', mode !== 'failed');
  artifactIndicator.classList.add('hidden');
  comparisonLabels.classList.toggle('hidden', mode !== 'canary');
}

function formatClock(seconds) {
  const safe = Number.isFinite(seconds) ? seconds : 0;
  return `00:${String(Math.floor(safe)).padStart(2, '0')}`;
}

function updateVideoTransport() {
  const duration = Number.isFinite(shotVideo.duration) ? shotVideo.duration : 8;
  const current = Number.isFinite(shotVideo.currentTime) ? shotVideo.currentTime : 0;
  videoProgress.style.width = `${Math.min(100, current / duration * 100)}%`;
  videoClock.textContent = `${formatClock(current)} / ${formatClock(duration)}`;
  const frame = Math.floor(current * 30);
  previewTimecode.textContent = `00:00:${String(Math.floor(current)).padStart(2, '0')}:${String(frame % 30).padStart(2, '0')}`;
  const failureActive = activePreviewMode === 'failed'
    && failedWindows.some(([start, end]) => current >= start && current <= end);
  artifactIndicator.classList.toggle('hidden', !failureActive);
}

function focusShotPreview() {
  const scroll = () => {
    document.querySelector('#shotPreview').scrollIntoView({behavior: 'smooth', block: 'start'});
  };
  if (shotVideo.readyState >= 1) scroll();
  else shotVideo.addEventListener('loadedmetadata', scroll, {once: true});
  setTimeout(scroll, 850);
}

function toggleVideoPlayback() {
  if (shotVideo.paused) shotVideo.play().catch(() => {});
  else shotVideo.pause();
}

const phases = [
  ['Reading active alerts', 18],
  ['Correlating GPU metrics', 37],
  ['Finding dominant log pattern', 58],
  ['Following the critical trace', 78],
  ['Preparing the recovery decision', 94],
];

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[char]));
}

async function loadHealth() {
  try {
    const response = await fetch('/api/health');
    const health = await response.json();
    const label = health.agent_runtime === 'live'
      ? `Gemini live · Grafana ${health.grafana_transport}`
      : 'Safe demo runtime';
    document.querySelector('#runtimeLabel').textContent = label;
  } catch {
    document.querySelector('#runtimeLabel').textContent = 'Runtime unavailable';
  }
}

function renderBrief(data) {
  document.querySelector('#severity').textContent = data.status.toUpperCase();
  document.querySelector('#resultShot').textContent = data.shot_id;
  document.querySelector('#confidence').textContent = `${Math.round(data.confidence * 100)}%`;
  document.querySelector('#headline').textContent = data.headline;
  document.querySelector('#diagnosis').textContent = data.diagnosis;
  document.querySelector('#deliveryRisk').textContent = `${data.delivery_risk_minutes} min`;
  document.querySelector('#recommendedCost').textContent = data.recommended_cost_usd > 0
    ? `$${data.recommended_cost_usd.toFixed(2)}` : 'See evidence';
  document.querySelector('#avoidedCost').textContent = data.avoided_cost_usd > 0
    ? `$${data.avoided_cost_usd.toFixed(2)} · ${Math.round(data.avoided_cost_percent)}%`
    : 'Not calculated';
  document.querySelector('#approval').textContent = data.approval_required ? 'Required' : 'Not required';
  document.querySelector('#narrative').textContent = data.agent_narrative;

  document.querySelector('#evidence').innerHTML = data.evidence.map(item => `
    <div class="evidence-item">
      <i class="signal ${escapeHtml(item.signal)}"></i>
      <div><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.value)}</p></div>
    </div>
  `).join('') || '<p>No structured evidence returned; see the agent narrative.</p>';

  document.querySelector('#recovery').innerHTML = data.recovery_plan.map(item => `
    <div class="recovery-item">
      <span class="order">${item.order}</span>
      <div>
        <strong>${escapeHtml(item.action)}</strong>
        <div class="meta"><span>${escapeHtml(item.owner)}</span><span>${escapeHtml(item.risk)} risk</span>${item.requires_approval ? '<span class="gate">approval gate</span>' : ''}</div>
      </div>
    </div>
  `).join('') || '<p>Review the live agent narrative before approving any action.</p>';

  document.querySelector('#tools').innerHTML = data.tools_used
    .map(tool => `<li>${escapeHtml(tool)}</li>`).join('') || '<li>No tool calls were reported.</li>';
}

function installGeneratedMedia(data) {
  if (!data.execution || !data.execution.media_base64) return;
  const mode = data.phase === 'canary' ? 'canary' : 'recovered';
  if (generatedMediaUrls[mode]) URL.revokeObjectURL(generatedMediaUrls[mode]);
  const binary = atob(data.execution.media_base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  const blob = new Blob([bytes], {type: data.execution.media_mime});
  generatedMediaUrls[mode] = URL.createObjectURL(blob);
  previewModes[mode].src = generatedMediaUrls[mode];
}

function resetRecoveryWorkflow() {
  recoveryWorkflow.classList.add('hidden');
  phaseVerification.classList.add('hidden');
  phaseVerification.classList.remove('failed');
  canaryStep.className = 'workflow-step ready';
  canaryStep.querySelector('strong').textContent = 'Awaiting approval';
  canaryStep.querySelector('p').textContent = 'Render five frames with safe asset config';
  approveCanaryButton.disabled = false;
  approveCanaryButton.textContent = 'Approve canary';
  recoveryStep.className = 'workflow-step locked';
  recoveryStep.querySelector('strong').textContent = 'Locked';
  recoveryStep.querySelector('p').textContent = 'Requires a Grafana-validated canary';
  approveRecoveryButton.disabled = true;
  approveRecoveryButton.textContent = 'Approve 38 frames';
  canaryTab.disabled = true;
  canaryTab.classList.add('hidden');
  continueWorkflowButton.classList.add('hidden');
  recoveredTab.disabled = true;
  recoveredTab.classList.add('locked', 'hidden');
}

function renderPhaseVerification(data) {
  phaseVerification.classList.remove('hidden');
  phaseVerification.classList.toggle('failed', data.status === 'failed');
  document.querySelector('#phaseStatus').textContent = data.status.toUpperCase();
  document.querySelector('#phaseHeadline').textContent = data.headline;
  document.querySelector('#phaseGpu').textContent = `${Math.round(data.gpu_memory_before_percent)}% → ${Math.round(data.gpu_memory_after_percent)}%`;
  document.querySelector('#phaseFrames').textContent = `${data.frames_processed - data.frames_failed} / ${data.frames_processed}`;
  document.querySelector('#phaseConfidence').textContent = `${Math.round(data.confidence * 100)}%`;
  document.querySelector('#phaseExecution').textContent = data.execution
    ? `FFmpeg · ${data.execution.duration_ms} ms` : 'Unavailable';
  document.querySelector('#prometheusCheck').textContent = data.verification_checks[0] || 'No metric result';
  document.querySelector('#lokiCheck').textContent = data.verification_checks[1] || 'No log result';
  document.querySelector('#tempoCheck').textContent = data.verification_checks[2] || 'No trace result';
  document.querySelector('#ffmpegCheck').textContent = data.verification_checks[3] || 'No execution result';
  document.querySelector('#phaseSummary').textContent = data.summary;
  document.querySelector('#phaseNext').textContent = data.next_action;
  const existing = [...document.querySelectorAll('#tools li')].map(item => item.textContent);
  const combined = [...new Set([...existing, ...data.tools_used])];
  document.querySelector('#tools').innerHTML = combined.map(tool => `<li>${escapeHtml(tool)}</li>`).join('');
}

async function runRecoveryPhase(phase) {
  const isCanary = phase === 'canary';
  const actionButton = isCanary ? approveCanaryButton : approveRecoveryButton;
  const step = isCanary ? canaryStep : recoveryStep;
  actionButton.disabled = true;
  actionButton.textContent = isCanary ? 'Rendering canary…' : 'Rerendering 38 frames…';
  step.className = 'workflow-step running';
  step.querySelector('strong').textContent = 'Running and observing';
  step.querySelector('p').textContent = 'Sending OTLP telemetry to Grafana Cloud';
  errorBox.classList.add('hidden');
  try {
    const response = await fetch(isCanary ? '/api/canary' : '/api/recovery', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({shot_id: document.querySelector('#shotId').value}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `${phase} verification failed`);
    installGeneratedMedia(data);
    renderPhaseVerification(data);
    if (data.status === 'failed') {
      step.className = 'workflow-step ready';
      step.querySelector('strong').textContent = 'Verification failed';
      step.querySelector('p').textContent = 'Review the Grafana checks before retrying';
      actionButton.disabled = false;
      actionButton.textContent = isCanary ? 'Retry canary' : 'Retry recovery';
      phaseVerification.scrollIntoView({behavior: 'smooth', block: 'center'});
      return;
    }
    step.className = 'workflow-step validated';
    step.querySelector('strong').textContent = isCanary ? 'Grafana validated' : '38 / 38 restored';
    step.querySelector('p').textContent = isCanary ? '0 failures · VRAM 72% · trace passed' : 'Shot verified and editorial ready';
    actionButton.textContent = isCanary ? 'Validated ✓' : 'Completed ✓';
    if (isCanary) {
      canaryTab.disabled = false;
      canaryTab.classList.remove('hidden');
      continueWorkflowButton.classList.remove('hidden');
      setPreviewMode('canary');
      recoveryStep.className = 'workflow-step ready';
      recoveryStep.querySelector('strong').textContent = 'Awaiting approval';
      recoveryStep.querySelector('p').textContent = 'Rerender only the 38 failed frames';
      approveRecoveryButton.disabled = false;
    } else {
      canaryTab.disabled = true;
      canaryTab.classList.add('hidden');
      continueWorkflowButton.classList.add('hidden');
      recoveredTab.disabled = false;
      recoveredTab.classList.remove('locked', 'hidden');
      setPreviewMode('recovered');
      document.querySelector('#approval').textContent = 'Completed';
    }
    focusShotPreview();
  } catch (error) {
    step.className = 'workflow-step ready';
    actionButton.disabled = false;
    actionButton.textContent = isCanary ? 'Retry canary' : 'Retry recovery';
    errorBox.textContent = error.message;
    errorBox.classList.remove('hidden');
  }
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  button.disabled = true;
  result.classList.add('hidden');
  resetRecoveryWorkflow();
  setPreviewMode('failed');
  errorBox.classList.add('hidden');
  progress.classList.remove('hidden');

  let phase = 0;
  const timer = setInterval(() => {
    const [label, width] = phases[Math.min(phase, phases.length - 1)];
    progressLabel.textContent = label;
    progressBar.style.width = `${width}%`;
    steps.forEach((step, index) => step.classList.toggle('active', index <= phase));
    phase += 1;
  }, 420);

  try {
    const response = await fetch('/api/investigate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        shot_id: document.querySelector('#shotId').value,
        objective: document.querySelector('#objective').value,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Investigation failed');
    renderBrief(data);
    recoveryWorkflow.classList.remove('hidden');
    progressBar.style.width = '100%';
    progressLabel.textContent = 'Decision ready';
    setTimeout(() => {
      progress.classList.add('hidden');
      result.classList.remove('hidden');
      result.scrollIntoView({behavior: 'smooth', block: 'start'});
    }, 320);
  } catch (error) {
    progress.classList.add('hidden');
    errorBox.textContent = error.message;
    errorBox.classList.remove('hidden');
  } finally {
    clearInterval(timer);
    button.disabled = false;
  }
});

previewTabs.forEach(tab => {
  tab.addEventListener('click', () => setPreviewMode(tab.dataset.mode));
});

document.querySelector('#previewFixButton').addEventListener('click', () => {
  recoveryWorkflow.scrollIntoView({behavior: 'smooth', block: 'start'});
});
continueWorkflowButton.addEventListener('click', () => {
  recoveryWorkflow.scrollIntoView({behavior: 'smooth', block: 'start'});
});

approveCanaryButton.addEventListener('click', () => runRecoveryPhase('canary'));
approveRecoveryButton.addEventListener('click', () => runRecoveryPhase('recovery'));
videoToggle.addEventListener('click', toggleVideoPlayback);
shotVideo.addEventListener('click', toggleVideoPlayback);
shotVideo.addEventListener('timeupdate', updateVideoTransport);
shotVideo.addEventListener('loadedmetadata', updateVideoTransport);
shotVideo.addEventListener('play', () => { videoToggle.textContent = 'Pause'; });
shotVideo.addEventListener('pause', () => { videoToggle.textContent = 'Play'; });
videoTrack.addEventListener('click', event => {
  const bounds = videoTrack.getBoundingClientRect();
  const ratio = Math.min(1, Math.max(0, (event.clientX - bounds.left) / bounds.width));
  if (Number.isFinite(shotVideo.duration)) shotVideo.currentTime = ratio * shotVideo.duration;
});

videoTrack.classList.remove('no-failures');
shotVideo.play().catch(() => {});
loadHealth();
