// App.tsx
import './App.css';
import Assistant from './components/Assistant';

const App = () => {
  return (
    <div className="chat-app">
      {/* You can add a sidebar here later if needed */}
      <div className="chat-container">
        <Assistant />
      </div>
    </div>
  );
};

export default App;
