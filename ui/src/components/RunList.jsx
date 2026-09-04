import { useEffect, useRef, useState } from 'react';

function slugify(text) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50);
}

const DEFAULT_FORM = {
  description: '',
  codebasePath: '',
  evalCommands: 'python -m pytest tests/',
  agentId: 'agent-v1',
  taskId: '',
  taskIdManual: false,
};

export default function RunList({ onSelect }) {
  const [runs, setRuns] = useState(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState(null);
  const [harnessConfigured, setHarnessConfigured] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(DEFAULT_FORM);
  const pollRef = useRef(null);

  const loadRuns = () =>
    fetch('/api/runs').then(r => r.json()).then(setRuns);

  const loadStatus = () =>
    fetch('/api/run/status').then(r => r.json()).then(s => {
      setRunning(s.running);
      setHarnessConfigured(s.harness_configured);
    });

  useEffect(() => {
    loadRuns();
    loadStatus();
  }, []);

  useEffect(() => {
    if (running) {
      const startedAt = Date.now();
      pollRef.current = setInterval(async () => {
        if (Date.now() - startedAt > 30_000) {
          clearInterval(pollRef.current);
          setRunning(false);
          setRunError('Timed out after 30s — harness may have failed to start.');
          return;
        }
        const s = await fetch('/api/run/status').then(r => r.json());
        setRunning(s.running);
        if (!s.running) {
          clearInterval(pollRef.current);
          setRunError(s.error);
          loadRuns();
        }
      }, 1500);
    }
    return () => clearInterval(pollRef.current);
  }, [running]);

  const handleDescriptionChange = (e) => {
    const desc = e.target.value;
    setForm(f => ({
      ...f,
      description: desc,
      taskId: f.taskIdManual ? f.taskId : slugify(desc),
    }));
  };

  const handleTaskIdChange = (e) => {
    setForm(f => ({ ...f, taskId: e.target.value, taskIdManual: true }));
  };

  const setField = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }));

  const isValid = form.description.trim() && form.codebasePath.trim() && form.evalCommands.trim();

  const handleRun = async () => {
    setRunError(null);
    const evalCommands = form.evalCommands.split('\n').map(s => s.trim()).filter(Boolean);
    const body = {
      description: form.description.trim(),
      codebase_path: form.codebasePath.trim(),
      eval_commands: evalCommands,
      agent_id: form.agentId.trim() || 'agent-v1',
      task_id: form.taskId || slugify(form.description),
    };
    const resp = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (resp.ok) {
      setRunning(true);
      setShowForm(false);
      setForm(DEFAULT_FORM);
    } else {
      const err = await resp.json();
      setRunError(err.detail);
    }
  };

  const toggleForm = () => {
    setShowForm(f => !f);
    setRunError(null);
  };

  if (runs === null) return <div className="loading">Loading...</div>;

  const passed = runs.filter(r => r.eval_passed).length;
  const pct = runs.length > 0 ? Math.round((passed / runs.length) * 100) : 0;

  return (
    <div>
      <div className="header">
        <h1>Agent Eval</h1>
        <span className="header-sub">{runs.length} run{runs.length !== 1 ? 's' : ''}</span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
          {runError && <span style={{ color: '#f87171', fontSize: 12 }}>{runError}</span>}
          {harnessConfigured && (
            running ? (
              <button className="run-btn run-btn-running" disabled>
                <span className="run-spinner" /> Running…
              </button>
            ) : (
              <button className="run-btn" onClick={toggleForm}>
                {showForm ? '✕ Cancel' : '▶ New Run'}
              </button>
            )
          )}
        </div>
      </div>

      {showForm && !running && (
        <div className="new-run-form">
          <div className="form-row">
            <label className="form-label">Task prompt</label>
            <textarea
              className="form-textarea"
              placeholder="Describe what the agent should do…"
              value={form.description}
              onChange={handleDescriptionChange}
              rows={3}
            />
          </div>

          <div className="form-row">
            <label className="form-label">Codebase path</label>
            <input
              className="form-input"
              type="text"
              placeholder="/absolute/path/to/your/codebase"
              value={form.codebasePath}
              onChange={setField('codebasePath')}
            />
            <div className="form-hint">Absolute path on disk. Copied into an isolated working directory before the run.</div>
          </div>

          <div className="form-row">
            <label className="form-label">Eval commands</label>
            <textarea
              className="form-textarea form-textarea-mono"
              placeholder="python -m pytest tests/"
              value={form.evalCommands}
              onChange={setField('evalCommands')}
              rows={3}
            />
            <div className="form-hint">One command per line. All must exit 0 to pass.</div>
          </div>

          <div className="form-row-2">
            <div>
              <label className="form-label">Agent ID</label>
              <input
                className="form-input"
                type="text"
                placeholder="agent-v1"
                value={form.agentId}
                onChange={setField('agentId')}
              />
            </div>
            <div>
              <label className="form-label">Task ID</label>
              <input
                className="form-input"
                type="text"
                placeholder="auto"
                value={form.taskId}
                onChange={handleTaskIdChange}
              />
              <div className="form-hint">Auto-generated from prompt. Used as folder name in tasks/.</div>
            </div>
          </div>

          <div className="form-actions">
            <button className="run-btn" onClick={handleRun} disabled={!isValid}>
              ▶ Run
            </button>
            <button className="back-btn" onClick={toggleForm}>Cancel</button>
          </div>
        </div>
      )}

      {runs.length === 0 ? (
        <div className="empty">
          <h2>No runs yet</h2>
          <p>{harnessConfigured ? 'Click New Run to start your first eval.' : 'Run an eval task from the CLI to see results here.'}</p>
        </div>
      ) : (
        <>
          <div className="pass-rate">
            <div className="pass-rate-bar">
              <div className="pass-rate-fill" style={{ width: `${pct}%` }} />
            </div>
            <span className="pass-rate-label">{passed}/{runs.length} passed ({pct}%)</span>
          </div>

          <div className="card" style={{ padding: 0 }}>
            <table className="run-table">
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Agent</th>
                  <th>Result</th>
                  <th>Status</th>
                  <th>Turns</th>
                  <th>Tokens In</th>
                  <th>Tokens Out</th>
                  <th>Time</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.index} onClick={() => onSelect(run.index)}>
                    <td style={{ fontWeight: 600 }}>{run.task_id}</td>
                    <td>{run.agent_id}</td>
                    <td>
                      <span className={`badge ${run.eval_passed ? 'badge-pass' : 'badge-fail'}`}>
                        {run.eval_passed ? 'PASS' : 'FAIL'}
                      </span>
                    </td>
                    <td>
                      <span className={`badge badge-${run.run_status}`}>{run.run_status}</span>
                    </td>
                    <td>{run.total_turns}</td>
                    <td>{run.total_input_tokens.toLocaleString()}</td>
                    <td>{run.total_output_tokens.toLocaleString()}</td>
                    <td>{run.run_duration.toFixed(1)}s</td>
                    <td style={{ fontSize: 12 }}>{formatTime(run.timestamp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
}
