export interface RoadSceneStats { fps: number; quality: number; night: number; flow: number; time: number; active: string | null; pinned: boolean; running: boolean; calls: number; triangles: number; pixelRatio: number; width: number; height: number }
export interface RoadScene {
  stats(): RoadSceneStats;
  /** Average milliseconds to draw one frame (test helper). */
  bench(frames?: number): number;
  potholes(): { id: string; severity: string; x: number; y: number }[];
  /** Renderer objects, for profiling in tests. */
  internals: Record<string, unknown>;
  /** Selects the nearest pothole in view and keeps its panel open. False when none is in view. */
  selectNearest(): boolean;
  close(): void;
  /** Relights the scene for night (true) or day (false); the change is eased. */
  setNight(on: boolean): void;
  dispose(): void;
}
/** Builds the scene inside `host`. Throws when WebGL is unavailable. */
export function createRoadScene(host: HTMLElement, assets: string): RoadScene;
