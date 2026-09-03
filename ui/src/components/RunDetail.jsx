import { useEffect, useState } from 'react';
import ConversationView from './ConversationView.jsx';

export default function RunDetail({ index, onBack }) {
  const [run, setRun] = useState(null);
  const [tab, setTab] = useState('conversation');

  useEffect(() => {
    fetch(`/api/runs/${index}`).then(r => r.json()).then(setRun);
  }, [index]);

  if (!run) return <div className="loading">Loading...</div>;

  return (
    <div>
      {/* Header */}
      <div className="header">
        <button className="back-btn" onClick={onBack}>← Back</button>
        <div>
          <h1>{run.task_id}</h1>
          <span className="header-sub">{run.agent_id} · {new Date(run.timestamp).toLocaleString()}</span>
        </div>
        <span className={`badge ${run.eval_passed ? 'badge-pass' : 'badge-fail'}`} style={{ marginLeft: 'auto', fontSize: 14, padding: '5px 14px' }}>
          {run.eval_passed ? 'PASS' : 'FAIL'}
        </span>
      </div>

      {/* Metrics strip */}
      <div className="metrics-strip">
        <Metric label="Status" value={<span className={`badge badge-${run.run_status}`}>{run.run_status}</span>} />
        <Metric label="Duration" value={`${run.run_duration.toFixed(1)}s`} />
        <Metric label="Turns" value={run.total_turns} />
        <Metric label="Tokens in" value={run.total_input_tokens.toLocaleString()} />
        <Metric label="Tokens out" value={run.total_output_tokens.toLocaleString()} />
        <Metric label="Tool calls" value={run.tool_calls.length} />
      </div>

      {/* Tabs */}
      <div className="tabs">
        {['conversation', 'eval'].map(t => (
          <button key={t} className={`tab-btn ${tab === t ? 'tab-btn-active' : ''}`} onClick={() => setTab(t)}>
            {t === 'conversation' ? 'Conversation' : `Eval (${run.eval_commands.length})`}
          </button>
        ))}
      </div>

      {/* Conversation tab */}
      {tab === 'conversation' && (
        <ConversationView logs={run.logs} />
      )}

      {/* Eval tab */}
      {tab === 'eval' && (
        <div>
          {run.eval_commands.length === 0 ? (
            <div className="empty"><p>No eval commands.</p></div>
          ) : (
            run.eval_commands.map((cmd, i) => <EvalCommand key={i} cmd={cmd} />)
          )}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metrics-strip-item">
      <div className="metrics-strip-label">{label}</div>
      <div className="metrics-strip-value">{value}</div>
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
        <span style={{ color: '#4a4f70', fontSize: 12 }}>exit {cmd.exit_code} · {cmd.duration.toFixed(1)}s</span>
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
