// Small geodesy helpers for drawn road geometry. Coordinates are [longitude, latitude] (GeoJSON order).

const EARTH_RADIUS_M = 6371008.8;

const toRad = (deg: number) => (deg * Math.PI) / 180;

/** Great-circle distance in metres between two [lon, lat] points. */
export function haversineMeters(a: number[], b: number[]): number {
  const dLat = toRad(b[1] - a[1]);
  const dLon = toRad(b[0] - a[0]);
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a[1])) * Math.cos(toRad(b[1])) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(h));
}

/** Length in metres of a line given as [lon, lat] pairs. */
export function lineLengthMeters(coordinates: number[][]): number {
  let total = 0;
  for (let i = 1; i < coordinates.length; i++) total += haversineMeters(coordinates[i - 1], coordinates[i]);
  return total;
}
