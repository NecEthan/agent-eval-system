import { useEffect, useState } from 'react';
import TurnTimeline from './TurnTimeline.jsx';

export default function RunDetail({ index, onBack }) {
  const [run, setRun] = useState(null);

  useEffect(() => {
    fetch(`/api/runs/${index}`).then(r => r.json()).then(setRun);
  }, [index]);

  if (!run) return <div className="loading">Loading...</div>;

  return (
    <div>
      <div className="header">
        <button className="back-btn" onClick={onBack}>← Back</button>
        <div>
          <h1>{run.task_id}</h1>
          <span className="header-sub">{run.agent_id}</span>
        </div>
        <span className={`badge ${run.eval_passed ? 'badge-pass' : 'badge-fail'}`} style={{ marginLeft: 'auto', fontSize: 14, padding: '4px 12px' }}>
          {run.eval_passed ? 'PASS' : 'FAIL'}
        </span>
      </div>

      {/* Metrics */}
      <div className="card">
        <div className="card-title">Run metrics</div>
        <div className="metrics">
          <div className="metric">
            <label>Status</label>
            <value><span className={`badge badge-${run.run_status}`}>{run.run_status}</span></value>
          </div>
          <div className="metric">
            <label>Duration</label>
            <value>{run.run_duration.toFixed(1)}<small>s</small></value>
          </div>
          <div className="metric">
            <label>Turns</label>
            <value>{run.total_turns}</value>
          </div>
          <div className="metric">
            <label>Tokens In</label>
            <value>{run.total_input_tokens.toLocaleString()}</value>
          </div>
          <div className="metric">
            <label>Tokens Out</label>
            <value>{run.total_output_tokens.toLocaleString()}</value>
          </div>
          <div className="metric">
            <label>Tool Calls</label>
            <value>{run.tool_calls.length}</value>
          </div>
        </div>
        {run.run_error && (
          <div style={{ marginTop: 12, color: '#f87171', fontSize: 13 }}>
            Error: {run.run_error}
          </div>
        )}
      </div>

      {/* Results */}
      {(() => {
        const finished = run.logs.find(e => e.type === 'AgentFinished');
        return finished?.final_text ? (
          <div className="card">
            <div className="card-title">Result</div>
            <div className="agent-text">{finished.final_text}</div>
          </div>
        ) : null;
      })()}

      {/* Turn timeline */}
      {run.logs.length > 0 && (
        <div className="card">
          <div className="card-title">Turn timeline</div>
          <TurnTimeline logs={run.logs} />
        </div>
      )}

      {/* Eval results */}
      {run.eval_commands.length > 0 && (
        <div className="card">
          <div className="card-title">Eval commands</div>
          {run.eval_commands.map((cmd, i) => (
            <EvalCommand key={i} cmd={cmd} />
          ))}
        </div>
      )}
    </div>
  );
}

function EvalCommand({ cmd }) {
  const [open, setOpen] = useState(!cmd.passed);
  const output = ((cmd.stdout || '') + (cmd.stderr || '')).trim();

  return (
    <div className="eval-cmd">
      <div className="eval-cmd-header" onClick={() => setOpen(o => !o)} style={{ cursor: 'pointer' }}>
        <span className={`badge ${cmd.passed ? 'badge-pass' : 'badge-fail'}`}>
          {cmd.passed ? 'PASS' : 'FAIL'}
        </span>
        <span className="eval-cmd-name">{cmd.command}</span>
        <span style={{ color: '#555', fontSize: 12 }}>exit {cmd.exit_code} · {cmd.duration.toFixed(1)}s</span>
        <span className="chevron">{open ? '▲' : '▼'}</span>
      </div>
      {open && output && (
        <div className="eval-output">
          <pre>{output}</pre>
        </div>
      )}
    </div>
  );
}
