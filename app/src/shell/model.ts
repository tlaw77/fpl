export const viewIds = ['intel', 'transfer', 'team', 'strategy', 'pool'] as const;

export type ViewId = (typeof viewIds)[number];

export interface NavigationItem {
  id: ViewId;
  label: string;
}

export interface ShellModel {
  title: string;
  eyebrow: string;
  phaseLabel: string;
  gameweekLabel: string;
  freshnessLabel: string;
  activeView: ViewId;
  navigation: readonly NavigationItem[];
}

const navigation: readonly NavigationItem[] = [
  { id: 'intel', label: 'League Intel' },
  { id: 'transfer', label: 'Transfer' },
  { id: 'team', label: 'Pick Team' },
  { id: 'strategy', label: 'Squad Strategy' },
  { id: 'pool', label: 'Player Pool' },
];

export function isViewId(value: string): value is ViewId {
  return viewIds.some((id) => id === value);
}

export function createShellModel(activeView: ViewId = 'intel'): ShellModel {
  return {
    title: 'I Fought the Law',
    eyebrow: 'FPL Decision Centre',
    phaseLabel: 'Rebuild preview',
    gameweekLabel: 'GW —',
    freshnessLabel: 'Waiting for canonical contracts',
    activeView,
    navigation,
  };
}
