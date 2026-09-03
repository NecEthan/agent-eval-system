import { useEffect, useRef, useState } from 'react';

export default function RunList({ onSelect }) {
  const [runs, setRuns] = useState(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState(null);
  const [harnessConfigured, setHarnessConfigured] = useState(false);
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

  // Poll while a run is in progress, timeout after 30s
  useEffect(() => {
    if (running) {
      const startedAt = Date.now();
      pollRef.current = setInterval(async () => {
        if (Date.now() - startedAt > 30_000) {
          clearInterval(pollRef.current);
          setRunning(false);
          setRunError('Timed out after 30s — harness may have failed to start. Check port 8000 is free.');
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

  const handleRun = async () => {
    setRunError(null);
    const resp = await fetch('/api/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
    if (resp.ok) {
      setRunning(true);
    } else {
      const err = await resp.json();
      setRunError(err.detail);
    }
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
            <button
              className={`run-btn ${running ? 'run-btn-running' : ''}`}
              onClick={handleRun}
              disabled={running}
            >
              {running ? (
                <><span className="run-spinner" /> Running…</>
              ) : '▶ Run'}
            </button>
          )}
        </div>
      </div>

      {runs.length === 0 ? (
        <div className="empty">
          <h2>No runs yet</h2>
          <p>{harnessConfigured ? 'Click Run to start your first eval.' : 'Run an eval task from the CLI to see results here.'}</p>
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
