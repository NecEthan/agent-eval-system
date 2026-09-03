import { useState } from 'react';
import RunList from './components/RunList.jsx';
import RunDetail from './components/RunDetail.jsx';

export default function App() {
  const [selectedRun, setSelectedRun] = useState(null);

  return (
    <div className="layout">
      {selectedRun === null ? (
        <RunList onSelect={setSelectedRun} />
      ) : (
        <RunDetail index={selectedRun} onBack={() => setSelectedRun(null)} />
      )}
    </div>
  );
}
