import { useState } from 'react';

export default function ConversationView({ logs }) {
  const turns = buildTurns(logs);
  const task = logs.find(e => e.type === 'AgentStarted')?.task;
  const systemPrompt = turns.find(t => t.system)?.system || null;

  if (turns.length === 0) return <div className="empty"><p>No turn data in logs.</p></div>;

  return (
    <div className="conv">
      {task && (
        <div className="conv-row conv-row-user" style={{ marginBottom: 16 }}>
          <div className="conv-role-label">Task</div>
          <div className="conv-message"><pre className="conv-pre">{task}</pre></div>
        </div>
      )}

      {systemPrompt && <SystemPromptBlock prompt={systemPrompt} />}

      {turns.map(turn => <TurnBlock key={turn.number} turn={turn} />)}
    </div>
  );
}

/* ── System prompt ── */

function SystemPromptBlock({ prompt }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="conv-tool-call" style={{ marginBottom: 12 }}>
      <div className="conv-tool-call-header" onClick={() => setOpen(o => !o)}>
        <span className="conv-role-label" style={{ color: '#4a4f70', textAlign: 'left', textTransform: 'uppercase', fontSize: 10, letterSpacing: '0.08em' }}>System</span>
        <span className="conv-tool-name" style={{ fontSize: 12, color: '#4a4f70' }}>{prompt.length.toLocaleString()} chars</span>
        <span className="chevron">{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div className="conv-tool-section">
          <pre className="conv-pre">{prompt}</pre>
        </div>
      )}
    </div>
  );
}

/* ── Turn block ── */

function TurnBlock({ turn }) {
  const [open, setOpen] = useState(true);
  const responseText = getResponseText(turn);

  return (
    <div className="turn-block">
      <div className="turn-header" onClick={() => setOpen(o => !o)}>
        <span className="turn-label">Turn {turn.number}</span>
        {turn.modelUsed && <span className="turn-model">{turn.modelUsed}</span>}
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
        {turn.maxTokens != null && <span className="turn-stat">max {turn.maxTokens.toLocaleString()} tok</span>}
        {turn.stopReason && (
          <span className={`turn-stat ${turn.stopReason === 'end_turn' ? 'turn-stop-final' : 'turn-stop-tool'}`}>
            {turn.stopReason}
          </span>
        )}
        {turn.responseId && <span className="turn-stat" style={{ fontFamily: 'monospace', fontSize: 11 }}>{turn.responseId}</span>}
        <span className="chevron" style={{ marginLeft: 'auto' }}>{open ? '▲' : '▼'}</span>
      </div>

      {open && (
        <div className="turn-body">
          {turn.retries.map((r, i) => <RetryEvent key={i} event={r} />)}
          {turn.aborted && <AbortedEvent event={turn.aborted} />}
          {turn.contextCondensed && <CondensedEvent event={turn.contextCondensed} />}

          {turn.messages && <MessagesBlock messages={turn.messages} />}
          {turn.tools && turn.tools.length > 0 && <ToolsBlock tools={turn.tools} />}

          {responseText && (
            <div className="conv-row conv-row-assistant" style={{ marginBottom: 4 }}>
              <div className="conv-role-label">Response</div>
              <div className="conv-message">
                <pre className="conv-pre">{responseText}</pre>
              </div>
            </div>
          )}

          {turn.toolEvents.map((tool, i) => <ToolPair key={i} tool={tool} />)}
        </div>
      )}
    </div>
  );
}

function getResponseText(turn) {
  if (turn.content) {
    const text = turn.content.filter(b => b.type === 'text').map(b => b.text).join('\n');
    if (text) return text;
  }
  return turn.text || '';
}

/* ── Messages sent to LLM ── */

function MessagesBlock({ messages }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="conv-tool-call" style={{ marginBottom: 6 }}>
      <div className="conv-tool-call-header" onClick={() => setOpen(o => !o)}>
        <span style={{ fontSize: 10, fontWeight: 700, color: '#4a4f70', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Sent to LLM</span>
        <span className="conv-tool-name" style={{ fontSize: 12, color: '#4a4f70' }}>{messages.length} message{messages.length !== 1 ? 's' : ''}</span>
        <span className="chevron">{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div className="conv-tool-section" style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {messages.map((msg, i) => <MessageRow key={i} msg={msg} />)}
        </div>
      )}
    </div>
  );
}

function ToolsBlock({ tools }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="conv-tool-call" style={{ marginBottom: 6 }}>
      <div className="conv-tool-call-header" onClick={() => setOpen(o => !o)}>
        <span style={{ fontSize: 10, fontWeight: 700, color: '#4a4f70', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Tools available</span>
        <span className="conv-tool-name" style={{ fontSize: 12, color: '#4a4f70' }}>{tools.length} tool{tools.length !== 1 ? 's' : ''}</span>
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

function MessageRow({ msg }) {
  const blocks = typeof msg.content === 'string'
    ? [{ type: 'text', text: msg.content }]
    : Array.isArray(msg.content) ? msg.content : [];

  return (
    <div className={`conv-row conv-row-${msg.role}`} style={{ marginBottom: 2 }}>
      <div className="conv-role-label">{msg.role}</div>
      <div className="conv-message">
        {blocks.map((block, i) => <ContentBlock key={i} block={block} />)}
      </div>
    </div>
  );
}

/* ── Content block renderer ── */

function ContentBlock({ block }) {
  if (block.type === 'text') {
    return <pre className="conv-pre">{block.text}</pre>;
  }
  if (block.type === 'tool_use') {
    return (
      <div className="conv-inline-block conv-inline-tool-call">
        <div className="conv-inline-header">
          <span className="conv-role-label-tool">tool_use</span>
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
          <span className="conv-role-label-toolresult">tool_result</span>
          {block.is_error && <span className="badge badge-error" style={{ fontSize: 10 }}>error</span>}
        </div>
        <ToolOutput raw={raw} />
      </div>
    );
  }
  return <pre className="conv-pre">{JSON.stringify(block, null, 2)}</pre>;
}

/* ── Tool execution pair ── */

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
            {tool.duration != null && <span className="conv-turn-stat">{tool.duration.toFixed(3)}s</span>}
            {tool.is_error && <span className="badge badge-error" style={{ fontSize: 10 }}>error</span>}
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
              {tool.is_error && <span className="badge badge-error" style={{ fontSize: 10 }}>error</span>}
            </div>
            {open && <ToolOutput raw={tool.output} />}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Special events ── */

function RetryEvent({ event }) {
  return (
    <div className="turn-event turn-event-retry">
      <span className="turn-event-label">Retry {event.attempt}</span>
      <span className="turn-event-detail">{event.error_type}: {event.error}</span>
      <span className="turn-event-meta">{event.delay?.toFixed(1)}s delay · {event.layer}</span>
    </div>
  );
}

function AbortedEvent({ event }) {
  return (
    <div className="turn-event turn-event-abort">
      <span className="turn-event-label">Control flow aborted</span>
      <span className="turn-event-detail">{event.repeated_count}× identical: {event.fingerprint}</span>
    </div>
  );
}

function CondensedEvent({ event }) {
  return (
    <div className="turn-event turn-event-condensed">
      <span className="turn-event-label">Context condensed</span>
      <span className="turn-event-detail">{event.messages_before} → {event.messages_after} messages</span>
      <span className="turn-event-meta">{event.input_tokens_before?.toLocaleString()} tokens before</span>
    </div>
  );
}

/* ── Tool output renderer ── */

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

/* ── Build turn map from flat event log ── */

function buildTurns(logs) {
  const map = {};

  for (const e of logs) {
    const n = e.turn;
    if (n == null) continue;
    if (!map[n]) {
      map[n] = {
        number: n, model: '', modelUsed: '', responseId: '',
        messageCount: 0, toolCount: 0, maxTokens: null,
        system: null, messages: null, tools: null,
        inputTokens: 0, outputTokens: 0, latency: 0,
        stopReason: '', content: null, text: '',
        toolEvents: [], contextCondensed: null, retries: [], aborted: null,
      };
    }

    if (e.type === 'ModelCalled') {
      map[n].model = e.model || '';
      map[n].messageCount = e.message_count || 0;
      map[n].toolCount = e.tool_count || 0;
      map[n].maxTokens = e.max_tokens ?? null;
      if (e.system) map[n].system = e.system;
      if (e.messages) map[n].messages = e.messages;
      if (e.tools) map[n].tools = e.tools;
    }
    if (e.type === 'ModelResponded') {
      map[n].inputTokens = e.input_tokens || 0;
      map[n].outputTokens = e.output_tokens || 0;
      map[n].latency = e.latency || 0;
      map[n].stopReason = e.stop_reason || '';
      map[n].modelUsed = e.model_used || e.model || '';
      map[n].responseId = e.response_id || '';
      if (e.content) map[n].content = e.content;
    }
    if (e.type === 'TurnEnded') {
      map[n].text = e.text || '';
    }
    if (e.type === 'ToolCalled') {
      if (!map[n].toolEvents.find(t => t.tool_use_id === e.tool_use_id)) {
        map[n].toolEvents.push({
          tool_use_id: e.tool_use_id, name: e.name, input: e.input,
          output: null, is_error: false, duration: null,
        });
      }
    }
    if (e.type === 'ToolResulted') {
      const tool = map[n].toolEvents.find(t => t.tool_use_id === e.tool_use_id);
      if (tool) {
        tool.output = e.output;
        tool.is_error = e.is_error || false;
        tool.duration = e.duration ?? null;
      }
    }
    if (e.type === 'ContextCondensed') map[n].contextCondensed = e;
    if (e.type === 'RetryScheduled') map[n].retries.push(e);
    if (e.type === 'ControlFlowAborted') map[n].aborted = e;
  }

  return Object.values(map).sort((a, b) => a.number - b.number);
}
