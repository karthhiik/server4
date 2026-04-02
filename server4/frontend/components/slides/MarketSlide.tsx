/**
 * Market Slide Component
 * Displays TAM/SAM/SOM, competitors, and market positioning
 */

interface MarketSlideProps {
  data: {
    tam?: number;
    sam?: number;
    som?: number;
    competitors?: string[];
    positioning?: string;
    target_segment?: string;
  };
  onUpdate?: (data: any) => void;
}

function formatMarketSize(size?: number): string {
  if (!size) return "N/A";
  if (size >= 1e9) return `$${(size / 1e9).toFixed(1)}B`;
  if (size >= 1e6) return `$${(size / 1e6).toFixed(1)}M`;
  return `$${size}`;
}

export function MarketSlide({ data, onUpdate }: MarketSlideProps) {
  return (
    <div className="slide-container market">
      <div className="slide-header">
        <h1>Market Opportunity</h1>
      </div>

      <div className="slide-content">
        <div className="tam-sam-som">
          <div className="market-metric">
            <div className="metric-value">{formatMarketSize(data.tam)}</div>
            <div className="metric-label">TAM</div>
            <div className="metric-desc">Total Addressable Market</div>
          </div>
          <div className="connector">→</div>
          <div className="market-metric">
            <div className="metric-value">{formatMarketSize(data.sam)}</div>
            <div className="metric-label">SAM</div>
            <div className="metric-desc">Serviceable Addressable Market</div>
          </div>
          <div className="connector">→</div>
          <div className="market-metric">
            <div className="metric-value">{formatMarketSize(data.som)}</div>
            <div className="metric-label">SOM</div>
            <div className="metric-desc">Serviceable Obtainable Market</div>
          </div>
        </div>

        <div className="market-details">
          <div className="left-column">
            {data.positioning && (
              <section>
                <h3>Market Positioning</h3>
                <p>{data.positioning}</p>
              </section>
            )}

            {data.target_segment && (
              <section>
                <h3>Target Segment</h3>
                <p>{data.target_segment}</p>
              </section>
            )}
          </div>

          <div className="right-column">
            {data.competitors && data.competitors.length > 0 && (
              <section>
                <h3>Key Competitors</h3>
                <ul className="competitor-list">
                  {data.competitors.map((competitor, idx) => (
                    <li key={idx}>{competitor}</li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        </div>
      </div>

      <style jsx>{`
        .slide-container {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 60px;
          height: 100%;
          display: flex;
          flex-direction: column;
        }

        .slide-header {
          margin-bottom: 40px;
        }

        .slide-header h1 {
          font-size: 48px;
          font-weight: 800;
          margin: 0;
        }

        .slide-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 40px;
        }

        .tam-sam-som {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 20px;
        }

        .market-metric {
          flex: 1;
          background: rgba(255, 255, 255, 0.1);
          padding: 20px;
          border-radius: 12px;
          text-align: center;
          backdrop-filter: blur(10px);
        }

        .metric-value {
          font-size: 32px;
          font-weight: 800;
          margin-bottom: 5px;
        }

        .metric-label {
          font-size: 14px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin-bottom: 5px;
        }

        .metric-desc {
          font-size: 12px;
          opacity: 0.8;
        }

        .connector {
          font-size: 24px;
          font-weight: bold;
        }

        .market-details {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 40px;
        }

        .left-column,
        .right-column {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        section h3 {
          font-size: 16px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin: 0 0 10px 0;
        }

        section p {
          font-size: 16px;
          line-height: 1.6;
          margin: 0;
        }

        .competitor-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .competitor-list li {
          font-size: 16px;
          margin-bottom: 8px;
          padding-left: 24px;
          position: relative;
        }

        .competitor-list li:before {
          content: "▸";
          position: absolute;
          left: 0;
          font-size: 20px;
        }
      `}</style>
    </div>
  );
}
