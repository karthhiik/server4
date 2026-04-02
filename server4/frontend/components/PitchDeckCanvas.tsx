/**
 * Pitch Deck Canvas - Main Component
 * Renders 9-slide pitch deck with navigation and export
 */

import React, { useState } from "react";
import {
  ExecutiveSummarySlide,
  ProductDemoSlide,
  MarketSlide,
  BusinessModelSlide,
  FinancialsSlide,
  TeamSlide,
  TractionSlide,
  AskSlide,
} from "./slides";

interface PitchDeckSlide {
  id: string;
  order: number;
  type: string;
  title: string;
  content: Record<string, any>;
  speaker_notes?: string;
}

interface PitchDeckCanvasProps {
  deck: {
    id: string;
    title: string;
    slides: PitchDeckSlide[];
    theme: string;
    status: "draft" | "published" | "archived";
  };
  onUpdate?: (updates: any) => void;
  onExport?: (format: "pdf" | "pptx") => void;
}

export function PitchDeckCanvas({
  deck,
  onUpdate,
  onExport,
}: PitchDeckCanvasProps) {
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [isPresenting, setIsPresenting] = useState(false);

  const currentSlide = deck.slides[currentSlideIndex];

  const renderSlide = (slide: PitchDeckSlide) => {
    switch (slide.type) {
      case "executive_summary":
        return <ExecutiveSummarySlide data={slide.content} onUpdate={onUpdate} />;
      case "product_demo":
        return <ProductDemoSlide data={slide.content} onUpdate={onUpdate} />;
      case "market":
        return <MarketSlide data={slide.content} onUpdate={onUpdate} />;
      case "business_model":
        return <BusinessModelSlide data={slide.content} onUpdate={onUpdate} />;
      case "financials":
        return <FinancialsSlide data={slide.content} onUpdate={onUpdate} />;
      case "team":
        return <TeamSlide data={slide.content} onUpdate={onUpdate} />;
      case "traction":
        return <TractionSlide data={slide.content} onUpdate={onUpdate} />;
      case "ask":
        return <AskSlide data={slide.content} onUpdate={onUpdate} />;
      default:
        return <div>Unknown slide type: {slide.type}</div>;
    }
  };

  const goToNext = () => {
    setCurrentSlideIndex(Math.min(currentSlideIndex + 1, deck.slides.length - 1));
  };

  const goToPrevious = () => {
    setCurrentSlideIndex(Math.max(currentSlideIndex - 1, 0));
  };

  const goToSlide = (index: number) => {
    setCurrentSlideIndex(Math.max(0, Math.min(index, deck.slides.length - 1)));
  };

  return (
    <div
      className="pitch-deck-container"
      role="application"
      aria-label="Pitch Deck Canvas"
    >
      <div className="deck-viewer" role="main">
        <div className="slide-display" role="region" aria-label="Current slide">
          {currentSlide && renderSlide(currentSlide)}
        </div>

        <div className="slide-counter" aria-live="polite" aria-atomic="true">
          {currentSlideIndex + 1} / {deck.slides.length}
        </div>

        <nav
          className="navigation-controls"
          role="navigation"
          aria-label="Pitch deck navigation"
        >
          <button
            onClick={goToPrevious}
            disabled={currentSlideIndex === 0}
            className="nav-button"
            aria-label="Previous slide - Navigate to the previous slide in the pitch deck"
          >
            ← Previous
          </button>

          <button
            onClick={() => setIsPresenting(!isPresenting)}
            className="present-button"
            aria-label={
              isPresenting
                ? "Exit Presentation - Exit presentation mode"
                : "Start Presentation - Begin presentation mode"
            }
          >
            {isPresenting ? "Exit Presentation" : "Start Presentation"}
          </button>

          <button
            onClick={goToNext}
            disabled={currentSlideIndex === deck.slides.length - 1}
            className="nav-button"
            aria-label="Next slide - Navigate to the next slide in the pitch deck"
          >
            Next →
          </button>
        </nav>

        {currentSlide.speaker_notes && (
          <aside
            className="speaker-notes"
            role="complementary"
            aria-label="Speaker notes for current slide"
          >
            <h4>Speaker Notes</h4>
            <p>{currentSlide.speaker_notes}</p>
          </aside>
        )}
      </div>

      <aside
        className="deck-sidebar"
        role="complementary"
        aria-label="Pitch deck controls and navigation"
      >
        <h2>{deck.title}</h2>
        <div className="deck-status">
          <span className="status-badge" data-status={deck.status}>
            {deck.status.toUpperCase()}
          </span>
          <span className="theme-badge">{deck.theme}</span>
        </div>

        <nav className="slide-thumbnails" role="navigation" aria-label="Slide thumbnails">
          {deck.slides.map((slide, index) => (
            <button
              key={slide.id}
              className={`thumbnail ${index === currentSlideIndex ? "active" : ""}`}
              onClick={() => goToSlide(index)}
              aria-label={`Slide ${index + 1}: ${slide.title} - Jump to this slide`}
              aria-current={index === currentSlideIndex ? "true" : undefined}
            >
              <div className="thumbnail-preview">
                {slide.type.charAt(0).toUpperCase()}
              </div>
              <div className="thumbnail-title">{slide.title}</div>
              <div className="thumbnail-order">{index + 1}</div>
            </button>
          ))}
        </nav>

        <div className="export-controls">
          <button
            className="export-btn pdf"
            onClick={() => onExport?.("pdf")}
            aria-label="Export pitch deck as PDF"
          >
            📄 Export PDF
          </button>
          <button
            className="export-btn pptx"
            onClick={() => onExport?.("pptx")}
            aria-label="Export pitch deck as PowerPoint presentation"
          >
            🎯 Export PPTX
          </button>
        </div>
      </aside>

      <style jsx>{`
        .pitch-deck-container {
          display: grid;
          grid-template-columns: 1fr 280px;
          gap: 20px;
          height: 100vh;
          background: #f5f5f5;
          padding: 20px;
        }

        .deck-viewer {
          display: flex;
          flex-direction: column;
          background: white;
          border-radius: 12px;
          box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
          overflow: hidden;
        }

        .slide-display {
          flex: 1;
          overflow: hidden;
          background: #1a1a1a;
          aspect-ratio: 16 / 9;
        }

        .slide-counter {
          text-align: center;
          padding: 10px;
          background: #f0f0f0;
          font-size: 14px;
          font-weight: 600;
          color: #666;
        }

        .navigation-controls {
          display: flex;
          gap: 10px;
          padding: 15px;
          background: #f9f9f9;
          border-top: 1px solid #e0e0e0;
        }

        .nav-button {
          flex: 1;
          padding: 10px;
          border: 1px solid #ddd;
          border-radius: 6px;
          background: white;
          cursor: pointer;
          font-size: 13px;
          font-weight: 600;
          color: #333;
          transition: all 0.2s;
        }

        .nav-button:hover:not(:disabled) {
          background: #f0f0f0;
          border-color: #999;
        }

        .nav-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .present-button {
          padding: 10px 20px;
          background: #667eea;
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-size: 13px;
          font-weight: 600;
          transition: background 0.2s;
        }

        .present-button:hover {
          background: #5568d3;
        }

        .speaker-notes {
          padding: 15px;
          background: #fffbf0;
          border-top: 1px solid #e0e0e0;
          max-height: 150px;
          overflow-y: auto;
        }

        .speaker-notes h4 {
          margin: 0 0 8px 0;
          font-size: 12px;
          font-weight: 700;
          text-transform: uppercase;
          color: #666;
        }

        .speaker-notes p {
          margin: 0;
          font-size: 13px;
          line-height: 1.5;
          color: #555;
        }

        .deck-sidebar {
          display: flex;
          flex-direction: column;
          background: white;
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 10px 40px rgba(0, 0, 0, 0.05);
        }

        .deck-sidebar h2 {
          font-size: 18px;
          font-weight: 700;
          margin: 0 0 10px 0;
          color: #1a1a1a;
          word-break: break-word;
        }

        .deck-status {
          display: flex;
          gap: 8px;
          margin-bottom: 20px;
          flex-wrap: wrap;
        }

        .status-badge,
        .theme-badge {
          font-size: 11px;
          font-weight: 700;
          padding: 4px 8px;
          border-radius: 4px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .status-badge {
          background: #e3f2fd;
          color: #1976d2;
        }

        .status-badge[data-status="published"] {
          background: #e8f5e9;
          color: #388e3c;
        }

        .status-badge[data-status="archived"] {
          background: #f3e5f5;
          color: #7b1fa2;
        }

        .theme-badge {
          background: #f3e5f5;
          color: #666;
        }

        .slide-thumbnails {
          flex: 1;
          overflow-y: auto;
          margin-bottom: 15px;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .thumbnail {
          padding: 8px;
          border: 2px solid transparent;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.2s;
          background: #f9f9f9;
        }

        .thumbnail:hover {
          background: #f0f0f0;
          border-color: #ddd;
        }

        .thumbnail.active {
          border-color: #667eea;
          background: #f3f5ff;
        }

        .thumbnail-preview {
          width: 100%;
          aspect-ratio: 16 / 9;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: 700;
          margin-bottom: 6px;
          font-size: 18px;
        }

        .thumbnail-title {
          font-size: 11px;
          font-weight: 600;
          color: #333;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .thumbnail-order {
          font-size: 10px;
          color: #999;
          margin-top: 2px;
        }

        .export-controls {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .export-btn {
          padding: 10px;
          border: none;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }

        .export-btn.pdf {
          background: #ffe0e0;
          color: #c33;
        }

        .export-btn.pdf:hover {
          background: #ffc0c0;
        }

        .export-btn.pptx {
          background: #e0e8ff;
          color: #446699;
        }

        .export-btn.pptx:hover {
          background: #c0d0ff;
        }
      `}</style>
    </div>
  );
}
