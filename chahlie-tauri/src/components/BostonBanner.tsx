import { ChahlieLogoMark } from "./BostonIcons";
import type { Status } from "../api";

type Props = {
  status?: Status | null;
  compact?: boolean;
};

export function BostonBanner({ status, compact = false }: Props) {
  return (
    <header className={`boston-banner ${compact ? "compact" : ""}`}>
      <div className="banner-skyline" aria-hidden />
      <div className="banner-inner">
        <div className="banner-brand">
          <ChahlieLogoMark size={compact ? 40 : 52} />
          <div className="banner-titles">
            <h1 className="banner-name">CHAHLIE</h1>
            {!compact && (
              <p className="banner-tagline">
                You're wicked smart — a coding assistant
              </p>
            )}
          </div>
        </div>
        {status && (
          <div className="banner-meta">
            <span className="banner-badge">⚾ Boston Pride</span>
            <span className="banner-version">
              v{status.version} &ldquo;{status.codename}&rdquo;
            </span>
            <span className="banner-backend">
              ☁ {status.backend} · {status.model} · {status.cost}
            </span>
          </div>
        )}
      </div>
    </header>
  );
}
