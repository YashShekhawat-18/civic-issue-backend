"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { readPhotoGps, photoPlaceProblem, distanceMeters, formatDistance } from "@/lib/geotag";
import { validatePhoto } from "@/lib/report";
import { fieldErrorsFromApi } from "@/lib/validation";
import Alert from "./Alert";
import { btnPrimary, plate } from "@/lib/ui";

/**
 * A worker finishes a job: an after-fix photo taken at the place, plus an optional note.
 * The photo must carry GPS and be within 300 m of the complaint. The backend checks it again.
 */
export default function ResolveForm({ complaintId, spot, onResolved }) {
  const [photo, setPhoto] = useState(null);
  const [gps, setGps] = useState(undefined); // {lat,lng} | null (none) | undefined (not read yet)
  const [preview, setPreview] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const input = useRef(null);
  const previewRef = useRef("");

  async function onPhotoChange(e) {
    const file = e.target.files?.[0] || null;
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = file ? URL.createObjectURL(file) : "";
    setPhoto(file);
    setGps(undefined);
    setError("");
    setPreview(previewRef.current);
    if (!file) return;
    const found = await readPhotoGps(file);
    if (input.current?.files?.[0] === file) setGps(found);
  }

  const typeProblem = photo ? validatePhoto(photo) : "";
  const placeProblem = photo && !typeProblem && gps !== undefined ? photoPlaceProblem(gps, spot, "the reported location") : "";
  const problem = typeProblem || placeProblem;
  const metres = photo && gps ? distanceMeters(gps, spot) : null;

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    if (!photo) return setError("Add the after-fix photo first");
    if (problem) return setError(problem);
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("photo", photo);
      if (note.trim()) form.append("note", note.trim());
      const updated = await api.post(`/worker/complaints/${complaintId}/resolve`, form);
      onResolved(updated);
    } catch (err) {
      setError(fieldErrorsFromApi(err.errors).photo || err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className={`${plate} space-y-4 p-5`} aria-label="Mark as resolved">
      <div>
        <h2 className="text-lg font-bold">Mark as resolved</h2>
        <p className="mt-1 text-sm text-asphalt-soft">
          Take a photo of the finished work at the spot, with location turned on. The citizen will see it.
        </p>
      </div>

      <Alert type="error">{error}</Alert>

      <div>
        <label htmlFor="after-photo" className="mb-1.5 block text-sm font-semibold">
          After-fix photo (JPEG with location)
        </label>
        <input
          ref={input}
          id="after-photo"
          type="file"
          accept="image/jpeg"
          onChange={onPhotoChange}
          className="block w-full rounded-lg border border-dashed border-line bg-concrete/60 p-3 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-asphalt file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-white"
        />
        {preview && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={preview} alt="After-fix photo preview" className="mt-3 h-36 rounded-lg border border-line object-cover" />
        )}
        {photo && !problem && metres !== null && (
          <p className="mt-1.5 text-xs font-medium text-highway-deep" data-testid="resolve-gps-ok">
            Photo taken {formatDistance(metres)} from the reported location. Looks good.
          </p>
        )}
        {problem && (
          <p className="mt-1.5 text-xs font-medium text-flag" data-testid="resolve-photo-problem">
            {problem}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="resolve-note" className="mb-1.5 block text-sm font-semibold">
          Note for the citizen (optional)
        </label>
        <textarea
          id="resolve-note"
          rows={2}
          maxLength={500}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          className="w-full rounded-lg border border-line bg-white px-3.5 py-2.5"
          placeholder="e.g. Pothole filled with asphalt"
        />
      </div>

      <button type="submit" disabled={submitting} className={`${btnPrimary} w-full !py-3 !text-base`}>
        {submitting ? "Saving..." : "Mark as resolved"}
      </button>
    </form>
  );
}
