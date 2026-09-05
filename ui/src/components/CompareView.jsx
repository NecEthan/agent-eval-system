import { useEffect, useState } from 'react';

export default function CompareView({ indices, onBack }) {
  const [runs, setRuns] = useState([null, null]);

  useEffect(() => {
    Promise.all(indices.map(i => fetch(`/api/runs/${i}`).then(r => r.json())))
      .then(([a, b]) => setRuns([a, b]));
  }, [indices]);

  if (!runs[0] || !runs[1]) return <div className="loading">Loading...</div>;

  const [a, b] = runs;

  return (
    <div>
      <div className="header">
        <button className="back-btn" onClick={onBack}>← Back</button>
        <h1>Compare Runs</h1>
      </div>

      {/* Identity rows */}
      <div className="cmp-grid">
        <div className="cmp-panel">
          <div className="cmp-run-title">{a.task_id}</div>
          <div className="cmp-run-sub">{a.agent_id} · {fmt(a.timestamp)}</div>
          <span className={`badge ${a.eval_passed ? 'badge-pass' : 'badge-fail'}`} style={{ marginTop: 6, display: 'inline-block' }}>
            {a.eval_passed ? 'PASS' : 'FAIL'}
          </span>
        </div>
        <div className="cmp-panel">
          <div className="cmp-run-title">{b.task_id}</div>
          <div className="cmp-run-sub">{b.agent_id} · {fmt(b.timestamp)}</div>
          <span className={`badge ${b.eval_passed ? 'badge-pass' : 'badge-fail'}`} style={{ marginTop: 6, display: 'inline-block' }}>
            {b.eval_passed ? 'PASS' : 'FAIL'}
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div className="cmp-section-label">Metrics</div>
      <div className="cmp-grid">
        <MetricsPanel run={a} other={b} />
        <MetricsPanel run={b} other={a} />
      </div>

      {/* Eval commands */}
      <div className="cmp-section-label">Eval commands</div>
      <div className="cmp-grid">
        <EvalPanel run={a} />
        <EvalPanel run={b} />
      </div>

      {/* Turn summary */}
      <div className="cmp-section-label">Turns</div>
      <div className="cmp-grid">
        <TurnPanel run={a} />
        <TurnPanel run={b} />
      </div>
    </div>
  );
}

function MetricsPanel({ run, other }) {
  const rows = [
    { label: 'Status',     a: run.run_status,                    b: other.run_status },
    { label: 'Duration',   a: run.run_duration.toFixed(1) + 's', b: other.run_duration.toFixed(1) + 's', numA: run.run_duration,       numB: other.run_duration,       lowerBetter: true },
    { label: 'Turns',      a: run.total_turns,                   b: other.total_turns,                   numA: run.total_turns,        numB: other.total_turns,        lowerBetter: true },
    { label: 'Tokens in',  a: run.total_input_tokens.toLocaleString(),  b: other.total_input_tokens.toLocaleString(),  numA: run.total_input_tokens,  numB: other.total_input_tokens,  lowerBetter: true },
    { label: 'Tokens out', a: run.total_output_tokens.toLocaleString(), b: other.total_output_tokens.toLocaleString(), numA: run.total_output_tokens, numB: other.total_output_tokens, lowerBetter: true },
    { label: 'Tool calls', a: run.tool_calls.length,             b: other.tool_calls.length,             numA: run.tool_calls.length,  numB: other.tool_calls.length,  lowerBetter: true },
  ];

  return (
    <div className="cmp-panel">
      {rows.map(row => {
        const hasCmp = row.numA != null;
        let highlight = null;
        if (hasCmp) {
          if (row.lowerBetter) highlight = row.numA < row.numB ? 'better' : row.numA > row.numB ? 'worse' : null;
          else highlight = row.numA > row.numB ? 'better' : row.numA < row.numB ? 'worse' : null;
        }
        return (
          <div key={row.label} className="cmp-metric-row">
            <span className="cmp-metric-label">{row.label}</span>
            <span className={`cmp-metric-value ${highlight ? `cmp-${highlight}` : ''}`}>{row.a}</span>
          </div>
        );
      })}
    </div>
  );
}

function EvalPanel({ run }) {
  return (
    <div className="cmp-panel">
      {run.eval_commands.length === 0 ? (
        <span className="cmp-empty">No eval commands</span>
      ) : run.eval_commands.map((cmd, i) => (
        <div key={i} className="cmp-eval-row">
          <span className={`badge ${cmd.passed ? 'badge-pass' : 'badge-fail'}`}>{cmd.passed ? 'PASS' : 'FAIL'}</span>
          <span className="cmp-eval-cmd">{cmd.command}</span>
          <span className="cmp-eval-dur">{cmd.duration.toFixed(1)}s</span>
        </div>
      ))}
    </div>
  );
}

function TurnPanel({ run }) {
  const turnEvents = buildTurnSummary(run.logs);
  if (turnEvents.length === 0) return <div className="cmp-panel"><span className="cmp-empty">No turn data</span></div>;

  return (
    <div className="cmp-panel" style={{ padding: 0 }}>
      <table className="cmp-turn-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Tokens in</th>
            <th>Tokens out</th>
            <th>Duration</th>
            <th>Stop</th>
          </tr>
        </thead>
        <tbody>
          {turnEvents.map(t => (
            <tr key={t.turn}>
              <td>{t.turn}</td>
              <td>{t.inputTokens.toLocaleString()}</td>
              <td>{t.outputTokens.toLocaleString()}</td>
              <td>{t.latency.toFixed(2)}s</td>
              <td className={t.stopReason === 'end_turn' ? 'cmp-stop-final' : 'cmp-stop-tool'}>{t.stopReason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function buildTurnSummary(logs) {
  const map = {};
  for (const e of logs) {
    if (e.turn == null) continue;
    if (!map[e.turn]) map[e.turn] = { turn: e.turn, inputTokens: 0, outputTokens: 0, latency: 0, stopReason: '' };
    if (e.type === 'ModelResponded') {
      map[e.turn].inputTokens = e.input_tokens || 0;
      map[e.turn].outputTokens = e.output_tokens || 0;
      map[e.turn].latency = e.latency || 0;
      map[e.turn].stopReason = e.stop_reason || '';
    }
  }
  return Object.values(map).sort((a, b) => a.turn - b.turn);
}

function fmt(iso) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
}
