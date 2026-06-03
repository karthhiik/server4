/**
 * ProductDemo Slide Component
 * Showcases product features and unique value proposition
 */

interface ProductDemoSlideProps {
  data: {
    product_name: string;
    description: string;
    features?: string[];
    unique_value?: string;
    differentiators?: string[];
    image_url?: string;
  };
  onUpdate?: (data: any) => void;
}

export function ProductDemoSlide({ data, onUpdate }: ProductDemoSlideProps) {
  return (
    <div className="slide-container product-demo">
      <div className="slide-header">
        <h1>{data.product_name}</h1>
        <p className="subtitle">{data.description}</p>
      </div>

      <div className="slide-content">
        {data.image_url && (
          <div className="product-image">
            <img src={data.image_url} alt={data.product_name} />
          </div>
        )}

        <div className="product-details">
          {data.unique_value && (
            <section className="unique-value">
              <h3>Unique Value</h3>
              <p>{data.unique_value}</p>
            </section>
          )}

          {data.features && data.features.length > 0 && (
            <section className="features">
              <h3>Key Features</h3>
              <ul className="feature-list">
                {data.features.map((feature, idx) => (
                  <li key={idx}>
                    <span className="feature-icon">✓</span>
                    {feature}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {data.differentiators && data.differentiators.length > 0 && (
            <section className="differentiators">
              <h3>Why We're Different</h3>
              <div className="differentiator-list">
                {data.differentiators.map((diff, idx) => (
                  <div key={idx} className="differentiator-item">
                    <span className="number">{idx + 1}</span>
                    <p>{diff}</p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>

      <style>{`
        .slide-container {
          background: linear-gradient(to right, #f5f7fa 0%, #c3cfe2 100%);
          padding: 60px;
          height: 100%;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }

        .slide-header {
          margin-bottom: 40px;
          text-align: center;
        }

        .slide-header h1 {
          font-size: 48px;
          font-weight: 800;
          margin: 0 0 10px 0;
          color: #1a202c;
        }

        .subtitle {
          font-size: 18px;
          color: #4a5568;
          margin: 0;
        }

        .slide-content {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 40px;
          align-items: center;
        }

        .product-image {
          display: flex;
          justify-content: center;
          align-items: center;
        }

        .product-image img {
          max-width: 100%;
          max-height: 300px;
          border-radius: 8px;
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }

        .product-details {
          display: flex;
          flex-direction: column;
          gap: 30px;
        }

        .product-details section h3 {
          font-size: 18px;
          font-weight: 700;
          margin: 0 0 15px 0;
          color: #1a202c;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .feature-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .feature-list li {
          display: flex;
          align-items: center;
          font-size: 16px;
          margin-bottom: 10px;
          color: #2d3748;
        }

        .feature-icon {
          color: #48bb78;
          font-weight: bold;
          margin-right: 12px;
          font-size: 20px;
        }

        .differentiator-list {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 15px;
        }

        .differentiator-item {
          background: white;
          padding: 15px;
          border-radius: 8px;
          display: flex;
          align-items: flex-start;
          gap: 12px;
        }

        .number {
          background: #667eea;
          color: white;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          flex-shrink: 0;
        }

        .differentiator-item p {
          font-size: 14px;
          color: #2d3748;
          margin: 0;
        }
      `}</style>
    </div>
  );
}
