import { useState } from 'react';

export default function ConversationView({ logs }) {
  // ModelCalled events now carry the full messages + tools sent to the LLM each turn
  const modelCalls = logs.filter(e => e.type === 'ModelCalled' && e.messages);
  const turnMeta = buildTurnMeta(logs);
  const systemPrompt = logs.find(e => e.type === 'SystemPrompt')?.content || null;

  const [selectedTurn, setSelectedTurn] = useState(
    modelCalls.length > 0 ? modelCalls[modelCalls.length - 1].turn : null
  );

  if (modelCalls.length === 0) {
    return (
      <div className="empty">
        <p>No message data — harness needs to include <code>messages</code> in <code>ModelCalled</code> events.</p>
      </div>
    );
  }

  const selected = modelCalls.find(e => e.turn === selectedTurn);
  const meta = turnMeta[selectedTurn] || {};

  return (
    <div className="conv">

      {/* System prompt */}
      <div className="conv-row conv-row-system">
        <div className="conv-role-label">System</div>
        <div className="conv-message">
          {systemPrompt
            ? <pre className="conv-pre">{systemPrompt}</pre>
            : <span className="conv-not-logged">
                Not logged — emit a <code>SystemPrompt</code> event from the harness to capture this.
              </span>
          }
        </div>
      </div>

      {/* Tools sent to LLM */}
      {selected?.tools?.length > 0 && (
        <ToolDefinitions tools={selected.tools} />
      )}

      {/* Turn selector */}
      <div className="conv-turn-selector">
        {modelCalls.map(e => (
          <button
            key={e.turn}
            className={`conv-turn-btn ${selectedTurn === e.turn ? 'conv-turn-btn-active' : ''}`}
            onClick={() => setSelectedTurn(e.turn)}
          >
            Turn {e.turn}
          </button>
        ))}
      </div>

      {/* Turn stats */}
      <div className="conv-turn-divider" style={{ paddingLeft: 0, marginBottom: 14 }}>
        {meta.model && <span className="conv-turn-stat">{meta.model}</span>}
        {meta.inputTokens > 0 && (
          <span className="conv-turn-stat">{meta.inputTokens.toLocaleString()} in · {meta.outputTokens.toLocaleString()} out</span>
        )}
        {meta.latency > 0 && <span className="conv-turn-stat">{meta.latency.toFixed(2)}s</span>}
        {meta.stopReason && <span className="conv-turn-stat conv-stop-reason">{meta.stopReason}</span>}
      </div>

      {/* Messages for selected turn */}
      {selected?.messages?.map((msg, i) => (
        <MessageBlock key={i} message={msg} />
      ))}
    </div>
  );
}

/* ── Tool definitions ── */

function ToolDefinitions({ tools }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="conv-tool-call" style={{ marginBottom: 12 }}>
      <div className="conv-tool-call-header" onClick={() => setOpen(o => !o)}>
        <span className="conv-role-label-tool">Tools</span>
        <span className="conv-tool-name">{tools.length} tool{tools.length !== 1 ? 's' : ''} available</span>
        <span className="chevron">{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div className="conv-tool-section">
          <pre className="conv-pre">{JSON.stringify(tools, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

/* ── Message block ── */

function MessageBlock({ message }) {
  const role = message.role;
  const content = message.content;
  const blocks = typeof content === 'string'
    ? [{ type: 'text', text: content }]
    : Array.isArray(content) ? content : [];

  return (
    <div className={`conv-row conv-row-${role}`}>
      <div className="conv-role-label">{role}</div>
      <div className="conv-message">
        {blocks.map((block, i) => <ContentBlock key={i} block={block} />)}
      </div>
    </div>
  );
}

function ContentBlock({ block }) {
  if (block.type === 'text') {
    return <pre className="conv-pre">{block.text}</pre>;
  }

  if (block.type === 'tool_use') {
    return (
      <div className="conv-inline-block conv-inline-tool-call">
        <div className="conv-inline-header">
          <span className="conv-role-label-tool">Tool call</span>
          <span className="conv-tool-name">{block.name}</span>
          {block.id && <span className="conv-turn-stat">{block.id}</span>}
        </div>
        {block.input && Object.keys(block.input).length > 0 && (
          <pre className="conv-pre" style={{ borderRadius: 0, border: 'none', background: '#0a0c14' }}>
            {JSON.stringify(block.input, null, 2)}
          </pre>
        )}
      </div>
    );
  }

  if (block.type === 'tool_result') {
    const raw = Array.isArray(block.content)
      ? block.content.map(c => c.text || '').join('\n')
      : (block.content || '');
    return (
      <div className={`conv-inline-block conv-inline-tool-result ${block.is_error ? 'conv-inline-tool-result-error' : ''}`}>
        <div className="conv-inline-header">
          <span className="conv-role-label-toolresult">Tool result</span>
          {block.tool_use_id && <span className="conv-turn-stat">{block.tool_use_id}</span>}
          {block.is_error && <span className="badge badge-error" style={{ fontSize: 10 }}>error</span>}
        </div>
        <ToolOutput raw={raw} />
      </div>
    );
  }

  return <pre className="conv-pre">{JSON.stringify(block, null, 2)}</pre>;
}

/* ── Tool output ── */

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
    return <pre className="conv-pre" style={{ borderRadius: 0, border: 'none', background: '#0a0c14' }}>{JSON.stringify(parsed, null, 2)}</pre>;
  } catch {
    return <pre className="conv-pre" style={{ borderRadius: 0, border: 'none', background: '#0a0c14' }}>{raw}</pre>;
  }
}

/* ── Helpers ── */

function buildTurnMeta(logs) {
  const map = {};
  for (const e of logs) {
    const n = e.turn;
    if (n == null) continue;
    if (!map[n]) map[n] = { model: '', stopReason: '', inputTokens: 0, outputTokens: 0, latency: 0 };
    if (e.type === 'ModelCalled') map[n].model = e.model || '';
    if (e.type === 'ModelResponded') {
      map[n].inputTokens = e.input_tokens || 0;
      map[n].outputTokens = e.output_tokens || 0;
      map[n].latency = e.latency || 0;
      map[n].stopReason = e.stop_reason || '';
    }
  }
  return map;
}
