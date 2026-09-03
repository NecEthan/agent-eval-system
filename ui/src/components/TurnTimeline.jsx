import { useState } from 'react';

export default function TurnTimeline({ logs }) {
  const turns = groupByTurn(logs);

  return (
    <div>
      {turns.map(turn => <Turn key={turn.num} turn={turn} />)}
    </div>
  );
}

function Turn({ turn }) {
  const [open, setOpen] = useState(false);
  const hasContent = turn.text || turn.tools.length > 0;

  return (
    <div className="turn">
      <div className="turn-header" onClick={() => hasContent && setOpen(o => !o)}>
        <span className="turn-num">Turn {turn.num}</span>
        <div className="turn-meta">
          {turn.stopReason && (
            <span className="badge badge-completed" style={{ fontSize: 11 }}>{turn.stopReason}</span>
          )}
          {turn.inputTokens > 0 && (
            <span className="turn-stat">{turn.inputTokens.toLocaleString()} in / {turn.outputTokens.toLocaleString()} out</span>
          )}
          {turn.latency > 0 && (
            <span className="turn-stat">{turn.latency.toFixed(2)}s</span>
          )}
          {turn.tools.length > 0 && (
            <span className="turn-stat">{turn.tools.length} tool call{turn.tools.length !== 1 ? 's' : ''}</span>
          )}
        </div>
        {turn.text && (
          <span className="turn-text">{turn.text}</span>
        )}
        {hasContent && <span className="chevron">{open ? '▲' : '▼'}</span>}
      </div>

      {open && (
        <div className="turn-body">
          {turn.tools.map((tool, i) => <ToolCall key={i} tool={tool} />)}
          {turn.text && (
            <div style={{ marginTop: turn.tools.length ? 12 : 0 }}>
              <div style={{ fontSize: 11, color: '#555', textTransform: 'uppercase', marginBottom: 6 }}>Agent response</div>
              <div className="agent-text">{turn.text}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ToolCall({ tool }) {
  const [open, setOpen] = useState(true);
  const { call, result } = tool;

  return (
    <div className="tool">
      <div className="tool-header" onClick={() => setOpen(o => !o)} style={{ cursor: 'pointer' }}>
        <span className={`badge ${result?.is_error ? 'badge-error' : 'badge-ok'}`}>
          {result?.is_error ? 'error' : 'ok'}
        </span>
        <span className="tool-name">{call.name}</span>
        {result?.duration != null && (
          <span style={{ fontSize: 12, color: '#555', marginLeft: 'auto' }}>{result.duration.toFixed(3)}s</span>
        )}
        <span className="chevron">{open ? '▲' : '▼'}</span>
      </div>

      {open && (
        <div className="tool-body">
          {call.input && Object.keys(call.input).length > 0 && (
            <div className="tool-section">
              <label>Input</label>
              <pre>{JSON.stringify(call.input, null, 2)}</pre>
            </div>
          )}
          {result?.output && (
            <div className="tool-section">
              <label>Output</label>
              <pre>{result.output}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function groupByTurn(logs) {
  const map = {};

  for (const event of logs) {
    const n = event.turn;
    if (n == null) continue;
    if (!map[n]) map[n] = { num: n, tools: [], text: '', stopReason: '', inputTokens: 0, outputTokens: 0, latency: 0 };

    if (event.type === 'ModelResponded') {
      map[n].inputTokens = event.input_tokens || 0;
      map[n].outputTokens = event.output_tokens || 0;
      map[n].latency = event.latency || 0;
      map[n].stopReason = event.stop_reason || '';
    }
    if (event.type === 'TurnEnded') {
      map[n].text = event.text || '';
      if (!map[n].stopReason) map[n].stopReason = event.stop_reason || '';
    }
    if (event.type === 'ToolCalled') {
      map[n].tools.push({ call: event, result: null });
    }
    if (event.type === 'ToolResulted') {
      const tool = map[n].tools.findLast(t => t.call.tool_use_id === event.tool_use_id);
      if (tool) tool.result = event;
    }
  }

  return Object.values(map).sort((a, b) => a.num - b.num);
}
