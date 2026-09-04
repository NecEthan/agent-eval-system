import { useState } from 'react';

export default function ConversationView({ logs }) {
  const turns = buildTurns(logs);
  const task = logs.find(e => e.type === 'AgentStarted')?.task;

  if (turns.length === 0) {
    return <div className="empty"><p>No turn data in logs.</p></div>;
  }

  return (
    <div className="conv">
      {task && (
        <div className="conv-row conv-row-user" style={{ marginBottom: 16 }}>
          <div className="conv-role-label">Task</div>
          <div className="conv-message">
            <pre className="conv-pre">{task}</pre>
          </div>
        </div>
      )}

      {turns.map(turn => <TurnBlock key={turn.number} turn={turn} />)}
    </div>
  );
}

function TurnBlock({ turn }) {
  const [open, setOpen] = useState(true);

  return (
    <div className="turn-block">
      <div className="turn-header" onClick={() => setOpen(o => !o)}>
        <span className="turn-label">Turn {turn.number}</span>
        {turn.model && <span className="turn-model">{turn.model}</span>}
        {turn.messageCount > 0 && (
          <span className="turn-stat">{turn.messageCount} msg · {turn.toolCount} tools sent</span>
        )}
        {turn.inputTokens > 0 && (
          <span className="turn-stat">
            <span style={{ color: '#a0a8d0' }}>{turn.inputTokens.toLocaleString()}</span>
            {' in · '}
            <span style={{ color: '#a0a8d0' }}>{turn.outputTokens.toLocaleString()}</span>
            {' out'}
          </span>
        )}
        {turn.latency > 0 && <span className="turn-stat">{turn.latency.toFixed(2)}s</span>}
        {turn.stopReason && (
          <span className={`turn-stat ${turn.stopReason === 'end_turn' ? 'turn-stop-final' : 'turn-stop-tool'}`}>
            {turn.stopReason}
          </span>
        )}
        <span className="chevron" style={{ marginLeft: 'auto' }}>{open ? '▲' : '▼'}</span>
      </div>

      {open && (
        <div className="turn-body">
          {/* LLM response text */}
          {turn.text && (
            <div className="conv-row conv-row-assistant" style={{ marginBottom: 4 }}>
              <div className="conv-role-label">Response</div>
              <div className="conv-message">
                <pre className="conv-pre">{turn.text}</pre>
              </div>
            </div>
          )}

          {/* Tool calls + results */}
          {turn.tools.map((tool, i) => (
            <ToolPair key={i} tool={tool} />
          ))}
        </div>
      )}
    </div>
  );
}

function ToolPair({ tool }) {
  const [open, setOpen] = useState(false);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 0, marginBottom: 4 }}>
      <div />
      <div>
        <div className="conv-tool-call">
          <div className="conv-tool-call-header" onClick={() => setOpen(o => !o)}>
            <span className="conv-role-label-tool">Tool call</span>
            <span className="conv-tool-name">{tool.name}</span>
            {tool.duration != null && (
              <span className="conv-turn-stat">{tool.duration.toFixed(3)}s</span>
            )}
            {tool.is_error && (
              <span className="badge badge-error" style={{ fontSize: 10 }}>error</span>
            )}
            <span className="chevron">{open ? '▲' : '▼'}</span>
          </div>
          {open && tool.input && (
            <div className="conv-tool-section">
              <pre className="conv-pre">{JSON.stringify(tool.input, null, 2)}</pre>
            </div>
          )}
        </div>

        {tool.output != null && (
          <div className={`conv-tool-result ${tool.is_error ? 'conv-tool-result-error' : ''}`}>
            <div className="conv-tool-result-header">
              <span className="conv-role-label-toolresult">Result</span>
              {tool.is_error && (
                <span className="badge badge-error" style={{ fontSize: 10 }}>error</span>
              )}
            </div>
            {open && <ToolOutput raw={tool.output} />}
          </div>
        )}
      </div>
    </div>
  );
}

function ToolOutput({ raw }) {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (parsed.content != null) {
      return (
        <div style={{ background: '#0a0c14' }}>
          {parsed.path && (
            <div className="conv-file-path" style={{ padding: '6px 12px 0' }}>
              {parsed.path}
              {parsed.total_lines != null && (
                <span style={{ color: '#4a4f70', fontWeight: 400 }}> · {parsed.total_lines} lines</span>
              )}
            </div>
          )}
          <pre className="conv-pre conv-pre-file" style={{ border: 'none', borderRadius: 0, background: 'none', padding: '6px 12px' }}>
            {parsed.content}
          </pre>
        </div>
      );
    }
    return (
      <pre className="conv-pre" style={{ borderRadius: 0, border: 'none', background: '#0a0c14' }}>
        {JSON.stringify(parsed, null, 2)}
      </pre>
    );
  } catch {
    return (
      <pre className="conv-pre" style={{ borderRadius: 0, border: 'none', background: '#0a0c14' }}>
        {raw}
      </pre>
    );
  }
}

function buildTurns(logs) {
  const map = {};

  for (const e of logs) {
    const n = e.turn;
    if (n == null) continue;
    if (!map[n]) {
      map[n] = {
        number: n,
        model: '',
        messageCount: 0,
        toolCount: 0,
        inputTokens: 0,
        outputTokens: 0,
        latency: 0,
        stopReason: '',
        text: '',
        tools: [],
      };
    }

    if (e.type === 'ModelCalled') {
      map[n].model = e.model || '';
      map[n].messageCount = e.message_count || 0;
      map[n].toolCount = e.tool_count || 0;
    }
    if (e.type === 'ModelResponded') {
      map[n].inputTokens = e.input_tokens || 0;
      map[n].outputTokens = e.output_tokens || 0;
      map[n].latency = e.latency || 0;
      map[n].stopReason = e.stop_reason || '';
    }
    if (e.type === 'TurnEnded') {
      map[n].text = e.text || '';
    }
    if (e.type === 'ToolCalled') {
      if (!map[n].tools.find(t => t.tool_use_id === e.tool_use_id)) {
        map[n].tools.push({
          tool_use_id: e.tool_use_id,
          name: e.name,
          input: e.input,
          output: null,
          is_error: false,
          duration: null,
        });
      }
    }
    if (e.type === 'ToolResulted') {
      const tool = map[n].tools.find(t => t.tool_use_id === e.tool_use_id);
      if (tool) {
        tool.output = e.output;
        tool.is_error = e.is_error || false;
        tool.duration = e.duration ?? null;
      }
    }
  }

  return Object.values(map).sort((a, b) => a.number - b.number);
}
