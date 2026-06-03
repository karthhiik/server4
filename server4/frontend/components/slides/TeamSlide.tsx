/**
 * Team Slide Component
 * Displays team members and advisors
 */

interface TeamMemberData {
  name: string;
  title: string;
  bio?: string;
  image_url?: string;
}

interface TeamSlideProps {
  data: {
    team_members?: TeamMemberData[];
    advisors?: string[];
  };
  onUpdate?: (data: any) => void;
}

export function TeamSlide({ data, onUpdate }: TeamSlideProps) {
  return (
    <div className="slide-container team">
      <div className="slide-header">
        <h1>Team</h1>
      </div>

      <div className="slide-content">
        {data.team_members && data.team_members.length > 0 && (
          <div className="team-members">
            <h3>Leadership Team</h3>
            <div className="members-grid">
              {data.team_members.map((member, idx) => (
                <div key={idx} className="member-card">
                  {member.image_url ? (
                    <div
                      className="member-image"
                      style={{ backgroundImage: `url(${member.image_url})` }}
                    ></div>
                  ) : (
                    <div className="member-image-placeholder">
                      {member.name.charAt(0)}
                    </div>
                  )}
                  <div className="member-info">
                    <h4>{member.name}</h4>
                    <p className="title">{member.title}</p>
                    {member.bio && <p className="bio">{member.bio}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.advisors && data.advisors.length > 0 && (
          <div className="advisors">
            <h3>Advisors & Board</h3>
            <div className="advisors-list">
              {data.advisors.map((advisor, idx) => (
                <div key={idx} className="advisor-item">
                  <span className="advisor-badge">★</span>
                  {advisor}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <style>{`
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

        .team-members h3,
        .advisors h3 {
          font-size: 18px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin: 0 0 20px 0;
        }

        .members-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 20px;
        }

        .member-card {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          overflow: hidden;
          backdrop-filter: blur(10px);
        }

        .member-image {
          width: 100%;
          aspect-ratio: 1;
          background-size: cover;
          background-position: center;
        }

        .member-image-placeholder {
          width: 100%;
          aspect-ratio: 1;
          background: rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 48px;
          font-weight: bold;
        }

        .member-info {
          padding: 15px;
        }

        .member-info h4 {
          font-size: 16px;
          font-weight: 700;
          margin: 0 0 5px 0;
        }

        .member-info .title {
          font-size: 12px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: rgba(255, 255, 255, 0.8);
          margin: 0 0 8px 0;
        }

        .member-info .bio {
          font-size: 13px;
          line-height: 1.4;
          margin: 0;
          color: rgba(255, 255, 255, 0.75);
        }

        .advisors-list {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 15px;
        }

        .advisor-item {
          display: flex;
          align-items: center;
          gap: 12px;
          font-size: 15px;
          padding: 12px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          backdrop-filter: blur(10px);
        }

        .advisor-badge {
          font-size: 18px;
        }
      `}</style>
    </div>
  );
}
