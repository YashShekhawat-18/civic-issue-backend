// Reads the GPS position stored inside a JPEG photo (EXIF data). Phones write it when location is on.
// Mirrors the backend reader (app/services/geotag_service.py); the backend still checks every upload.

const TYPE_SIZES = { 1: 1, 2: 1, 3: 2, 4: 4, 5: 8 };
const GPS_POINTER_TAG = 0x8825;

function findExifBlock(view) {
  if (view.byteLength < 4 || view.getUint16(0) !== 0xffd8) return null;
  let pos = 2;
  while (pos + 4 <= view.byteLength) {
    if (view.getUint8(pos) !== 0xff) return null;
    const marker = view.getUint8(pos + 1);
    if (marker === 0xff) {
      pos += 1;
      continue;
    }
    if (marker === 0xda || marker === 0xd9) return null; // image data starts: no more headers
    const length = view.getUint16(pos + 2);
    // "Exif\0\0" = 45 78 69 66 00 00
    if (marker === 0xe1 && length >= 8 && view.getUint32(pos + 4) === 0x45786966 && view.getUint16(pos + 8) === 0) {
      return new DataView(view.buffer, view.byteOffset + pos + 10, Math.min(length - 8, view.byteLength - pos - 10));
    }
    pos += 2 + length;
  }
  return null;
}

function readIfd(tiff, little, offset) {
  const entries = {};
  const count = tiff.getUint16(offset, little);
  for (let i = 0; i < count; i++) {
    const base = offset + 2 + i * 12;
    const tag = tiff.getUint16(base, little);
    const kind = tiff.getUint16(base + 2, little);
    const n = tiff.getUint32(base + 4, little);
    const size = (TYPE_SIZES[kind] || 0) * n;
    entries[tag] = { kind, n, pos: size <= 4 ? base + 8 : tiff.getUint32(base + 8, little) };
  }
  return entries;
}

function readDegrees(tiff, little, entry) {
  if (entry.kind !== 5 || entry.n !== 3) throw new RangeError("GPS coordinate must be 3 rationals");
  const part = (i) => {
    const num = tiff.getUint32(entry.pos + i * 8, little);
    const den = tiff.getUint32(entry.pos + i * 8 + 4, little);
    return den ? num / den : 0;
  };
  return part(0) + part(1) / 60 + part(2) / 3600;
}

function readRef(tiff, entry) {
  return String.fromCharCode(tiff.getUint8(entry.pos));
}

/** {lat, lng} from the bytes of a JPEG, or null when there is no usable position. Never throws. */
export function gpsFromBytes(buffer) {
  try {
    const view = new DataView(buffer);
    const tiff = findExifBlock(view);
    if (!tiff) return null;
    const order = tiff.getUint16(0);
    const little = order === 0x4949;
    if (!little && order !== 0x4d4d) return null;
    if (tiff.getUint16(2, little) !== 42) return null;
    const ifd0 = readIfd(tiff, little, tiff.getUint32(4, little));
    if (!ifd0[GPS_POINTER_TAG]) return null;
    const gps = readIfd(tiff, little, tiff.getUint32(ifd0[GPS_POINTER_TAG].pos, little));
    if (![1, 2, 3, 4].every((t) => gps[t])) return null;
    const lat = readDegrees(tiff, little, gps[2]) * (readRef(tiff, gps[1]).toUpperCase() === "S" ? -1 : 1);
    const lng = readDegrees(tiff, little, gps[4]) * (readRef(tiff, gps[3]).toUpperCase() === "W" ? -1 : 1);
    if (!(Math.abs(lat) <= 90 && Math.abs(lng) <= 180)) return null;
    if (lat === 0 && lng === 0) return null; // "no GPS fix"
    const round = (n) => Math.round(n * 1e6) / 1e6; // about 10 cm, and no 19.186700000000002 on screen
    return { lat: round(lat), lng: round(lng) };
  } catch {
    return null;
  }
}

function readBytes(blob) {
  if (typeof blob.arrayBuffer === "function") return blob.arrayBuffer();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsArrayBuffer(blob);
  });
}

/** Reads the position from a chosen File. The header is at the start, so only the first 256 KB is read. */
export async function readPhotoGps(file) {
  if (!file) return null;
  try {
    return gpsFromBytes(await readBytes(file.slice(0, 256 * 1024)));
  } catch {
    return null;
  }
}
