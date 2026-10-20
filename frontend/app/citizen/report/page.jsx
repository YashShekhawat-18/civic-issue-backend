"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { buildReportFormData, validatePhoto, validateReport } from "@/lib/report";
import { readPhotoGps, photoPlaceProblem } from "@/lib/geotag";
import { fieldErrorsFromApi } from "@/lib/validation";
import Alert from "@/components/Alert";
import Spinner from "@/components/Spinner";
import RoadTracker from "@/components/RoadTracker";
import { IconCheck } from "@/components/icons";
import FormField from "@/components/FormField";
import LocationPicker from "@/components/LocationPickerLoader";
import DuplicateWarning from "@/components/DuplicateWarning";
import { useT } from "@/context/LanguageContext";
import { btnPrimary, btnSecondary, btnSignal, plate } from "@/lib/ui";

const EMPTY = { categoryId: "", title: "", description: "", isAnonymous: false };

export default function ReportPage() {
  const t = useT();
  const [categories, setCategories] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [form, setForm] = useState(EMPTY);
  const [location, setLocation] = useState(null);
  const [photo, setPhoto] = useState(null);
  const [photoGps, setPhotoGps] = useState(undefined); // {lat,lng} from the photo, null = none, undefined = not read yet
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

  async function onPhotoChange(e) {
    const file = e.target.files?.[0] || null;
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = file ? URL.createObjectURL(file) : "";
    setPhoto(file);
    setPhotoGps(undefined);
    setPreview(previewRef.current);
    setErrors((prev) => ({ ...prev, photo: undefined }));
    if (!file) return;
    // The photo says where it was taken: put the map pin there for the citizen.
    const gps = await readPhotoGps(file);
    if (fileInput.current?.files?.[0] !== file) return; // another photo was chosen meanwhile
    setPhotoGps(gps);
    if (gps) setLocation(gps);
  }

  // What we know about the photo's position right now (shown under the photo).
  const typeProblem = photo ? validatePhoto(photo) : "";
  const photoProblem = typeProblem || (photo && photoGps !== undefined ? photoPlaceProblem(photoGps, location, "the pinned location") : "");
  const photoFound = photo && photoGps && !photoProblem;

  const onChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === "checkbox" ? checked : value });
  };

  async function onSubmit(e) {
    e.preventDefault();
    setServerError("");
    const gps = photo && photoGps === undefined ? await readPhotoGps(photo) : photoGps;
    if (gps !== photoGps) setPhotoGps(gps);
    const found = validateReport({ ...form, location, photo, photoGps: gps });
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
    setPhotoGps(undefined);
    setPreview("");
    setErrors({});
    setCreated(null);
    setDuplicate(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  if (created) {
    return (
      <div className={`${plate} mx-auto max-w-xl p-6 text-center`}>
        <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-highway text-white">
          <IconCheck size={28} />
        </span>
        <h1 className="mt-4 text-2xl font-extrabold">{t("Complaint submitted")}</h1>
        <p className="mt-2">
          {t("Your complaint number is")} <strong data-testid="complaint-number">{created.complaintNumber}</strong>.
        </p>
        <p className="mx-auto mt-1 max-w-sm text-sm text-asphalt-soft">
          {t("It was sent to the {department} department. We will alert you when its status changes.", { department: created.department?.name || t("responsible") })}
        </p>
        <div className="mx-auto mt-6 max-w-sm px-2">
          <RoadTracker status={created.status || "SUBMITTED"} compact />
        </div>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link href={`/citizen/complaints/${created.id}`} className={btnPrimary}>
            {t("Follow this complaint")}
          </Link>
          <button onClick={reset} className={btnSecondary}>
            {t("Report another issue")}
          </button>
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
    <div className={`${plate} mx-auto max-w-2xl p-5 sm:p-7`}>
      <h1 className="mb-1 text-3xl font-extrabold">{t("Report an issue")}</h1>
      <p className="mb-6 text-asphalt-soft">{t("Add a photo, describe the problem and mark where it is.")}</p>

      <form onSubmit={onSubmit} noValidate className="space-y-5">
        <Alert type="error">{serverError}</Alert>

        <div>
          <label htmlFor="categoryId" className="mb-1.5 block text-sm font-semibold">
            {t("Category")}
          </label>
          <select
            id="categoryId"
            name="categoryId"
            value={form.categoryId}
            onChange={onChange}
            aria-invalid={errors.categoryId ? "true" : "false"}
            className={`w-full rounded-lg border bg-white px-3.5 py-2.5 ${errors.categoryId ? "border-flag" : "border-line"}`}
          >
            <option value="">{t("Select a category...")}</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {t(c.name)}
              </option>
            ))}
          </select>
          {errors.categoryId && <p className="mt-1.5 text-xs font-medium text-flag">{t(errors.categoryId)}</p>}
        </div>

        <FormField id="title" label={t("Title")} value={form.title} onChange={onChange} error={errors.title} maxLength={150} hint="e.g. Large pothole near the bus stop" />

        <div>
          <label htmlFor="description" className="mb-1.5 block text-sm font-semibold">
            {t("Description")}
          </label>
          <textarea
            id="description"
            name="description"
            rows={4}
            value={form.description}
            onChange={onChange}
            maxLength={2000}
            aria-invalid={errors.description ? "true" : "false"}
            className={`w-full rounded-lg border bg-white px-3.5 py-2.5 ${errors.description ? "border-flag" : "border-line"}`}
          />
          {errors.description && <p className="mt-1.5 text-xs font-medium text-flag">{t(errors.description)}</p>}
        </div>

        <div>
          <label htmlFor="photo" className="mb-1.5 block text-sm font-semibold">
            {t("Photo taken at the spot (JPEG with location, up to 5 MB)")}
          </label>
          <input
            ref={fileInput}
            id="photo"
            name="photo"
            type="file"
            accept="image/jpeg"
            onChange={onPhotoChange}
            className="block w-full rounded-lg border border-dashed border-line bg-concrete/60 p-3 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-asphalt file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-white"
          />
          {preview && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt={t("Selected photo preview")} className="mt-3 h-36 rounded-lg border border-line object-cover" />
          )}
          {photoFound && (
            <p className="mt-1.5 text-xs font-medium text-highway-deep" data-testid="photo-gps-ok">
              {t("Location found in the photo. The pin was set for you.")}
            </p>
          )}
          {(errors.photo || photoProblem) && (
            <p className="mt-1.5 text-xs font-medium text-flag" data-testid="photo-problem">
              {t(errors.photo || photoProblem)}
            </p>
          )}
        </div>

        <div>
          <p className="mb-1.5 text-sm font-semibold">{t("Location")}</p>
          <LocationPicker value={location} onChange={setLocation} error={errors.location && t(errors.location)} />
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name="isAnonymous" checked={form.isAnonymous} onChange={onChange} />
          {t("Hide my name from other citizens")}
        </label>

        <button
          type="submit"
          disabled={submitting}
          className={`${btnSignal} w-full !py-3 !text-base`}
        >
          {submitting ? t("Submitting...") : t("Submit complaint")}
        </button>
      </form>
    </div>
  );
}
