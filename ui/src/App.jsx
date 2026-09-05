import { useState } from 'react';
import RunList from './components/RunList.jsx';
import RunDetail from './components/RunDetail.jsx';
import CompareView from './components/CompareView.jsx';

export default function App() {
  const [view, setView] = useState({ type: 'list' });

  return (
    <div className="layout">
      {view.type === 'list' && (
        <RunList
          onSelect={i => setView({ type: 'detail', index: i })}
          onCompare={indices => setView({ type: 'compare', indices })}
        />
      )}
      {view.type === 'detail' && (
        <RunDetail index={view.index} onBack={() => setView({ type: 'list' })} />
      )}
      {view.type === 'compare' && (
        <CompareView indices={view.indices} onBack={() => setView({ type: 'list' })} />
      )}
    </div>
  );
}
