"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { buildReportFormData, validateReport } from "@/lib/report";
import { fieldErrorsFromApi } from "@/lib/validation";
import Alert from "@/components/Alert";
import Spinner from "@/components/Spinner";
import FormField from "@/components/FormField";
import LocationPicker from "@/components/LocationPickerLoader";
import DuplicateWarning from "@/components/DuplicateWarning";

const EMPTY = { categoryId: "", title: "", description: "", isAnonymous: false };

export default function ReportPage() {
  const [categories, setCategories] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [form, setForm] = useState(EMPTY);
  const [location, setLocation] = useState(null);
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState("");
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState(null); // the new complaint
  const [duplicate, setDuplicate] = useState(null); // duplicate payload from the backend
  const fileInput = useRef(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get("/categories")
      .then((list) => !cancelled && setCategories(list))
      .catch((err) => !cancelled && setLoadError(err.message));
    return () => {
      cancelled = true;
    };
  }, []);

  // Thumbnail of the chosen photo. The temporary browser URL is freed when the photo changes or the page closes.
  const previewRef = useRef("");
  useEffect(() => () => previewRef.current && URL.revokeObjectURL(previewRef.current), []);

  function onPhotoChange(e) {
    const file = e.target.files?.[0] || null;
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = file ? URL.createObjectURL(file) : "";
    setPhoto(file);
    setPreview(previewRef.current);
  }

  const onChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === "checkbox" ? checked : value });
  };

  async function onSubmit(e) {
    e.preventDefault();
    setServerError("");
    const found = validateReport({ ...form, location, photo });
    setErrors(found);
    if (Object.keys(found).length) return;

    setSubmitting(true);
    try {
      const data = await api.post("/complaints", buildReportFormData({ ...form, location, photo }));
      if (data?.duplicate) setDuplicate(data);
      else setCreated(data);
    } catch (err) {
      const fields = fieldErrorsFromApi(err.errors);
      // backend field names -> form field names
      setErrors({
        categoryId: fields.categoryId || fields.category_id,
        title: fields.title,
        description: fields.description,
        location: fields.latitude || fields.longitude,
        photo: fields.photo,
      });
      setServerError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  function reset() {
    setForm(EMPTY);
    setLocation(null);
    setPhoto(null);
    setPreview("");
    setErrors({});
    setCreated(null);
    setDuplicate(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  if (created) {
    return (
      <div className="mx-auto max-w-xl rounded-lg border border-green-200 bg-green-50 p-6 text-center">
        <h1 className="text-xl font-bold text-green-900">Complaint submitted</h1>
        <p className="mt-2 text-green-900">
          Your complaint number is <strong data-testid="complaint-number">{created.complaintNumber}</strong>.
        </p>
        <p className="mt-1 text-sm text-green-800">
          It was sent to the {created.department?.name || "responsible"} department. You will be notified when its status changes.
        </p>
        <div className="mt-5 flex justify-center gap-3">
          <button onClick={reset} className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700">
            Report another issue
          </button>
          <Link href="/citizen" className="rounded-md border border-slate-300 bg-white px-4 py-2 hover:bg-slate-100">
            Back to home
          </Link>
        </div>
      </div>
    );
  }

  if (duplicate) {
    return <DuplicateWarning result={duplicate} onBack={() => setDuplicate(null)} />;
  }

  if (loadError) return <Alert type="error">{loadError}</Alert>;
  if (!categories) return <Spinner />;

  return (
    <div className="mx-auto max-w-2xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="mb-1 text-2xl font-bold">Report an issue</h1>
      <p className="mb-5 text-sm text-slate-600">Add a photo, describe the problem and mark where it is.</p>

      <form onSubmit={onSubmit} noValidate className="space-y-5">
        <Alert type="error">{serverError}</Alert>

        <div>
          <label htmlFor="categoryId" className="mb-1 block text-sm font-medium text-slate-700">
            Category
          </label>
          <select
            id="categoryId"
            name="categoryId"
            value={form.categoryId}
            onChange={onChange}
            aria-invalid={errors.categoryId ? "true" : "false"}
            className={`w-full rounded-md border bg-white px-3 py-2 ${errors.categoryId ? "border-red-400" : "border-slate-300"}`}
          >
            <option value="">Select a category...</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          {errors.categoryId && <p className="mt-1 text-xs text-red-600">{errors.categoryId}</p>}
        </div>

        <FormField id="title" label="Title" value={form.title} onChange={onChange} error={errors.title} maxLength={150} hint="e.g. Large pothole near the bus stop" />

        <div>
          <label htmlFor="description" className="mb-1 block text-sm font-medium text-slate-700">
            Description
          </label>
          <textarea
            id="description"
            name="description"
            rows={4}
            value={form.description}
            onChange={onChange}
            maxLength={2000}
            aria-invalid={errors.description ? "true" : "false"}
            className={`w-full rounded-md border px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 ${errors.description ? "border-red-400" : "border-slate-300"}`}
          />
          {errors.description && <p className="mt-1 text-xs text-red-600">{errors.description}</p>}
        </div>

        <div>
          <label htmlFor="photo" className="mb-1 block text-sm font-medium text-slate-700">
            Photo (JPEG, PNG or WebP, up to 5 MB)
          </label>
          <input
            ref={fileInput}
            id="photo"
            name="photo"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={onPhotoChange}
            className="block w-full text-sm"
          />
          {preview && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt="Selected photo preview" className="mt-2 h-32 rounded-md border border-slate-200 object-cover" />
          )}
          {errors.photo && <p className="mt-1 text-xs text-red-600">{errors.photo}</p>}
        </div>

        <div>
          <p className="mb-1 text-sm font-medium text-slate-700">Location</p>
          <LocationPicker value={location} onChange={setLocation} error={errors.location} />
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name="isAnonymous" checked={form.isAnonymous} onChange={onChange} />
          Hide my name from other citizens
        </label>

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-blue-600 py-2.5 font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {submitting ? "Submitting..." : "Submit complaint"}
        </button>
      </form>
    </div>
  );
}
