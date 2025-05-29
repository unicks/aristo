import React, { Component } from "react";

interface State {
  compact: boolean;
  text: string;
  question: string;
}

interface Props {
  onConfirm: (comment: { text: string; question: string; emoji: string }) => void;
  onOpen: () => void;
  onUpdate?: () => void;
}

export class Tip extends Component<Props, State> {
  state: State = {
    compact: true,
    text: "",
    question: "",
  };

  // for TipContainer
  componentDidUpdate(_: Props, nextState: State) {
    const { onUpdate } = this.props;

    if (onUpdate && this.state.compact !== nextState.compact) {
      onUpdate();
    }
  }

  render() {
    const { onConfirm, onOpen } = this.props;
    const { compact, text, question } = this.state;

    return (
      <div>
        {compact ? (
          <div
            style={{
              cursor: "pointer",
              backgroundColor: "#3d464d",
              border: "1px solid rgba(255, 255, 255, 0.25)",
              color: "white",
              padding: "8px 12px",
              borderRadius: "4px",
              fontSize: "14px",
            }}
            onClick={() => {
              onOpen();
              this.setState({ compact: false });
            }}
          >
            Add Comment
          </div>
        ) : (
          <form
            style={{
              padding: "15px",
              background: "#fff",
              border: "1px solid #ddd",
              borderRadius: "6px",
              boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
              minWidth: "280px",
            }}
            onSubmit={(event) => {
              event.preventDefault();
              onConfirm({ text, question, emoji: "" });
            }}
          >
            <div style={{ marginBottom: "12px" }}>
              <label 
                style={{ 
                  display: "block", 
                  marginBottom: "4px", 
                  fontSize: "12px", 
                  fontWeight: "bold",
                  color: "#333"
                }}
              >
                Question Number:
              </label>
              <input
                type="text"
                placeholder="e.g., 1, 2a, Problem 3"
                value={question}
                onChange={(event) =>
                  this.setState({ question: event.target.value })
                }
                style={{
                  width: "100%",
                  padding: "8px",
                  fontSize: "14px",
                  border: "1px solid #ccc",
                  borderRadius: "4px",
                  boxSizing: "border-box",
                }}
              />
            </div>
            
            <div style={{ marginBottom: "15px" }}>
              <label 
                style={{ 
                  display: "block", 
                  marginBottom: "4px", 
                  fontSize: "12px", 
                  fontWeight: "bold",
                  color: "#333"
                }}
              >
                Comment:
              </label>
              <textarea
                placeholder="Enter your comment here..."
                autoFocus
                value={text}
                onChange={(event) =>
                  this.setState({ text: event.target.value })
                }
                style={{
                  width: "100%",
                  height: "80px",
                  padding: "8px",
                  fontSize: "14px",
                  border: "1px solid #ccc",
                  borderRadius: "4px",
                  boxSizing: "border-box",
                  resize: "vertical",
                  fontFamily: "inherit",
                }}
                ref={(node) => {
                  if (node) {
                    node.focus();
                  }
                }}
              />
            </div>
            
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                type="submit"
                style={{
                  flex: "1",
                  padding: "8px 16px",
                  fontSize: "14px",
                  backgroundColor: "#007bff",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
              >
                Save Comment
              </button>
              <button
                type="button"
                onClick={() => this.setState({ compact: true })}
                style={{
                  padding: "8px 16px",
                  fontSize: "14px",
                  backgroundColor: "#6c757d",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    );
  }
} 