import React from "react";
import type { IHighlight } from "./react-pdf-highlighter";
import type { ReactNode } from "react";
import logoImg from "./assets/logo.png";

interface Props {
  highlights: Array<IHighlight>;
  resetHighlights: () => void;
  children?: ReactNode;
}

const updateHash = (highlight: IHighlight) => {
  document.location.hash = `highlight-${highlight.id}`;
};

declare const APP_VERSION: string;

export function Sidebar({
  highlights,
  resetHighlights,
  children,
}: Props) {
  return (
    <div className="sidebar" style={{ width: "25vw" }}>
      <div className="description" style={{ 
        padding: "1.5rem", 
        textAlign: "center",
        borderBottom: "1px solid rgba(0, 0, 0, 0.1)",
      }}>
        <img 
          src={logoImg} 
          alt="Aristo Logo" 
          style={{
            width: "60px",
            height: "60px",
            marginBottom: "1rem",
            borderRadius: "12px",
            boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)",
          }}
        />
        <h2 style={{ 
          marginBottom: "0.5rem",
          color: "#2c3e50",
          fontSize: "1.8rem",
          fontWeight: "600",
        }}>
          Aristo
        </h2>

        <p style={{ 
          fontSize: "0.85rem",
          color: "#6c757d",
          margin: "0",
          lineHeight: "1.4",
        }}>
          Your AI-powered assignment grader.
        </p>
      </div>

      {children}

      <ul className="sidebar__highlights">
        {highlights.map((highlight, index) => (
          <li
            // biome-ignore lint/suspicious/noArrayIndexKey: This is an example app
            key={index}
            className="sidebar__highlight"
            onClick={() => {
              updateHash(highlight);
            }}
          >
            <div>
              <strong>{highlight.comment.text}</strong>
              {highlight.content.text ? (
                <blockquote style={{ marginTop: "0.5rem" }}>
                  {`${highlight.content.text.slice(0, 90).trim()}…`}
                </blockquote>
              ) : null}
              {highlight.content.image ? (
                <div
                  className="highlight__image"
                  style={{ marginTop: "0.5rem" }}
                >
                  <img src={highlight.content.image} alt={"Screenshot"} />
                </div>
              ) : null}
            </div>
            <div className="highlight__location">
              Page {highlight.position.pageNumber}
            </div>
          </li>
        ))}
      </ul>
      {highlights.length > 0 ? (
        <div style={{ padding: "1rem" }}>
          <button 
            type="button" 
            onClick={resetHighlights}
            style={{
              width: "100%",
              padding: "0.6rem",
              backgroundColor: "#dc3545",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "0.85rem",
              fontWeight: "500",
              transition: "all 0.15s ease",
            }}
          >
            🗑️ Reset highlights
          </button>
        </div>
      ) : null}
    </div>
  );
}
