import { useEffect, useState } from 'react';

export default function RunList({ onSelect }) {
  const [runs, setRuns] = useState(null);

  useEffect(() => {
    fetch('/api/runs').then(r => r.json()).then(setRuns);
  }, []);

  if (runs === null) return <div className="loading">Loading...</div>;

  if (runs.length === 0) {
    return (
      <div>
        <div className="header"><h1>Agent Eval</h1></div>
        <div className="empty">
          <h2>No runs yet</h2>
          <p>Run an eval task to see results here.</p>
        </div>
      </div>
    );
  }

  const passed = runs.filter(r => r.eval_passed).length;
  const pct = Math.round((passed / runs.length) * 100);

  return (
    <div>
      <div className="header">
        <h1>Agent Eval</h1>
        <span className="header-sub">{runs.length} run{runs.length !== 1 ? 's' : ''}</span>
      </div>

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
                <td style={{ color: '#8b949e' }}>{run.agent_id}</td>
                <td>
                  <span className={`badge ${run.eval_passed ? 'badge-pass' : 'badge-fail'}`}>
                    {run.eval_passed ? 'PASS' : 'FAIL'}
                  </span>
                </td>
                <td>
                  <span className={`badge badge-${run.run_status}`}>{run.run_status}</span>
                </td>
                <td style={{ color: '#8b949e' }}>{run.total_turns}</td>
                <td style={{ color: '#8b949e' }}>{run.total_input_tokens.toLocaleString()}</td>
                <td style={{ color: '#8b949e' }}>{run.total_output_tokens.toLocaleString()}</td>
                <td style={{ color: '#8b949e' }}>{run.run_duration.toFixed(1)}s</td>
                <td style={{ color: '#555', fontSize: 12 }}>{formatTime(run.timestamp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
}
