/**
 * Ask Slide Component
 * Displays funding request and use of funds
 */

interface AskSlideProps {
  data: {
    funding_amount?: number;
    use_of_funds?: Record<string, number>;
    timeline?: string;
  };
  onUpdate?: (data: any) => void;
}

function formatFunding(amount?: number): string {
  if (!amount) return "$0";
  if (amount >= 1e6) return `$${(amount / 1e6).toFixed(0)}M`;
  if (amount >= 1e3) return `$${(amount / 1e3).toFixed(0)}K`;
  return `$${amount}`;
}

export function AskSlide({ data, onUpdate }: AskSlideProps) {
  const totalFunds = Object.values(data.use_of_funds || {}).reduce(
    (a, b) => a + b,
    0
  );

  return (
    <div className="slide-container ask">
      <div className="slide-header">
        <h1>Our Ask</h1>
      </div>

      <div className="slide-content">
        {data.funding_amount && (
          <div className="funding-request">
            <div className="funding-box">
              <div className="funding-label">Seeking Investment</div>
              <div className="funding-amount">
                {formatFunding(data.funding_amount)}
              </div>
            </div>
          </div>
        )}

        {data.use_of_funds && totalFunds > 0 && (
          <div className="use-of-funds">
            <h3>Use of Funds</h3>
            <div className="funds-breakdown">
              {Object.entries(data.use_of_funds).map(([category, percentage]) => (
                <div key={category} className="fund-category">
                  <div className="category-header">
                    <span className="category-name">{category}</span>
                    <span className="category-percent">{percentage}%</span>
                  </div>
                  <div className="category-bar">
                    <div
                      className="category-fill"
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.timeline && (
          <div className="timeline-box">
            <h3>Timeline</h3>
            <p>{data.timeline}</p>
          </div>
        )}
      </div>

      <style jsx>{`
        .slide-container {
          background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
          color: white;
          padding: 60px;
          height: 100%;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
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

        .funding-request {
          display: flex;
          justify-content: center;
          align-items: center;
          margin: 20px 0;
        }

        .funding-box {
          background: rgba(255, 255, 255, 0.15);
          padding: 40px;
          border-radius: 16px;
          text-align: center;
          backdrop-filter: blur(10px);
          border: 2px solid rgba(255, 255, 255, 0.3);
        }

        .funding-label {
          font-size: 14px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin-bottom: 10px;
          opacity: 0.95;
        }

        .funding-amount {
          font-size: 56px;
          font-weight: 900;
        }

        .use-of-funds {
          background: rgba(255, 255, 255, 0.1);
          padding: 30px;
          border-radius: 12px;
          backdrop-filter: blur(10px);
        }

        .use-of-funds h3 {
          font-size: 16px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin: 0 0 20px 0;
        }

        .funds-breakdown {
          display: flex;
          flex-direction: column;
          gap: 15px;
        }

        .fund-category {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .category-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .category-name {
          font-size: 14px;
          font-weight: 600;
        }

        .category-percent {
          font-size: 16px;
          font-weight: 700;
        }

        .category-bar {
          background: rgba(255, 255, 255, 0.2);
          height: 24px;
          border-radius: 4px;
          overflow: hidden;
        }

        .category-fill {
          background: rgba(255, 255, 255, 0.9);
          height: 100%;
          transition: width 0.3s;
        }

        .timeline-box {
          background: rgba(255, 255, 255, 0.1);
          padding: 20px;
          border-radius: 8px;
          backdrop-filter: blur(10px);
        }

        .timeline-box h3 {
          font-size: 14px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin: 0 0 10px 0;
        }

        .timeline-box p {
          font-size: 16px;
          line-height: 1.6;
          margin: 0;
        }
      `}</style>
    </div>
  );
}
