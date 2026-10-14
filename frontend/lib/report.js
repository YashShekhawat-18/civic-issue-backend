// Rules for the "report an issue" form. They mirror the backend (title 5-150, description 10-2000,
// JPEG/PNG/WebP up to 5 MB) so the citizen gets instant feedback; the backend still re-checks everything.
export const MAX_PHOTO_MB = 5;
export const ALLOWED_PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"];

export function validatePhoto(file) {
  if (!file) return "Please add a photo of the issue";
  if (!ALLOWED_PHOTO_TYPES.includes(file.type)) return "Photo must be a JPEG, PNG or WebP image";
  if (file.size === 0) return "The photo file is empty";
  if (file.size > MAX_PHOTO_MB * 1024 * 1024) return `Photo is too large (maximum ${MAX_PHOTO_MB} MB)`;
  return null;
}

export function validateReport({ categoryId, title, description, location, photo }) {
  const errors = {};
  if (!categoryId) errors.categoryId = "Choose a category";
  const t = title.trim();
  if (t.length < 5) errors.title = "Title must be at least 5 characters";
  else if (t.length > 150) errors.title = "Title must be at most 150 characters";
  const d = description.trim();
  if (d.length < 10) errors.description = "Description must be at least 10 characters";
  else if (d.length > 2000) errors.description = "Description must be at most 2000 characters";
  if (!location) errors.location = "Pick the location on the map";
  const photoError = validatePhoto(photo);
  if (photoError) errors.photo = photoError;
  return errors;
}

// Builds the multipart body the backend expects. Field names must match the backend exactly.
export function buildReportFormData({ categoryId, title, description, location, photo, isAnonymous }) {
  const form = new FormData();
  form.append("title", title.trim());
  form.append("description", description.trim());
  form.append("categoryId", categoryId);
  form.append("latitude", String(location.lat));
  form.append("longitude", String(location.lng));
  form.append("isAnonymous", isAnonymous ? "true" : "false");
  form.append("photo", photo);
  return form;
}
