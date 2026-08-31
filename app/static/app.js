const form = document.querySelector('#investigationForm');
const button = document.querySelector('#runButton');
const progress = document.querySelector('#progress');
const result = document.querySelector('#result');
const errorBox = document.querySelector('#error');
const progressBar = document.querySelector('#progressBar');
const progressLabel = document.querySelector('#progressLabel');
const steps = [...document.querySelectorAll('.steps span')];

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
  document.querySelector('#runtimeMode').textContent = data.runtime === 'demo' ? 'Demo telemetry' : 'Gemini + MCP';
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

form.addEventListener('submit', async event => {
  event.preventDefault();
  button.disabled = true;
  result.classList.add('hidden');
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

loadHealth();
