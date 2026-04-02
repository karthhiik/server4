/**
 * Traction Slide Component
 * Displays key metrics and milestones
 */

interface MetricData {
  label: string;
  value: any;
}

interface MilestoneData {
  date: string;
  milestone: string;
}

interface TractionSlideProps {
  data: {
    metrics?: MetricData[];
    timeline?: MilestoneData[];
  };
  onUpdate?: (data: any) => void;
}

export function TractionSlide({ data, onUpdate }: TractionSlideProps) {
  return (
    <div className="slide-container traction">
      <div className="slide-header">
        <h1>Traction</h1>
        <p>Key metrics demonstrating market fit and growth</p>
      </div>

      <div className="slide-content">
        {data.metrics && data.metrics.length > 0 && (
          <div className="metrics-section">
            <h3>Key Metrics</h3>
            <div className="metrics-showcase">
              {data.metrics.map((metric, idx) => (
                <div key={idx} className="metric-showcase">
                  <div className="metric-icon">📊</div>
                  <div className="metric-value">{metric.value}</div>
                  <div className="metric-label">{metric.label}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.timeline && data.timeline.length > 0 && (
          <div className="timeline-section">
            <h3>Milestones</h3>
            <div className="timeline">
              {data.timeline.map((item, idx) => (
                <div key={idx} className="timeline-item">
                  <div className="timeline-marker"></div>
                  <div className="timeline-content">
                    <div className="timeline-date">{item.date}</div>
                    <div className="timeline-text">{item.milestone}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
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
          margin: 0 0 10px 0;
        }

        .slide-header p {
          font-size: 16px;
          margin: 0;
          opacity: 0.95;
        }

        .slide-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 40px;
        }

        .metrics-section h3,
        .timeline-section h3 {
          font-size: 18px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin: 0 0 20px 0;
        }

        .metrics-showcase {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 20px;
        }

        .metric-showcase {
          background: rgba(255, 255, 255, 0.15);
          padding: 25px;
          border-radius: 12px;
          text-align: center;
          backdrop-filter: blur(10px);
          transition: transform 0.3s;
        }

        .metric-showcase:hover {
          transform: translateY(-5px);
        }

        .metric-icon {
          font-size: 32px;
          margin-bottom: 10px;
        }

        .metric-value {
          font-size: 32px;
          font-weight: 800;
          margin-bottom: 8px;
        }

        .metric-label {
          font-size: 12px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          opacity: 0.9;
        }

        .timeline {
          position: relative;
          padding-left: 40px;
        }

        .timeline::before {
          content: "";
          position: absolute;
          left: 8px;
          top: 0;
          bottom: 0;
          width: 2px;
          background: rgba(255, 255, 255, 0.3);
        }

        .timeline-item {
          display: flex;
          gap: 20px;
          margin-bottom: 20px;
          position: relative;
        }

        .timeline-marker {
          position: absolute;
          left: -32px;
          top: 4px;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: white;
          border: 3px solid rgba(255, 255, 255, 0.3);
        }

        .timeline-item:last-child .timeline-marker {
          background: rgba(255, 255, 255, 0.8);
        }

        .timeline-content {
          flex: 1;
        }

        .timeline-date {
          font-size: 12px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 5px;
          opacity: 0.8;
        }

        .timeline-text {
          font-size: 15px;
          line-height: 1.4;
        }
      `}</style>
    </div>
  );
}
