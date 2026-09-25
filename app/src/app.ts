import { createShellModel, isViewId, type ShellModel, type ViewId } from './shell/model';

const placeholderCopy: Record<ViewId, { title: string; summary: string }> = {
  intel: {
    title: 'League position and live context',
    summary: 'Canonical standings, score basis and manager comparisons will land in Slice 06.',
  },
  transfer: {
    title: 'One coherent transfer decision',
    summary: 'Working plans, declared actions and recommendation evidence will land in Slice 07.',
  },
  team: {
    title: 'Legal XI, captaincy and bench',
    summary: 'The effective-squad team selector and pitch experience will land in Slice 08.',
  },
  strategy: {
    title: 'Squad structure and future windows',
    summary: 'Fixture outlook, squad shape and chip windows will land in Slice 09.',
  },
  pool: {
    title: 'Credible player alternatives',
    summary: 'Bounded player evidence and comparison will land in Slice 09.',
  },
};

function shellMarkup(model: ShellModel): string {
  const active = placeholderCopy[model.activeView];

  return `
    <div class="app-shell">
      <header class="app-header">
        <div>
          <p class="eyebrow">${model.eyebrow}</p>
          <h1>${model.title}</h1>
          <p class="freshness" aria-live="polite">${model.freshnessLabel}</p>
        </div>
        <div class="phase-stack" aria-label="Gameweek context">
          <span class="phase-pill">${model.phaseLabel}</span>
          <strong>${model.gameweekLabel}</strong>
        </div>
      </header>

      <section class="kpi-grid" aria-label="Key performance indicators">
        ${['Rank', 'Gameweek', 'Gap / lead', 'Bank'].map((label) => `
          <article class="kpi-card">
            <span>${label}</span>
            <strong>—</strong>
            <small>Awaiting contract</small>
          </article>
        `).join('')}
      </section>

      <nav class="primary-nav" aria-label="Decision Centre views">
        ${model.navigation.map((item) => `
          <button
            type="button"
            data-view="${item.id}"
            aria-current="${item.id === model.activeView ? 'page' : 'false'}"
          >${item.label}</button>
        `).join('')}
      </nav>

      <main id="main-content" tabindex="-1">
        <section class="hero-card" data-active-view="${model.activeView}">
          <div>
            <p class="eyebrow">${model.navigation.find(({ id }) => id === model.activeView)?.label}</p>
            <h2>${active.title}</h2>
            <p>${active.summary}</p>
          </div>
          <span class="status-badge">Scaffold</span>
        </section>

        <section class="content-grid" aria-label="Rebuild placeholders">
          <article class="content-card">
            <p class="eyebrow">Source of truth</p>
            <h3>Contract-first delivery</h3>
            <p>Pages will consume validated, gameweek-applicable contracts rather than recalculate domain values.</p>
          </article>
          <article class="content-card">
            <p class="eyebrow">Mobile baseline</p>
            <h3>Dense but calm</h3>
            <p>Wide content remains bounded, interaction targets stay usable and semantic states do not rely on colour alone.</p>
          </article>
        </section>
      </main>
    </div>
  `;
}

export function mountApp(root: HTMLElement): void {
  let activeView: ViewId = 'intel';

  const render = (): void => {
    root.innerHTML = shellMarkup(createShellModel(activeView));
    root.querySelectorAll<HTMLButtonElement>('[data-view]').forEach((button) => {
      button.addEventListener('click', () => {
        const requested = button.dataset.view ?? '';
        if (!isViewId(requested) || requested === activeView) return;
        activeView = requested;
        render();
      });
    });
  };

  render();
}
