/**
 * BusinessModel Slide Component
 * Displays revenue streams, pricing model, and unit economics
 */

interface BusinessModelSlideProps {
  data: {
    revenue_streams?: string[];
    pricing_model?: string;
    unit_economics?: {
      ltv?: number;
      cac?: number;
      payback_period_months?: number;
    };
    revenue_breakdown?: Record<string, number>;
  };
  onUpdate?: (data: any) => void;
}

export function BusinessModelSlide({ data, onUpdate }: BusinessModelSlideProps) {
  const totalBreakdown = Object.values(data.revenue_breakdown || {}).reduce(
    (a, b) => a + b,
    0
  );

  return (
    <div className="slide-container business-model">
      <div className="slide-header">
        <h1>Business Model</h1>
      </div>

      <div className="slide-content">
        <div className="model-grid">
          {data.revenue_streams && data.revenue_streams.length > 0 && (
            <section className="revenue-streams">
              <h3>Revenue Streams</h3>
              <div className="stream-list">
                {data.revenue_streams.map((stream, idx) => (
                  <div key={idx} className="stream-item">
                    <span className="badge">{idx + 1}</span>
                    <span>{stream}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {data.pricing_model && (
            <section className="pricing-model">
              <h3>Pricing Model</h3>
              <div className="pricing-box">{data.pricing_model}</div>
            </section>
          )}
        </div>

        <div className="model-metrics">
          {data.unit_economics && (
            <div className="unit-economics">
              <h3>Unit Economics</h3>
              <div className="metrics-grid">
                {data.unit_economics.ltv && (
                  <div className="metric">
                    <div className="metric-label">LTV</div>
                    <div className="metric-value">
                      ${(data.unit_economics.ltv / 1000).toFixed(0)}K
                    </div>
                  </div>
                )}
                {data.unit_economics.cac && (
                  <div className="metric">
                    <div className="metric-label">CAC</div>
                    <div className="metric-value">
                      ${(data.unit_economics.cac / 1000).toFixed(0)}K
                    </div>
                  </div>
                )}
                {data.unit_economics.ltv && data.unit_economics.cac && (
                  <div className="metric">
                    <div className="metric-label">LTV:CAC Ratio</div>
                    <div className="metric-value">
                      {(data.unit_economics.ltv / data.unit_economics.cac).toFixed(1)}
                      :1
                    </div>
                  </div>
                )}
                {data.unit_economics.payback_period_months && (
                  <div className="metric">
                    <div className="metric-label">Payback Period</div>
                    <div className="metric-value">
                      {data.unit_economics.payback_period_months}m
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {data.revenue_breakdown && totalBreakdown > 0 && (
            <div className="revenue-breakdown">
              <h3>Revenue Breakdown</h3>
              <div className="breakdown-items">
                {Object.entries(data.revenue_breakdown).map(([key, value]) => (
                  <div key={key} className="breakdown-item">
                    <div className="label">{key}</div>
                    <div className="bar">
                      <div
                        className="fill"
                        style={{ width: `${value}%` }}
                      ></div>
                    </div>
                    <div className="percentage">{value}%</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        .slide-container {
          background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
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
          gap: 30px;
        }

        .model-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 30px;
        }

        section h3 {
          font-size: 16px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin: 0 0 15px 0;
        }

        .stream-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .stream-item {
          display: flex;
          align-items: center;
          gap: 12px;
          font-size: 16px;
        }

        .badge {
          background: rgba(255, 255, 255, 0.3);
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          flex-shrink: 0;
        }

        .pricing-box {
          background: rgba(255, 255, 255, 0.15);
          padding: 20px;
          border-radius: 8px;
          font-size: 16px;
          line-height: 1.6;
          backdrop-filter: blur(10px);
        }

        .model-metrics {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 30px;
        }

        .unit-economics .metrics-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 15px;
        }

        .metric {
          background: rgba(255, 255, 255, 0.1);
          padding: 15px;
          border-radius: 8px;
          text-align: center;
          backdrop-filter: blur(10px);
        }

        .metric-label {
          font-size: 12px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 8px;
          opacity: 0.9;
        }

        .metric-value {
          font-size: 24px;
          font-weight: 800;
        }

        .breakdown-items {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .breakdown-item {
          display: grid;
          grid-template-columns: 100px 1fr 50px;
          gap: 12px;
          align-items: center;
        }

        .breakdown-item .label {
          font-size: 14px;
        }

        .bar {
          background: rgba(255, 255, 255, 0.2);
          border-radius: 4px;
          overflow: hidden;
          height: 24px;
        }

        .fill {
          background: rgba(255, 255, 255, 0.8);
          height: 100%;
          transition: width 0.3s;
        }

        .percentage {
          text-align: right;
          font-size: 14px;
          font-weight: 600;
        }
      `}</style>
    </div>
  );
}
