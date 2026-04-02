/**
 * Financials Slide Component
 * Displays financial projections, growth rate, and valuation
 */

interface FinancialsSlideProps {
  data: {
    revenue_2024?: number;
    revenue_2025?: number;
    revenue_2026?: number;
    growth_rate?: number;
    mrr?: number;
    arr?: number;
    valuation?: number;
  };
  onUpdate?: (data: any) => void;
}

function formatCurrency(value?: number): string {
  if (!value) return "$0";
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
  return `$${value}`;
}

export function FinancialsSlide({ data, onUpdate }: FinancialsSlideProps) {
  const years = [
    { year: 2024, revenue: data.revenue_2024 },
    { year: 2025, revenue: data.revenue_2025 },
    { year: 2026, revenue: data.revenue_2026 },
  ].filter((y) => y.revenue);

  const maxRevenue = Math.max(...years.map((y) => y.revenue || 0));

  return (
    <div className="slide-container financials">
      <div className="slide-header">
        <h1>Financials</h1>
      </div>

      <div className="slide-content">
        {years.length > 0 && (
          <div className="revenue-projection">
            <h3>Revenue Projection</h3>
            <div className="chart">
              <div className="bars">
                {years.map((item, idx) => (
                  <div key={idx} className="bar-item">
                    <div className="bar-label">{item.year}</div>
                    <div className="bar-container">
                      <div
                        className="bar"
                        style={{
                          height: `${(item.revenue / maxRevenue) * 200}px`,
                        }}
                      ></div>
                    </div>
                    <div className="bar-value">{formatCurrency(item.revenue)}</div>
                  </div>
                ))}
              </div>
            </div>
            {data.growth_rate && (
              <div className="growth-rate">
                <span className="label">Growth Rate:</span>
                <span className="value">{data.growth_rate.toFixed(1)}x YoY</span>
              </div>
            )}
          </div>
        )}

        <div className="metrics-grid">
          {data.mrr && (
            <div className="metric-card">
              <div className="metric-label">Monthly Recurring Revenue</div>
              <div className="metric-value">{formatCurrency(data.mrr)}</div>
            </div>
          )}

          {data.arr && (
            <div className="metric-card">
              <div className="metric-label">Annual Recurring Revenue</div>
              <div className="metric-value">{formatCurrency(data.arr)}</div>
            </div>
          )}

          {data.valuation && (
            <div className="metric-card">
              <div className="metric-label">Valuation</div>
              <div className="metric-value">{formatCurrency(data.valuation)}</div>
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        .slide-container {
          background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
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

        .revenue-projection {
          background: rgba(255, 255, 255, 0.1);
          padding: 30px;
          border-radius: 12px;
          backdrop-filter: blur(10px);
        }

        .revenue-projection h3 {
          font-size: 16px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin: 0 0 20px 0;
        }

        .chart {
          margin-bottom: 20px;
        }

        .bars {
          display: flex;
          justify-content: space-around;
          align-items: flex-end;
          height: 250px;
          gap: 30px;
        }

        .bar-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 10px;
          flex: 1;
        }

        .bar-label {
          font-size: 14px;
          font-weight: 600;
          order: 2;
        }

        .bar-container {
          display: flex;
          align-items: flex-end;
          justify-content: center;
          order: 1;
          flex: 1;
          width: 60px;
        }

        .bar {
          width: 100%;
          background: rgba(255, 255, 255, 0.8);
          border-radius: 4px 4px 0 0;
          min-height: 20px;
        }

        .bar-value {
          font-size: 12px;
          font-weight: 600;
          order: 3;
        }

        .growth-rate {
          display: flex;
          justify-content: center;
          gap: 10px;
          margin-top: 15px;
          padding-top: 15px;
          border-top: 1px solid rgba(255, 255, 255, 0.2);
        }

        .growth-rate .label {
          font-size: 14px;
        }

        .growth-rate .value {
          font-size: 18px;
          font-weight: 800;
        }

        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 20px;
        }

        .metric-card {
          background: rgba(255, 255, 255, 0.15);
          padding: 20px;
          border-radius: 8px;
          text-align: center;
          backdrop-filter: blur(10px);
        }

        .metric-label {
          font-size: 12px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 10px;
          opacity: 0.9;
        }

        .metric-value {
          font-size: 28px;
          font-weight: 800;
        }
      `}</style>
    </div>
  );
}
