import { Component, ChangeEvent } from 'react';
import api from '../api';

type Message = {
  sender: 'user' | 'ai';
  text: string;
};

type AppProps = {};

type AppState = {
  input: string;
  messages: Message[];
  showChart: boolean;
  isLoading: boolean;
};

export class Assistant extends Component<AppProps, AppState> {
  constructor(props: AppProps) {
    super(props);
    this.state = {
      input: '',
      messages: [],
      showChart: false,
      isLoading: false,
    };
  }

  doSendQuery = async () => {
    const userMessage: Message = {
      sender: 'user',
      text: this.state.input,
    };

    this.setState((prevState) => ({
      messages: [...prevState.messages, userMessage],
      input: '',
      isLoading: true,
    }));

    try {
      const res = await api.post('/chat', {
        user_input: userMessage.text,
      });

      const replyText = res.data.reply;
      const chartDetected = replyText.toLowerCase().includes('stock.png');

      const aiMessage: Message = {
        sender: 'ai',
        text: replyText,
      };

      this.setState((prevState) => ({
        messages: [...prevState.messages, aiMessage],
        showChart: chartDetected,
        isLoading: false,
      }));
    } catch (error) {
      console.error('Error contacting backend:', error);
      const errorMessage: Message = {
        sender: 'ai',
        text: '⚠️ An error occurred while contacting the assistant.',
      };

      this.setState((prevState) => ({
        messages: [...prevState.messages, errorMessage],
        isLoading: false,
      }));
    }
  };

  render() {
    return (
      <div className="assistant">
        <div className="chat-header">
          <h1>Financial Assistant</h1>
        </div>

        <div className="chat-window">
          <div className="messages">
            {this.state.messages.map((msg, index) => (
              <div
                key={index}
                className={`message ${msg.sender === 'user' ? 'user' : 'ai'}`}
              >
                {msg.text}
              </div>
            ))}

            {this.state.showChart && (
              <div className="message ai">
                <h4>📊 Chart Preview</h4>
                <img
                  src="http://localhost:8000/chart"
                  alt="Generated chart"
                />
                <a href="http://localhost:8000/chart" download="stock_chart.png">
                  ⬇️ Download Chart
                </a>
              </div>
            )}

            {this.state.isLoading && (
              <div className="message ai loading-indicator">Thinking...</div>
            )}
          </div>
        </div>

        <div className="chat-input">
          <input
            type="text"
            value={this.state.input}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              this.setState({ input: e.target.value })
            }
            placeholder="Ask me about stocks, plotting, or finance..."
            onKeyDown={(e) => {
              if (e.key === 'Enter') this.doSendQuery();
            }}
          />
          <button onClick={this.doSendQuery}>Send</button>
        </div>
      </div>
    );
  }
}

export default Assistant;
