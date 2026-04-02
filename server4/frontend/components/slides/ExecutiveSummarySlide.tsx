/**
 * ExecutiveSummary Slide Component
 * Displays company overview, vision, problem, and solution
 */

interface ExecutiveSummarySlideProps {
  data: {
    company_name: string;
    tagline: string;
    description: string;
    vision?: string;
    problem?: string;
    solution?: string;
  };
  onUpdate?: (data: any) => void;
}

export function ExecutiveSummarySlide({ data, onUpdate }: ExecutiveSummarySlideProps) {
  return (
    <div className="slide-container executive-summary">
      <div className="slide-header">
        <h1 className="company-name">{data.company_name}</h1>
        <h2 className="tagline">{data.tagline}</h2>
      </div>

      <div className="slide-content">
        <section className="section">
          <p className="description">{data.description}</p>
        </section>

        {data.vision && (
          <section className="section vision">
            <h3>Vision</h3>
            <p>{data.vision}</p>
          </section>
        )}

        <div className="two-column">
          {data.problem && (
            <section className="section problem">
              <h3>Problem</h3>
              <p>{data.problem}</p>
            </section>
          )}

          {data.solution && (
            <section className="section solution">
              <h3>Solution</h3>
              <p>{data.solution}</p>
            </section>
          )}
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
          justify-content: space-between;
        }

        .slide-header {
          margin-bottom: 40px;
        }

        .company-name {
          font-size: 56px;
          font-weight: 800;
          margin: 0 0 10px 0;
        }

        .tagline {
          font-size: 28px;
          font-weight: 300;
          margin: 0;
          opacity: 0.95;
        }

        .slide-content {
          flex: 1;
        }

        .section {
          margin-bottom: 20px;
        }

        .description {
          font-size: 18px;
          line-height: 1.6;
          margin: 0 0 20px 0;
        }

        .two-column {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }

        .section h3 {
          font-size: 18px;
          font-weight: 600;
          margin: 0 0 10px 0;
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .section p {
          font-size: 16px;
          line-height: 1.5;
          margin: 0;
        }
      `}</style>
    </div>
  );
}
